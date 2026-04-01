from pymongo import MongoClient
from app.config import MONGO_URI

client = None
db = None

def connect_to_mongo():
    global client, db
    if not MONGO_URI:
        print("No MONGO_URI provided")
        return

    client = MongoClient(MONGO_URI)
    db = client["theyarding"]

    try:
        client.admin.command("ping")
        print("MongoDB connected successfully")
    except Exception as e:
        print("MongoDB connection failed:", e)

def get_db():
    return db