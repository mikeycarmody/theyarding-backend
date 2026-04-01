from fastapi import APIRouter
from app.database import get_db

router = APIRouter()

@router.get("/jbs-grid")
def get_jbs_grid():
    db = get_db()
    return list(db["jbs_grid"].find({}, {"_id": 0}))