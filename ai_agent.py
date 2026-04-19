import google.generativeai as genai
import asyncio
import time
import json
from database import save_order
from payos import PayOS

# Cấu hình PayOS
payos = PayOS(
    client_id="4817b69c-7e10-4624-b2c1-173ed3f54f8a", 
    api_key="d3e44a8b-2888-43d2-a2a5-cb351e742f73", 
    checksum_key="5b638b343946ee1525bec61e18ebaf864410989479392f63c22c7bc7648891af"
)

chat_sessions = {}

def get_ai_response(chat_id, user_text, menu_text):
    genai.configure(api_key="AIzaSyD9hncdWSuD2tkaye9OXrcOXcKqt6vZfFg")
    
    def create_order(items: str, total_price: int, customer_address: str, customer_phone: str) -> str:
        order_code = int(time.time()) # Mã đơn hàng duy nhất dựa trên thời gian
        
        # --- BƯỚC 1: LƯU ĐƠN VÀO DATABASE (QUAN TRỌNG) ---
        order_data = {
            "order_id": order_code,
            "chat_id": chat_id,
            "items": items,
            "total": total_price,
            "address": customer_address,
            "phone": customer_phone,
            "status": "pending" # Trạng thái chờ thanh toán
        }
        
        try:
            # Chạy lưu DB trong nền để không làm nghẽn AI
            loop = asyncio.get_running_loop()
            loop.create_task(save_order(order_data))
        except RuntimeError:
            asyncio.run(save_order(order_data))
        
        # --- BƯỚC 2: TẠO LINK THANH TOÁN QUA API PAYOS ---
        try:
            payment_data = {
                "orderCode": order_code,
                "amount": total_price,
                "description": f"DonHang{order_code}",
                "cancelUrl": "https://your-website.com/cancel",
                "returnUrl": "https://your-website.com/success"
            }
            # Gọi API PayOS để sinh QR xịn
            payment_link_res = payos.createPaymentLink(payment_data)
            qr_url = payment_link_res.qrCode 
        except Exception as e:
            print(f"Lỗi gọi API PayOS: {e}")
            # Dự phòng nếu API lỗi thì dùng VietQR tĩnh
            qr_url = f"https://img.vietqr.io/image/BIDV-7011068444-compact.png?amount={total_price}&addInfo=DonHang{order_code}"

        return json.dumps({
            "is_payment": True,
            "qr_url": qr_url,
            "text": f"Dạ cô chủ lên đơn xong cho mình rồi ạ!\n\n📋 Món của mình: {items}\n💰 Tổng tiền: {total_price:,}đ.\n\nAnh/Chị quét mã QR dưới đây để thanh toán giúp em nhé!",
            "order_id": order_code
        })

    if chat_id not in chat_sessions:
        # Giữ nguyên phần sys_instruct cực kỳ chi tiết của bạn
        sys_instruct = (
            f"Bạn là cô chủ quán trà sữa. Dưới đây là Menu DUY NHẤT của quán:\n{menu_text}\n\n"
            "QUY TẮC NGHIÊM NGẶT:\n"
            "0. Khi giới thiệu món không được ghép các món rồi để giá theo khoảng... \n"
            "1. CHỈ BÁN các món và topping có mặt trong Menu trên. \n"
            "2. Nếu khách yêu cầu món KHÔNG CÓ TRONG MENU... bạn phải TỪ CHỐI lịch sự.\n"
            "3. Nhiệm vụ: Chào hỏi và đưa menu, lấy thông tin món, tính tổng tiền, xin SĐT và địa chỉ giao hàng, gửi QR thanh toán.\n"
            "4. KHI ĐÃ ĐỦ THÔNG TIN, BẮT BUỘC gọi hàm create_order."
        )
        
        model = genai.GenerativeModel(
            model_name='gemini-flash-latest',
            tools=[create_order],
            system_instruction=sys_instruct,
            generation_config={"temperature": 0.2}
        )
        chat_sessions[chat_id] = model.start_chat(enable_automatic_function_calling=True)
    
    response = chat_sessions[chat_id].send_message(user_text)
    return response.text