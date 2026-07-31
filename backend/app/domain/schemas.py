from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

DocumentType = Literal["CCCD", "CCCD_2021", "CAN_CUOC_2024", "PASSPORT_TD3"]
CaptureDocumentType = Literal["CCCD", "PASSPORT"]


class CreateSessionRequest(BaseModel):
    subject_ref: str = Field(min_length=3, max_length=255)
    document_type: DocumentType | None = None
    callback_url: HttpUrl | None = None


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    session_token: str
    stage: str
    expires_at: datetime


class HandoffResponse(BaseModel):
    handoff_id: uuid.UUID
    handoff_token: str
    capture_url: str
    expires_at: datetime


class ClaimRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)


class ClaimResponse(BaseModel):
    session_id: uuid.UUID
    capture_token: str
    document_type: str | None
    stage: str
    expires_at: datetime


class SelectDocumentTypeRequest(BaseModel):
    document_type: CaptureDocumentType


class ReviewDecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    notes: str = Field(min_length=3, max_length=2000)


class SessionPublic(BaseModel):
    id: uuid.UUID
    document_type: str
    stage: str
    decision: str
    voice_challenge: str | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    next_action: str
