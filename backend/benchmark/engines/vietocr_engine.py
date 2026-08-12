from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

DEFAULT_WEIGHTS_PATH = Path("vietocr/vietocr_vgg_transformer.pth")
DEFAULT_CONFIG_PATH = Path("vietocr/vgg_transformer_config.yml")


class VietocrEngine:
    """vietocr vgg_transformer recognizer - line-level only, no text
    detection (unlike LocalOcr/RapidOCR, which detects and recognizes a
    whole page). Callers must pass an already-cropped single-line image.

    Always loads config/weights from local files, never vocr.vn: vietocr's
    own `Cfg.load_config_from_name()` and `Predictor()` both reach the
    network by default (config from vocr.vn, weights via an http(s) URL
    check), which the M0 governance rule "adapter không được tự download
    model hoặc artifact runtime" forbids. `vgg_transformer_config.yml` was
    fetched once, offline from then on; the weight is fetched only via
    `scripts/models.py` (checksum-verified, models/manifest.json-driven).
    """

    def __init__(self, weights_path: Path, config_path: Path) -> None:
        if not config_path.is_file():
            raise FileNotFoundError(f"vietocr config not found at {config_path}")
        if not weights_path.is_file():
            raise FileNotFoundError(
                f"vietocr weights not found at {weights_path}; download via "
                "'python scripts/models.py --profile benchmark_only "
                "--include vietocr-vgg-transformer' first (never auto-downloaded "
                "at benchmark runtime)"
            )

        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor

        cfg = Cfg.load_config_from_file(str(config_path))
        cfg["weights"] = str(weights_path)
        cfg["device"] = "cpu"
        cfg["cnn"]["pretrained"] = False
        cfg["predictor"]["beamsearch"] = False
        self._predictor = Predictor(cfg)

    def read_line(self, image: np.ndarray) -> tuple[str, float]:
        text, prob = self._predictor.predict(Image.fromarray(image), return_prob=True)
        return text.strip(), float(prob)
