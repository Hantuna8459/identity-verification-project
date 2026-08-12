from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Vietnamese names with real diacritics - the whole point of comparing
# against vietocr is Vietnamese text, so the fixture must actually contain
# it, not a stripped-ASCII stand-in.
_SURNAMES = ("NGUYỄN", "TRẦN", "LÊ", "PHẠM", "HOÀNG", "VŨ", "ĐẶNG", "BÙI")
_GIVEN_NAMES = (
    "VĂN AN",
    "THỊ BÍCH",
    "MINH CHÂU",
    "QUỐC ĐẠT",
    "THU HƯƠNG",
    "NGỌC PHƯỢNG",
    "THANH GIANG",
)
_FONT_SIZE = 42
_IMAGE_SIZE = (900, 220)
_LINE_HEIGHT = 60
_MARGIN = 30
_CROP_TOP_PAD = 8

# PIL's built-in default font has no Vietnamese diacritic glyphs at all (they
# render as tofu boxes) - DejaVu Sans does. Fall back to the built-in font
# only if no Vietnamese-capable one is found, and flag that on the sample so
# a report can say fidelity was reduced instead of silently pretending
# otherwise.
_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
)


def _load_font(size: int) -> tuple[ImageFont.FreeTypeFont, bool]:
    for candidate in _FONT_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), size), True
    return ImageFont.load_default(size=size), False


@dataclass(frozen=True)
class OcrSample:
    sample_id: str
    image: np.ndarray
    ground_truth_lines: list[str]
    # Per-line crops for line-level recognizers (e.g. vietocr) that expect an
    # already-detected text region, unlike RapidOCR which detects+recognizes
    # the whole page itself.
    line_crops: list[np.ndarray]


def _random_id_number(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(12))


def _random_date(rng: random.Random) -> str:
    return f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/{rng.randint(1960, 2006)}"


def _render(lines: list[str], font: ImageFont.FreeTypeFont) -> tuple[np.ndarray, list[np.ndarray]]:
    image = Image.new("RGB", _IMAGE_SIZE, "white")
    draw = ImageDraw.Draw(image)
    y = _MARGIN
    for line in lines:
        draw.text((_MARGIN, y), line, fill="black", font=font)
        y += _LINE_HEIGHT
    array = np.array(image)
    crops = []
    for index in range(len(lines)):
        top = max(0, _MARGIN + index * _LINE_HEIGHT - _CROP_TOP_PAD)
        bottom = min(array.shape[0], top + _LINE_HEIGHT)
        crops.append(array[top:bottom, :])
    return array, crops


def generate_ocr_samples(count: int, seed: int) -> tuple[list[OcrSample], bool]:
    """Deterministic synthetic CCCD-style field lines (Vietnamese name/ID
    number/DOB) rendered to an image, paired with known ground truth text, so
    document_ocr can be scored with CER/WER without any external dataset.

    Returns (samples, has_diacritics_font) - callers should surface
    has_diacritics_font in any report, since without it the names fall back
    to a font that can't render Vietnamese diacritics and the benchmark no
    longer tests what it claims to."""
    font, has_diacritics_font = _load_font(_FONT_SIZE)
    rng = random.Random(seed)
    samples: list[OcrSample] = []
    for index in range(count):
        surname = rng.choice(_SURNAMES)
        given = rng.choice(_GIVEN_NAMES)
        lines = [
            f"{surname} {given}",
            f"SO: {_random_id_number(rng)}",
            _random_date(rng),
        ]
        image, crops = _render(lines, font)
        samples.append(
            OcrSample(
                sample_id=f"ocr-{seed}-{index:04d}",
                image=image,
                ground_truth_lines=lines,
                line_crops=crops,
            )
        )
    return samples, has_diacritics_font
