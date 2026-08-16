from fastapi import APIRouter
from app.database import get_db

router = APIRouter()


@router.get("/upcoming-sales")
def get_upcoming_sales():

    db = get_db()

    cursor = (
        db["upcoming_sales"]
        .find({}, {"_id": 0})
        .sort("sale_date", 1)
    )

    return list(cursor)
