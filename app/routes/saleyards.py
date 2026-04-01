from fastapi import APIRouter
from app.database import get_db

router = APIRouter()

@router.get("/saleyards")
def get_saleyards():
    db = get_db()
    return list(db["saleyards"].find({}, {"_id": 0}))