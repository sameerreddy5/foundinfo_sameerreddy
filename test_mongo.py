import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")

def test_mongo():
    print(f"Testing MongoDB connection to {MONGO_URI.split('@')[-1]}...") # Don't print password
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        print("MongoDB connection successful!")
        
        db = client["leakosint_bot"]
        print(f"Accessing database: {db.name}")
        
    except Exception as e:
        print(f"MongoDB connection failed: {e}")

if __name__ == "__main__":
    test_mongo()
