from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

quiz_collection = db["quizzes"]
rank_collection = db["rankings"]
