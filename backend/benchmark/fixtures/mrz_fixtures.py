from __future__ import annotations

import random
from dataclasses import dataclass

# Independent re-implementation of the ICAO 7-3-1 weighted check digit (not
# imported from ai_modules.ekyc.passport_mrz) so fixture ground truth isn't
# coupled to the exact code path it's meant to exercise.
_WEIGHTS = (7, 3, 1)
_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_DEFECT_KINDS = ("mutate_check_digit", "mutate_field_char", "truncate_line")
_SURNAMES = ("NGUYEN", "TRAN", "LE", "PHAM", "HOANG")
_GIVEN_NAMES = ("VAN A", "THI B", "MINH C", "QUOC D", "HUONG E")


def _char_value(character: str) -> int:
    if character.isdigit():
        return int(character)
    if "A" <= character <= "Z":
        return ord(character) - ord("A") + 10
    if character == "<":
        return 0
    raise ValueError(f"invalid MRZ character: {character!r}")


def _check_digit(value: str) -> str:
    checksum = sum(_char_value(c) * _WEIGHTS[i % 3] for i, c in enumerate(value))
    return str(checksum % 10)


def _random_field(rng: random.Random, length: int, pad_to: int) -> str:
    body = "".join(rng.choice(_ALPHABET) for _ in range(length))
    return body.ljust(pad_to, "<")[:pad_to]


@dataclass(frozen=True)
class MrzSample:
    sample_id: str
    lines: list[str]
    expected_status: str
    defect: str | None


def _build_valid_pair(rng: random.Random, surname: str, given: str) -> tuple[str, str]:
    doc_number = _random_field(rng, 9, 9)
    doc_check = _check_digit(doc_number)
    nationality = "VNM"
    birth = f"{rng.randint(50, 99):02d}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}"
    birth_check = _check_digit(birth)
    sex = rng.choice("MF<")
    expiry = f"{rng.randint(25, 35):02d}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}"
    expiry_check = _check_digit(expiry)
    personal = _random_field(rng, 10, 14)
    personal_check = _check_digit(personal)
    second = (
        doc_number
        + doc_check
        + nationality
        + birth
        + birth_check
        + sex
        + expiry
        + expiry_check
        + personal
        + personal_check
    )
    composite_input = second[0:10] + second[13:20] + second[21:43]
    second += _check_digit(composite_input)
    assert len(second) == 44

    name_field = f"{surname}<<{given}".upper().replace(" ", "<")
    first = ("P<" + nationality + name_field).ljust(44, "<")[:44]
    return first, second


def generate_mrz_samples(count: int, seed: int, defect_ratio: float = 0.3) -> list[MrzSample]:
    """Deterministic synthetic ICAO TD3 line pairs: ``defect_ratio`` of them
    intentionally corrupted so the benchmark measures detection, not just
    the happy path."""
    rng = random.Random(seed)
    samples: list[MrzSample] = []
    for index in range(count):
        surname = rng.choice(_SURNAMES)
        given = rng.choice(_GIVEN_NAMES)
        first, second = _build_valid_pair(rng, surname, given)
        defect: str | None = None
        expected_status = "OK"
        if rng.random() < defect_ratio:
            defect = rng.choice(_DEFECT_KINDS)
            chars = list(second)
            if defect == "mutate_check_digit":
                position = rng.choice([9, 19, 27, 42, 43])
                chars[position] = str((int(chars[position]) + rng.randint(1, 9)) % 10)
                second = "".join(chars)
            elif defect == "mutate_field_char":
                position = rng.choice([1, 2, 3, 4, 5, 14, 15, 16])
                chars[position] = rng.choice(_ALPHABET)
                second = "".join(chars)
            else:
                second = second[:40]
            expected_status = "INCONCLUSIVE"
        samples.append(
            MrzSample(
                sample_id=f"mrz-{seed}-{index:04d}",
                lines=[first, second],
                expected_status=expected_status,
                defect=defect,
            )
        )
    return samples
