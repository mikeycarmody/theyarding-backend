from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.dashboard import router as dashboard_router
from app.routes.jbs_grid import router as jbs_router
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_to_mongo



app = FastAPI()

@app.on_event("startup")
def startup_db_client():
    connect_to_mongo()
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(jbs_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "The Yarding backend is running"}