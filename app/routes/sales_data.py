from fastapi import APIRouter, Query
from app.database import get_db

router = APIRouter()

@router.get("/sales-data")
def get_sales_data(
    saleyard_name: str | None = None,
    sale_date_from: str | None = None,
    sale_date_to: str | None = None,
    sex: str | None = None,
    breed: str | None = None,
    limit: int = Query(default=1000, ge=1, le=5000),
):
    db = get_db()

    query = {}

    if saleyard_name:
        query["saleyard_name"] = saleyard_name

    if sale_date_from or sale_date_to:
        query["sale_date"] = {}

        if sale_date_from:
            query["sale_date"]["$gte"] = sale_date_from

        if sale_date_to:
            query["sale_date"]["$lte"] = sale_date_to

    if sex:
        query["sex"] = sex

    if breed:
        query["breed"] = breed

    cursor = (
        db["sales_data"]
        .find(query, {"_id": 0})
        .limit(limit)
    )

    return list(cursor)