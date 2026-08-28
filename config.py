import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "111")
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://Sophie:0000@cluster0.e9c4kuq.mongodb.net/?appName=Cluster0")
    MONGO_DBNAME = os.environ.get("MONGO_DBNAME", "equallink")
    PER_PAGE = 5  # rows shown per page in opportunity / application tables
