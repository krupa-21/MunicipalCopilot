import json
import re
from difflib import SequenceMatcher

def normalize_fact(text: str) -> str:
    """Normalize text for reliable case-insensitive comparison."""
    return " ".join(str(text).casefold().split())


def clean_fact_list(facts: list) -> list:
    """Remove empty entries and duplicate requirements."""
    cleaned = []
    seen = set()

    for item in facts or []:
        if not isinstance(item, (str, int, float)):
            continue

        text = str(item).strip()
        key = normalize_fact(text)

        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)

    return cleaned


def extract_critical_values(text: str) -> list:
    """
    Identify values and wording that can materially change a policy.
    """
    text = str(text).casefold()

    patterns = [
        r"\b\d+(?:\.\d+)?\b",
        r"\bworking\s+hours?\b",
        r"\bworking\s+days?\b",
        r"\bhours?\b",
        r"\bdays?\b",
        r"\bminutes?\b",
        r"\bseconds?\b",
        r"\bweeks?\b",
        r"\bmonths?\b",
        r"\byears?\b",
        r"\bwithin\b",
        r"\bafter\b",
        r"\bbefore\b",
        r"\buntil\b",
        r"\bunless\b",
        r"\bexcept\b",
        r"\bif\b",
        r"\bwhen\b",
        r"\bnot\b",
        r"\bnever\b",
        r"\bonly\b",
        r"\bmust\b",
        r"\bshall\b",
        r"\bmay\b",
        r"\bshould\b",
        r"\brequired\b",
        r"\boptional\b",
        r"\bmandatory\b",
        r"\bprohibited\b",
    ]

    values = []

    for pattern in patterns:
        values.extend(re.findall(pattern, text))

    return values


def exact_compare_fact_lists(
    previous_facts: list,
    revised_facts: list
) -> dict:
    """
    Compare requirements without using AI.
    Exact matches are considered unchanged.
    """

    previous_facts = clean_fact_list(previous_facts)
    revised_facts = clean_fact_list(revised_facts)

    previous_lookup = {
        normalize_fact(item): item
        for item in previous_facts
    }

    revised_lookup = {
        normalize_fact(item): item
        for item in revised_facts
    }

    common = previous_lookup.keys() & revised_lookup.keys()
    removed = previous_lookup.keys() - revised_lookup.keys()
    added = revised_lookup.keys() - previous_lookup.keys()

    return {
        "unchanged_exact_matches": [
            {
                "previous": previous_lookup[key],
                "revised": revised_lookup[key],
                "reason": "The requirement matches after normalization.",
                "requires_verification": False
            }
            for key in sorted(common)
        ],
        "semantic_matches": [],
        "potential_modifications": [],
        "potential_additions": [
            revised_lookup[key] for key in sorted(added)
        ],
        "potential_removals": [
            previous_lookup[key] for key in sorted(removed)
        ],
        "requires_verification": bool(added or removed),
        "comparison_method": "normalized_exact_text"
    }


def find_fact_pages(
    fact: str,
    page_texts: list,
    maximum_pages: int = 3
) -> dict:
    """
    Find the pages most likely to contain a requirement.

    This is a text-matching estimate, not proof that the complete
    requirement appears on the selected page.
    """

    fact = str(fact).strip()

    if not fact or not page_texts:
        return {
            "pages": [],
            "page_match_method": "no_match",
            "requires_page_verification": True
        }

    fact_normalized = normalize_fact(fact)

    # Prefer an exact phrase match.
    exact_pages = []

    for page_number, page_text in enumerate(page_texts, start=1):
        if fact_normalized in normalize_fact(page_text):
            exact_pages.append(page_number)

    if exact_pages:
        return {
            "pages": exact_pages[:maximum_pages],
            "page_match_method": "exact_phrase",
            "requires_page_verification": False
        }

    # Otherwise, rank pages using informative word overlap.
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for",
        "from", "in", "is", "it", "of", "on", "or", "that", "the",
        "their", "this", "to", "was", "were", "will", "with"
    }

    fact_words = {
        word
        for word in re.findall(r"\b[a-z0-9]+\b", fact_normalized)
        if word not in stop_words and len(word) > 1
    }

    if not fact_words:
        return {
            "pages": [],
            "page_match_method": "no_match",
            "requires_page_verification": True
        }

    scored_pages = []

    for page_number, page_text in enumerate(page_texts, start=1):
        page_normalized = normalize_fact(page_text)

        page_words = {
            word
            for word in re.findall(r"\b[a-z0-9]+\b", page_normalized)
            if word not in stop_words and len(word) > 1
        }

        overlap = fact_words & page_words

        # Jaccard-style score penalizes unrelated pages.
        union = fact_words | page_words
        score = len(overlap) / len(union) if union else 0.0

        # Coverage helps identify a page containing most of the fact's
        # informative terms, even if the page contains other content.
        coverage = len(overlap) / len(fact_words)

        scored_pages.append(
            (page_number, score, coverage)
        )

    scored_pages.sort(
        key=lambda item: (item[2], item[1]),
        reverse=True
    )

    # Require meaningful word coverage to avoid misleading references.
    matches = [
        page_number
        for page_number, score, coverage in scored_pages
        if coverage >= 0.35
    ][:maximum_pages]

    return {
        "pages": matches,
        "page_match_method": "keyword_overlap",
        "requires_page_verification": True
    }


def attach_source_reference(
    fact: str,
    page_texts: list,
    filename: str
) -> dict:
    """Attach source PDF and page references to one requirement."""

    page_result = find_fact_pages(fact, page_texts)

    return {
        "document": filename,
        "pages": page_result["pages"],
        "page_match_method": page_result["page_match_method"],
        "requires_page_verification": (
            page_result["requires_page_verification"]
        )
    }


def parse_comparison_json(raw_response) -> dict:
    """Parse a JSON object from the local AI response."""

    if hasattr(raw_response, "content"):
        raw_response = raw_response.content

    text = str(raw_response).strip()

    # Remove optional Markdown fences.
    text = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```\s*$",
        "",
        text
    )

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Recover a JSON object if the model added surrounding text.
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end <= start:
            raise ValueError("No valid JSON object was returned.")

        result = json.loads(text[start:end + 1])

    if not isinstance(result, dict):
        raise ValueError("The comparison response must be a JSON object.")

    return result


def compare_structured_documents(
    previous_facts: dict,
    revised_facts: dict,
    comparison_llm
) -> dict:
    """
    Compare extracted facts using exact matching first and small AI batches.

    Improvements:
    1. Exact matches are handled without AI.
    2. Remaining fields are compared in small batches.
    3. Each AI response contains only a few fields, reducing malformed JSON.
    4. Model output is validated against the original extracted facts.
    5. Missing or invalid classifications are safely flagged for verification.
    6. AI failure never produces a confirmed policy-change claim.
    """

    fields = [
        "document_purpose",
        "priority_categories",
        "response_times",
        "escalation_rules",
        "responsibilities",
        "acknowledgment_requirements",
        "status_update_requirements",
        "closure_and_verification",
        "reporting_requirements",
        "record_retention",
        "data_protection",
        "other_instructions"
    ]

    previous_remaining = {}
    revised_remaining = {}
    exact_matches = {}

    # --------------------------------------------------
    # STEP 1: NORMALIZE INPUT AND FIND EXACT MATCHES
    # --------------------------------------------------

    for field in fields:
        old_value = previous_facts.get(field, [])
        new_value = revised_facts.get(field, [])

        if field == "document_purpose":
            old_list = (
                [old_value.strip()]
                if isinstance(old_value, str) and old_value.strip()
                else []
            )
            new_list = (
                [new_value.strip()]
                if isinstance(new_value, str) and new_value.strip()
                else []
            )
        else:
            old_list = clean_fact_list(
                old_value if isinstance(old_value, list) else []
            )
            new_list = clean_fact_list(
                new_value if isinstance(new_value, list) else []
            )

        # Preserve duplicate entries rather than silently dropping them.
        remaining_new = list(new_list)
        unchanged = []
        remaining_old = []

        for old_item in old_list:
            old_normalized = normalize_fact(old_item)

            matching_index = next(
                (
                    index
                    for index, new_item in enumerate(remaining_new)
                    if normalize_fact(new_item) == old_normalized
                ),
                None
            )

            if matching_index is not None:
                new_item = remaining_new.pop(matching_index)

                unchanged.append({
                    "previous": old_item,
                    "revised": new_item,
                    "reason": "Exact normalized match.",
                    "requires_verification": False
                })
            else:
                remaining_old.append(old_item)

        exact_matches[field] = unchanged
        previous_remaining[field] = remaining_old
        revised_remaining[field] = remaining_new

    # --------------------------------------------------
    # STEP 2: INITIALIZE FINAL RESULTS
    # --------------------------------------------------

    final_fields = {
        field: {
            "unchanged": list(exact_matches[field]),
            "modified": [],
            "added": [],
            "removed": []
        }
        for field in fields
    }

    # --------------------------------------------------
    # STEP 3: HELPER TO ADD SAFE FALLBACK RESULTS
    # --------------------------------------------------

    def add_fallback_items(batch_fields, reason):
        """
        Unmatched facts are potential additions/removals only.
        They are not confirmed policy changes.
        """
        for field in batch_fields:
            existing_added = {
                item for item in final_fields[field]["added"]
                if isinstance(item, str)
            }
            existing_removed = {
                item for item in final_fields[field]["removed"]
                if isinstance(item, str)
            }

            for item in revised_remaining[field]:
                if item not in existing_added:
                    final_fields[field]["added"].append(item)
                    existing_added.add(item)

            for item in previous_remaining[field]:
                if item not in existing_removed:
                    final_fields[field]["removed"].append(item)
                    existing_removed.add(item)

            final_fields[field]["fallback_reason"] = reason

    # --------------------------------------------------
    # STEP 4: PREPARE SMALL AI COMPARISON BATCHES
    # --------------------------------------------------

    ai_requests = 0
    successful_batches = 0
    failed_batches = []
    
    def build_batch_prompt(batch_fields):
        payload = {
            "previous": {
                field: previous_remaining[field]
                for field in batch_fields
            },
            "revised": {
                field: revised_remaining[field]
                for field in batch_fields
            }
        }

        expected_fields = {
            field: {
                "unchanged": [],
                "modified": [],
                "added": [],
                "removed": []
            }
            for field in batch_fields
        }

        prompt = f"""
You are comparing requirements extracted from two municipal policy documents.

INPUT DATA:
{json.dumps(payload, ensure_ascii=False)}

OUTPUT FORMAT:
Return one JSON object with this structure:
{json.dumps({"fields": expected_fields}, ensure_ascii=False)}

COMPARISON RULES:

1. Compare requirements by meaning, not just by wording.

2. Before classifying anything as added or removed, check whether
   a requirement in the other document expresses the same underlying
   duty, responsibility, action, procedure, or rule.

3. Classify as "unchanged" only when the underlying obligation and
   all important details remain the same.

4. Classify as "modified" when the same underlying requirement exists
   in both documents but a meaningful detail has changed.

5. Meaningful changes include:
   - Different deadlines, durations, or numerical values.
   - Different responsible people, roles, or departments.
   - Changes to conditions, exceptions, or scope.
   - Changes to mandatory, recommended, or optional obligations.
   - Changes to escalation, reporting, verification, or retention rules.

6. Classify as "added" only when a revised requirement has no
   equivalent requirement in the previous document.

7. Classify as "removed" only when a previous requirement has no
   equivalent requirement in the revised document.

8. Do not classify differently worded versions of the same duty as
   an addition and a removal when they can reasonably be paired.

9. Do not force matches between unrelated requirements merely to
   reduce the number of additions or removals.

10. Do not assume that similar subject matter means identical
    obligations. Check deadlines, roles, conditions, and scope.

11. Copy every requirement exactly as provided in the input.
    Never invent, paraphrase, or silently omit a requirement.

12. Use each previous requirement and each revised requirement
    at most once across all four classifications.

13. Every input requirement must be classified exactly once.

14. If a reliable match cannot be established, classify the unmatched
    requirement as added or removed.

15. Treat the result as a comparison suggestion, not a legal conclusion.
16. Prefer atomic one-duty-to-one-duty matches. If one input item contains multiple independent duties, do not pretend a single paired item fully accounts for every duty; identify the matching duty and leave genuinely new duties as additions where the input allows this safely.
17. For each modified item, explain the actual difference specifically (for example, deadline changed from 4 to 2 working hours, a new recipient was added, or a mandatory duty replaced a recommendation). Do not use generic wording such as 'the wording differs'.
18. Never pair items solely because they share keywords. Check the responsible role, action, condition, deadline, and scope.

REQUIRED ITEM FORMATS:

For "unchanged":
{{"previous": "exact previous text",
  "revised": "exact revised text",
  "reason": "brief explanation"}}

For "modified":
{{"previous": "exact previous text",
  "revised": "exact revised text",
  "reason": "brief explanation of the meaningful difference"}}

For "added":
["exact revised requirement"]

For "removed":
["exact previous requirement"]

Return ONLY valid JSON.
Do not include Markdown fences or additional commentary.
"""

        return prompt

    # --------------------------------------------------
    # STEP 5: PROCESS EACH BATCH (FAST SINGLE PASS)
    # --------------------------------------------------

    active_fields = [
        field for field in fields
        if previous_remaining[field] or revised_remaining[field]
    ]

    if not active_fields:
        return {
            "fields": final_fields,
            "ai_requests": 0,
            "successful_batches": 0,
            "failed_batches": []
        }

    field_batches = [active_fields]

    for batch_fields in field_batches:

        prompt = build_batch_prompt(active_fields)
        ai_requests += 1

        try:
            response = comparison_llm.invoke(prompt)

            # Retry once only when the model returns malformed JSON.
            try:
                ai_result = parse_comparison_json(response)
            except (ValueError, json.JSONDecodeError) as parse_error:
                print(
                    f"Malformed JSON in comparison batch "
                    f"({', '.join(active_fields)}); retrying once: {parse_error}"
                )
                retry_prompt = prompt + "\n\nRETRY REQUIREMENT: Your previous response was not valid JSON. Return the complete requested JSON object now. Use double quotes for every JSON key and string, escape internal quotes, do not truncate the response, and do not include Markdown or commentary."
                retry_response = comparison_llm.invoke(retry_prompt)
                ai_result = parse_comparison_json(retry_response)

            if not isinstance(ai_result, dict):
                raise ValueError("AI response is not a JSON object.")

            ai_fields = ai_result.get("fields")

            if not isinstance(ai_fields, dict):
                raise ValueError("AI response is missing the fields object.")

            # A batch must return every requested field.
            missing_fields = [
                field for field in active_fields
                if not isinstance(ai_fields.get(field), dict)
            ]

            if missing_fields:
                raise ValueError(
                    "AI response is missing valid results for: "
                    + ", ".join(missing_fields)
                )

            # Validate each field independently.
            for field in active_fields:
                result = ai_fields[field]

                for key in ("unchanged", "modified", "added", "removed"):
                    if not isinstance(result.get(key, []), list):
                        raise ValueError(
                            f"Invalid '{key}' list for field '{field}'."
                        )

                old_items = previous_remaining[field]
                new_items = revised_remaining[field]

                old_used = set()
                new_used = set()

                valid_old = set(old_items)
                valid_new = set(new_items)

                # ------------------------------
                # Validate unchanged pairs
                # ------------------------------

                for item in result.get("unchanged", []):
                    if not isinstance(item, dict):
                        continue

                    old = item.get("previous")
                    new = item.get("revised")

                    if old not in valid_old or new not in valid_new:
                        continue

                    if old in old_used or new in new_used:
                        continue

                    # Do not accept important numeric or deadline changes
                    # as unchanged.
                    old_critical = extract_critical_values(old)
                    new_critical = extract_critical_values(new)

                    if old_critical != new_critical:
                        final_fields[field]["modified"].append({
                            "previous": old,
                            "revised": new,
                            "reason": (
                                "Important values or conditions differ; "
                                "manual verification is required."
                            ),
                            "critical_terms_previous": old_critical,
                            "critical_terms_revised": new_critical,
                            "requires_verification": True
                        })
                    else:
                        final_fields[field]["unchanged"].append({
                            "previous": old,
                            "revised": new,
                            "reason": str(
                                item.get("reason", "AI-suggested semantic match.")
                            ),
                            "requires_verification": True
                        })

                    old_used.add(old)
                    new_used.add(new)

                # ------------------------------
                # Validate modified pairs
                # ------------------------------

                for item in result.get("modified", []):
                    if not isinstance(item, dict):
                        continue

                    old = item.get("previous")
                    new = item.get("revised")

                    if old not in valid_old or new not in valid_new:
                        continue

                    if old in old_used or new in new_used:
                        continue

                    final_fields[field]["modified"].append({
                        "previous": old,
                        "revised": new,
                        "reason": str(
                            item.get("reason", "Potential modification.")
                        ),
                        "critical_terms_previous": extract_critical_values(old),
                        "critical_terms_revised": extract_critical_values(new),
                        "requires_verification": True
                    })

                    old_used.add(old)
                    new_used.add(new)

                # ------------------------------
                # Validate additions
                # ------------------------------

                for item in result.get("added", []):
                    if (
                        isinstance(item, str)
                        and item in valid_new
                        and item not in new_used
                    ):
                        final_fields[field]["added"].append(item)
                        new_used.add(item)

                # ------------------------------
                # Validate removals
                # ------------------------------

                for item in result.get("removed", []):
                    if (
                        isinstance(item, str)
                        and item in valid_old
                        and item not in old_used
                    ):
                        final_fields[field]["removed"].append(item)
                        old_used.add(item)

                # ------------------------------
                # Recover omitted requirements
                # ------------------------------

                # If the model omitted a requirement, retain it as a
                # potential addition/removal rather than losing information.
                for item in old_items:
                    if item not in old_used:
                        final_fields[field]["removed"].append(item)

                for item in new_items:
                    if item not in new_used:
                        final_fields[field]["added"].append(item)

            successful_batches += 1

        except Exception as error:
            print(
                f"Structured comparison batch failed "
                f"({', '.join(active_fields)}): {error!r}"
            )

            failed_batches.append({
                "fields": active_fields,
                "reason": str(error)
            })

            # Preserve exact matches and safely classify unmatched items.
            add_fallback_items(
                active_fields,
                "AI comparison failed for this batch. Unmatched items are "
                "potential additions/removals, not confirmed changes."
            )
    # --------------------------------------------------
    # STEP 5.5: CONSERVATIVE MATCHING
    # Unmatched AI results remain separate potential additions/removals.
    # Do not infer semantic equivalence from position, role prefixes,
    # or keyword similarity alone.

    # STEP 5.7: AVOID FALSE REMOVALS
    # --------------------------------------------------
    # If a revised field extracted no facts, absence is not proof that
    # every previous requirement was removed. Preserve these for review.
    for field in fields:
        previous_items = previous_facts.get(field, [])
        revised_items = revised_facts.get(field, [])

        if not isinstance(previous_items, list):
            previous_items = [previous_items] if previous_items else []
        if not isinstance(revised_items, list):
            revised_items = [revised_items] if revised_items else []

        if field == "other_instructions" and previous_items and not revised_items:
            existing_unverified = final_fields[field].setdefault(
                "unverified_previous", []
            )
            existing_unverified.extend(
                item for item in final_fields[field]["removed"]
                if item not in existing_unverified
            )
            final_fields[field]["removed"] = []
            final_fields[field]["review_warning"] = (
                "No revised facts were extracted for this field. Previous "
                "instructions are unverified, not confirmed removals."
            )

    # --------------------------------------------------
    # STEP 5.8: PREVENT CROSS-CATEGORY DUPLICATES SAFELY
    # --------------------------------------------------
    # Only suppress exact normalized duplicates already consumed by a paired
    # unchanged/modified result. Do not use loose keyword overlap: it can hide
    # a genuine privacy, reporting, or closure requirement.
    for field in fields:
        result = final_fields[field]

        used_previous = set()
        used_revised = set()
        for item in result["unchanged"] + result["modified"]:
            if not isinstance(item, dict):
                continue
            previous_text = item.get("previous")
            revised_text = item.get("revised")
            if isinstance(previous_text, str) and previous_text.strip():
                used_previous.add(normalize_fact(previous_text))
            if isinstance(revised_text, str) and revised_text.strip():
                used_revised.add(normalize_fact(revised_text))

        result["removed"] = [
            item for item in result["removed"]
            if normalize_fact(item) not in used_previous
        ]
        result["added"] = [
            item for item in result["added"]
            if normalize_fact(item) not in used_revised
        ]

    # --------------------------------------------------
    # STEP 6: REMOVE DUPLICATE STRING RESULTS
    # --------------------------------------------------

    for field in fields:
        for key in ("added", "removed"):
            values = final_fields[field][key]
            seen = set()
            deduplicated = []

            for value in values:
                if value not in seen:
                    seen.add(value)
                    deduplicated.append(value)

            final_fields[field][key] = deduplicated

    # --------------------------------------------------
    # STEP 7: BUILD FINAL RESPONSE
    # --------------------------------------------------

    if ai_requests == 0:
        comparison_method = "exact_text_only"
    elif failed_batches and successful_batches:
        comparison_method = "exact_matching_plus_batched_ai_with_fallback"
    elif failed_batches:
        comparison_method = "exact_text_fallback"
    else:
        comparison_method = "exact_matching_plus_batched_ai"

    return {
        "fields": final_fields,
        "comparison_method": comparison_method,
        "ai_requests": ai_requests,
        "successful_ai_batches": successful_batches,
        "failed_ai_batches": failed_batches,
        "requires_verification": (
            ai_requests > 0 or bool(failed_batches)
        ),
        "important_note": (
            "AI classifications are suggestions. Verify modified, added, "
            "and removed requirements and their page references against "
            "the original PDF documents before treating them as confirmed "
            "policy changes."
        )
    }


def compare_priority_targets(
    previous_facts: dict,
    revised_facts: dict
) -> dict:
    """
    Compare response targets only when priority category names match
    after normalization. Never infer category equivalence by position.
    """

    previous_categories = clean_fact_list(
        previous_facts.get("priority_categories", [])
    )
    revised_categories = clean_fact_list(
        revised_facts.get("priority_categories", [])
    )
    previous_times = clean_fact_list(
        previous_facts.get("response_times", [])
    )
    revised_times = clean_fact_list(
        revised_facts.get("response_times", [])
    )

    def manual_verification(reason):
        return {
            "status": "manual_verification_required",
            "reason": reason,
            "previous_categories": previous_categories,
            "previous_response_times": previous_times,
            "revised_categories": revised_categories,
            "revised_response_times": revised_times,
            "requires_verification": True
        }

    if (
        len(previous_categories) != len(previous_times)
        or len(revised_categories) != len(revised_times)
    ):
        return manual_verification(
            "Priority categories and response-time lists do not align "
            "within one or both documents. Category-to-target mappings "
            "cannot be safely inferred."
        )

    def build_category_map(categories, targets):
        result = {}

        for category, target in zip(categories, targets):
            key = normalize_fact(category)

            if not key or key in result:
                return None

            result[key] = {
                "category": category,
                "response_target": target
            }

        return result

    previous_map = build_category_map(
        previous_categories, previous_times
    )
    revised_map = build_category_map(
        revised_categories, revised_times
    )

    if previous_map is None or revised_map is None:
        return manual_verification(
            "A document contains an empty or duplicate normalized "
            "priority category. Exact category-to-target matching "
            "would be ambiguous."
        )

    comparisons = []
    all_keys = list(previous_map)

    for key in revised_map:
        if key not in previous_map:
            all_keys.append(key)

    for key in all_keys:
        previous = previous_map.get(key)
        revised = revised_map.get(key)

        if previous is None:
            comparisons.append({
                "change_type": "category_and_target_added",
                "revised_category": revised["category"],
                "revised_response_target": revised["response_target"],
                "reason": (
                    "This priority category has no exact normalized "
                    "category-name match in the previous document."
                ),
                "requires_verification": True
            })
            continue

        if revised is None:
            comparisons.append({
                "change_type": "category_and_target_removed",
                "previous_category": previous["category"],
                "previous_response_target": previous["response_target"],
                "reason": (
                    "This priority category has no exact normalized "
                    "category-name match in the revised document."
                ),
                "requires_verification": True
            })
            continue

        previous_target = previous["response_target"]
        revised_target = revised["response_target"]

        target_unchanged = (
            normalize_fact(previous_target)
            == normalize_fact(revised_target)
        )

        if target_unchanged:
            change_type = "unchanged"
            reason = (
                "The exact normalized priority category and its "
                "response target match."
            )
        else:
            change_type = "response_target_changed"
            reason = (
                "The priority category name matches, but its response "
                "target differs. Verify the specific time change "
                "against both source documents."
            )

        comparisons.append({
            "change_type": change_type,
            "previous_category": previous["category"],
            "revised_category": revised["category"],
            "previous_response_target": previous_target,
            "revised_response_target": revised_target,
            "reason": reason,
            "requires_verification": change_type != "unchanged"
        })

    return {
        "status": "compared_with_verification",
        "comparison_method": "exact_normalized_category_name_alignment",
        "previous_category_count": len(previous_categories),
        "revised_category_count": len(revised_categories),
        "comparisons": comparisons,
        "important_note": (
            "Response targets are matched only by exact normalized "
            "priority category names, never by list position. Renamed "
            "or unmatched categories appear as separate additions or "
            "removals and require manual verification."
        )
    }


def compare_fact_lists(
    previous_facts: list,
    revised_facts: list
) -> dict:
    """
    Compatibility helper for existing code.

    Uses exact comparison for this standalone helper. The main endpoint
    uses compare_structured_documents to make one AI request for all fields.
    """

    return exact_compare_fact_lists(previous_facts, revised_facts)


def run_structured_comparison(
    filename1,
    filename2,
    upload_dir,
    collection,
    extraction_llm,
    comparison_llm
):
    from fastapi import HTTPException
    from pathlib import Path
    from app.services.document_service import (
        resolve_file_path,
        extract_document_text
    )
    from app.services.fact_extraction_service import extract_document_facts

    supported_ext = {".pdf", ".docx", ".txt"}

    for filename in (filename1, filename2):
        if not filename or Path(filename).suffix.lower() not in supported_ext:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document filename (PDF, DOCX, TXT only): {filename}"
            )

    previous_path = resolve_file_path(filename1, upload_dir, collection)
    revised_path = resolve_file_path(filename2, upload_dir, collection)

    if not previous_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Previous document not found: {filename1}"
        )

    if not revised_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Revised document not found: {filename2}"
        )

    try:
        prev_pages, _ = extract_document_text(
            previous_path.read_bytes(), previous_path.suffix.lower()
        )
        rev_pages, _ = extract_document_text(
            revised_path.read_bytes(), revised_path.suffix.lower()
        )

        previous_page_texts = [page["text"] for page in prev_pages]
        revised_page_texts = [page["text"] for page in rev_pages]

        previous_text = "\n".join(
            f"Page {number}:\n{text}"
            for number, text in enumerate(previous_page_texts, start=1)
        )
        revised_text = "\n".join(
            f"Page {number}:\n{text}"
            for number, text in enumerate(revised_page_texts, start=1)
        )

        if not previous_text.strip():
            raise HTTPException(
                status_code=400,
                detail="The previous document contains no readable text."
            )

        if not revised_text.strip():
            raise HTTPException(
                status_code=400,
                detail="The revised document contains no readable text."
            )

        previous_facts = extract_document_facts(
            previous_text, extraction_llm
        )
        revised_facts = extract_document_facts(
            revised_text, extraction_llm
        )

        comparison = compare_structured_documents(
            previous_facts,
            revised_facts,
            comparison_llm
        )

        for field, field_result in comparison["fields"].items():
            for item in field_result.get("unchanged", []):
                item["previous_source"] = attach_source_reference(
                    item["previous"], previous_page_texts, filename1
                )
                item["revised_source"] = attach_source_reference(
                    item["revised"], revised_page_texts, filename2
                )

            for item in field_result.get("modified", []):
                item["previous_source"] = attach_source_reference(
                    item["previous"], previous_page_texts, filename1
                )
                item["revised_source"] = attach_source_reference(
                    item["revised"], revised_page_texts, filename2
                )

            field_result["added"] = [
                {
                    "requirement": item,
                    "revised_source": attach_source_reference(
                        item, revised_page_texts, filename2
                    ),
                    "requires_verification": True
                }
                for item in field_result.get("added", [])
            ]

            field_result["removed"] = [
                {
                    "requirement": item,
                    "previous_source": attach_source_reference(
                        item, previous_page_texts, filename1
                    ),
                    "requires_verification": True
                }
                for item in field_result.get("removed", [])
            ]

            if "unverified_previous" in field_result:
                field_result["unverified_previous"] = [
                    {
                        "requirement": item,
                        "previous_source": attach_source_reference(
                            item, previous_page_texts, filename1
                        ),
                        "requires_verification": True
                    }
                    for item in field_result["unverified_previous"]
                ]

        priority_comparison = compare_priority_targets(
            previous_facts, revised_facts
        )

        return {
            "previous_document": filename1,
            "revised_document": filename2,
            "comparison": comparison,
            "priority_and_response_time_comparison": priority_comparison,
            "source_reference_method": (
                "Page-level exact phrase matching with keyword-overlap "
                "fallback. Verify references against the PDFs."
            ),
            "performance": {
                "fact_extraction_runs": 2,
                "structured_comparison_ai_requests": comparison.get(
                    "ai_requests", 0
                ),
                "page_text_extracted_once_per_document": True
            },
            "important_notes": [
                "Added and removed items are comparison candidates, not proof of a legally effective policy change.",
                "AI may misunderstand semantically similar requirements. Review modified, added, and removed items.",
                "A page reference may identify a relevant page without containing the complete requirement.",
                "An empty extracted field does not prove that the source document contains no requirement for that field."
            ]
        }

    except HTTPException:
        raise
    except Exception as error:
        print("\n--- STRUCTURED COMPARISON ERROR ---")
        print(repr(error))
        print("--- END STRUCTURED COMPARISON ERROR ---\n")
        raise HTTPException(
            status_code=500,
            detail=f"Structured comparison failed: {str(error)}"
        )

