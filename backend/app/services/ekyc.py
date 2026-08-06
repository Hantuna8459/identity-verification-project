from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, delete, select

from app.adapters.security import TokenService
from app.core.config import Settings
from app.domain.models import AuditEvent, EkycSession, Evidence, Handoff, ReviewTask
from app.domain.ports import EkycAnalyzer, EvidencePayload, EvidenceStorage

TERMINAL_STAGES = {"COMPLETED", "CANCELLED", "EXPIRED", "PURGED"}


class EkycService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        tokens: TokenService,
        storage: EvidenceStorage,
        analyzer: EkycAnalyzer,
    ) -> None:
        self.db = db
        self.settings = settings
        self.tokens = tokens
        self.storage = storage
        self.analyzer = analyzer

    def create_session(
        self, subject_ref: str, document_type: str | None, callback_url: str | None
    ) -> tuple[EkycSession, str]:
        now = datetime.now(UTC).replace(tzinfo=None)
        raw_token = self.tokens.issue()
        item = EkycSession(
            subject_ref=subject_ref,
            document_type=document_type or "UNSELECTED",
            session_token_hash=self.tokens.digest(raw_token),
            callback_url=callback_url,
            expires_at=now + timedelta(minutes=self.settings.session_ttl_minutes),
        )
        self.db.add(item)
        self._audit(item.id, "VID_CLIENT", "vid", "session.create")
        self.db.commit()
        self.db.refresh(item)
        return item, raw_token

    def require_session_token(self, session_id: uuid.UUID, token: str) -> EkycSession:
        item = self.db.get(EkycSession, session_id)
        if item is None or not self.tokens.matches(token, item.session_token_hash):
            raise PermissionError("Invalid session token")
        self._expire_if_needed(item)
        return item

    def create_handoff(self, item: EkycSession) -> tuple[Handoff, str]:
        now = datetime.now(UTC).replace(tzinfo=None)
        active = self.db.exec(
            select(Handoff).where(
                Handoff.session_id == item.id,
                Handoff.status.in_(["CREATED", "CLAIMED"]),
            )
        ).all()
        for handoff in active:
            handoff.status = "REVOKED"
            handoff.revoked_at = now
            self.db.add(handoff)
        raw_token = self.tokens.issue()
        handoff = Handoff(
            session_id=item.id,
            token_hash=self.tokens.digest(raw_token),
            expires_at=now + timedelta(seconds=self.settings.handoff_ttl_seconds),
        )
        item.stage = "AWAITING_MOBILE"
        item.updated_at = now
        item.version += 1
        self.db.add(handoff)
        self.db.add(item)
        self._audit(item.id, "VID_CLIENT", "vid", "handoff.create")
        self.db.commit()
        self.db.refresh(handoff)
        return handoff, raw_token

    def claim_handoff(self, raw_token: str) -> tuple[EkycSession, Handoff, str]:
        digest = self.tokens.digest(raw_token)
        handoff = self.db.exec(select(Handoff).where(Handoff.token_hash == digest)).first()
        now = datetime.now(UTC).replace(tzinfo=None)
        if handoff is None or handoff.status != "CREATED" or handoff.expires_at <= now:
            raise PermissionError("Handoff token is invalid, used, revoked or expired")
        item = self.db.get(EkycSession, handoff.session_id)
        if item is None or item.stage in TERMINAL_STAGES:
            raise PermissionError("Session is not available")
        capture_token = self.tokens.issue()
        handoff.capture_token_hash = self.tokens.digest(capture_token)
        handoff.status = "CLAIMED"
        handoff.claimed_at = now
        item.stage = "CAPTURING"
        item.updated_at = now
        item.version += 1
        self.db.add(handoff)
        self.db.add(item)
        self._audit(item.id, "CAPTURE_CLIENT", "capture", "handoff.claim")
        self.db.commit()
        return item, handoff, capture_token

    def select_document_type(self, item: EkycSession, document_type: str) -> EkycSession:
        selected = "PASSPORT_TD3" if document_type == "PASSPORT" else "CCCD"
        evidence = self.db.exec(select(Evidence).where(Evidence.session_id == item.id)).first()
        if evidence is not None and item.document_type != selected:
            raise ValueError("Document type cannot be changed after evidence capture")
        item.document_type = selected
        item.updated_at = datetime.now(UTC).replace(tzinfo=None)
        item.version += 1
        self.db.add(item)
        self._audit(
            item.id,
            "CAPTURE_CLIENT",
            "capture",
            "document.type.select",
            {"document_type": selected},
        )
        self.db.commit()
        self.db.refresh(item)
        return item

    def require_capture_token(self, token: str) -> tuple[EkycSession, Handoff]:
        digest = self.tokens.digest(token)
        handoff = self.db.exec(select(Handoff).where(Handoff.capture_token_hash == digest)).first()
        if handoff is None or handoff.status != "CLAIMED":
            raise PermissionError("Invalid capture token")
        if handoff.claimed_at is None or handoff.claimed_at + timedelta(
            minutes=self.settings.capture_ttl_minutes
        ) <= datetime.now(UTC).replace(tzinfo=None):
            raise PermissionError("Capture token expired")
        item = self.db.get(EkycSession, handoff.session_id)
        if item is None or item.stage != "CAPTURING":
            raise PermissionError("Session is not accepting evidence")
        return item, handoff

    def create_voice_challenge(self, item: EkycSession) -> str:
        challenge = " ".join(str(random.SystemRandom().randint(0, 9)) for _ in range(6))
        item.voice_challenge = challenge
        item.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.add(item)
        self._audit(item.id, "CAPTURE_CLIENT", "capture", "voice.challenge.create")
        self.db.commit()
        return challenge

    def add_evidence(
        self, item: EkycSession, evidence_type: str, content_type: str, payload: bytes
    ) -> Evidence:
        previous = self.db.exec(
            select(Evidence).where(
                Evidence.session_id == item.id,
                Evidence.evidence_type == evidence_type,
            )
        ).all()
        for existing in previous:
            self.storage.delete(existing.storage_key)
            self.db.delete(existing)
        stored = self.storage.put(item.id, evidence_type, payload)
        evidence = Evidence(
            session_id=item.id,
            evidence_type=evidence_type,
            storage_key=stored.storage_key,
            content_type=content_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
        )
        self.db.add(evidence)
        self._audit(
            item.id, "CAPTURE_CLIENT", "capture", "evidence.upload", {"type": evidence_type}
        )
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def submit(self, item: EkycSession, handoff: Handoff) -> EkycSession:
        if item.document_type == "UNSELECTED":
            raise ValueError("Document type has not been selected")
        evidence = self.db.exec(select(Evidence).where(Evidence.session_id == item.id)).all()
        types = {entry.evidence_type for entry in evidence}
        required = {"SELFIE_VIDEO"}
        if item.document_type == "PASSPORT_TD3":
            required.add("PASSPORT_PAGE")
        else:
            required.update({"DOCUMENT_FRONT", "DOCUMENT_BACK"})
        missing = sorted(required - types)
        if missing:
            raise ValueError(f"Missing required evidence: {', '.join(missing)}")
        if not item.voice_challenge:
            raise ValueError("Voice challenge has not been created")
        item.stage = "PROCESSING"
        item.updated_at = datetime.now(UTC).replace(tzinfo=None)
        item.version += 1
        self.db.add(item)
        self.db.commit()
        try:
            payloads = [
                EvidencePayload(
                    evidence_type=entry.evidence_type,
                    content_type=entry.content_type,
                    payload=self.storage.get(entry.storage_key),
                )
                for entry in evidence
            ]
            analysis = self.analyzer.analyze(
                item.id, item.document_type, item.voice_challenge, payloads
            )
            item.analysis = analysis
            item.stage = "MANUAL_REVIEW"
            review = ReviewTask(
                session_id=item.id,
                reason_codes=analysis.get("summary_reason_codes", ["INCONCLUSIVE"]),
            )
            self.db.add(review)
        except Exception as exc:
            item.analysis = {"error": type(exc).__name__, "reason_codes": ["PROCESSING_FAILED"]}
            item.stage = "PROCESSING_FAILED"
        handoff.status = "CONSUMED"
        item.updated_at = datetime.now(UTC).replace(tzinfo=None)
        item.version += 1
        self.db.add(handoff)
        self.db.add(item)
        self._audit(item.id, "SYSTEM", "analyzer", "session.submit", {"stage": item.stage})
        self.db.commit()
        self.db.refresh(item)
        return item

    def rerun_document_ocr(self, session_id: uuid.UUID, reviewer_id: str) -> dict[str, Any]:
        if (
            not self.settings.demo_ocr_rerun_enabled
            or self.settings.model_profile != "technical_demo"
        ):
            raise PermissionError("Demo OCR rerun is disabled")
        item = self.db.get(EkycSession, session_id)
        review = self.db.exec(select(ReviewTask).where(ReviewTask.session_id == session_id)).first()
        if item is None or review is None or review.status != "OPEN":
            raise ValueError("Open review task not found")

        expected_types = (
            {"PASSPORT_PAGE"}
            if item.document_type == "PASSPORT_TD3"
            else {"DOCUMENT_FRONT", "DOCUMENT_BACK"}
        )
        evidence = [
            entry
            for entry in self.db.exec(
                select(Evidence).where(Evidence.session_id == session_id)
            ).all()
            if entry.evidence_type in expected_types
        ]
        present_types = {entry.evidence_type for entry in evidence}
        missing = sorted(expected_types - present_types)
        if missing:
            raise ValueError(f"Missing document evidence: {', '.join(missing)}")

        payloads = [
            EvidencePayload(
                evidence_type=entry.evidence_type,
                content_type=entry.content_type,
                payload=self.storage.get(entry.storage_key),
            )
            for entry in evidence
        ]
        result = self.analyzer.analyze_document(item.document_type, payloads)
        self._audit(
            item.id,
            "REVIEWER",
            reviewer_id,
            "review.ocr_rerun",
            {"document_type": item.document_type, "evidence_types": sorted(present_types)},
        )
        self.db.commit()
        return result

    def decide(
        self, session_id: uuid.UUID, reviewer_id: str, decision: str, notes: str
    ) -> EkycSession:
        item = self.db.get(EkycSession, session_id)
        review = self.db.exec(select(ReviewTask).where(ReviewTask.session_id == session_id)).first()
        if item is None or review is None or review.status != "OPEN":
            raise ValueError("Open review task not found")
        now = datetime.now(UTC).replace(tzinfo=None)
        review.status = "RESOLVED"
        review.reviewer_id = reviewer_id
        review.decision = decision
        review.notes = notes
        review.resolved_at = now
        item.stage = "COMPLETED"
        item.decision = decision
        item.completed_at = now
        item.updated_at = now
        item.purge_after = now + timedelta(hours=self.settings.development_retention_hours)
        item.version += 1
        self.db.add(review)
        self.db.add(item)
        self._audit(item.id, "REVIEWER", reviewer_id, "review.decide", {"decision": decision})
        self.db.commit()
        self.db.refresh(item)
        return item

    def purge_due(self, actor_id: str) -> list[uuid.UUID]:
        now = datetime.now(UTC).replace(tzinfo=None)
        due = self.db.exec(
            select(EkycSession).where(
                EkycSession.purge_after.is_not(None),
                EkycSession.purge_after <= now,
                EkycSession.stage != "PURGED",
            )
        ).all()
        purged: list[uuid.UUID] = []
        for item in due:
            evidence = self.db.exec(select(Evidence).where(Evidence.session_id == item.id)).all()
            for entry in evidence:
                self.storage.delete(entry.storage_key)
            self.db.exec(delete(Evidence).where(Evidence.session_id == item.id))
            self.db.exec(delete(Handoff).where(Handoff.session_id == item.id))
            self.db.exec(delete(ReviewTask).where(ReviewTask.session_id == item.id))
            item.analysis = None
            item.subject_ref = f"purged:{item.id}"
            item.stage = "PURGED"
            item.updated_at = now
            self.db.add(item)
            self._audit(item.id, "SYSTEM", actor_id, "session.purge")
            purged.append(item.id)
        self.db.commit()
        return purged

    def session_public(self, item: EkycSession) -> dict[str, Any]:
        actions = {
            "AWAITING_MOBILE": "SCAN_QR",
            "CAPTURING": "CAPTURE_EVIDENCE",
            "PROCESSING": "WAIT",
            "MANUAL_REVIEW": "WAIT_FOR_REVIEW",
            "PROCESSING_FAILED": "CONTACT_SUPPORT",
            "COMPLETED": "DONE",
            "PURGED": "NONE",
        }
        return {
            "id": item.id,
            "document_type": item.document_type,
            "stage": item.stage,
            "decision": item.decision,
            "voice_challenge": item.voice_challenge,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "expires_at": item.expires_at,
            "next_action": actions.get(item.stage, "WAIT"),
        }

    def _expire_if_needed(self, item: EkycSession) -> None:
        if item.stage not in TERMINAL_STAGES and item.expires_at <= datetime.now(UTC).replace(
            tzinfo=None
        ):
            item.stage = "EXPIRED"
            item.purge_after = datetime.now(UTC).replace(tzinfo=None) + timedelta(
                hours=self.settings.development_retention_hours
            )
            self.db.add(item)
            self.db.commit()

    def _audit(
        self,
        session_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.db.add(
            AuditEvent(
                session_id=session_id,
                actor_type=actor_type,
                actor_id=actor_id,
                action=action,
                outcome="SUCCESS",
                details=details or {},
            )
        )
