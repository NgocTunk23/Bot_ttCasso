from motor.motor_asyncio import AsyncIOMotorClient
import os

# Lấy URL từ môi trường
raw_url = os.getenv("MONGO_URL", "mongodb://db:27017")

client = AsyncIOMotorClient(raw_url)
db = client.tra_sua_db

async def save_order(order_data):
    await db.orders.insert_one(order_data)

async def update_order_status(order_id: int, status: str):
    result = await db.orders.update_one({"order_id": order_id}, {"$set": {"status": status}})
    if result.modified_count > 0:
        print(f"✅ Đã cập nhật đơn {order_id} thành {status}")
    else:
        print(f"⚠️ Không tìm thấy đơn {order_id} trong Database để cập nhật!")

async def ping_db():
    try:
        # Gửi lệnh ping lên server MongoDB Atlas
        await client.admin.command('ping')
        print("✅ KẾT NỐI MONGODB ATLAS THÀNH CÔNG!")
    except Exception as e:
        print("❌ LỖI KẾT NỐI MONGODB:", e)