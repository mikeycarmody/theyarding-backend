from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.dashboard import router as dashboard_router

app = FastAPI()

app.include_router(health_router)
app.include_router(dashboard_router)

@app.get("/")
def root():
    return {"message": "The Yarding backend is running"}