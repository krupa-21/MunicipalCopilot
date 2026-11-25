from io import BytesIO

import fitz
from docx import Document as DocxDocument


def extract_document_text(contents: bytes, extension: str):
    extracted_pages = []

    if extension == ".pdf":
        with fitz.open(stream=contents, filetype="pdf") as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text")

                if len(page_text.strip()) < 30:
                    try:
                        textpage = page.get_textpage_ocr(flags=0, full=True)
                        ocr_text = page.get_text("text", textpage=textpage)
                        if ocr_text.strip():
                            page_text = ocr_text
                    except Exception as ocr_err:
                        print(f"OCR fallback note for page {page_number}: {ocr_err}")

                extracted_pages.append({
                    "page": page_number,
                    "text": page_text
                })

            total_pages = len(document)

    elif extension == ".docx":
        document = DocxDocument(BytesIO(contents))
        text_parts = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        for table in document.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip()
                    for cell in row.cells
                )

                if row_text.strip():
                    text_parts.append(row_text)

        full_text = "\n".join(text_parts)

        extracted_pages.append({
            "page": 1,
            "text": full_text
        })

        total_pages = 1

    elif extension == ".txt":
        try:
            full_text = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError(
                "The TXT file must use UTF-8 text encoding."
            )

        extracted_pages.append({
            "page": 1,
            "text": full_text
        })

        total_pages = 1

    else:
        raise ValueError(
            "Unsupported file format. Upload PDF, DOCX, or TXT."
        )

    return extracted_pages, total_pages

from pathlib import Path

import fitz
from fastapi import HTTPException


def list_uploaded_documents(upload_dir, collection):
    documents = []
    supported_extensions = {".pdf", ".docx", ".txt"}

    for file_path in upload_dir.iterdir():
        if not file_path.is_file():
            continue

        extension = file_path.suffix.lower()

        if extension not in supported_extensions:
            continue

        try:
            file_size_kb = round(file_path.stat().st_size / 1024, 2)

            stored_document = collection.get(
                where={"internal_filename": file_path.name},
                include=["metadatas"]
            )

            metadatas = stored_document.get("metadatas") or []
            meta = metadatas[0] if metadatas else {}
            original_filename = meta.get("filename", file_path.name)
            department = meta.get("department", "General Administration")
            document_type = meta.get("document_type", "Circular")
            issue_date = meta.get("issue_date", "")
            version = meta.get("version", "1.0")

            if extension == ".pdf":
                with fitz.open(file_path) as pdf:
                    total_pages = len(pdf)
            else:
                total_pages = 1

            documents.append({
                "filename": file_path.name,
                "original_filename": original_filename,
                "file_type": extension.lstrip("."),
                "total_pages": total_pages,
                "file_size_kb": file_size_kb,
                "department": department,
                "document_type": document_type,
                "issue_date": issue_date,
                "version": version
            })

        except Exception as e:
            print(f"Unable to read document {file_path.name}: {e}")

    return {
        "total_documents": len(documents),
        "documents": documents
    }


def resolve_file_path(filename, upload_dir, collection):
    file_path = upload_dir / filename

    if not file_path.is_file():
        try:
            records = collection.get(
                where={"filename": filename},
                limit=1,
                include=["metadatas"]
            )

            if records.get("metadatas") and records["metadatas"][0]:
                internal = records["metadatas"][0].get("internal_filename")

                if internal and (upload_dir / internal).is_file():
                    return upload_dir / internal

        except Exception:
            pass

        for path in upload_dir.iterdir():
            if path.name.lower() == filename.lower():
                return path

    return file_path


def delete_uploaded_document(filename, upload_dir, collection):
    supported_extensions = {".pdf", ".docx", ".txt"}

    if (
        not filename
        or Path(filename).name != filename
        or Path(filename).suffix.lower() not in supported_extensions
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid document filename."
        )

    file_path = upload_dir / filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        stored_document = collection.get(
            where={"internal_filename": filename},
            include=["metadatas"]
        )

        chunk_ids = stored_document.get("ids", [])

        if Path(filename).suffix.lower() == ".pdf":
            legacy_records = collection.get(
                where={"filename": filename},
                include=["metadatas"]
            )

            for chunk_id in legacy_records.get("ids", []):
                if chunk_id.startswith(filename + "_"):
                    chunk_ids.append(chunk_id)

        chunk_ids = list(set(chunk_ids))

        if chunk_ids:
            collection.delete(ids=chunk_ids)

        file_path.unlink()

        return {
            "message": "Document deleted successfully.",
            "filename": filename,
            "deleted_chunks": len(chunk_ids)
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to delete document: {str(e)}"
        )
