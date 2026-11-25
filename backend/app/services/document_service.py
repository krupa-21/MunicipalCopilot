from io import BytesIO
import os
import shutil

import fitz
import pytesseract
from docx import Document as DocxDocument
from PIL import Image


def _configure_tesseract():
    """Locate tesseract.exe and its tessdata if not already on PATH."""
    if shutil.which("tesseract"):
        return

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    conda_prefix = os.path.join(local_app_data, "Programs", "tesseract_env")
    conda_tesseract = os.path.join(conda_prefix, "Library", "bin", "tesseract.exe")
    conda_tessdata = os.path.join(conda_prefix, "share", "tessdata")

    if os.path.isfile(conda_tesseract):
        pytesseract.pytesseract.tesseract_cmd = conda_tesseract
        if os.path.isdir(conda_tessdata):
            os.environ.setdefault("TESSDATA_PREFIX", conda_tessdata)
        return

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(local_app_data, "Programs", "Tesseract-OCR", "tesseract.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return


def _ocr_image_bytes(image_bytes: bytes) -> str:
    """Run Tesseract OCR on raw image bytes and return extracted text."""
    _configure_tesseract()
    with Image.open(BytesIO(image_bytes)) as img:
        return pytesseract.image_to_string(img).strip()


def _extract_pdf_page_ocr(document, page, has_text_layer: bool) -> str:
    """Extract OCR text from a scanned PDF page or its embedded images."""
    if not has_text_layer:
        pixmap = page.get_pixmap(dpi=200)
        return _ocr_image_bytes(pixmap.tobytes("png"))

    ocr_parts = []
    seen_xrefs = set()

    for img_info in page.get_images(full=True):
        xref = img_info[0]
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)

        extracted = document.extract_image(xref)
        if not extracted or not extracted.get("image"):
            continue

        text = _ocr_image_bytes(extracted["image"])
        if text:
            ocr_parts.append(text)

    return "\n\n".join(ocr_parts)


def extract_document_text(contents: bytes, extension: str):
    extracted_pages = []

    if extension == ".pdf":
        with fitz.open(stream=contents, filetype="pdf") as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text")
                has_text_layer = len(page_text.strip()) >= 30

                try:
                    ocr_text = _extract_pdf_page_ocr(
                        document, page, has_text_layer
                    )
                    if ocr_text:
                        if has_text_layer:
                            page_text = f"{page_text.rstrip()}\n\n{ocr_text}"
                        else:
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
