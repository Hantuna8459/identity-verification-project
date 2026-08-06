from __future__ import annotations

import re
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


def find_td3_lines(lines: list[str]) -> tuple[str, str] | None:
    normalized = [normalize_line(line) for line in lines]
    exact = [line for line in normalized if len(line) == 44]
    for index in range(len(exact) - 1):
        if exact[index].startswith("P"):
            return exact[index], exact[index + 1]
    return None


def inspect_td3(lines: list[str]) -> dict[str, Any]:
    pair = find_td3_lines(lines)
    if pair is None:
        return {
            "status": "INCONCLUSIVE",
            "format": "ICAO_TD3",
            "mrz_detected": False,
            "all_check_digits_valid": False,
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
    return {
        "status": "OK" if all_valid else "INCONCLUSIVE",
        "format": "ICAO_TD3",
        "mrz_detected": True,
        "line_lengths": [len(first), len(second)],
        "check_digits": checks,
        "all_check_digits_valid": all_valid,
    }
