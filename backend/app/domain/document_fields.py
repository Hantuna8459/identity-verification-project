from __future__ import annotations

import re
from datetime import date

# Pure text cleanup over DocumentLayoutResult.fields (the normalized
# contract from ai_modules.ekyc.document_layout), not a model adapter -
# lives in domain per the same split as face_matching.py. Rule-based only,
# no LLM (AGENTS.md forbids LLM for OCR/extraction).
#
# Each YOLO field crop still contains the printed bilingual CCCD label
# (e.g. "Ngày sinh / Date of birth: 30/05/2001") because the box is drawn
# around the label+value together, not the value alone.

_DATE_FIELDS = frozenset({"date_of_birth", "issue_date", "expiry_date"})
_DATE_RE = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")
_DATE_COMPONENTS_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_ID_RE = re.compile(r"\d{9,12}")
# mrz has no printed label to strip - it's the raw back-side ID/MRZ block.
_UNLABELED_FIELDS = frozenset({"mrz"})
# Different OCR engines punctuate the printed label/value boundary
# differently - RapidOCR usually keeps ":", VietOCR sometimes reads it as
# ";" or drops it to a bare space (e.g. "Gioi tinh/Sex Nam"). The English
# label word itself is the one thing that's stable across engines, so it's
# the fallback anchor when no separator punctuation survives OCR.
_FIELD_LABEL_KEYWORDS: dict[str, str] = {
    "full_name": "full name",
    "sex": "sex",
    "nationality": "nationality",
    "place_of_origin": "place of origin",
    "place_of_residence": "place of residence",
    "issue_place": "issuing authority",
}


def _strip_label(field_label: str, text: str) -> str:
    """Take the text after the printed label - that's the value."""
    for separator in (":", ";"):
        if separator in text:
            tail = text.rsplit(separator, 1)[-1].strip()
            if tail:
                return tail
    keyword = _FIELD_LABEL_KEYWORDS.get(field_label)
    if keyword:
        index = text.lower().rfind(keyword)
        if index != -1:
            tail = text[index + len(keyword) :].strip()
            if tail:
                return tail
    return text.strip()


def _clean_punctuation(value: str) -> str:
    value = re.sub(r",\s*,", ",", value)
    return re.sub(r"\s+", " ", value).strip(" ,.")


def parse_layout_field(field_label: str, raw_text: str) -> str:
    """Clean one field's raw crop OCR text into its value."""
    text = raw_text.strip()
    if field_label in _UNLABELED_FIELDS:
        return text
    if field_label in _DATE_FIELDS:
        match = _DATE_RE.search(text)
        return match.group(0) if match else _clean_punctuation(_strip_label(field_label, text))
    if field_label == "id_number":
        match = _ID_RE.search(text)
        return match.group(0) if match else _clean_punctuation(_strip_label(field_label, text))
    return _clean_punctuation(_strip_label(field_label, text))


def parse_layout_fields(fields: dict[str, str]) -> dict[str, str]:
    """Clean every field in a DocumentLayoutResult.fields dict."""
    return {label: parse_layout_field(label, text) for label, text in fields.items()}


def is_cccd_expired(parsed_fields: dict[str, str], *, today: date | None = None) -> bool | None:
    """Whether the card's printed expiry_date has passed, or None when
    expiry_date wasn't parsed (field missed by YOLO/OCR) or isn't a clean
    dd/mm/yyyy value - an unknown expiry must never be reported as "not
    expired"."""
    raw = parsed_fields.get("expiry_date")
    if not raw:
        return None
    match = _DATE_COMPONENTS_RE.match(raw.strip())
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        expiry = date(year, month, day)
    except ValueError:
        return None
    return expiry < (today or date.today())
