import time
from pathlib import Path

import fitz
from fastapi import HTTPException


def compare_documents(filename1, filename2, upload_dir, comparison_llm):

    if (
        Path(filename1).name != filename1
        or Path(filename2).name != filename2
        or not filename1.lower().endswith(".pdf")
        or not filename2.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF filenames."
        )

    file1 = upload_dir / filename1
    file2 = upload_dir / filename2

    if not file1.is_file() or not file2.is_file():
        raise HTTPException(
            status_code=404,
            detail="One or both documents were not found."
        )

    if filename1 == filename2:
        raise HTTPException(
            status_code=400,
            detail="Please select two different documents."
        )

    try:
        document1 = fitz.open(file1)
        text1 = ""

        for page_number, page in enumerate(document1, start=1):
            text1 += (
                f"\nPage {page_number}:\n"
                f"{page.get_text('text')}\n"
            )

        document1.close()

        document2 = fitz.open(file2)
        text2 = ""

        for page_number, page in enumerate(document2, start=1):
            text2 += (
                f"\nPage {page_number}:\n"
                f"{page.get_text('text')}\n"
            )

        document2.close()

        if not text1.strip() or not text2.strip():
            raise HTTPException(
                status_code=400,
                detail="One or both PDFs contain no readable text."
            )

        prompt = f"""
        You are a precise municipal policy change detection assistant.

        Compare the previous document (A) with the revised document (B).

        DOCUMENT A:
        {text1}

        DOCUMENT B:
        {text2}

        OBJECTIVE:
        Report only genuine differences between the two documents.
        Do not rewrite the complete documents.

        CHECK THESE CATEGORIES:
        - Priority categories and response-time targets
        - Escalation rules and deadlines
        - Officer and department responsibilities
        - Complaint acknowledgment and reference numbers
        - Complainant status updates
        - Closure and verification
        - Weekly and monthly reporting
        - Report review and follow-up actions
        - Record retention and personal-data protection

        ACCURACY RULES:
        1. Verify every finding against both documents.
        2. Preserve exact values, conditions, and time units.
        3. Do not assume that working hours and working days are equivalent.
        4. A new requirement must be absent from A and present in B.
        5. A removed requirement must be present in A and absent from B.
        6. A modified requirement must be different in meaning or obligation.
        7. Do not report unchanged requirements as changes.
        8. Do not infer a change merely because wording differs.
        9. If a detail cannot be verified, do not present it as a confirmed change.
        10. Do not invent information or page numbers.

        OUTPUT FORMAT:

        ## 1. Confirmed Changes

        Use this table:

        | Topic | Previous Requirement (A) | Revised Requirement (B) |
        |---|---|---|

        Include only verified changes. Compare each priority category
        separately and include exact response-time targets.

        ## 2. Newly Added Requirements

        List only requirements confirmed to be absent from A and present in B.
        If none are verified, state that clearly.

        ## 3. Removed Requirements

        List only requirements confirmed to be present in A and absent from B.
        If none are verified, state that clearly.

        ## 4. Summary

        Provide at most three bullet points describing the most important
        confirmed changes.

        Do not repeat the same change in multiple sections.
        Do not include unchanged requirements.
        Keep the response concise and factual.
        These are fictional test documents, not official policies.
        """

        start_time = time.time()

        response = comparison_llm.invoke(prompt)

        generation_time = round(time.time() - start_time, 2)

        print(
            f"Document Comparison Time: {generation_time} seconds"
        )

        return {
            "document_a": filename1,
            "document_b": filename2,
            "comparison": response.content,
            "generation_time_seconds": generation_time
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to compare documents: {str(e)}"
        )
