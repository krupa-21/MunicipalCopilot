import os
from pathlib import Path

os.environ["OLLAMA_KEEP_ALIVE"] = "30m"

UPLOAD_DIR = Path("uploads")
DATABASE_URL = os.getenv("DATABASE_URL")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
OLLAMA_MODEL_NAME = "qwen2.5:3b"
