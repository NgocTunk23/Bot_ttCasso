from fastapi import FastAPI, Request
import httpx
from ai_agent import setup_ai

app = FastAPI()
TELEGRAM_TOKEN = "8667624909:AAEfRknh7Yueon-vmP-MlRqzoXzeLo3YFhY"

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        
        # Gọi AI xử lý
        ai_response = call_gemini_logic(user_text) # Hàm giả định gọi từ ai_agent.py
        
        # Gửi lại Telegram
        await send_message(chat_id, ai_response)
    return {"status": "ok"}

async def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})