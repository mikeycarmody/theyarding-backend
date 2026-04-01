from fastapi import APIRouter
from app.database import get_db

router = APIRouter()

@router.get("/sales-data")
def get_sales_data():
    db = get_db()
    return list(db["sales_data"].find({}, {"_id": 0}))