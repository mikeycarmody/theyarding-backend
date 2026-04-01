from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
def get_dashboard():
    return {
        "total_animals": 0,
        "average_weight": 0,
        "average_value": 0
    }