from motor.motor_asyncio import AsyncIOMotorClient
import os
# Nó sẽ ưu tiên lấy từ mây, nếu không có mới dùng local
MONGO_URL = os.getenv("MONGO_URL", "mongodb://db:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.tra_sua_db

async def save_order(order_data):
    await db.orders.insert_one(order_data)

async def update_order_status(order_id: int, status: str):
    """Cập nhật trạng thái đơn hàng"""
    await db.orders.update_one({"order_id": order_id}, {"$set": {"status": status}})