from fastapi import APIRouter

router = APIRouter()

@router.get("/jbs-grid")
def get_jbs_grid():
    return [
        {
            "week": 14,
            "date": "5/04/2025",
            "weight": "240-420",
            "dentition": "0-4",
            "butt": "A-C",
            "fat": "5-22mm",
            "brooklyn": "$7.00",
            "scone": "$60.90"
        },
        {
            "week": 15,
            "date": "12/04/2025",
            "weight": "240-420",
            "dentition": "0-4",
            "butt": "A-C",
            "fat": "5-22mm",
            "brooklyn": "$7.00",
            "scone": "$6.90"
        },
        {
            "week": 25,
            "date": "21/06/2025",
            "weight": "240-420",
            "dentition": "0-4",
            "butt": "A-C",
            "fat": "5-22mm",
            "brooklyn": "$7.20",
            "scone": "$7.10"
        },
        {
            "week": 26,
            "date": "28/06/2025",
            "weight": "240-420",
            "dentition": "0-4",
            "butt": "A-C",
            "fat": "5-22mm",
            "brooklyn": "$7.20",
            "scone": "$7.10"
        }
    ]