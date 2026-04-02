from dotenv import load_dotenv
import os

load_dotenv("production/.env")
print("DATABASE_URL:", os.environ.get("DATABASE_URL", "NOT FOUND"))
print("GEMINI_API_KEY:", os.environ.get("GEMINI_API_KEY", "NOT FOUND")[:20])
