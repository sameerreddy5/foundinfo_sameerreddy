import os
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017") # Placeholder
DB_NAME = "leakosint_bot"

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            self.users = self.db["users"]
            self.admins = self.db["admins"]
            self.blacklist = self.db["blacklist"]
            self.settings = self.db["settings"]
            
            # Ensure primary admin exists
            self.add_admin(5892468047, "flashman66")
            
            # Ensure default settings
            if not self.settings.find_one({"key": "starting_credits"}):
                self.settings.insert_one({"key": "starting_credits", "value": 5})
            
            logger.info("Connected to MongoDB successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")

    # --- User Management ---
    def register_user(self, user_id, first_name, username):
        # Check if user already exists
        user = self.users.find_one({"user_id": user_id})
        if not user:
            starting_credits = self.get_starting_credits()
            user_data = {
                "user_id": user_id,
                "first_name": first_name,
                "username": username,
                "credits": starting_credits
            }
            self.users.insert_one(user_data)
        else:
            # If user exists but has no credits field, add them
            if "credits" not in user:
                starting_credits = self.get_starting_credits()
                self.users.update_one({"user_id": user_id}, {"$set": {"credits": starting_credits}})
            self.users.update_one({"user_id": user_id}, {"$set": {"first_name": first_name, "username": username}})

    def get_users_count(self):
        return self.users.count_documents({})

    def get_all_user_ids(self):
        return [user["user_id"] for user in self.users.find({}, {"user_id": 1})]

    # --- Admin Management ---
    def add_admin(self, user_id, username):
        admin_data = {
            "user_id": user_id,
            "username": username
        }
        self.admins.update_one({"user_id": user_id}, {"$set": admin_data}, upsert=True)

    def remove_admin(self, user_id):
        self.admins.delete_one({"user_id": user_id})

    def is_admin(self, user_id):
        # Always allow ID 5892468047
        if user_id == 5892468047:
            return True
        return self.admins.find_one({"user_id": user_id}) is not None

    def get_all_admins(self):
        return list(self.admins.find({}))

    # --- Blacklist Management ---
    def add_to_blacklist(self, value):
        self.blacklist.update_one({"value": value}, {"$set": {"value": value}}, upsert=True)

    def remove_from_blacklist(self, value):
        self.blacklist.delete_one({"value": value})

    def is_blacklisted(self, query):
        # Clean query for checking
        query = query.strip().lower()
        # Check if the query contains any blacklisted item
        # Or if the query itself is blacklisted
        # For simplicity, we check for exact matches or inclusion
        return self.blacklist.find_one({"value": query}) is not None

    def get_blacklist(self):
        return list(self.blacklist.find({}))

    # --- Credit Management ---
    def get_user_credits(self, user_id):
        user = self.users.find_one({"user_id": user_id})
        return user.get("credits", 0) if user else 0

    def add_credits(self, user_id, amount):
        self.users.update_one({"user_id": user_id}, {"$inc": {"credits": amount}})

    def deduct_credit(self, user_id):
        self.users.update_one({"user_id": user_id}, {"$inc": {"credits": -1}})

    def bulk_add_credits(self, amount):
        self.users.update_many({}, {"$inc": {"credits": amount}})

    def set_starting_credits(self, amount):
        self.settings.update_one({"key": "starting_credits"}, {"$set": {"value": amount}}, upsert=True)

    def get_starting_credits(self):
        setting = self.settings.find_one({"key": "starting_credits"})
        return setting["value"] if setting else 5

db = Database()
