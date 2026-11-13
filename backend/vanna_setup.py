# Vanna (RAG for text-to-SQL) + Gemini + ChromaDB, wired to the read-only SQLite DB.
# Import `vn` anywhere you need it.

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vanna.legacy.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.legacy.google.gemini_chat import GoogleGeminiChat

from backend.db import run_readonly_sql, get_schema_ddl
from config import GEMINI_KEYS, GEMINI_MODEL, VECTOR_STORE_PATH
from training.knowledge import DOCUMENTATION, QA_PAIRS


class MyVanna(ChromaDB_VectorStore, GoogleGeminiChat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        GoogleGeminiChat.__init__(self, config=config)

    def log(self, message: str, title: str = "Info"):
        pass


def train_all(vn_instance) -> None:
    """Load schema, business definitions and example Q-SQL pairs into the vector store."""
    for ddl in get_schema_ddl():
        vn_instance.train(ddl=ddl)
    for doc in DOCUMENTATION:
        vn_instance.train(documentation=doc)
    for question, sql in QA_PAIRS:
        vn_instance.train(question=question, sql=sql)


vn = MyVanna(config={
    "api_key":    GEMINI_KEYS[0],
    "model_name": GEMINI_MODEL,
    "path":       VECTOR_STORE_PATH,
})

# Route every query through the read-only connection
vn.run_sql = run_readonly_sql
vn.run_sql_is_set = True
vn.dialect = "SQLite"

# First start (e.g. fresh deploy): build the knowledge base automatically
if len(vn.get_training_data()) == 0:
    train_all(vn)
