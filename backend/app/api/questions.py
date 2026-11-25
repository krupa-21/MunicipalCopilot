from fastapi import APIRouter

from app.core.resources import embedding_model, qa_llm
from app.database.vector_store import collection
from app.database.audit_db import log_audit
from app.services.question_service import answer_question


router = APIRouter()


@router.get("/ask")
def ask_question(
    query: str,
    department: str = None,
    document_type: str = None,
    user_role: str = "Officer"
):
    return answer_question(
        query=query,
        department=department,
        document_type=document_type,
        user_role=user_role,
        collection=collection,
        embedding_model=embedding_model,
        qa_llm=qa_llm,
        log_audit=log_audit
    )
