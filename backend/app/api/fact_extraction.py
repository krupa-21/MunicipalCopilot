from fastapi import APIRouter

from app.core.config import UPLOAD_DIR
from app.core.resources import extraction_llm
from app.services.fact_extraction_service import extract_pdf_facts


router = APIRouter()


@router.post("/test-fact-extraction")
def test_fact_extraction(filename: str):
    return extract_pdf_facts(
        filename=filename,
        upload_dir=UPLOAD_DIR,
        extraction_llm=extraction_llm
    )
