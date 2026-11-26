from fastapi import APIRouter

from app.core.config import UPLOAD_DIR
from app.core.resources import extraction_llm, comparison_llm
from app.database.vector_store import collection
from app.services.fact_comparison_service import run_structured_comparison

router = APIRouter()


@router.post("/test-structured-comparison")
def test_structured_comparison(filename1: str, filename2: str):
    return run_structured_comparison(
        filename1=filename1,
        filename2=filename2,
        upload_dir=UPLOAD_DIR,
        collection=collection,
        extraction_llm=extraction_llm,
        comparison_llm=comparison_llm
    )
