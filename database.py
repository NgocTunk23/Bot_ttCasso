from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timedelta

raw_url = os.getenv("MONGO_URL", "mongodb://db:27017")
client = AsyncIOMotorClient(raw_url)
db = client.tra_sua_db

async def save_order(order_data):
    # Thêm thời gian đặt hàng vào dữ liệu
    order_data["created_at"] = datetime.now()
    await db.orders.insert_one(order_data)

async def update_order_status(order_id: int, status: str):
    await db.orders.update_one({"order_id": order_id}, {"$set": {"status": status}})

async def get_order(order_id: int):
    return await db.orders.find_one({"order_id": order_id})

async def ping_db():
    try:
        await client.admin.command('ping')
        print("✅ KẾT NỐI MONGODB THÀNH CÔNG!")
    except Exception as e:
        print("❌ LỖI KẾT NỐI MONGODB:", e)

async def calculate_revenue(period: str):
    """
    Tính doanh thu theo: 'today', 'month', 'year'
    """
    now = datetime.now()
    if period == "today":
        start_date = datetime(now.year, now.month, now.day)
    elif period == "month":
        start_date = datetime(now.year, now.month, 1)
    elif period == "year":
        start_date = datetime(now.year, 1, 1)
    else:
        return None

    pipeline = [
        {"$match": {
            "created_at": {"$gte": start_date},
            "status": {"$in": ["paid_transfer", "paid_cash"]}
        }},
        {"$group": {
            "_id": "$status",
            "total_amount": {"$sum": "$total"},
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.orders.aggregate(pipeline).to_list(length=10)
    
    report = {"transfer": {"sum": 0, "count": 0}, "cash": {"sum": 0, "count": 0}}
    for res in results:
        if res["_id"] == "paid_transfer":
            report["transfer"] = {"sum": res["total_amount"], "count": res["count"]}
        else:
            report["cash"] = {"sum": res["total_amount"], "count": res["count"]}
            
    return report