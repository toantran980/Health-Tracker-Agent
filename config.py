import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Server Settings
PORT = int(os.getenv("PORT", "5001"))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# MongoDB Settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "health_tracker")
MONGO_CONNECT_RETRIES = int(os.getenv("MONGO_CONNECT_RETRIES", "5"))
MONGO_CONNECT_RETRY_DELAY = float(os.getenv("MONGO_CONNECT_RETRY_DELAY", "2"))

# API Keys
USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
EXERCISEDB_API_KEY = os.getenv("EXERCISEDB_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
