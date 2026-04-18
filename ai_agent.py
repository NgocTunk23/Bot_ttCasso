import google.generativeai as genai
import asyncio
import time
import json
from database import save_order

chat_sessions = {}

def get_ai_response(chat_id, user_text, menu_text):
    # 🔴 BƯỚC 1: ĐIỀN API KEY GEMINI MỚI TẠO Ở ĐÂY
    genai.configure(api_key="AIzaSyDlSkxJHDy_4OlN1RvSby-EZEU-icI_RrU")
    
    def create_order(items: str, total_price: int, customer_address: str, customer_phone: str) -> str:
        # Tạo mã đơn bằng Timestamp
        order_code = int(time.time())
        
        # 1. Lưu DB
        order_data = {
            "order_id": order_code,
            "chat_id": chat_id,
            "items": items,
            "total": total_price,
            "address": customer_address,
            "phone": customer_phone,
            "status": "pending"
        }
        
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(save_order(order_data))
        except RuntimeError:
            asyncio.run(save_order(order_data))

        # 🔴 BƯỚC 2: CẤU HÌNH NGÂN HÀNG THẬT CỦA BẠN (ĐỂ KHÁCH QUÉT QR)
        # Tên viết tắt ngân hàng: MB, VCB, TCB, ACB, TPB...
        bank_id = "MB"  
        account_no = "123456789"  # Số tài khoản của bạn/mẹ bạn
        
        # Tạo link sinh ảnh VietQR
        qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact.png?amount={total_price}&addInfo=DonHang{order_code}"

        # Trả JSON về cho hàm xử lý của main.py
        return json.dumps({
            "is_payment": True,
            "qr_url": qr_url,
            "text": f"Dạ cô chủ lên đơn xong cho mình rồi ạ!\n\n📋 Món của mình: {items}\n💰 Tổng tiền: {total_price:,}đ.\n\nAnh/Chị quét mã QR dưới đây để thanh toán giúp em nhé!",
            "order_id": order_code
        })

    if chat_id not in chat_sessions:
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=[create_order],
            system_instruction=f"Bạn là cô chủ quán trà sữa. Dưới đây là Menu:\n{menu_text}\nNhiệm vụ: Chào hỏi, lấy thông tin món, tính tổng tiền, xin SĐT và địa chỉ. KHI ĐÃ ĐỦ THÔNG TIN, BẮT BUỘC gọi hàm create_order."
        )
        chat_sessions[chat_id] = model.start_chat(enable_automatic_function_calling=True)
    
    response = chat_sessions[chat_id].send_message(user_text)
    return response.text