from typing import Literal

from pydantic import BaseModel

VerdictType = Literal["real", "fake", "uncertain"]


class LipSyncResponse(BaseModel):
    verdict: VerdictType
    is_real: bool
    is_fake: bool
    confidence: float
    manipulation_probability: float
    av_offset_frames: int | None = None
    min_distance: float | None = None
    sync_confidence: float | None = None
    face_detected: bool | None = None
    detail: str | None = None
    engine: str = "syncnet_hf"
