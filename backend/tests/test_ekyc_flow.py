from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.analyzer import OfflineModelAnalyzer

VID_HEADERS = {"X-V-ID-Client-Key": "test-vid-key"}
REVIEWER_HEADERS = {"Authorization": "Bearer test-reviewer-token"}


def create_claimed_session(client: TestClient, document_type: str = "CAN_CUOC_2024") -> dict:
    created = client.post(
        "/api/v2/ekyc/sessions",
        headers=VID_HEADERS,
        json={"subject_ref": "opaque-user-001", "document_type": document_type},
    )
    assert created.status_code == 201, created.text
    session = created.json()
    desktop_headers = {"X-Session-Token": session["session_token"]}
    handoff = client.post(
        f"/api/v2/ekyc/sessions/{session['session_id']}/handoffs",
        headers=desktop_headers,
    )
    assert handoff.status_code == 200, handoff.text
    handoff_data = handoff.json()
    claim = client.post(
        "/api/v2/ekyc/handoffs/claim",
        json={"token": handoff_data["handoff_token"]},
    )
    assert claim.status_code == 200, claim.text
    return {**session, **claim.json(), "desktop_headers": desktop_headers, "handoff": handoff_data}


def upload(client: TestClient, capture_token: str, kind: str, media_type: str) -> None:
    response = client.post(
        f"/api/v2/ekyc/capture/evidence/{kind}",
        headers={"Authorization": f"Bearer {capture_token}"},
        files={"file": (f"{kind.lower()}.bin", b"synthetic-evidence-content", media_type)},
    )
    assert response.status_code == 201, response.text


def test_full_cccd_qr_capture_and_manual_review(client: TestClient) -> None:
    flow = create_claimed_session(client)
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}

    replay = client.post(
        "/api/v2/ekyc/handoffs/claim",
        json={"token": flow["handoff"]["handoff_token"]},
    )
    assert replay.status_code == 401

    challenge = client.post("/api/v2/ekyc/capture/voice-challenge", headers=capture_headers)
    assert challenge.status_code == 200
    assert len(challenge.json()["challenge"].split()) == 6

    upload(client, flow["capture_token"], "DOCUMENT_FRONT", "image/jpeg")
    upload(client, flow["capture_token"], "DOCUMENT_BACK", "image/jpeg")
    upload(client, flow["capture_token"], "SELFIE_VIDEO", "video/webm")

    submitted = client.post("/api/v2/ekyc/capture/submit", headers=capture_headers)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["stage"] == "MANUAL_REVIEW"

    reviews = client.get("/api/v2/reviews", headers=REVIEWER_HEADERS)
    assert reviews.status_code == 200
    assert len(reviews.json()) == 1
    assert reviews.json()[0]["session_id"] == flow["session_id"]

    decision = client.post(
        f"/api/v2/reviews/{flow['session_id']}/decisions",
        headers=REVIEWER_HEADERS,
        json={"decision": "APPROVED", "notes": "Synthetic fixture reviewed successfully."},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["decision"] == "APPROVED"

    status = client.get(
        f"/api/v2/ekyc/sessions/{flow['session_id']}",
        headers=flow["desktop_headers"],
    )
    assert status.status_code == 200
    assert status.json()["stage"] == "COMPLETED"
    assert status.json()["decision"] == "APPROVED"


def test_end_user_facing_responses_never_expose_provider_identity(client: TestClient) -> None:
    """Provider/model identity is dev-team-only, surfaced through the
    reviewer API's `analysis` field - it must never appear in any response
    the capture/desktop client (an unauthenticated end user, from the
    platform's point of view) can see."""
    provider_markers = [
        "rapidocr",
        "insightface",
        "minifasnet",
        "vosk-small",
        "syncnet",
        "cccd-layout-yolov11",
        "scrfd",
        "deepfake-detector",
        "provider_id",
        "adapter_spec_version",
        "manifest_entry_id",
        '"attempts"',
        '"engine"',
    ]

    flow = create_claimed_session(client)
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}
    responses = [client.post("/api/v2/ekyc/capture/voice-challenge", headers=capture_headers)]
    for kind, media_type in (
        ("DOCUMENT_FRONT", "image/jpeg"),
        ("DOCUMENT_BACK", "image/jpeg"),
        ("SELFIE_VIDEO", "video/webm"),
    ):
        responses.append(
            client.post(
                f"/api/v2/ekyc/capture/evidence/{kind}",
                headers=capture_headers,
                files={"file": (f"{kind.lower()}.bin", b"synthetic-evidence-content", media_type)},
            )
        )
    responses.append(client.post("/api/v2/ekyc/capture/submit", headers=capture_headers))
    responses.append(
        client.get(f"/api/v2/ekyc/sessions/{flow['session_id']}", headers=flow["desktop_headers"])
    )
    responses.append(
        client.get(
            f"/api/v2/ekyc/sessions/{flow['session_id']}/handoff-status",
            headers=flow["desktop_headers"],
        )
    )

    for response in responses:
        body = response.text.lower()
        for marker in provider_markers:
            assert marker.lower() not in body, f"{marker!r} leaked via {response.request.url}"

    # Sanity check: the reviewer surface (a different trust boundary) is
    # allowed to see it - proves the assertions above are actually
    # exercising the leak path, not just testing an empty analysis.
    detail = client.get(f"/api/v2/reviews/{flow['session_id']}", headers=REVIEWER_HEADERS)
    assert "provider_id" in detail.text


def test_demo_ocr_rerun_decrypts_only_document_evidence_without_persisting(
    client: TestClient, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    def fake_analyze_document(self, document_type, evidence):
        captured["document_type"] = document_type
        captured["evidence_types"] = sorted(item.evidence_type for item in evidence)
        captured["payloads"] = [item.payload for item in evidence]
        return {
            "schema_version": "demo-ocr-rerun/1.0",
            "transient": True,
            "documents": {
                "document_front": {
                    "execution_status": "COMPLETED",
                    "engine": "test-ocr",
                    "lines": ["SYNTHETIC OCR TEXT"],
                }
            },
        }

    monkeypatch.setattr(OfflineModelAnalyzer, "analyze_document", fake_analyze_document)
    flow = create_claimed_session(client)
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}
    client.post("/api/v2/ekyc/capture/voice-challenge", headers=capture_headers)
    upload(client, flow["capture_token"], "DOCUMENT_FRONT", "image/jpeg")
    upload(client, flow["capture_token"], "DOCUMENT_BACK", "image/jpeg")
    upload(client, flow["capture_token"], "SELFIE_VIDEO", "video/webm")
    submitted = client.post("/api/v2/ekyc/capture/submit", headers=capture_headers)
    assert submitted.json()["stage"] == "MANUAL_REVIEW"

    denied = client.post(f"/api/v2/reviews/{flow['session_id']}/ocr-runs")
    assert denied.status_code == 401
    response = client.post(
        f"/api/v2/reviews/{flow['session_id']}/ocr-runs",
        headers=REVIEWER_HEADERS,
    )

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["transient"] is True
    assert response.json()["documents"]["document_front"]["lines"] == ["SYNTHETIC OCR TEXT"]
    assert captured == {
        "document_type": "CAN_CUOC_2024",
        "evidence_types": ["DOCUMENT_BACK", "DOCUMENT_FRONT"],
        "payloads": [b"synthetic-evidence-content", b"synthetic-evidence-content"],
    }

    detail = client.get(f"/api/v2/reviews/{flow['session_id']}", headers=REVIEWER_HEADERS).json()
    assert "SYNTHETIC OCR TEXT" not in str(detail["analysis"])
    events = client.get("/api/v2/admin/audit-events", headers=REVIEWER_HEADERS).json()
    rerun_events = [event for event in events if event["action"] == "review.ocr_rerun"]
    assert len(rerun_events) == 1
    assert "SYNTHETIC OCR TEXT" not in str(rerun_events[0])


def test_passport_requires_single_td3_page(client: TestClient) -> None:
    flow = create_claimed_session(client, "PASSPORT_TD3")
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}
    client.post("/api/v2/ekyc/capture/voice-challenge", headers=capture_headers)
    upload(client, flow["capture_token"], "PASSPORT_PAGE", "image/png")
    upload(client, flow["capture_token"], "SELFIE_VIDEO", "video/mp4")
    submitted = client.post("/api/v2/ekyc/capture/submit", headers=capture_headers)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["stage"] == "MANUAL_REVIEW"


def test_submit_reports_missing_evidence(client: TestClient) -> None:
    flow = create_claimed_session(client)
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}
    client.post("/api/v2/ekyc/capture/voice-challenge", headers=capture_headers)
    upload(client, flow["capture_token"], "DOCUMENT_FRONT", "image/jpeg")
    response = client.post("/api/v2/ekyc/capture/submit", headers=capture_headers)
    assert response.status_code == 409
    assert "DOCUMENT_BACK" in response.json()["detail"]


def test_document_evidence_upload_reports_quality_selfie_video_does_not(
    client: TestClient,
) -> None:
    """document_quality runs synchronously at upload time for a still
    document photo (fast retake feedback), never for the selfie video. The
    test client's model_dir has no manifest.json, so the provider is
    ungoverned here and reports UNAVAILABLE - this asserts the endpoint
    wires the capability call and shapes the response either way, not that
    a specific model_dir happens to have it approved."""
    from support.tiny_media import tiny_jpeg_bytes, tiny_mp4_bytes

    flow = create_claimed_session(client)
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}

    document_response = client.post(
        "/api/v2/ekyc/capture/evidence/DOCUMENT_FRONT",
        headers=capture_headers,
        files={"file": ("front.jpg", tiny_jpeg_bytes(), "image/jpeg")},
    )
    assert document_response.status_code == 201, document_response.text
    assert "quality" in document_response.json()
    assert document_response.json()["quality"]["status"] == "UNAVAILABLE"

    video_response = client.post(
        "/api/v2/ekyc/capture/evidence/SELFIE_VIDEO",
        headers=capture_headers,
        files={"file": ("selfie.mp4", tiny_mp4_bytes(), "video/mp4")},
    )
    assert video_response.status_code == 201, video_response.text
    assert "quality" not in video_response.json()


def create_unselected_claimed_session(client: TestClient) -> dict:
    created = client.post(
        "/api/v2/ekyc/sessions",
        headers=VID_HEADERS,
        json={"subject_ref": "opaque-user-unselected"},
    )
    assert created.status_code == 201, created.text
    session = created.json()
    desktop_headers = {"X-Session-Token": session["session_token"]}
    handoff = client.post(
        f"/api/v2/ekyc/sessions/{session['session_id']}/handoffs",
        headers=desktop_headers,
    )
    assert handoff.status_code == 200, handoff.text
    claim = client.post(
        "/api/v2/ekyc/handoffs/claim",
        json={"token": handoff.json()["handoff_token"]},
    )
    assert claim.status_code == 200, claim.text
    assert claim.json()["document_type"] is None
    return {**session, **claim.json(), "desktop_headers": desktop_headers}


def test_capture_client_selects_cccd_without_choosing_card_revision(client: TestClient) -> None:
    flow = create_unselected_claimed_session(client)
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}
    selected = client.post(
        "/api/v2/ekyc/capture/document-type",
        headers=capture_headers,
        json={"document_type": "CCCD"},
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["document_type"] == "CCCD"
    status = client.get(
        f"/api/v2/ekyc/sessions/{flow['session_id']}",
        headers=flow["desktop_headers"],
    )
    assert status.status_code == 200
    assert status.json()["document_type"] == "CCCD"


def test_document_type_cannot_change_after_capture_starts(client: TestClient) -> None:
    flow = create_unselected_claimed_session(client)
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}
    selected = client.post(
        "/api/v2/ekyc/capture/document-type",
        headers=capture_headers,
        json={"document_type": "CCCD"},
    )
    assert selected.status_code == 200
    upload(client, flow["capture_token"], "DOCUMENT_FRONT", "image/jpeg")
    changed = client.post(
        "/api/v2/ekyc/capture/document-type",
        headers=capture_headers,
        json={"document_type": "PASSPORT"},
    )
    assert changed.status_code == 409


def test_capture_client_selects_passport_and_submits_single_page(client: TestClient) -> None:
    flow = create_unselected_claimed_session(client)
    capture_headers = {"Authorization": f"Bearer {flow['capture_token']}"}
    selected = client.post(
        "/api/v2/ekyc/capture/document-type",
        headers=capture_headers,
        json={"document_type": "PASSPORT"},
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["document_type"] == "PASSPORT_TD3"
    client.post("/api/v2/ekyc/capture/voice-challenge", headers=capture_headers)
    upload(client, flow["capture_token"], "PASSPORT_PAGE", "image/jpeg")
    upload(client, flow["capture_token"], "SELFIE_VIDEO", "video/webm")
    submitted = client.post("/api/v2/ekyc/capture/submit", headers=capture_headers)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["stage"] == "MANUAL_REVIEW"
