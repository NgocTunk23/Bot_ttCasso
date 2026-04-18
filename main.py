from fastapi import FastAPI, Request, BackgroundTasks
import httpx
import json
import csv
from ai_agent import get_ai_response
from database import update_order_status

app = FastAPI()

# 🔴 BƯỚC 3: ĐIỀN THÔNG TIN TELEGRAM
TELEGRAM_TOKEN = "8079622074:AAEBJDogcM767t4kr4UGkjLYZAWghp1R0M0"
KITCHEN_GROUP_ID = -5237546308  # Điền ID Group của Bếp (Ví dụ: -100xxx)

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
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})

async def send_photo_with_button(chat_id, photo_url, caption, order_id):
    """Gửi ảnh QR kèm nút bấm xác nhận"""
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
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def process_telegram_message(chat_id, user_text):
    ai_reply = get_ai_response(chat_id, user_text, MENU_TEXT)
    
    try:
        # Nếu AI trả về JSON (khi chốt đơn gọi QR)
        reply_data = json.loads(ai_reply)
        if reply_data.get("is_payment"):
            await send_photo_with_button(chat_id, reply_data["qr_url"], reply_data["text"], reply_data["order_id"])
    except json.JSONDecodeError:
        # Nếu AI trả về Text bình thường (Đang tư vấn)
        await send_message(chat_id, ai_reply)

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    # --- LUỒNG 1: KHÁCH BẤM NÚT "ĐÃ CHUYỂN KHOẢN" ---
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        callback_data = cb["data"]
        
        if callback_data.startswith("paid_"):
            order_id = int(callback_data.split("_")[1])
            
            # Trả lời khách
            background_tasks.add_task(send_message, chat_id, "✅ Dạ cô chủ đã nhận được thông báo. Mẹ em đang làm món ngay cho mình rồi nha!")
            
            # Thông báo vào Group của Bếp (Mẹ)
            thong_bao_bep = f"🚀 TING TING ĐƠN MỚI!\n\nMã đơn: #{order_id}\nTrạng thái: Khách đã báo chuyển khoản.\n\nMẹ check app ngân hàng và bắt đầu làm món nhé!"
            background_tasks.add_task(send_message, KITCHEN_GROUP_ID, thong_bao_bep)
            
            # Lưu CSDL trạng thái Paid
            background_tasks.add_task(update_order_status, order_id, "paid")
            
        return {"status": "ok"}

    # --- LUỒNG 2: KHÁCH NHẮN TIN BÌNH THƯỜNG ---
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        background_tasks.add_task(process_telegram_message, chat_id, user_text)

    return {"status": "ok"}