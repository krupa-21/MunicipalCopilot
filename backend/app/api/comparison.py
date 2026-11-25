from fastapi import APIRouter

from app.core.config import UPLOAD_DIR
from app.core.resources import comparison_llm
from app.services.comparison_service import compare_documents as compare_documents_service


router = APIRouter()


@router.post("/compare-documents")
def compare_documents(filename1: str, filename2: str):
    return compare_documents_service(
        filename1=filename1,
        filename2=filename2,
        upload_dir=UPLOAD_DIR,
        comparison_llm=comparison_llm
    )
