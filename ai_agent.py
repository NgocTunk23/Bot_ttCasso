import google.generativeai as genai

def setup_ai(menu_text):
    genai.configure(api_key="AIzaSyAiYSBkHxPE2TR7aybN-4iMLXWGoBqPfTM")
    
    # Định nghĩa công cụ để AI gọi khi khách chốt đơn
    def create_order(items, total_price, customer_info):
        """Hàm này sẽ được AI gọi khi khách xác nhận đặt hàng"""
        # Logic lưu vào DB hoặc gửi tin nhắn cho mẹ bạn
        return f"Đã ghi nhận đơn hàng {total_price}đ"

    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        tools=[create_order],
        system_instruction=f"Bạn là trợ lý ảo của quán trà sữa. Menu: {menu_text}. Hãy thân thiện, tư vấn món và dùng công cụ create_order khi khách chốt đơn."
    )
    return model