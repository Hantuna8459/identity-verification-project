# M0 Contract, Governance và Baseline cấu hình

Cập nhật: 2026-08-03.

## 1. Phạm vi M0

M0 là design/governance gate để các milestone M1-M4 bắt đầu trên cùng một contract.
M0 không triển khai runtime, không chọn dataset cụ thể, không approval model hoặc
threshold production và không tạo quyền auto approve/reject.

Quyết định hiện tại:

- Người dùng là owner quyết định cuối cùng cho M0.
- Dataset cụ thể chưa chốt; milestone này chỉ định nghĩa registry schema và quy
  trình approval/license.
- `demo_device_profile` ban đầu là Tecno Spark 30, Android 14, Chrome.
- Browser exact version, camera capability, MIME/codec và media limits được đo ở
  M1 device preflight.

## 2. Capability chuẩn

Mỗi capability phải nằm sau provider interface, có readiness riêng, provenance riêng
và output không được tự biến thành quyết định xác minh danh tính.

| Capability | Mục đích | Input chính | Output tối thiểu | Failure/Unavailable |
|---|---|---|---|---|
| `document_quality` | Kiểm tra chất lượng trước layout/OCR | document side image/video frame | defect flags, reason codes, quality metrics | `QUALITY_CHECK_UNAVAILABLE` |
| `document_layout` | Phát hiện vùng giấy tờ và vùng trường | document image | boxes, side/page type, confidence | `LAYOUT_UNAVAILABLE` |
| `document_ocr` | OCR field hoặc full-page/region | cropped regions/document image | extracted fields hoặc safe metadata, confidence, source side | `OCR_UNAVAILABLE` |
| `passport_mrz` | Đọc và validate MRZ TD3 | passport page image | MRZ line status, check digit status, parse errors | `MRZ_UNAVAILABLE` |
| `face_detection` | Tìm mặt và landmark | selfie/video/document portrait | face boxes, landmarks, detection confidence | `FACE_DETECTION_UNAVAILABLE` |
| `face_embedding` | Tạo embedding để match | normalized face crop | embedding reference, model metadata, quality | `FACE_EMBEDDING_UNAVAILABLE` |
| `face_matching` | So sánh portrait/selfie | document portrait + selfie frames | similarity score, aggregation method, frame count | `FACE_MATCH_UNAVAILABLE` |
| `passive_liveness` | Tín hiệu sống từ ảnh/video | selfie video/frames | liveness score/signal, reason codes | `LIVENESS_UNAVAILABLE` |
| `active_liveness` | Kiểm tra chuỗi hành động challenge | challenge events + video | step coverage, mismatch/missing-step reason | `ACTIVE_LIVENESS_UNAVAILABLE` |
| `visual_deepfake` | Phát hiện thao túng hình ảnh/video | selfie video/frames | manipulation score/signal, warnings | `DEEPFAKE_UNAVAILABLE` |
| `voice_challenge` | Kiểm tra nội dung challenge đọc ra | audio track + expected sequence | transcript match status, digit error metrics | `VOICE_CHALLENGE_UNAVAILABLE` |
| `speech_verification` | Định danh/đối chiếu speaker khi có model phù hợp | enrolled/claimed speaker evidence + audio | speaker score/signal, scope | `SPEECH_VERIFICATION_UNAVAILABLE` |
| `lip_sync` | Kiểm tra khớp môi và âm thanh | face video + audio | sync score/signal, segments | `LIPSYNC_UNAVAILABLE` |
| `replay_attack` | Phát hiện replay màn hình/video | video frames + metadata + timing | replay score/signal, reason codes | `REPLAY_CHECK_UNAVAILABLE` |
| `camera_injection` | Phát hiện camera injection/virtual feed | media metadata + timing + frames | injection score/signal, reason codes | `CAMERA_INJECTION_UNAVAILABLE` |

Quality failure như blur, glare, missing corner hoặc document too small phải đi
recapture, không kích hoạt provider fallback. Score thấp hoặc tín hiệu nghi ngờ cũng
không phải điều kiện fallback.

## 3. eKYC analysis result contract

Contract kế tiếp là `ekyc-analysis/1.0`. Đây là contract kết quả phân tích eKYC giữa
AI/capability pipeline và orchestration/manual review/benchmark/monitoring. Use case
không gọi model trực tiếp; use case gọi capability port, còn provider/model cụ thể
được chọn qua composition root, config/profile và manifest governance.

`ekyc-analysis/1.0` kế thừa tinh thần tách `execution_status` và `review_signal` từ
`model-analysis/1.2`, nhưng đổi tên để tránh hiểu nhầm đây là contract riêng của
model. Contract này thêm provenance chuẩn cho provider/model/config/threshold và
attempts theo capability.

Envelope tối thiểu:

```json
{
  "contract_version": "ekyc-analysis/1.0",
  "session_id": "opaque-session-id",
  "execution_status": "COMPLETED|PARTIAL|UNAVAILABLE|FAILED",
  "review_signal": "MANUAL_REVIEW_REQUIRED|MODEL_UNAVAILABLE|RECAPTURE_REQUIRED",
  "capabilities": {},
  "summary_reason_codes": [],
  "created_at": "RFC3339"
}
```

Mỗi capability result tối thiểu:

```json
{
  "status": "COMPLETED|INCONCLUSIVE|UNAVAILABLE|SKIPPED|FAILED",
  "review_signal": "NO_ADVERSE_SIGNAL|INCONCLUSIVE|ADVERSE_SIGNAL|RECAPTURE_REQUIRED|UNAVAILABLE",
  "score": null,
  "score_interpretation": "higher_is_risk|higher_is_match|higher_is_live|higher_is_confidence|not_applicable",
  "reason_codes": [],
  "attempts": [
    {
      "provider_id": "string",
      "provider_role": "primary|secondary|fallback",
      "model_id": "string|null",
      "model_revision": "string|null",
      "manifest_entry_id": "string|null",
      "adapter_spec_version": "string",
      "config_version": "string",
      "threshold_profile": "technical-demo-v1|none",
      "threshold_version": "string|null",
      "started_at": "RFC3339",
      "duration_ms": 0,
      "status": "COMPLETED|TIMEOUT|INVALID_OUTPUT|UNAVAILABLE|FAILED",
      "reason_codes": []
    }
  ],
  "metadata": {}
}
```

Rules:

- `execution_status` chỉ mô tả khả năng chạy capability/provider.
- `review_signal` chỉ là tín hiệu cho reviewer, không phải quyết định approve/reject.
- Monitoring, benchmark, manual review và orchestration đều là consumer của contract
  này; contract không tự đưa ra quyết định cuối cùng.
- Threshold `evaluation_only` phải được ghi rõ; production threshold chưa được mặc định.
- Raw OCR, MRZ, transcript, embedding, raw evidence path/key hoặc signed URL không
  thuộc analysis response mặc định.
- Điều kiện để một attempt chạy chỉ có một: provider có governance entry trong
  `manifest.json#providers[]` và `usage_scope` khớp profile đang chạy. Không có
  trường trạng thái phê duyệt (approval status) nào trong contract này hay
  trong manifest - rủi ro pháp lý/license của một provider/model được ghi ở
  `notes` trong `manifest.json` và ở `docs/model_license_risk_matrix.html`,
  ngoài contract này.

## 4. Provider/model adapter spec

Hướng dẫn thao tác đổi/thêm provider theo spec này (M2 implementation) nằm tại
[`CAPABILITY_PROVIDER_GUIDE.md`](./CAPABILITY_PROVIDER_GUIDE.md).

Mỗi provider adapter phải có spec tối thiểu để mô tả cách raw model output được map
về `ekyc-analysis/1.0`. Spec này là nơi ghi ý nghĩa score của từng model, thay vì để
use case hoặc reviewer tự suy luận từ tài liệu model.

Adapter spec tối thiểu:

```json
{
  "adapter_spec_version": "string",
  "capability": "passive_liveness",
  "provider_id": "string",
  "manifest_entry_id": "string|null",
  "model_id": "string|null",
  "model_revision": "string|null",
  "required_inputs": ["selfie_video"],
  "preprocessing": {
    "version": "string",
    "summary": "resize/crop/normalize/frame-sampling policy"
  },
  "raw_outputs": [
    {
      "name": "p_live",
      "type": "probability|logit|distance|similarity|confidence|label|embedding|box|text",
      "range": "string|null",
      "higher_means": "live|risk|match|confidence|not_applicable"
    }
  ],
  "normalized_output": {
    "score_interpretation": "higher_is_live|higher_is_risk|higher_is_match|higher_is_confidence|not_applicable",
    "aggregation_method": "string|null",
    "metadata_fields": ["string"]
  },
  "threshold_applicability": "none|evaluation_only|requires_benchmark",
  "fallback_eligibility": "technical_failure_only|not_allowed",
  "benchmark_requirements": "dataset/split/metric notes",
  "known_limitations": "string",
  "license_scope": "string"
}
```

Rules:

- Use case chỉ phụ thuộc capability output đã normalize, không phụ thuộc raw model
  score hoặc tài liệu riêng của model.
- Đổi adapter spec, preprocessing, aggregation hoặc model revision làm threshold cũ
  mất hiệu lực cho capability bị ảnh hưởng.
- Adapter không được tự chọn model ngoài composition/config/profile đã cho phép.
- Adapter không được tự download model hoặc artifact runtime.
- Điều kiện để adapter chạy chỉ là `usage_scope` khớp profile đang chạy - không
  có trường trạng thái phê duyệt riêng nào ở đây. Rủi ro pháp lý/license của
  model đứng sau adapter (`license_scope` ở trên) được ghi chi tiết hơn ở
  `notes` trong `manifest.json` và ở `docs/model_license_risk_matrix.html`.

## 5. ADR M0

### ADR-M0-001 Capability provider và composition root

Decision: domain/use case chỉ gọi capability ports. Provider cụ thể được chọn tại
composition root theo profile/config. `backend/ai_modules` không chứa business
workflow và không quyết định session outcome.

Consequence: M2 phải tách provider registry/factory và fake providers cho test.

### ADR-M0-002 Fallback bounded và fail closed

Decision: fallback chỉ xảy ra với lỗi kỹ thuật allowlist: unavailable, timeout,
invalid output hoặc provider failure. Không fallback vì score thấp, input quality
kém hoặc tín hiệu nghi ngờ.

Consequence: all-provider-failure trả `UNAVAILABLE` hoặc `MODEL_UNAVAILABLE` cho
manual review/state machine; không tự reject.

### ADR-M0-003 Controlled disclosure

Decision: technical demo chốt trước một vai trò reviewer tối thiểu. Reviewer mặc
định xem dữ liệu đã mask, được reveal dữ liệu nhạy cảm cần thiết trong phạm vi session
được phân công review. Lần reveal phải được audit theo session/review reason hiện có;
không yêu cầu nhập reason riêng trong flow demo. Response chứa raw/PII phải `no-store`
và không expose storage path/key dài hạn. Quyền chi tiết cho PII, evidence raw,
biometric, export, delete và decide là hướng tách sau, không phải yêu cầu phải hoàn
thiện toàn bộ trong technical demo.

Consequence: M6 không mở raw evidence viewer chỉ bằng quyền admin tổng quát, nhưng
cũng không bắt buộc xây permission matrix phức tạp trước khi vai trò reviewer được
chốt.

### ADR-M0-004 Threshold lifecycle

Decision: threshold gắn với model, preprocessing, aggregation, dataset, split, device
profile và config. Bất kỳ thay đổi nào trong các biến này làm threshold cũ không còn
hiệu lực cho capability bị ảnh hưởng cho đến khi benchmark lại.

Consequence: M5 chỉ tạo threshold `evaluation_only`; không suy ra production policy.

## 6. Dataset registry schema

Mọi dataset dùng trong benchmark (ngoài smoke synthetic) phải có record trong
`benchmark/datasets/registry.json`. Record ghi lại provenance/license/sensitivity
cho mục đích tra cứu rủi ro pháp lý - nó không phải một cổng phê duyệt.
`get_dataset()` (`backend/benchmark/dataset_registry.py`) chỉ còn hai điều kiện
thật sự: dataset có tồn tại trong registry, và nó có đăng ký cho đúng capability
đang benchmark. Không có trạng thái approval nào chặn việc dùng dataset.

Dataset record tối thiểu:

```json
{
  "dataset_id": "string",
  "name": "string",
  "version": "string",
  "capabilities": ["document_ocr"],
  "source_url": "string|null",
  "source_type": "public|gated|internal_synthetic|internal_test|manual",
  "license_name": "string|null",
  "license_url": "string|null",
  "terms_summary": "string",
  "distribution_permission": "allowed|restricted|forbidden|unknown",
  "usage_scope": "technical_demo|benchmark_only|development_only|production_candidate",
  "sensitivity": "synthetic|public_non_pii|contains_pii|contains_biometric|unknown",
  "storage_location": "outside_git|not_downloaded|tbd",
  "checksum_sha256": "string|null",
  "split_policy": "identity_document_device_separated|synthetic_smoke|tbd",
  "notes": "string"
}
```

Process:

1. Tạo record với source/license/scope rõ nhất có thể trước khi dùng dataset.
2. Ghi rủi ro pháp lý/license đã biết (nếu có) vào `notes` - đây là nơi lưu mối lo
   pháp lý, không phải lý do để trì hoãn dùng dataset.
3. Giữ dataset chỉ được đọc qua runner của đúng capability nó phục vụ (không dùng
   chéo capability ngoài `capabilities[]` đã khai báo), để đổi/gỡ dataset sau này
   không ảnh hưởng runner khác - cùng nguyên tắc swap-được của ADR-M0-001.
4. Full dataset, license evidence nhạy cảm và benchmark report nhạy cảm nằm ngoài Git.

## 7. Hard-code inventory baseline

| Nhóm | Ví dụ | Nơi quản lý | Rule |
|---|---|---|---|
| Secret | token signing key, DB password, evidence encryption key, client secret | `SecretProvider`/`.env` development | không vào browser bundle, log hoặc Git |
| Environment config | host, port, timeout, retry, feature flag, provider profile | typed settings/env | validate ở startup; placeholder fail ngoài dev/test |
| Versioned policy | fallback chain, recapture limit, review reason allowlist, quality threshold | policy config có version | thay đổi cần version/change record |
| Model-specific constant | input size, normalization, labels, stride/anchor, aggregation method | model adapter config gắn manifest revision | thay model/config làm benchmark/threshold cũ mất hiệu lực |

M0 chỉ lập baseline phân loại. Việc di chuyển từng hard-code ra config/secret/policy
là workstream X1 và các milestone runtime tương ứng.

## 8. Manual reviewer contract

### Vai trò technical demo

M0 chốt vai trò tối thiểu `manual_reviewer_demo` trước khi tách quyền chi tiết.
Vai trò này dùng để hoàn thiện M6 theo flow gọn, có kiểm soát và không suy ra quyền
production.

Reviewer demo được phép:

- xem danh sách session chờ review và session metadata tối thiểu;
- xem reason codes, recapture history, execution summary và model unavailable/fallback
  attempts;
- xem structured fields đã mask, confidence/source/validation status nếu có;
- xem thumbnail/evidence representation đã mask hoặc đã kiểm soát;
- xem document quality issues;
- xem face/liveness/deepfake/voice/lip-sync/replay/camera-injection signals ở mức
  phục vụ review;
- xem provider/model/config/threshold/benchmark provenance;
- reveal dữ liệu nhạy cảm cần thiết trong session được phân công; lần reveal dùng
  session/review reason hiện có, phải có audit và response `no-store`;
- ra quyết định review theo output allowlist bên dưới.

Reviewer demo không được phép:

- truy cập storage path/key, signed URL dài hạn hoặc file evidence trực tiếp;
- export raw evidence hoặc PII;
- delete evidence/session;
- sửa model result, threshold, provider config hoặc benchmark report;
- approve/reject ngoài output contract;
- xem dữ liệu ngoài session được phân công;
- dùng kết quả AI để auto approve/reject thay cho quyết định review thủ công.

Input mặc định:

- session metadata, reason codes, recapture history và execution summary;
- structured fields đã mask, confidence/source/validation status nếu có;
- thumbnail/evidence representation đã mask hoặc đã kiểm soát;
- document quality issues;
- face/liveness/deepfake/voice/lip-sync/replay/camera-injection signals;
- provider/model/config/threshold/benchmark provenance;
- fallback attempts và model unavailable được tách khỏi fraud signal.

Output reviewer:

- `APPROVED`
- `REJECTED`
- `RECAPTURE_REQUESTED`
- `RETRY_ANALYSIS`
- `ESCALATED`

Mỗi output phải có reason code allowlist, optional note, reviewer identity, decision
scope, optimistic concurrency check và audit event không chứa PII/raw evidence.

Quyền chi tiết sau technical demo:

- `review:read`
- `review:reveal_sensitive`
- `pii:unmask`
- `evidence:view`
- `biometric:view`
- `review:decide`
- `evidence:export`
- `evidence:delete`

Trong technical demo, có thể collapse các quyền xem dữ liệu nhạy cảm thành
`review:reveal_sensitive` nếu vẫn giữ session assignment scope, audit, short-lived
access và `no-store` response. Reason riêng chỉ cần cho truy cập ngoại lệ ngoài phạm
vi review được phân công hoặc cho quyền production chi tiết sau này. `evidence:export`
và `evidence:delete` không thuộc quyền mặc định của reviewer demo.

## 9. Demo device profile

```json
{
  "profile_id": "technical-demo-device-1",
  "device_model": "Tecno Spark 30",
  "os": "Android 14",
  "browser": "Chrome",
  "browser_version": "M1_PREFLIGHT_TBD",
  "camera": "M1_PREFLIGHT_TBD",
  "microphone": "M1_PREFLIGHT_TBD",
  "media_recorder_mime_types": "M1_PREFLIGHT_TBD",
  "video_codec": "M1_PREFLIGHT_TBD",
  "audio_codec": "M1_PREFLIGHT_TBD",
  "network_profile": "local_https_same_origin_tbd",
  "validated_at": null
}
```

M1 phải ghi exact browser version, supported MIME/codec, camera facing-mode behavior,
permission behavior, max practical duration/size và ba lần E2E thành công trên profile
này.

## 10. Review checklist M0

M0 chưa đánh dấu `DONE` cho đến khi review checklist này được chốt.

Checklist cần review:

- Tên contract `ekyc-analysis/1.0` có đúng ý nghĩa là contract kết quả phân tích eKYC,
  không phải contract riêng của model không?
- Capability list đã đủ để M1-M4 bắt đầu chưa, hay cần thêm/bớt capability nào trước?
- Provider/model adapter spec đã đủ để ghi ý nghĩa raw score, preprocessing,
  aggregation và threshold applicability của từng model chưa?
- Fallback rule đã đúng chưa: chỉ fallback do lỗi kỹ thuật, không fallback vì score
  thấp hoặc input quality kém?
- Reviewer role `manual_reviewer_demo` đã đủ gọn cho M6 chưa, và danh sách được
  xem/không được xem có cần chỉnh gì không?
- Dataset registry schema đã đủ cho candidate chưa chọn chưa, hay cần thêm field
  về nơi lưu license record/benchmark data ngoài Git?
- Demo device profile đã đủ cho M1 preflight chưa?
- Có quyết định nào trong tài liệu đang vô tình suy ra production threshold,
  production approval, production retention hoặc quyền production không?

M0 được xem là sẵn sàng để chốt khi:

- capability list, `ekyc-analysis/1.0`, adapter spec, ADR, dataset registry,
  hard-code baseline, reviewer contract và demo device profile cùng được review;
- `PROJECT_ROADMAP.md` và `IMPLEMENTATION_STATUS.md` tham chiếu cùng quyết định;
- không có dataset/model/threshold/quyền production nào được mặc định;
- các unresolved production decision vẫn được giữ ngoài technical demo.
