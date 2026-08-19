from __future__ import annotations

import re
from datetime import date
from typing import Any

_WEIGHTS = (7, 3, 1)


def _value(character: str) -> int:
    if character.isdigit():
        return int(character)
    if "A" <= character <= "Z":
        return ord(character) - ord("A") + 10
    if character == "<":
        return 0
    raise ValueError(f"Invalid MRZ character: {character!r}")


def valid_check_digit(value: str, digit: str) -> bool:
    if len(digit) != 1 or not digit.isdigit():
        return False
    checksum = sum(_value(char) * _WEIGHTS[index % 3] for index, char in enumerate(value))
    return checksum % 10 == int(digit)


def normalize_line(value: str) -> str:
    return re.sub(r"[^A-Z0-9<]", "", value.upper())


def _decode_mrz_date(digits: str, *, today: date) -> date | None:
    """Decode an MRZ YYMMDD field into a real date, picking whichever
    century (current, previous, next) lands closest to `today` - MRZ dates
    are two-digit years with no explicit century, and document validity
    windows are short (years, not decades), so "closest to today" is the
    standard disambiguation used for both birth and expiry fields."""
    if len(digits) != 6 or not digits.isdigit():
        return None
    year, month, day = int(digits[0:2]), int(digits[2:4]), int(digits[4:6])
    current_century = (today.year // 100) * 100
    candidates = []
    for century in (current_century, current_century - 100, current_century + 100):
        try:
            candidates.append(date(century + year, month, day))
        except ValueError:
            continue
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: abs((candidate - today).days))


def find_td3_lines(lines: list[str]) -> tuple[str, str] | None:
    normalized = [normalize_line(line) for line in lines]
    exact = [line for line in normalized if len(line) == 44]
    for index in range(len(exact) - 1):
        if exact[index].startswith("P"):
            return exact[index], exact[index + 1]
    return None


def inspect_td3(lines: list[str], *, today: date | None = None) -> dict[str, Any]:
    pair = find_td3_lines(lines)
    if pair is None:
        return {
            "status": "INCONCLUSIVE",
            "format": "ICAO_TD3",
            "mrz_detected": False,
            "all_check_digits_valid": False,
            "expired": None,
        }
    first, second = pair
    checks = {
        "document_number": valid_check_digit(second[0:9], second[9]),
        "birth_date": valid_check_digit(second[13:19], second[19]),
        "expiry_date": valid_check_digit(second[21:27], second[27]),
        "personal_number": valid_check_digit(second[28:42], second[42]),
        "composite": valid_check_digit(second[0:10] + second[13:20] + second[21:43], second[43]),
    }
    all_valid = all(checks.values())
    # Only trust the decoded date - and only ever surface a bool, never the
    # date itself - when its own check digit passed; otherwise OCR noise in
    # the date field could silently flip expired either way. The decoded
    # value never leaves this function (see test_icao_td3_check_digits_are_
    # valid_without_exposing_mrz) - MRZ carries PII this contract must not
    # echo back unmasked.
    expired: bool | None = None
    if checks["expiry_date"]:
        decoded = _decode_mrz_date(second[21:27], today=today or date.today())
        if decoded is not None:
            expired = decoded < (today or date.today())
    return {
        "status": "OK" if all_valid else "INCONCLUSIVE",
        "format": "ICAO_TD3",
        "mrz_detected": True,
        "line_lengths": [len(first), len(second)],
        "check_digits": checks,
        "all_check_digits_valid": all_valid,
        "expired": expired,
    }
