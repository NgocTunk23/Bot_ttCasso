from fastapi import FastAPI, Request, BackgroundTasks
import httpx
import csv
from ai_agent import get_ai_response

app = FastAPI()
TELEGRAM_TOKEN = "8667624909:AAEfRknh7Yueon-vmP-MlRqzoXzeLo3YFhY" # Nhớ đổi key mới!

# Đọc file Menu.csv
def load_menu():
    menu_str = "MENU QUÁN:\n"
    try:
        with open("Menu.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["available"].lower() == "true":
                    menu_str += f"- {row['name']} ({row['category']}): Size M {row['price_m']}đ, Size L {row['price_l']}đ. Topping: {row['description']}\n"
    except Exception as e:
        print("Lỗi đọc menu:", e)
    return menu_str

MENU_TEXT = load_menu()

async def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})

async def process_telegram_message(chat_id, user_text):
    # Gọi AI xử lý tin nhắn
    ai_reply = get_ai_response(chat_id, user_text, MENU_TEXT)
    # Gửi lại Telegram
    await send_message(chat_id, ai_reply)

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        
        # Đưa vào task chạy ngầm để trả về 200 OK cho Telegram ngay lập tức
        background_tasks.add_task(process_telegram_message, chat_id, user_text)
        
    return {"status": "ok"}