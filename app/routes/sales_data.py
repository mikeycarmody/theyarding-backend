from fastapi import APIRouter, Query
from app.database import get_db
from datetime import datetime, timedelta, timezone

router = APIRouter()


@router.get("/sales-data")
def get_sales_data(
    saleyard_name: str | None = None,
    sex: str | None = None,
    breed: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=25000, ge=1, le=25000),
):
    db = get_db()

    cutoff_date = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).date().isoformat()

    query = {
        "sale_date": {
            "$gte": cutoff_date
        }
    }

    if saleyard_name:
        query["saleyard_name"] = saleyard_name

    if sex:
        query["sex"] = sex.upper()

    if breed:
        query["breed"] = breed.upper()

    cursor = (
        db["sales_data"]
        .find(query, {"_id": 0})
        .sort("sale_date", -1)
        .limit(limit)
    )

    return list(cursor)