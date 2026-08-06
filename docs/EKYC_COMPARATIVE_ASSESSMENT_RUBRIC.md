# Rubric đánh giá so sánh eyePass và V-ID-eKYC

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 1.0 |
| Cập nhật | 2026-08-05 |
| Mục đích | Chấm nhất quán hai dự án eKYC theo evidence, yêu cầu và mức sẵn sàng. |
| Dùng cùng | [EKYC_COMPARATIVE_ASSESSMENT_BASELINE.md](./EKYC_COMPARATIVE_ASSESSMENT_BASELINE.md) |
| Phê duyệt | Project owner xác nhận scope, fact và kết luận cuối. |

## 1. Mục đích và giới hạn

Rubric này là cách chấm lặp lại được cho eyePass (hệ thống tham chiếu) và V-ID-eKYC (dự án hiện tại). Đơn vị chấm là tiêu chí nguyên tử ở mục 7, không phải cảm nhận về UI, tuổi đời dự án hay một tài liệu đơn lẻ. Mỗi tiêu chí phải có evidence riêng cho từng hệ thống.

Đây không phải benchmark độ chính xác model, chứng nhận security/compliance, UAT/pilot gate hay production-readiness assessment. Điểm cao chỉ nói hệ thống đáp ứng rubric trong scope đã chốt. Không được suy ra model chạy được là được phép dùng, OCR/MRZ là xác thực thật/giả, capability được mô tả là đã triển khai, hoặc tổng điểm cao là đủ auto approve/reject.

Mặc định scope là technical demo nội bộ: synthetic/test data hợp lệ, runtime offline, AI chỉ phát review signal, mọi session vào manual review hoặc `MODEL_UNAVAILABLE`. Tiêu chí production phải ghi `OUT_OF_SCOPE` hoặc `TBD` đến khi owner mở scope; không được mặc định pass.

## 2. Nguồn evidence và nguyên tắc

V-ID-eKYC dùng theo thứ tự: `AGENTS.md`/owner decision, `EKYC_FLOW_DESIGN.md`, `M0_CONTRACT_GOVERNANCE_BASELINE.md`, `PROJECT_ROADMAP.md`, `IMPLEMENTATION_STATUS.md`, sau đó mới source, test, CI/run output, model manifest và config được phép xem. eyePass dùng BRD, flow/rule workbook, architecture/deployment/integration diagram, API/SDK, handover/UAT/test checklist và artifact vận hành được phép xem.

Checklist, slide, backlog hoặc lời kể không kèm artifact kiểm chứng chỉ là evidence mô tả. Screenshot UI đơn lẻ, assertion không output, source không chạy được không đủ `E4`. Không đưa PII, raw evidence, token, key, signed URL, raw OCR/MRZ/transcript/embedding vào matrix hoặc report.

Khi evidence mâu thuẫn, ghi cả hai nguồn vào decision log, gán confidence `DISPUTED`, không tự chọn một nguồn để xếp hạng và yêu cầu owner chốt.

## 3. Thang điểm

Mỗi tiêu chí có bốn trường độc lập: `Applicability` (`IN_SCOPE`, `OUT_OF_SCOPE`, `TBD`), evidence level, conformance score và evidence confidence (`HIGH`, `MEDIUM`, `LOW`, `DISPUTED`). Evidence không tự bằng conformance: có test vẫn có thể chỉ đáp ứng một phần expectation.

### 3.1 Evidence level

| Mức | Ý nghĩa | Điều kiện tối thiểu |
|---|---|---|
| `E0` | Chưa có evidence | Không có artifact kiểm chứng. |
| `E1` | Được mô tả | BRD, diagram, checklist, roadmap có thể truy vết. |
| `E2` | Đã thiết kế | Contract, ADR, data/state design hoặc acceptance criteria rõ. |
| `E3` | Đã triển khai | Source/config phù hợp thiết kế, review được. |
| `E4` | Đã kiểm chứng | E3 cộng test/run/review output truy vết trong môi trường phù hợp. |

### 3.2 Conformance score

| Điểm | Neo chấm |
|---:|---|
| `0` | Không có, trái expectation hoặc chỉ có claim. |
| `1` | Ý định/coverage rất hẹp, thiếu phần cốt lõi hoặc failure path. |
| `2` | Đáp ứng một phần; happy path có thể có nhưng gap quan trọng mở. |
| `3` | Đáp ứng expectation trong scope, có design/implementation rõ; thiếu kiểm chứng đầy đủ hoặc hardening. |
| `4` | Đáp ứng đầy đủ, có E4 và negative/failure case liên quan được kiểm chứng. |

Không chấm 4 nếu dưới E4, không chấm 3 nếu dưới E2; E0 luôn là 0, E1 không quá 1, E2/E3 không quá 3. `LOW` confidence không quá 2; `DISPUTED` không thể là cơ sở kết luận hệ thống thắng. `TBD` có điểm 0 và không được âm thầm đổi thành `N/A`.

### 3.3 Công thức và band

```text
domain_score = 100 × Σ(weight_i × score_i / 4) / Σ(weight_i áp dụng)
overall_score = Σ(domain_weight × domain_score) / Σ(domain_weight áp dụng)
evidence_coverage = 100 × criteria IN_SCOPE có E3/E4 / criteria IN_SCOPE
verification_coverage = 100 × criteria IN_SCOPE có E4 / criteria IN_SCOPE
```

`OUT_OF_SCOPE` chỉ bị loại khỏi mẫu số khi scope register có lý do và owner xác nhận. Làm tròn một chữ số thập phân khi trình bày. Band: A 85–100, B 70–84.9, C 50–69.9, D 25–49.9, E 0–24.9. Band và overall score không thay critical gate.

## 4. Quy trình đánh giá

1. Khóa scope register: phiên bản, environment, document, model profile, role và kỳ đánh giá.
2. Lập source register: nguồn, owner, ngày/version, access limitation, độ tin cậy.
3. Tạo evidence card: claim, artifact, vị trí, assessor, ngày xem, E-level, confidence, limitation và redaction.
4. Product/Architecture và Engineering/QA chấm độc lập mọi P0/P1; không xem điểm nhau trước.
5. Calibration mọi chênh lệch từ 2 điểm, evidence level khác nhau hoặc `DISPUTED`; ghi rationale.
6. Chạy hoặc quan sát test/gate; nếu không có quyền/môi trường, ghi rõ limitation.
7. Xuất matrix, scorecard, gap/action log và executive summary liên kết ngược tới evidence card.

Assessor không tự gán E4 cho artifact mình tạo nếu không có independent review hoặc CI/run output tái lập được.

## 5. Critical gate không được bù bằng điểm

Kết luận “phù hợp để demo theo scope” chỉ dùng khi mọi gate áp dụng có score ≥3, evidence ≥E3 và không còn P0. Kết luận “đã kiểm chứng” cần E4. Production gate mặc định ngoài scope: lawful basis, retention/region/KMS production, model production-approved, threshold calibrated, production RBAC và DR/SLA.

| Gate | Điều kiện technical demo | Domain |
|---|---|---|
| `G-D1` | Session/handoff one-time, ràng buộc claim; state transition kiểm soát, không có capture session độc lập ngoài policy. | C01, C05 |
| `G-D2` | Model/capability lỗi route `UNAVAILABLE` hoặc manual review; không auto approve/reject. | C03, C04 |
| `G-D3` | Evidence dùng opaque key, ngoài public/static; không log PII/raw evidence/token. | C07, C08 |
| `G-D4` | Runtime không tự download model; required artifact checksum/readiness đúng profile. | C06 |
| `G-D5` | Access nhạy cảm có authz/audit; reviewer mask mặc định theo scope. | C04, C07, C08 |
| `G-D6` | Polling/webhook dùng cùng state machine; webhook chỉ pass khi signature, replay, retry, idempotency được kiểm chứng. | C05 |

## 6. Domain và trọng số

| Domain | Trọng số | Số tiêu chí |
|---|---:|---:|
| C01 Luồng & UX | 12 | 5 |
| C02 Giấy tờ, OCR & MRZ | 12 | 5 |
| C03 Sinh trắc học & anti-spoof | 12 | 5 |
| C04 Decision & manual review | 12 | 5 |
| C05 API & integration | 11 | 5 |
| C06 Model governance & offline | 11 | 5 |
| C07 Data, evidence & privacy | 11 | 5 |
| C08 Security & operations | 8 | 4 |
| C09 Quality & verification | 7 | 4 |
| C10 Delivery governance | 4 | 4 |

Tiêu chí trong domain có trọng số bằng nhau, trừ khi owner duyệt thay đổi trước khi xem kết quả. N/A chỉ hợp lệ khi capability đó bị loại khỏi scope cho cả hai hệ thống, không dùng để xóa gap sau khi scope đã khóa.

## 7. Tiêu chí nguyên tử

Expectation là mức score 3. Score 4 cần E4 và kiểm thử negative/failure liên quan.

### C01 — Luồng & UX

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C01.1 | Desktop session và QR/handoff one-time liên kết đúng session; expiry/revoke/recreate không orphan. | Contract/state + used/expired/revoked test và audit. |
| C01.2 | Capture theo document type, hướng dẫn, permission, progress, retry và lỗi hiểu được. | UX flow + happy path, permission/network E2E. |
| C01.3 | Một state machine cho desktop polling, capture, review; transition bất hợp lệ bị chặn. | State table/source + parallel/invalid transition test. |
| C01.4 | Recapture đúng evidence/side/page, giữ evidence tốt, attempt limit qua config. | Reason code/state + synthetic recapture test. |
| C01.5 | Reviewer thấy trạng thái/public reason và action được phép, không phơi dữ liệu nhạy cảm mặc định. | UI/API contract + role/audit test. |

### C02 — Giấy tờ, OCR & MRZ

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C02.1 | CCCD 2021, căn cước 2024, passport TD3 chỉ bật khi có fixture, benchmark và release rule tương ứng. | Scope/fixture/release register. |
| C02.2 | Quality gate tách OCR/layout; blur/glare/corner/area/brightness/occlusion yêu cầu recapture, không fallback. | Contract + synthetic negative fixture test. |
| C02.3 | OCR/layout qua adapter, output/error/provenance an toàn, không dùng LLM. | Adapter + contract test + manifest. |
| C02.4 | MRZ country-neutral đọc 2×44 TD3, check digit ICAO; parse error không bị gọi là fraud. | Valid/invalid check-digit fixture test. |
| C02.5 | Extraction/rule/cross-check/benchmark versioned và không claim document authenticity quá scope. | Rule registry + report hoặc limitation rõ. |

### C03 — Sinh trắc học & anti-spoof

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C03.1 | Face detection/alignment/embedding/match có quality, aggregation, score meaning và provenance. | Capability/adapter contract + deterministic/fake test. |
| C03.2 | Passive/active liveness, deepfake trả signal/reason; low/suspicious không kích hoạt fallback. | Failure matrix + unavailable/inconclusive/adverse test. |
| C03.3 | Voice, speaker verification nếu scope, lip-sync/replay/camera injection có claim không vượt benchmark. | Spec + mismatch/missing/suspicious test. |
| C03.4 | Embedding, transcript, face crop/media không nằm trong default response/API/log. | Response/log inspection test. |
| C03.5 | Timeout/unavailable/invalid output có attempts/provenance, fail-closed/manual-review. | Provider failure test. |

### C04 — Decision & manual review

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C04.1 | Execution status, review signal, public reason, final decision tách biệt; score không là verdict. | Versioned contract + test. |
| C04.2 | Demo không auto approve/reject; completed/partial/inconclusive/unavailable route đúng. | Decision/state test + run evidence. |
| C04.3 | Review queue có assignment, allowed action, reason, idempotency; retry/recapture/escalate theo policy. | Reviewer contract + authz/integration test. |
| C04.4 | Mask mặc định; reveal/decrypt/export/delete/decision tách quyền, audit, no-store. | Role matrix + negative authz test. |
| C04.5 | Threshold/policy versioned/approved; đổi model/preprocess/aggregation làm threshold cũ hết hiệu lực. | Governance record/change test. |

### C05 — API & integration

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C05.1 | API versioned, validate input, idempotency, opaque subject/session ID, payload/error contract tối thiểu. | OpenAPI + validation/idempotency test. |
| C05.2 | Polling dùng cùng state, không lộ OCR/model/evidence; channel/tenant authz đúng. | API/state + authz test. |
| C05.3 | Webhook khi enabled có signature, timestamp, replay protection, retry/backoff, idempotency/outbox. | Protocol + duplicate/replay test. |
| C05.4 | Callback chỉ có session ID/state/public reason/minimal metadata, không token/signed URL/raw model/OCR. | Payload + serialization/log test. |
| C05.5 | Capture URL one-time/TTL, demo web feature flag không bypass claim/tạo session riêng. | Config + expired/reuse test. |

### C06 — Model governance & offline

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C06.1 | Manifest đủ source/revision/file/SHA/license/required/approval/scope/distribution/reference. | Schema + validation test. |
| C06.2 | Local downloader và Docker cùng manifest; extraction/cache an toàn; runtime local-only. | Script/Docker/source + offline smoke. |
| C06.3 | Thiếu/sai checksum/sai approval required model làm readiness fail closed, không download/fallback model khác. | Negative readiness test. |
| C06.4 | Selection qua composition/config; adapter tách workflow; fallback bounded, attempts/provenance. | Source + config-switch/failure test. |
| C06.5 | License/approval/benchmark độc lập; evaluation-only không bị mô tả production approved. | Manifest/report/docs review. |

### C07 — Data, evidence & privacy

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C07.1 | Storage port, opaque non-client key, traversal-safe, ngoài public/static, DB không client path. | Source/schema + traversal test. |
| C07.2 | Encryption scoped; DB/queue/log tối thiểu, không PII/raw media/OCR/MRZ/transcript/embedding. | Data flow + schema/log test. |
| C07.3 | Purge idempotent phủ DB/evidence/private/derived data; `purge_after` tách scheduler, có orphan handling. | Repeated/orphan purge test. |
| C07.4 | View/download/decrypt/delete/export có quyền/audit, masked/no-store mặc định. | Authz/audit/header test. |
| C07.5 | Lawful basis/purpose/controller/retention/residency/subject-right chỉ pass khi đúng approval scope. | Approved policy/config + test; nếu thiếu là TBD. |

### C08 — Security & operations

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C08.1 | Auth provider qua interface; secret/config phân loại, không browser/log/Git/image; placeholder fail ngoài dev/test. | Config review + scan/negative startup. |
| C08.2 | RBAC tách analyze/review/decrypt/export/delete; không shared service key ở scope mục tiêu. | Permission matrix + authz test. |
| C08.3 | Custom CA build secret an toàn nếu cần; runtime trust tách; non-root, verification, offline network policy. | Docker/build redacted + smoke. |
| C08.4 | Readiness, safe telemetry, timeout/resource, incident/change runbook; production DR ghi TBD nếu chưa quyết. | Health/runbook/negative test. |

### C09 — Quality & verification

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C09.1 | Tests phủ state, contract, provider failure, authz, purge, critical UI/API; data synthetic/hợp lệ. | Inventory + command/output. |
| C09.2 | E2E trên device/profile chốt, HTTPS/preflight/codec/recovery được ghi nhận. | Device matrix + ba run evidence. |
| C09.3 | Benchmark độc lập session/review, dataset provenance/split chống leakage, metric/latency/resource/CI versioned. | Registry/CLI/report; thiếu thì không claim accuracy. |
| C09.4 | Formatter/linter/type/security/dependency/model verification/Docker smoke ở release gate. | CI/run output ngày chạy. |

### C10 — Delivery governance

| ID | Expectation | Evidence/test tối thiểu |
|---|---|---|
| C10.1 | Roadmap có owner/dependency/DoD; status dựa code/test/docs evidence. | Roadmap/status cross-check. |
| C10.2 | Risk/decision/exception/open decision có ID, owner, due/next step; không hard-code TBD. | Log sample. |
| C10.3 | Demo/release gate, rollback/kill switch, change control model/rule/config và traceability requirement→test→evidence. | Gate/runbook/change record. |
| C10.4 | Docs/API/UI claim khớp scope/limitation; không overclaim compliance/accuracy/identity verification. | Documentation review. |

## 8. Workbook và kết luận

`04_Gap_and_Traceability_Matrix.xlsx` cần bốn sheet:

1. `Criteria_Matrix`: criterion/domain/weight/applicability/rationale/expectation/test method; evidence ID, E-level, score, confidence cho từng hệ thống; delta; finding; gap/action/priority/owner/decision/due.
2. `Evidence_Register`: evidence ID, system, claim, source/path/section, version/date, type, assessor, review date, redaction, E-level, confidence, limitation, internal hash/link.
3. `Scorecard`: domain score/band, overall score, evidence/verification coverage, gate pass/fail, P0/P1/P2/TBD và delta.
4. `Gate_and_Decision_Log`: gate, applicability, score/E-level cho từng hệ thống, pass/fail, evidence, owner, decision, next action, closure evidence.

Finding chỉ dùng một trong các trạng thái sau:

| Status | Điều kiện |
|---|---|
| `CẢI TIẾN ĐÃ KIỂM CHỨNG` | V-ID cao hơn ≥1, E4, không disputed/gate fail. |
| `CẢI TIẾN ĐÃ THIẾT KẾ` | V-ID cao hơn ≥1 nhưng evidence E1–E3. |
| `TƯƠNG ĐƯƠNG TRONG SCOPE` | Delta ≤0.5, applicability/confidence tương đương. |
| `KẾ THỪA CÓ CHỌN LỌC` | eyePass có rule/test/ops asset hữu ích, không tự sao chép implementation. |
| `CẦN HOÀN THIỆN` | V-ID score <3, gate fail hoặc evidence thiếu. |
| `KHÔNG KẾ THỪA` | Cách làm eyePass trái nguyên tắc/scope V-ID. |
| `NGOÀI PHẠM VI` | Owner đã chốt cho cả hai. |
| `CHƯA KẾT LUẬN` | Conflict, evidence thiếu hoặc TBD. |

Ưu tiên: `P0` vi phạm gate/rò rỉ/auto-decision/runtime download; `P1` cần trước MVP hoặc target integration; `P2` hardening/discovery sau scope hiện tại; `TBD` cần owner/legal/product/security quyết.

Executive summary phải nêu riêng domain winner + evidence level, cải tiến V-ID đã thiết kế/đã kiểm chứng, tài sản eyePass nên kế thừa, gate/gap chặn demo/MVP/production assessment và owner decision tiếp theo. Không viết “V-ID tốt hơn eyePass” nếu không ghi domain, delta, E-level và limitation.

## 9. Checklist trước khi chấm

- [ ] Owner khóa phiên bản, environment và scope của hai hệ thống.
- [ ] Source register và redaction/access rule hoàn chỉnh.
- [ ] Hai assessor độc lập được chỉ định cho P0/P1.
- [ ] Weight, anchor, gate đã khóa trước khi xem kết quả.
- [ ] Mọi N/A/TBD/score 4/gate pass/improvement claim có rationale và evidence link.
- [ ] Matrix, scorecard, risk/decision log và executive summary khớp nhau.
