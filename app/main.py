from pymongo import MongoClient
from app.config import MONGO_URI

client = None
db = None

def connect_to_mongo():
    global client, db
    client = MongoClient(MONGO_URI)
    db = client["theyarding"]

def get_db():
    return db