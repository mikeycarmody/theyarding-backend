import csv
from pymongo import MongoClient
from app.config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["theyarding"]

def load_csv(file_path):
    with open(file_path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def import_collection(file_path, collection_name):
    data = load_csv(file_path)

    if not data:
        print(f"No data found in {file_path}")
        return

    db[collection_name].delete_many({})
    db[collection_name].insert_many(data)
    print(f"Imported {len(data)} records into {collection_name}")

if __name__ == "__main__":
    import_collection("/home/mikey/Downloads/SaleData_export.csv", "sales_data")
    import_collection("/home/mikey/Downloads/Saleyard_export.csv", "saleyards")
    import_collection("/home/mikey/Downloads/SaleyardGroup_export.csv", "saleyard_groups")