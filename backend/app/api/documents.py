from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.core.config import UPLOAD_DIR
from app.core.resources import embedding_model
from app.database.vector_store import collection
from app.services.upload_service import process_upload


router = APIRouter()


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    department: str = Form("General Administration"),
    document_type: str = Form("Circular"),
    issue_date: str = Form(""),
    version: str = Form("1.0")
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required."
        )

    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    if extension not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, and TXT files are supported."
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    return process_upload(
        contents=contents,
        original_filename=original_filename,
        extension=extension,
        department=department,
        document_type=document_type,
        issue_date=issue_date,
        version=version,
        collection=collection,
        embedding_model=embedding_model,
        upload_dir=UPLOAD_DIR
    )

from app.services.retrieval_service import (
    search_documents as search_documents_service,
    get_debug_chunks
)


@router.get("/search")
def search_documents(query: str):
    return search_documents_service(
        query,
        collection,
        embedding_model
    )


@router.get("/debug-chunks")
def debug_chunks():
    return get_debug_chunks(collection)

from fastapi.responses import FileResponse

from app.services.document_service import (
    list_uploaded_documents,
    resolve_file_path,
    delete_uploaded_document
)


@router.get("/documents")
def list_documents():
    return list_uploaded_documents(UPLOAD_DIR, collection)


@router.get("/files/{filename}")
def get_file(filename: str):
    file_path = resolve_file_path(
        filename,
        UPLOAD_DIR,
        collection
    )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}"
        )

    ext = file_path.suffix.lower()

    if ext == ".pdf":
        media_type = "application/pdf"
    elif ext == ".txt":
        media_type = "text/plain; charset=utf-8"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{file_path.name}"'
        }
    )


@router.delete("/documents/{filename}")
def delete_document(filename: str):
    return delete_uploaded_document(
        filename,
        UPLOAD_DIR,
        collection
    )
