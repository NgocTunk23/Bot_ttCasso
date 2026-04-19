import google.generativeai as genai
import time
import json

chat_sessions = {}

def get_ai_response(chat_id, user_text, menu_text):
    genai.configure(api_key="AIzaSyB92aWetyG38NxKE9MySj8SFjReABF2YFY")
    
    def create_order(items: str, total_price: int, customer_address: str, customer_phone: str) -> str:
        order_code = int(time.time())
        qr_url = f"https://img.vietqr.io/image/BIDV-7011068444-compact.png?amount={total_price}&addInfo=DonHang{order_code}"

        return json.dumps({
            "is_payment": True,
            "qr_url": qr_url,
            "text": f"Dạ cô chủ lên đơn xong rồi ạ!\n\n📋 Món: {items}\n💰 Tổng: {total_price:,}đ.\n\nAnh/Chị chọn hình thức thanh toán bên dưới nhé!",
            "order_id": order_code,
            "items": items,
            "total": total_price,
            "address": customer_address,
            "phone": customer_phone
        })

    if chat_id not in chat_sessions:
        sys_instruct = (
            f"Bạn là cô chủ quán trà sữa. Dưới đây là Menu DUY NHẤT của quán:\n{menu_text}\n\n"
            "QUY TẮC NGHIÊM NGẶT:\n"
            "0. Khi giới thiệu món không được ghép các món rồi để giá theo khoảng... \n"
            "1. CHỈ BÁN các món và topping có mặt trong Menu trên. \n"
            "2. Nếu khách yêu cầu món KHÔNG CÓ TRONG MENU... bạn phải TỪ CHỐI lịch sự.\n"
            "3. Nhiệm vụ: Chào hỏi và đưa menu, lấy thông tin món, tính tổng tiền, xin SĐT và địa chỉ giao hàng, xác nhận đơn hàng bằng cách bấm vào phương thức thanh toán, đưa qr khi thanh toán online.\n"
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