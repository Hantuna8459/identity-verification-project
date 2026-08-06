from __future__ import annotations

import uuid
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlmodel import Session, select

from app.adapters.analyzer import OfflineModelAnalyzer
from app.adapters.capability_registry import CapabilityRegistry
from app.adapters.ekyc_providers import build_capability_registry
from app.adapters.security import TokenService
from app.adapters.storage import EncryptedLocalEvidenceStorage
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.domain.models import AuditEvent, EkycSession, Evidence, Handoff, ReviewTask
from app.domain.schemas import (
    ClaimRequest,
    ClaimResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    HandoffResponse,
    ReviewDecisionRequest,
    SelectDocumentTypeRequest,
    SessionPublic,
)
from app.services.ekyc import EkycService

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def capability_registry(settings: SettingsDep, request: Request) -> CapabilityRegistry:
    """Build the provider registry once per distinct Settings instance and
    reuse it across requests - the registry (and the model engines its
    providers lazily construct) would otherwise be rebuilt on every request,
    since `app` is a single long-lived FastAPI instance. Keyed by
    `id(settings)` rather than unconditionally cached so tests that override
    `get_settings` per-test (a fresh `tmp_path` model dir each time) get an
    isolated registry instead of a stale one left over from another test.
    """
    cached: tuple[int, CapabilityRegistry] | None = getattr(
        request.app.state, "capability_registry_cache", None
    )
    settings_id = id(settings)
    if cached is None or cached[0] != settings_id:
        cached = (settings_id, build_capability_registry(settings))
        request.app.state.capability_registry_cache = cached
    return cached[1]


CapabilityRegistryDep = Annotated[CapabilityRegistry, Depends(capability_registry)]


def service(db: DbDep, settings: SettingsDep, registry: CapabilityRegistryDep) -> EkycService:
    return EkycService(
        db=db,
        settings=settings,
        tokens=TokenService(settings.token_secret),
        storage=EncryptedLocalEvidenceStorage(settings.evidence_dir, settings.evidence_key),
        analyzer=OfflineModelAnalyzer(
            registry,
            settings.require_models,
            profile=settings.model_profile,
            max_video_frames=settings.max_video_frames,
            max_face_match_frames=settings.max_face_match_frames,
            replay_suspicious_threshold=settings.replay_suspicious_threshold,
            camera_injection_suspicious_threshold=settings.camera_injection_suspicious_threshold,
        ),
    )


def require_vid_client(
    settings: SettingsDep,
    x_v_id_client_key: Annotated[str | None, Header()] = None,
) -> str:
    if x_v_id_client_key != settings.vid_client_key:
        raise HTTPException(status_code=401, detail="Invalid V-ID client credential")
    return "vid-client"


def require_reviewer(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    expected = f"Bearer {settings.reviewer_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid reviewer credential")
    return "local-reviewer"


def capture_bearer(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Capture token required")
    return authorization.removeprefix("Bearer ").strip()


def session_token(x_session_token: Annotated[str | None, Header()] = None) -> str:
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Session token required")
    return x_session_token


def _readiness(settings: Settings, registry: CapabilityRegistry) -> dict[str, Any]:
    analyzer = OfflineModelAnalyzer(
        registry,
        settings.require_models,
        profile=settings.model_profile,
        max_video_frames=settings.max_video_frames,
        max_face_match_frames=settings.max_face_match_frames,
    )
    return analyzer.readiness()


@router.get("/utils/health-check")
def health(settings: SettingsDep, registry: CapabilityRegistryDep) -> dict[str, Any]:
    """Unauthenticated by design (Docker HEALTHCHECK, load balancers, uptime
    monitors all need this reachable without credentials) - the response must
    therefore never carry provider/model identity or approval detail. See
    /admin/readiness for the full breakdown, behind reviewer auth."""
    readiness = _readiness(settings, registry)
    if settings.require_models and not readiness["ready"]:
        raise HTTPException(status_code=503, detail={"status": "not_ready"})
    return {"status": "ok"}


@router.get("/admin/readiness")
def admin_readiness(
    settings: SettingsDep,
    registry: CapabilityRegistryDep,
    _: Annotated[str, Depends(require_reviewer)],
) -> dict[str, Any]:
    return _readiness(settings, registry)


@router.post("/ekyc/sessions", response_model=CreateSessionResponse, status_code=201)
def create_session(
    payload: CreateSessionRequest,
    core: Annotated[EkycService, Depends(service)],
    _: Annotated[str, Depends(require_vid_client)],
) -> CreateSessionResponse:
    callback_url = str(payload.callback_url) if payload.callback_url else None
    if callback_url and core.settings.webhook_allowlist:
        if not any(callback_url.startswith(prefix) for prefix in core.settings.webhook_allowlist):
            raise HTTPException(status_code=400, detail="Callback URL is not allowlisted")
    item, raw_token = core.create_session(payload.subject_ref, payload.document_type, callback_url)
    return CreateSessionResponse(
        session_id=item.id,
        session_token=raw_token,
        stage=item.stage,
        expires_at=item.expires_at,
    )


@router.post("/ekyc/sessions/{session_id}/handoffs", response_model=HandoffResponse)
def create_handoff(
    session_id: uuid.UUID,
    core: Annotated[EkycService, Depends(service)],
    token: Annotated[str, Depends(session_token)],
) -> HandoffResponse:
    try:
        item = core.require_session_token(session_id, token)
        handoff, raw_token = core.create_handoff(item)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    query = urlencode({"t": raw_token})
    return HandoffResponse(
        handoff_id=handoff.id,
        handoff_token=raw_token,
        capture_url=f"{core.settings.frontend_url.rstrip('/')}/capture?{query}",
        expires_at=handoff.expires_at,
    )


@router.post("/ekyc/handoffs/claim", response_model=ClaimResponse)
def claim_handoff(
    payload: ClaimRequest,
    core: Annotated[EkycService, Depends(service)],
) -> ClaimResponse:
    try:
        item, handoff, capture_token = core.claim_handoff(payload.token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return ClaimResponse(
        session_id=item.id,
        capture_token=capture_token,
        document_type=None if item.document_type == "UNSELECTED" else item.document_type,
        stage=item.stage,
        expires_at=item.expires_at,
    )


@router.post("/ekyc/capture/document-type")
def select_document_type(
    payload: SelectDocumentTypeRequest,
    core: Annotated[EkycService, Depends(service)],
    token: Annotated[str, Depends(capture_bearer)],
) -> dict[str, str]:
    try:
        item, _ = core.require_capture_token(token)
        item = core.select_document_type(item, payload.document_type)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"document_type": item.document_type}


@router.get("/ekyc/sessions/{session_id}", response_model=SessionPublic)
def get_session_status(
    session_id: uuid.UUID,
    core: Annotated[EkycService, Depends(service)],
    token: Annotated[str, Depends(session_token)],
) -> dict[str, Any]:
    try:
        item = core.require_session_token(session_id, token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return core.session_public(item)


@router.get("/ekyc/sessions/{session_id}/handoff-status")
def handoff_status(
    session_id: uuid.UUID,
    core: Annotated[EkycService, Depends(service)],
    token: Annotated[str, Depends(session_token)],
) -> dict[str, Any]:
    try:
        item = core.require_session_token(session_id, token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    handoff = core.db.exec(
        select(Handoff).where(Handoff.session_id == item.id).order_by(Handoff.created_at.desc())
    ).first()
    return {
        "session_id": item.id,
        "stage": item.stage,
        "handoff_status": handoff.status if handoff else None,
        "mobile_connected": bool(handoff and handoff.status in {"CLAIMED", "CONSUMED"}),
    }


@router.post("/ekyc/sessions/{session_id}/handoffs/{handoff_id}/revoke")
def revoke_handoff(
    session_id: uuid.UUID,
    handoff_id: uuid.UUID,
    core: Annotated[EkycService, Depends(service)],
    token: Annotated[str, Depends(session_token)],
) -> dict[str, str]:
    try:
        item = core.require_session_token(session_id, token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    handoff = core.db.get(Handoff, handoff_id)
    if handoff is None or handoff.session_id != item.id:
        raise HTTPException(status_code=404, detail="Handoff not found")
    handoff.status = "REVOKED"
    core.db.add(handoff)
    core.db.commit()
    return {"status": "REVOKED"}


@router.post("/ekyc/capture/voice-challenge")
def create_voice_challenge(
    core: Annotated[EkycService, Depends(service)],
    token: Annotated[str, Depends(capture_bearer)],
) -> dict[str, str]:
    try:
        item, _ = core.require_capture_token(token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"challenge": core.create_voice_challenge(item)}


ALLOWED_CONTENT_TYPES = {
    "DOCUMENT_FRONT": {"image/jpeg", "image/png", "image/webp"},
    "DOCUMENT_BACK": {"image/jpeg", "image/png", "image/webp"},
    "PASSPORT_PAGE": {"image/jpeg", "image/png", "image/webp"},
    "SELFIE_VIDEO": {"video/mp4", "video/webm", "video/quicktime"},
}


@router.post("/ekyc/capture/evidence/{evidence_type}", status_code=201)
async def upload_evidence(
    evidence_type: str,
    core: Annotated[EkycService, Depends(service)],
    token: Annotated[str, Depends(capture_bearer)],
    file: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    evidence_type = evidence_type.upper()
    allowed = ALLOWED_CONTENT_TYPES.get(evidence_type)
    if allowed is None:
        raise HTTPException(status_code=400, detail="Unsupported evidence type")
    content_type = (file.content_type or "").lower()
    if content_type not in allowed:
        raise HTTPException(status_code=415, detail="Unsupported media type")
    try:
        item, _ = core.require_capture_token(token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    payload = await file.read()
    max_mb = (
        core.settings.max_video_size_mb
        if evidence_type == "SELFIE_VIDEO"
        else core.settings.max_document_size_mb
    )
    if not payload or len(payload) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File must be between 1 byte and {max_mb} MB")
    entry = core.add_evidence(item, evidence_type, content_type, payload)
    return {
        "evidence_id": entry.id,
        "evidence_type": entry.evidence_type,
        "size_bytes": entry.size_bytes,
        "sha256": entry.sha256,
    }


@router.post("/ekyc/capture/submit")
def submit_capture(
    core: Annotated[EkycService, Depends(service)],
    token: Annotated[str, Depends(capture_bearer)],
) -> dict[str, Any]:
    try:
        item, handoff = core.require_capture_token(token)
        item = core.submit(item, handoff)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"session_id": item.id, "stage": item.stage, "decision": item.decision}


@router.get("/reviews")
def list_reviews(
    db: DbDep,
    _: Annotated[str, Depends(require_reviewer)],
    review_status: str = Query(default="OPEN", alias="status"),
) -> list[dict[str, Any]]:
    statement = select(ReviewTask).where(ReviewTask.status == review_status.upper())
    tasks = db.exec(statement.order_by(ReviewTask.created_at.desc())).all()
    result: list[dict[str, Any]] = []
    for task in tasks:
        item = db.get(EkycSession, task.session_id)
        if item:
            result.append(
                {
                    "review_id": task.id,
                    "session_id": item.id,
                    "document_type": item.document_type,
                    "stage": item.stage,
                    "decision": item.decision,
                    "reason_codes": task.reason_codes,
                    "created_at": task.created_at,
                }
            )
    return result


@router.get("/reviews/{session_id}")
def review_detail(
    session_id: uuid.UUID,
    db: DbDep,
    settings: SettingsDep,
    _: Annotated[str, Depends(require_reviewer)],
) -> dict[str, Any]:
    item = db.get(EkycSession, session_id)
    task = db.exec(select(ReviewTask).where(ReviewTask.session_id == session_id)).first()
    if item is None or task is None:
        raise HTTPException(status_code=404, detail="Review not found")
    evidence = db.exec(select(Evidence).where(Evidence.session_id == session_id)).all()
    return {
        "session": {
            "id": item.id,
            "subject_ref": item.subject_ref,
            "document_type": item.document_type,
            "stage": item.stage,
            "decision": item.decision,
            "created_at": item.created_at,
        },
        "review": {
            "id": task.id,
            "status": task.status,
            "reason_codes": task.reason_codes,
            "notes": task.notes,
        },
        "analysis": item.analysis,
        "demo_capabilities": {
            "ocr_rerun": settings.demo_ocr_rerun_enabled
            and settings.model_profile == "technical_demo"
        },
        "evidence": [
            {
                "id": entry.id,
                "type": entry.evidence_type,
                "content_type": entry.content_type,
                "size_bytes": entry.size_bytes,
                "sha256": entry.sha256,
            }
            for entry in evidence
        ],
    }


@router.post("/reviews/{session_id}/ocr-runs")
def rerun_review_ocr(
    session_id: uuid.UUID,
    response: Response,
    core: Annotated[EkycService, Depends(service)],
    reviewer: Annotated[str, Depends(require_reviewer)],
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    try:
        return core.rerun_document_ocr(session_id, reviewer)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="Demo OCR rerun is unavailable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/reviews/{session_id}/decisions")
def decide_review(
    session_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    core: Annotated[EkycService, Depends(service)],
    reviewer: Annotated[str, Depends(require_reviewer)],
) -> dict[str, Any]:
    try:
        item = core.decide(session_id, reviewer, payload.decision, payload.notes)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"session_id": item.id, "stage": item.stage, "decision": item.decision}


@router.post("/admin/purge/run")
def run_purge(
    core: Annotated[EkycService, Depends(service)],
    reviewer: Annotated[str, Depends(require_reviewer)],
) -> dict[str, Any]:
    purged = core.purge_due(reviewer)
    return {"purged_count": len(purged), "session_ids": purged}


@router.get("/admin/audit-events")
def audit_events(
    db: DbDep,
    _: Annotated[str, Depends(require_reviewer)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditEvent]:
    return list(
        db.exec(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    )
