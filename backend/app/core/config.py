import os
from pathlib import Path

os.environ["OLLAMA_KEEP_ALIVE"] = "30m"

AUDIT_DB_PATH = Path("audit_logs.db")
UPLOAD_DIR = Path("uploads")
CHROMA_DB_PATH = "./chroma_db"
CHROMA_COLLECTION_NAME = "municipal_documents"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
OLLAMA_MODEL_NAME = "qwen2.5:3b"
