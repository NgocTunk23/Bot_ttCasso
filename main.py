from fastapi import FastAPI, Request, BackgroundTasks
import httpx
import json
import csv
import re
from ai_agent import get_ai_response
from database import update_order_status, client, ping_db

app = FastAPI()
@app.on_event("startup")
async def startup_db_client():
    await ping_db()

# THÔNG TIN TELEGRAM
TELEGRAM_TOKEN = "8079622074:AAEBJDogcM767t4kr4UGkjLYZAWghp1R0M0"
KITCHEN_GROUP_ID = -1003636305886

def load_menu():
    menu_str = "MENU QUÁN:\n"
    try:
        with open("Menu.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["available"].lower() == "true":
                    menu_str += f"- {row['name']}: Size M {row['price_m']}đ, Size L {row['price_l']}đ. Topping: {row['description']}\n"
    except Exception as e:
        print("Lỗi đọc menu:", e)
    return menu_str

MENU_TEXT = load_menu()

async def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client: # Tăng lên 30s cho chắc
            await client.post(url, json={"chat_id": chat_id, "text": text})
    except httpx.ConnectTimeout:
        print(f"❌ LỖI: Không thể kết nối tới Telegram (Timeout) khi gửi tới {chat_id}")

async def send_photo_with_button(chat_id, photo_url, caption, order_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "✅ Em đã chuyển khoản rồi ạ", "callback_data": f"paid_{order_id}"}
            ]]
        }
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(url, json=payload)
    except httpx.ConnectTimeout:
        print(f"❌ LỖI: Timeout khi gửi ảnh QR tới {chat_id}")

# --- XỬ LÝ TIN NHẮN TELEGRAM ---
async def process_telegram_message(chat_id, user_text):
    ai_reply = get_ai_response(chat_id, user_text, MENU_TEXT)
    try:
        reply_data = json.loads(ai_reply)
        if reply_data.get("is_payment"):
            await send_photo_with_button(chat_id, reply_data["qr_url"], reply_data["text"], reply_data["order_id"])
    except:
        await send_message(chat_id, ai_reply)

@app.post("/webhook")
async def handle_telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        callback_data = cb["data"]
        if callback_data.startswith("paid_"):
            order_id = int(callback_data.split("_")[1])
            background_tasks.add_task(send_message, chat_id, "✅ Dạ cô chủ đã nhận thông báo. Mẹ em đang làm món rồi nha!")
            background_tasks.add_task(update_order_status, order_id, "paid")
        return {"status": "ok"}
    if "message" in data and "text" in data["message"]:
        background_tasks.add_task(process_telegram_message, data["message"]["chat"]["id"], data["message"]["text"])
    return {"status": "ok"}

# --- XỬ LÝ WEBHOOK PAYOS (TIỀN VÀO TỰ ĐỘNG) ---
@app.post("/payos-webhook")
async def handle_payos_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        print("\n" + "="*50)
        print("🔔 CÓ TÍN HIỆU TỪ PAYOS TRUYỀN VỀ CỔNG /payos-webhook")
        print("📦 Dữ liệu thô:", json.dumps(payload, ensure_ascii=False))
        
        # Kiểm tra code thành công của PayOS
        if str(payload.get("code")) == "00" or payload.get("success") == True:
            data = payload.get("data", {})
            desc = data.get("description", "").upper()
            amount = data.get("amount", 0)
            
            print(f"🔍 Đang tìm mã đơn trong nội dung chuyển khoản: '{desc}'")
            
            # Lớp 1: Tìm trong nội dung chuyển khoản (Description)
            match = re.search(r'DONHANG(\d+)', desc)
            order_id = None
            
            if match:
                order_id = int(match.group(1))
            elif data.get("orderCode"):
                # Lớp 2: Nếu không thấy trong nội dung, lấy thẳng từ orderCode của PayOS
                order_id = data.get("orderCode")
            
            # Trong file main.py, phần xử lý payos-webhook
            if order_id:
                order_id = int(order_id) # ÉP CHẶT KIỂU SỐ NGUYÊN ĐỂ KHỚP VỚI DATABASE
                print(f"✅ TÌM THẤY MÃ ĐƠN: {order_id}. Đang báo Telegram...")
                
                # 1. Cập nhật DB
                background_tasks.add_task(update_order_status, order_id, "paid")
                
                # 2. Báo cho Bếp
                thong_bao = f"🚀 TING TING TIỀN VÀO!\n\nMã đơn: #{order_id}\nSố tiền: {amount:,}đ\nNội dung: {desc}\n\nMẹ làm món ngay nhé!"
                background_tasks.add_task(send_message, KITCHEN_GROUP_ID, thong_bao)
                print("✅ Đã đẩy lệnh gửi tin nhắn Telegram vào Background!")
            else:
                print("⚠️ LỖI: Không tìm thấy chữ 'DONHANG' kèm số trong nội dung chuyển khoản!")
        else:
            print(f"⚠️ LỖI: PayOS báo giao dịch thất bại hoặc định dạng lạ. Code: {payload.get('code')}")
            
        print("="*50 + "\n")
        return {"error": 0, "message": "Ok", "success": True}
        
    except Exception as e:
        print("❌ Lỗi sập Webhook PayOS:", e)
        return {"error": 1, "message": str(e), "success": False}