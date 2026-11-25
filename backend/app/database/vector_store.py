from app.core.config import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME

import chromadb

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

collection = chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME
)
