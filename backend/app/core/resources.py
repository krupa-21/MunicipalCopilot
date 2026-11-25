from pathlib import Path

from app.core.config import (
    EMBEDDING_MODEL_NAME,
    OLLAMA_MODEL_NAME
)

from sentence_transformers import SentenceTransformer
from langchain_ollama import ChatOllama

print("Loading embedding model...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
print("Embedding model loaded successfully!")

qa_llm = ChatOllama(
    model=OLLAMA_MODEL_NAME,
    temperature=0.1,
    num_predict=120,
    num_ctx=2048,
    keep_alive="30m"
)

summary_llm = ChatOllama(
    model=OLLAMA_MODEL_NAME,
    temperature=0.1,
    num_predict=700,
    num_ctx=4096,
    keep_alive="30m"
)

comparison_llm = ChatOllama(
    model=OLLAMA_MODEL_NAME,
    temperature=0.1,
    num_predict=650,
    num_ctx=4096,
    keep_alive="30m"
)

extraction_llm = ChatOllama(
    model=OLLAMA_MODEL_NAME,
    temperature=0,
    num_predict=1400,
    num_ctx=4096,
    keep_alive="30m",
    format="json"
)
