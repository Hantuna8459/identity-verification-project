from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class EkycSession(SQLModel, table=True):
    __tablename__ = "ekyc_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    subject_ref: str = Field(index=True, max_length=255)
    document_type: str = Field(index=True, max_length=32)
    stage: str = Field(default="AWAITING_MOBILE", index=True, max_length=32)
    decision: str = Field(default="PENDING", index=True, max_length=32)
    session_token_hash: str = Field(max_length=64)
    voice_challenge: str | None = Field(default=None, max_length=64)
    analysis: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    callback_url: str | None = Field(default=None, max_length=1024)
    callback_secret_ref: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(index=True)
    purge_after: datetime | None = Field(default=None, index=True)
    completed_at: datetime | None = Field(default=None)
    version: int = Field(default=1)


class Handoff(SQLModel, table=True):
    __tablename__ = "ekyc_handoffs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="ekyc_sessions.id", index=True)
    token_hash: str = Field(unique=True, index=True, max_length=64)
    capture_token_hash: str | None = Field(default=None, unique=True, index=True, max_length=64)
    status: str = Field(default="CREATED", index=True, max_length=24)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(index=True)
    claimed_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)


class Evidence(SQLModel, table=True):
    __tablename__ = "ekyc_evidence"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="ekyc_sessions.id", index=True)
    evidence_type: str = Field(index=True, max_length=48)
    storage_key: str = Field(unique=True, max_length=255)
    content_type: str = Field(max_length=128)
    size_bytes: int
    sha256: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=utcnow)


class ReviewTask(SQLModel, table=True):
    __tablename__ = "ekyc_review_tasks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="ekyc_sessions.id", unique=True, index=True)
    status: str = Field(default="OPEN", index=True, max_length=24)
    reason_codes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    reviewer_id: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, sa_column=Column(Text))
    decision: str | None = Field(default=None, max_length=32)
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = Field(default=None)


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID | None = Field(default=None, index=True)
    actor_type: str = Field(max_length=32)
    actor_id: str = Field(max_length=255)
    action: str = Field(index=True, max_length=128)
    outcome: str = Field(max_length=32)
    details: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)
