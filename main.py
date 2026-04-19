from fastapi import FastAPI, Request, BackgroundTasks
import httpx
import json
import csv
from ai_agent import get_ai_response
from database import update_order_status, ping_db, get_order, save_order, calculate_revenue

app = FastAPI()
@app.on_event("startup")
async def startup_db_client(): await ping_db()

TELEGRAM_TOKEN = "8079622074:AAEBJDogcM767t4kr4UGkjLYZAWghp1R0M0"
KITCHEN_GROUP_ID = -1003636305886

def load_menu():
    menu_str = ""
    try:
        with open("Menu.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["available"].lower() == "true":
                    menu_str += f"- {row['name']}: {row['price_m']}đ/{row['price_l']}đ\n"
    except: pass
    return menu_str

MENU_TEXT = load_menu()

async def send_tg(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup: payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client: await client.post(url, json=payload)

async def notify_kitchen(order_id, method):
    order = await get_order(order_id)
    if not order: return
    msg = (f"🚀 ĐƠN HÀNG MỚI (#{order_id})\n"
           f"⏰ Lúc: {order['created_at'].strftime('%H:%M %d/%m')}\n"
           f"💰 Tổng: {order['total']:,}đ ({method})\n"
           f"📋 Món: {order['items']}\n"
           f"📍 ĐC: {order['address']} - {order['phone']}")
    await send_tg(KITCHEN_GROUP_ID, msg)

@app.post("/webhook")
async def handle_webhook(request: Request, bg: BackgroundTasks):
    data = await request.json()
    
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id, cb_data = cb["message"]["chat"]["id"], cb["data"]
        order_id = int(cb_data.split("_")[-1])
        
        if "ck" in cb_data:
            bg.add_task(send_tg, chat_id, "✅ Đã báo bếp. Mẹ em đang làm món ạ! Nhớ đưa cho mình ảnh chuyển khoản khi nhận hàng để mình check nhé!")
            bg.add_task(update_order_status, order_id, "paid_transfer")
            bg.add_task(notify_kitchen, order_id, "Chuyển khoản")
        else:
            bg.add_task(send_tg, chat_id, "✅ Đã báo bếp.")
            bg.add_task(update_order_status, order_id, "paid_cash")
            bg.add_task(notify_kitchen, order_id, "Tiền mặt")
        return {"ok": True}

    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id, text = msg["chat"]["id"], msg["text"]

        # Lệnh xem doanh thu cho bếp
        if text.startswith("/doanhthu") and chat_id == KITCHEN_GROUP_ID:
            period = text.split(" ")[1] if " " in text else "today"
            rev = await calculate_revenue(period)
            report = (f"📊 BÁO CÁO DOANH THU ({period})\n"
                      f"💳 CK: {rev['transfer']['sum']:,}đ ({rev['transfer']['count']} đơn)\n"
                      f"💵 Tiền mặt: {rev['cash']['sum']:,}đ ({rev['cash']['count']} đơn)\n"
                      f"🔥 Tổng: {rev['transfer']['sum'] + rev['cash']['sum']:,}đ")
            await send_tg(chat_id, report)
            return {"ok": True}

        ai_reply = get_ai_response(chat_id, text, MENU_TEXT)
        try:
            res = json.loads(ai_reply)
            if res.get("is_payment"):
                order_data = {"order_id": res["order_id"], "chat_id": chat_id, "items": res["items"], 
                              "total": res["total"], "address": res["address"], "phone": res["phone"], "status": "pending"}
                await save_order(order_data)
                
                markup = {"inline_keyboard": [[{"text": "✅ Đã chuyển khoản", "callback_data": f"paid_ck_{res['order_id']}"}],
                                              [{"text": "💵 Tiền mặt", "callback_data": f"paid_cash_{res['order_id']}"}]]}
                url_photo = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
                async with httpx.AsyncClient() as c:
                    await c.post(url_photo, json={"chat_id": chat_id, "photo": res["qr_url"], "caption": res["text"], "reply_markup": markup})
            else: await send_tg(chat_id, ai_reply)
        except: await send_tg(chat_id, ai_reply)
    return {"ok": True}