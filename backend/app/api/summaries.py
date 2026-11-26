from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.config import UPLOAD_DIR
from app.core.resources import summary_llm
from app.database.vector_store import collection
from app.services.summary_service import (
    build_summary_pdf_filename,
    generate_summary_pdf,
    summarize_document as summarize_document_service
)


router = APIRouter()


class SummaryPdfRequest(BaseModel):
    filename: str
    original_filename: str | None = None
    total_pages: int | None = None
    summary: str


@router.post("/summarize/export-pdf")
def export_summary_pdf(payload: SummaryPdfRequest):
    display_name = payload.original_filename or payload.filename
    pdf_bytes = generate_summary_pdf(
        summary_text=payload.summary,
        display_filename=display_name,
        total_pages=payload.total_pages
    )
    download_name = build_summary_pdf_filename(display_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"'
        }
    )


@router.post("/summarize/{filename}")
def summarize_document(filename: str):
    return summarize_document_service(
        filename=filename,
        upload_dir=UPLOAD_DIR,
        collection=collection,
        summary_llm=summary_llm
    )
