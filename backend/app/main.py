from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import UPLOAD_DIR
from app.database.audit_db import init_audit_db
from app.database.vector_store import init_vector_db
from app.core.resources import qa_llm

from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.questions import router as questions_router
from app.api.audit import router as audit_router
from app.api.summaries import router as summaries_router
from app.api.comparison import router as comparison_router
from app.api.fact_extraction import router as fact_extraction_router
from app.api.structured_comparison import router as structured_comparison_router

app = FastAPI(
    title="Municipal Knowledge Copilot",
    description="AI-powered assistant for municipal document management and knowledge retrieval.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR.mkdir(exist_ok=True)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(questions_router)
app.include_router(audit_router)
app.include_router(summaries_router)
app.include_router(comparison_router)
app.include_router(fact_extraction_router)
app.include_router(structured_comparison_router)


@app.on_event("startup")
def startup_warmup():
    init_audit_db()
    init_vector_db()
    try:
        print("Preloading Ollama LLM with 30-minute keep-alive...")
        qa_llm.invoke("ping")
        print("Ollama model ready and pinned in memory for 30 minutes.")
    except Exception as e:
        print(f"Warmup notice: {e}")
