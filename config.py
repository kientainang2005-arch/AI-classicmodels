# Configuration is read from environment variables (or a local .env file).
# Never hard-code credentials here. See .env.example.

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))

# SQLite database, opened read-only by backend/db.py
DB_PATH = os.getenv("DB_PATH", os.path.join(ROOT, "data", "classicmodels.db"))

# Vector store used by Vanna for RAG (rebuilt automatically if empty)
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", os.path.join(ROOT, "chroma_store"))

# Gemini: one key, or several separated by commas (used as fallback on quota errors)
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEY", "").split(",") if k.strip()]
# Models tried in order (each has its own free-tier quota)
GEMINI_MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "gemini-2.5-flash,gemini-3-flash-preview").split(",") if m.strip()]
GEMINI_MODEL = GEMINI_MODELS[0]

if not GEMINI_KEYS:
    raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in.")

# Tables the AI is allowed to query
ALLOWED_TABLES = {
    "customers", "orders", "orderdetails", "products",
    "productlines", "employees", "offices", "payments",
}
