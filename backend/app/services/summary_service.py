from datetime import datetime
import html
import io
from pathlib import Path
import random
import re
import time

import pymupdf as fitz
from fastapi import HTTPException

from app.services.document_service import (
    extract_document_text,
    resolve_file_path
)


def build_summary_pdf_filename(original_filename: str) -> str:
    """Build a safe download filename: <Filename>_summary_<random>.pdf."""
    stem = Path(original_filename or "document").stem.strip() or "document"
    safe_stem = re.sub(r'[<>:"/\\|?*\s]+', "_", stem).strip("_") or "document"
    rand_num = random.randint(100000, 999999)
    return f"{safe_stem}_summary_{rand_num}.pdf"


def _format_inline_markdown(text: str) -> str:
    """Escape HTML and convert **bold** / *italic* markdown into HTML tags."""
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    return escaped


def _summary_markdown_to_html(summary_text: str) -> str:
    """Convert structured LLM summary text (headings, bullets, paragraphs) to HTML."""
    lines = (summary_text or "").splitlines()
    html_parts = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            close_list()
            continue

        # Markdown headings (e.g. ## 1. Document Overview or ### Section)
        heading_match = re.match(r"^#{1,4}\s+(.+)$", line)
        if heading_match:
            close_list()
            html_parts.append(f"<h2>{_format_inline_markdown(heading_match.group(1))}</h2>")
            continue

        # Numbered section headings (e.g. 1. Document Overview or **1. Document Overview**)
        numbered_match = re.match(r"^(?:\*\*)?(\d+\.\s+[^:*]+?)(?:\*\*)?:?$", line)
        if numbered_match and len(line) <= 90:
            close_list()
            html_parts.append(f"<h2>{_format_inline_markdown(numbered_match.group(1))}</h2>")
            continue

        # Bullet list items (- item, * item, • item)
        bullet_match = re.match(r"^[-*•]\s+(.+)$", line)
        if bullet_match:
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_format_inline_markdown(bullet_match.group(1))}</li>")
            continue

        close_list()
        html_parts.append(f"<p>{_format_inline_markdown(line)}</p>")

    close_list()
    return "\n".join(html_parts)


def generate_summary_pdf(
    summary_text: str,
    display_filename: str,
    total_pages: int | None = None
) -> bytes:
    """Render a clean, multi-page PDF document for a municipal summary."""
    if not (summary_text or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Summary text cannot be empty."
        )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    pages_label = f"{total_pages} pages" if total_pages else "N/A"
    body_html = _summary_markdown_to_html(summary_text)

    full_html = f"""
    <html>
      <head>
        <style>
          body {{
            font-family: sans-serif;
            font-size: 10.5pt;
            line-height: 1.5;
            color: #222826;
          }}
          .header-box {{
            background-color: #0C232C;
            color: #FFFFFF;
            padding: 14px 16px;
            border-bottom: 3px solid #B84E32;
            margin-bottom: 14px;
          }}
          .header-kicker {{
            font-size: 8.5pt;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: #B2D8C3;
            margin-bottom: 4px;
          }}
          .header-title {{
            font-size: 14pt;
            font-weight: bold;
            color: #FFFFFF;
            margin: 0;
          }}
          .meta-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 14px;
            background-color: #F4EFE6;
            border: 1px solid #DDD8CE;
          }}
          .meta-table td {{
            padding: 7px 10px;
            font-size: 9pt;
            color: #222826;
            border: 1px solid #DDD8CE;
          }}
          .meta-label {{
            font-weight: bold;
            color: #58625F;
            text-transform: uppercase;
            font-size: 8pt;
          }}
          h2 {{
            font-size: 11.5pt;
            color: #1B4931;
            border-bottom: 1px solid #DDD8CE;
            padding-bottom: 3px;
            margin-top: 14px;
            margin-bottom: 6px;
          }}
          p {{
            margin-top: 0;
            margin-bottom: 7px;
          }}
          ul {{
            margin-top: 2px;
            margin-bottom: 8px;
            padding-left: 18px;
          }}
          li {{
            margin-bottom: 4px;
          }}
          .footer-note {{
            margin-top: 16px;
            padding-top: 8px;
            border-top: 1px solid #DDD8CE;
            font-size: 8.5pt;
            color: #58625F;
          }}
        </style>
      </head>
      <body>
        <div class="header-box">
          <div class="header-kicker">Ahmedabad Municipal Corporation • Knowledge Copilot</div>
          <div class="header-title">Structured Document Summary</div>
        </div>
        <table class="meta-table">
          <tr>
            <td><span class="meta-label">Source Document:</span> {html.escape(display_filename)}</td>
            <td><span class="meta-label">Pages Processed:</span> {html.escape(pages_label)}</td>
            <td><span class="meta-label">Generated:</span> {html.escape(generated_at)}</td>
          </tr>
        </table>
        {body_html}
        <div class="footer-note">
          Generated locally by AMC Municipal Operations &amp; Knowledge Copilot. Verify critical figures against the original circular.
        </div>
      </body>
    </html>
    """

    story = fitz.Story(html=full_html)
    mediabox = fitz.paper_rect("a4")
    where = mediabox + (42, 42, -42, -42)

    buffer = io.BytesIO()
    writer = fitz.DocumentWriter(buffer)
    try:
        more = True
        while more:
            dev = writer.begin_page(mediabox)
            more, _ = story.place(where)
            story.draw(dev)
            writer.end_page()
    finally:
        writer.close()

    return buffer.getvalue()


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
