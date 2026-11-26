from fastapi import APIRouter

from app.core.config import UPLOAD_DIR
from app.core.resources import summary_llm
from app.database.vector_store import collection
from app.services.summary_service import summarize_document as summarize_document_service


router = APIRouter()


@router.post("/summarize/{filename}")
def summarize_document(filename: str):
    return summarize_document_service(
        filename=filename,
        upload_dir=UPLOAD_DIR,
        collection=collection,
        summary_llm=summary_llm
    )
