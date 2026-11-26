import time

from fastapi import HTTPException

from app.services.document_service import (
    extract_document_text,
    resolve_file_path
)


def summarize_document(filename, upload_dir, collection, summary_llm):
    file_path = resolve_file_path(
        filename,
        upload_dir,
        collection
    )

    supported = {".pdf", ".docx", ".txt"}

    if not file_path.is_file() or file_path.suffix.lower() not in supported:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        contents = file_path.read_bytes()
        extension = file_path.suffix.lower()

        extracted_pages, total_pages = extract_document_text(
            contents,
            extension
        )

        full_text = "\n".join(
            f"Page {page['page']}:\n{page['text']}"
            for page in extracted_pages
        )

        if not full_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text found in this document."
            )

        prompt = f"""
        You are a Municipal Document Analysis Assistant.

        Analyze the following municipal document and create
        a clear, structured summary.

        Keep the summary concise but complete.
        Avoid repeating the same information.
        Use bullet points wherever appropriate.
        Preserve all important deadlines, responsibilities and instructions.

        Include these sections:

        1. Document Overview
        2. Key Instructions and Guidelines
        3. Responsibilities
        4. Important Deadlines and Timelines
        5. Important Points

        Use simple and professional language.

        Only include information available in the document.
        Do not invent facts or missing information.

        DOCUMENT:
        {full_text}
        """

        start_time = time.time()

        response = summary_llm.invoke(prompt)

        generation_time = round(time.time() - start_time, 2)

        print(f"AI Generation Time: {generation_time} seconds")

        return {
            "filename": filename,
            "total_pages": total_pages,
            "summary": response.content
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to summarize document: {str(e)}"
        )
