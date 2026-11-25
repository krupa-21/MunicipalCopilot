import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException

from app.services.document_service import extract_document_text
from app.services.chunking_service import create_chunks


def process_upload(
    contents,
    original_filename,
    extension,
    department,
    document_type,
    issue_date,
    version,
    collection,
    embedding_model,
    upload_dir
):
    file_hash = hashlib.sha256(contents).hexdigest()

    try:
        existing_document = collection.get(
            where={"file_hash": file_hash},
            limit=1,
            include=["metadatas"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to check for duplicate documents: {str(e)}"
        )

    if existing_document.get("ids"):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "This document has already been uploaded.",
                "filename": original_filename,
                "duplicate": True
            }
        )

    file_path = None

    try:
        extracted_pages, total_pages = extract_document_text(
            contents,
            extension
        )

        all_chunks = []

        for page_data in extracted_pages:
            page_number = page_data["page"]
            page_text = page_data["text"]

            print(
                f"Extracted text: {extension.upper()} "
                f"page {page_number} ({len(page_text)} characters)"
            )

            for chunk in create_chunks(page_text):
                all_chunks.append({
                    "page": page_number,
                    "text": chunk
                })

        if not all_chunks:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No extractable text was found in this document. "
                    "Scanned PDFs require OCR support."
                )
            )

        internal_filename = f"{uuid.uuid4()}{extension}"
        file_path = upload_dir / internal_filename

        texts = [
            chunk["text"]
            for chunk in all_chunks
        ]

        embeddings = embedding_model.encode(texts).tolist()

        ids = [
            f"{internal_filename}_{i}"
            for i in range(len(all_chunks))
        ]

        metadatas = [
            {
                "filename": original_filename,
                "internal_filename": internal_filename,
                "file_hash": file_hash,
                "file_type": extension.lstrip("."),
                "page": chunk["page"],
                "department": department or "General Administration",
                "document_type": document_type or "Circular",
                "issue_date": issue_date or "",
                "version": version or "1.0"
            }
            for chunk in all_chunks
        ]

        file_path.write_bytes(contents)

        try:
            collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
        except Exception:
            if file_path.exists():
                file_path.unlink()
            raise

        return {
            "message": "Document uploaded successfully!",
            "filename": original_filename,
            "internal_filename": internal_filename,
            "file_type": extension.lstrip("."),
            "department": department or "General Administration",
            "document_type": document_type or "Circular",
            "issue_date": issue_date or "",
            "version": version or "1.0",
            "total_pages": total_pages,
            "extracted_pages": extracted_pages,
            "total_chunks": len(all_chunks),
            "chunk_preview": all_chunks[:2]
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to process document: {str(e)}"
        )

