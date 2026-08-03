from fastapi import APIRouter, Query
from app.database import get_db
from datetime import datetime, timedelta, timezone

router = APIRouter()


@router.get("/sales-data")
def get_sales_data(
    saleyard_name: str | None = None,
    sale_date_from: str | None = None,
    sale_date_to: str | None = None,
    sex: str | None = None,
    breed: str | None = None,
    days: int | None = Query(default=None, ge=1, le=365),
    limit: int = Query(default=25000, ge=1, le=25000),
):
    db = get_db()

    query = {}

    # Optional shortcut: ?days=90
    if days is not None:
        cutoff_date = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).date().isoformat()

        query["sale_date"] = {
            "$gte": cutoff_date
        }

    # Explicit date range overrides/extends date filtering
    if sale_date_from or sale_date_to:

        query["sale_date"] = {}

        if sale_date_from:
            query["sale_date"]["$gte"] = sale_date_from

        if sale_date_to:
            query["sale_date"]["$lte"] = sale_date_to

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