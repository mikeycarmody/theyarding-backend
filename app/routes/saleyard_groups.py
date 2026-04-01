from fastapi import APIRouter
from app.database import get_db

router = APIRouter()

@router.get("/saleyard-groups")
def get_saleyard_groups():
    db = get_db()
    return list(db["saleyard_groups"].find({}, {"_id": 0}))