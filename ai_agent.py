import google.generativeai as genai
import asyncio
from database import save_order

# Lưu trữ phiên chat của từng khách hàng (Memory)
chat_sessions = {}

def get_ai_response(chat_id, user_text, menu_text):
    genai.configure(api_key="AIzaSyAiYSBkHxPE2TR7aybN-4iMLXWGoBqPfTM") # Nhớ đổi key mới!
    
    # Định nghĩa công cụ để AI gọi khi khách chốt đơn
    def create_order(items: str, total_price: int, customer_address: str, customer_phone: str) -> str:
        """
        Gọi hàm này CHỈ KHI khách hàng đã chốt đơn và cung cấp đủ: món uống (kèm size, đường, đá), tổng tiền, địa chỉ và SĐT.
        """
        order_data = {
            "houseid": "HS001", # Kế thừa cấu trúc IoT của bạn
            "chat_id": chat_id,
            "items": items,
            "total_price": total_price,
            "address": customer_address,
            "phone": customer_phone,
            "status": "pending"
        }
        
        # Kích hoạt lưu vào MongoDB
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(save_order(order_data))
        except RuntimeError:
            asyncio.run(save_order(order_data))
            
        return f"Đã ghi nhận đơn hàng {total_price}đ. Báo bếp làm món ngay!"

    # Khởi tạo model nếu user này chưa chat bao giờ
    if chat_id not in chat_sessions:
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash', # CHỈ CẦN SỬA DÒNG NÀY
            tools=[create_order],
            system_instruction=f"Bạn là cô chủ quán trà sữa. Dưới đây là Menu:\n{menu_text}\nNhiệm vụ: Chào hỏi, tư vấn món. Bắt buộc hỏi size, lượng đường, đá. Khi khách chốt, tính tổng tiền và xin địa chỉ, số điện thoại. Cuối cùng bắt buộc gọi hàm create_order để chốt."
        )
        # Bật tự động gọi hàm
        chat_sessions[chat_id] = model.start_chat(enable_automatic_function_calling=True)
    
    # Gửi tin nhắn mới vào phiên chat hiện tại
    response = chat_sessions[chat_id].send_message(user_text)
    return response.text