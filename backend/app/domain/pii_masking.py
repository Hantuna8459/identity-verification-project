from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

# Per-field masking strategy for document_layout's structured fields - this
# map is the "key" ADR-M0-003 (docs/M0_CONTRACT_GOVERNANCE_BASELINE.md) calls
# for: reviewers see masked data by default, unmasked access only through the
# audited reveal path (EkycService.reveal_document_fields /
# POST .../reviews/{id}/reveal). Field labels absent from this map pass
# through unmasked - they don't identify the subject on their own in
# isolation (sex, nationality).
_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def _mask_name(value: str) -> str:
    words = value.split()
    if not words:
        return value
    return " ".join(word[0] + "*" * (len(word) - 1) if len(word) > 1 else word for word in words)


def _mask_keep_last_digits(count: int) -> Callable[[str], str]:
    def _mask(value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if not digits:
            return "*" * min(len(value), 8)
        if len(digits) <= count:
            return "*" * len(digits)
        return "*" * (len(digits) - count) + digits[-count:]

    return _mask


def _mask_date_year_only(value: str) -> str:
    match = _DATE_RE.search(value)
    return f"**/**/{match.group(3)}" if match else "**/**/****"


def _mask_full(value: str) -> str:
    return "*" * min(len(value), 8) if value else value


FIELD_MASKS: dict[str, Callable[[str], str]] = {
    "full_name": _mask_name,
    "id_number": _mask_keep_last_digits(4),
    "date_of_birth": _mask_date_year_only,
    "issue_date": _mask_date_year_only,
    "expiry_date": _mask_date_year_only,
    "place_of_residence": _mask_full,
    "place_of_origin": _mask_full,
    "issue_place": _mask_full,
    "mrz": _mask_full,
}


def mask_layout_fields(fields: dict[str, str]) -> dict[str, str]:
    return {label: FIELD_MASKS[label](value) if label in FIELD_MASKS else value
            for label, value in fields.items()}


def _mask_layout(layout: dict[str, Any]) -> dict[str, Any]:
    masked = dict(layout)
    if isinstance(layout.get("fields"), dict):
        masked["fields"] = mask_layout_fields(layout["fields"])
    if isinstance(layout.get("parsed_fields"), dict):
        masked["parsed_fields"] = mask_layout_fields(layout["parsed_fields"])
    return masked


def _document_layout(document: Any) -> dict[str, Any] | None:
    if not isinstance(document, dict):
        return None
    details = document.get("details")
    if not isinstance(details, dict):
        return None
    layout = details.get("layout")
    return layout if isinstance(layout, dict) else None


def mask_analysis(analysis: dict[str, Any] | None) -> dict[str, Any] | None:
    """Mask structured PII fields in an ekyc-analysis/1.0 result for the
    reviewer's default (non-revealed) view - see ADR-M0-003. Only
    capabilities.ocr.documents.*.details.layout.{fields,parsed_fields} carry
    structured PII; every other field in the contract is already
    score/status/provenance, not raw identity data (raw OCR `lines` never
    reach this contract in the first place - see EkycOrchestrator.analyze)."""
    if not analysis:
        return analysis
    capabilities = analysis.get("capabilities")
    if not isinstance(capabilities, dict):
        return analysis
    ocr = capabilities.get("ocr")
    if not isinstance(ocr, dict) or not isinstance(ocr.get("documents"), dict):
        return analysis
    masked_documents: dict[str, Any] = {}
    for name, document in ocr["documents"].items():
        layout = _document_layout(document)
        if layout is None:
            masked_documents[name] = document
            continue
        details = {**document["details"], "layout": _mask_layout(layout)}
        masked_documents[name] = {**document, "details": details}
    return {
        **analysis,
        "capabilities": {**capabilities, "ocr": {**ocr, "documents": masked_documents}},
    }


def extract_layout_fields(analysis: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Unmasked per-document layout fields - used only by the audited reveal
    path, never by the default reviewer view."""
    if not analysis:
        return {}
    capabilities = analysis.get("capabilities")
    if not isinstance(capabilities, dict):
        return {}
    ocr = capabilities.get("ocr")
    if not isinstance(ocr, dict) or not isinstance(ocr.get("documents"), dict):
        return {}
    revealed: dict[str, dict[str, Any]] = {}
    for name, document in ocr["documents"].items():
        layout = _document_layout(document)
        if layout and (layout.get("fields") or layout.get("parsed_fields")):
            revealed[name] = {
                "fields": layout.get("fields", {}),
                "parsed_fields": layout.get("parsed_fields", {}),
            }
    return revealed
