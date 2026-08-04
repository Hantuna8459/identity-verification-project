# Kế hoạch triển khai tiếp theo

Cập nhật: 2026-08-03.

## 1. Mục đích và phạm vi

Tài liệu này sắp xếp các nhận xét sau technical demo thành kế hoạch thực thi theo
dependency kỹ thuật. Đây là roadmap cho technical demo nội bộ và nền móng MVP,
không phải kế hoạch tuyên bố production-ready.

Roadmap không thay thế yêu cầu trong `AGENTS.md`, `EKYC_FLOW_DESIGN.md` hoặc
`M0_CONTRACT_GOVERNANCE_BASELINE.md`. Tiến độ tổng hợp phải được cập nhật tại
`IMPLEMENTATION_STATUS.md`; tài liệu này giữ phạm vi, thứ tự, đầu ra và tiêu chí
hoàn thành của từng milestone.

Các mục tiêu bắt buộc gồm:

- pipeline không phụ thuộc một model cụ thể, thay provider qua composition/config;
- fallback có giới hạn, có provenance và không biến lỗi kỹ thuật thành kết luận;
- hoàn thiện mobile web trên một điện thoại được chỉ định cho technical demo;
- phát hiện CCCD mờ, lóa, thiếu góc và yêu cầu chụp lại đúng evidence lỗi;
- benchmark chạy độc lập với session/manual-review workflow;
- có seed threshold để bắt đầu đánh giá và threshold được hiệu chỉnh từ benchmark;
- thiết kế lại admin/manual review với input/output và controlled disclosure rõ ràng;
- giảm hard-code, tách config/policy/secret và dùng `.env` tạm thời cho secret cho
  đến khi có KMS/secret manager.

## 2. Nguyên tắc thực thi

1. Kết quả AI của technical demo không tự động approve/reject.
2. Fallback chỉ dùng provider được phép trong cùng profile; không fallback sang
   model `quarantined`, `rejected` hoặc ngoài usage scope.
3. Input kém chất lượng đi `RECAPTURE_DOCUMENT`, không kích hoạt model fallback.
4. Đổi model, preprocessing, aggregation hoặc device profile làm threshold cũ mất
   hiệu lực cho đến khi benchmark lại.
5. Dataset tải được công khai không mặc nhiên được phép dùng. Dataset phải có
   provenance, license, checksum, usage scope và approval status riêng.
6. Dữ liệu thật không được commit, đưa vào fixture, log, screenshot, Docker image
   hoặc artifact CI. Dữ liệu benchmark và report nhạy cảm nằm ngoài Git.
7. Không đưa mọi literal vào `.env`: secret, environment config, versioned policy
   và hằng số gắn với model là bốn loại cấu hình khác nhau.

## 3. Đường găng và workstream song song

```text
M0 Contract/governance
       |
       +--> M1 Mobile demo foundation
       |
       +--> M2 Capability/provider architecture --> M3 Quality + recapture
                         |                              |
                         +--> M4 Benchmark foundation -+
                                        |
                                        v
                                M5 Threshold calibration
                                        |
                                        v
                                M6 Manual-review implementation
                                        |
                                        v
                                M7 Integrated demo hardening
```

Dataset discovery/license review bắt đầu từ M0 vì có lead time bên ngoài. Thiết kế
UX/contract admin cũng bắt đầu từ M0, nhưng implementation phụ thuộc structured
quality/model output và controlled-disclosure contract nên được hoàn tất ở M6.

Config/secret hardening là workstream xuyên suốt M0-M7.

## 4. Milestone thực thi

### M0 — Chốt contract, governance và baseline cấu hình

**Mục tiêu:** tạo nền chung để các workstream không phát triển contract riêng.

**Đầu ra:**

- danh sách capability chuẩn: document quality/layout/OCR, face detection/embedding,
  passive/active liveness, visual deepfake, voice challenge, lip-sync, replay và
  camera injection;
- `ekyc-analysis/1.0` contract có provider/model/config/threshold provenance;
- provider/model adapter spec và ADR cho capability provider, fallback, controlled disclosure và threshold lifecycle;
- schema dataset registry và quy trình approval/license review;
- inventory các giá trị hard-code và phân loại thành secret, environment config,
  versioned policy hoặc model-specific constant;
- contract input/output của manual reviewer;
- `demo_device_profile` ghi model điện thoại, OS, browser, codec, camera và version.

**Quyết định hiện tại cho M0:**

- M0 chỉ cần đủ để M1-M4 bắt đầu; không mở rộng sang implementation runtime.
- Dataset cụ thể chưa chốt. M0 chỉ tạo registry schema và approval/license process;
  không download, đóng gói hoặc approval dataset trong milestone này.
- Người dùng là owner quyết định/phê duyệt tạm thời cho M0 và dataset governance.
- `demo_device_profile` ban đầu: Tecno Spark 30, Android 14, Chrome. Browser exact
  version, camera capability, MIME/codec và media limits được đo trong M1 preflight.

**Tiêu chí hoàn thành:** contract được version hóa; không có threshold hoặc quyền
production bị mặc định; mọi milestone sau tham chiếu cùng contract.

### M1 — Mobile web demo-ready trên thiết bị chỉ định

**Mục tiêu:** chạy ổn định luồng QR → giấy tờ → challenge → submit trên đúng điện
thoại demo, không tuyên bố hỗ trợ mọi thiết bị.

**Đầu ra:**

- local HTTPS reverse proxy để điện thoại truy cập frontend/API cùng origin;
- QR dùng host điện thoại resolve được, không dùng `localhost` của máy chạy Docker;
- preflight cho secure context, camera trước/sau, microphone, MediaRecorder,
  MIME/codec và permission;
- preview/chụp lại từng mặt, upload progress, retry idempotent và lỗi dễ hiểu;
- kiểm tra video có audio track, không rỗng, decode được và nằm trong giới hạn;
- recovery khi mất mạng, permission bị từ chối, tab background hoặc upload timeout;
- runbook trước/sau demo, gồm readiness, network/certificate và purge session demo;
- E2E checklist khóa theo `demo_device_profile`.

**Tiêu chí hoàn thành:** ba lần liên tiếp chạy end-to-end thành công trên thiết bị
được chỉ định; codec backend decode được; retry không tạo evidence hoặc session trùng;
technical failure không bị trình bày là người dùng thất bại xác minh.

### M2 — Capability/provider architecture và fallback

**Mục tiêu:** orchestration không khởi tạo trực tiếp model implementation.

**Đầu ra:**

- port/contract riêng cho các capability cần thay model độc lập;
- provider registry/factory tại composition root;
- cấu hình `capability -> primary/secondary provider` theo profile;
- bounded timeout, retry/fallback budget và circuit/open-unavailable behavior;
- output có `attempts`, provider/model/revision/config version, duration và reason;
- readiness theo capability và provider;
- fake providers cho contract/integration test.

**Fallback chỉ được kích hoạt khi:** provider unavailable, timeout, invalid output
hoặc lỗi kỹ thuật allowlist. Không fallback khi score thấp hoặc input quality không đạt.

**Tiêu chí hoàn thành:** thay ít nhất một provider chỉ bằng composition/config;
primary lỗi thì secondary hợp lệ chạy; tất cả provider lỗi trả `UNAVAILABLE` và route
manual review/model unavailable, không tự reject.

### M3 — Document quality gate và recapture

**Mục tiêu:** kiểm tra chất lượng trước layout/OCR và cho chụp lại đúng mặt lỗi.

**Đầu ra:**

- capability `document_quality` cho blur, glare, corner coverage, document area,
  brightness, contrast và occlusion;
- reason code ổn định: `DOCUMENT_BLUR`, `DOCUMENT_GLARE`,
  `DOCUMENT_CORNER_MISSING`, `DOCUMENT_TOO_SMALL`, `DOCUMENT_TOO_DARK`,
  `DOCUMENT_TOO_BRIGHT`, `DOCUMENT_OCCLUDED`, `QUALITY_CHECK_UNAVAILABLE`;
- state/transition `RECAPTURE_DOCUMENT` hoặc tên tương đương thống nhất với state machine;
- recapture đúng front/back/passport page, revoke token cũ và audit reason;
- attempt limit lấy từ config, không hard-code quyết định production;
- fixture synthetic cho CCCD 2021, căn cước 2024 và passport TD3.

**Tiêu chí hoàn thành:** bộ fixture rõ/mờ/lóa/mất góc/tối/sáng/che khuất route đúng;
quality failure không gọi OCR/model fallback; evidence tốt trước đó không bị mất nếu
upload thay thế thất bại.

### M4 — Benchmark foundation và dataset intake

**Mục tiêu:** đánh giá model/capability độc lập với session và manual review.

**Đầu ra:**

- thư mục/CLI benchmark riêng, không thay đổi session state hoặc operational DB;
- dataset registry gồm source/version/checksum/license/sensitivity/usage scope,
  distribution permission và approval status;
- split theo identity/document/device để tránh leakage giữa development và test;
- metrics chuẩn theo capability;
- report chứa model/provider/config/dataset/device version, sample count, exclusion,
  latency, resource usage và confidence interval;
- smoke subset synthetic cho CI; full dataset và report nhạy cảm chạy ngoài CI/Git;
- dataset downloader không nằm trong runtime path và không tự tải dataset chưa duyệt.

**Dataset candidate, chưa phải approval:**

| Capability | Candidate | Ghi chú intake |
|---|---|---|
| Document/layout/OCR | [MIDV-2020](https://l3i-share.univ-lr.fr/MIDV2020/midv2020.html) | Mock document; cần chấp nhận license/access |
| Document/layout/OCR | [DocXPand-25k](https://github.com/QuickSign/docxpand/releases/tag/v1.0.0) | Synthetic; dataset CC BY-NC-SA 4.0 |
| Mobile document quality | [MIDV-500/MIDV-2019](https://arxiv.org/abs/1807.05786), [SmartDoc](https://sites.google.com/site/icdar15smartdoc/home) | Kiểm tra license và quyền phân phối trước khi tải |
| CCCD Việt Nam | Fixture synthetic nội bộ | Cần bao phủ mẫu 2021 và 2024 |
| Face matching | [DigiFace-1M](https://microsoft.github.io/DigiFace1M/) | Synthetic; không đủ để chốt production threshold |
| Mobile liveness/PAD | [OULU-NPU](https://sites.google.com/site/oulunpudatabase/) | Cần EULA và quyền truy cập |
| Visual deepfake | [FaceForensics++](https://github.com/ondyari/faceforensics) | Gated/Terms of Use; chỉ external evaluation phù hợp scope |
| Audio spoof | [ASVspoof 2021](https://www.asvspoof.org/index2021.html) | Kiểm tra attribution và phạm vi benchmark |
| Audio-visual/lip-sync | [LAV-DF](https://huggingface.co/datasets/ControlNet/LAV-DF), [FakeAVCeleb](https://github.com/DASH-Lab/FakeAVCeleb) | Non-commercial/gated; cần legal/license review |

**Metrics tối thiểu:**

- quality: defect recall tại false-recapture rate cố định, corner IoU;
- OCR: field exact match, CER/WER, MRZ exact line và check digit;
- face match: ROC/DET, FMR, FNMR và EER;
- PAD: APCER, BPCER, ACER theo attack/device/condition;
- deepfake/lip-sync: AUROC, AUPRC, EER, TPR tại FPR cố định;
- voice challenge: sequence exact match và digit error rate;
- system: failure rate, p50/p95 latency và peak memory.

**Tiêu chí hoàn thành:** cùng một config/dataset checksum sinh report tái lập được;
test split không được dùng để chọn threshold; dataset chưa duyệt bị fail closed.

### M5 — Seed threshold và calibration

**Mục tiêu:** có baseline định lượng để điều chỉnh nhưng không tạo quyết định production.

**Seed `evaluation_only` ban đầu:**

| Capability | Không có tín hiệu xấu | Manual review/inconclusive | Đáng ngờ |
|---|---:|---:|---:|
| Face cosine | `>= 0.40` | `0.30 - 0.40` | `< 0.30` |
| Passive liveness `p_live` | `>= 0.80` | `0.20 - 0.80` | `<= 0.20` |
| Visual deepfake `p_manipulation` | `<= 0.30` | `0.30 - 0.70` | `>= 0.70` |
| Voice challenge | đủ 6/6, similarity `1.0` | sai/thiếu hoặc ASR inconclusive | không dùng để kết luận speaker identity |
| Replay | `< 0.62` | chưa đủ điều kiện xác nhận | `>= 0.62` và confirmed |
| Camera injection | `< 0.60` | metadata/timing chưa đủ | `>= 0.60` kèm điều kiện xác nhận |

Các số trên chỉ là điểm bắt đầu cho threshold sweep. Score từ model không mặc nhiên
là calibrated probability.

**Operating target để chọn threshold từ development split:**

- face match: threshold tại `FMR <= 10^-3`, báo FNMR; báo thêm tại `FMR <= 10^-4`;
- PAD: báo APCER/BPCER/ACER; target technical-demo ban đầu `APCER <= 5%` chỉ dùng
  để đánh giá nội bộ;
- deepfake/lip-sync: TPR tại FPR 1% và 5%, cùng AUROC/AUPRC/EER;
- quality: chọn threshold tại false-recapture rate được công bố trong report;
- OCR/voice dùng accuracy/error metric, không dùng confidence thay accuracy.

**Lifecycle:** chọn trên development split → freeze model/preprocessing/config/device
→ chạy test split → tạo benchmark reference → review/approve scope → version threshold.

**Tiêu chí hoàn thành:** `technical-demo-v1` có report, confidence interval và
benchmark reference; UI ghi rõ `evaluation_only`; session vẫn luôn vào manual review.

### M6 — Admin/manual review có controlled disclosure

**Mục tiêu:** reviewer thấy đủ dữ liệu cần thiết nhưng quyền xem PII/biometric được
tách biệt, có mục đích, thời hạn và audit.

**Input mặc định cho reviewer:**

- session/review metadata, reason code và lịch sử recapture;
- PII/structured fields đã mask, confidence, source side và validation result;
- thumbnail giấy tờ đã mask và document-quality issues;
- ảnh chân dung giấy tờ/selfie representative frame đã kiểm soát;
- face/liveness/deepfake/voice/lip-sync signal;
- provider/model/config/threshold/benchmark provenance;
- model unavailable/fallback attempts được trình bày tách khỏi fraud signal.

**Controlled disclosure:** quyền `review:read`, `pii:unmask`, `evidence:view`,
`biometric:view`, `review:decide`, `evidence:export` và `evidence:delete` tách riêng.
Reviewer phải cung cấp reason/purpose; grant ngắn hạn ràng buộc reviewer/session/data
category; response `no-store`; mọi lần cấp/xem/giải mã/playback/từ chối đều audit.

**Output reviewer:** `APPROVED`, `REJECTED`, `RECAPTURE_REQUESTED`,
`RETRY_ANALYSIS`, `ESCALATED`, kèm reason code allowlist, note và concurrency check.

Technical demo được phép dùng local auth và `.env`, nhưng contract phải nằm sau
authentication/authorization/secret/decrypt interfaces để thay V-ID auth và KMS.

**Tiêu chí hoàn thành:** masked-by-default; không trả storage path/key hoặc signed URL
dài hạn; không có quyền xem raw evidence ngầm từ quyền system admin; mọi disclosure
và decision có audit không chứa PII.

### M7 — Integrated demo hardening và bàn giao

**Mục tiêu:** chứng minh toàn bộ kiến trúc bằng synthetic/test data và thiết bị demo.

**Đầu ra và tiêu chí hoàn thành:**

- mobile chạy end-to-end ba lần liên tiếp trên thiết bị chỉ định;
- quality recapture đúng mặt lỗi;
- đổi provider bằng config và demo primary-failure/secondary-success;
- all-provider-failure trả `UNAVAILABLE`;
- benchmark report và threshold `evaluation_only` hiển thị đúng provenance;
- reviewer masked/unmask/disclosure/decision tạo audit đúng;
- test tải/resource/timeout trên máy demo;
- formatter, linter, type checker, test liên quan, model verify và Docker smoke pass;
- purge toàn bộ session/evidence dùng trong rehearsal và demo;
- cập nhật README, flow design và implementation status theo evidence thực tế.

## 5. Config và secret hardening xuyên suốt

| Loại | Ví dụ | Nơi quản lý hiện tại/đích |
|---|---|---|
| Secret | token signing, evidence key, DB password, reviewer/client credential | `.env` tạm thời qua `SecretProvider`; KMS/secret manager về sau |
| Environment config | URL, timeout, retry, resource limit, feature flag, provider profile | typed settings/environment |
| Versioned policy | fallback chain, quality threshold, recapture limit, review reason | config có schema/version/change control |
| Model constant | input shape, normalization, anchor/stride, class mapping | adapter/model config gắn revision |

Ưu tiên sớm:

- không đưa credential bí mật vào biến `NEXT_PUBLIC_*` hoặc browser bundle;
- startup fail nếu còn placeholder secret ngoài development/test;
- validate range và quan hệ giữa threshold/timeout/provider;
- không dump toàn bộ settings hoặc secret vào log/readiness;
- local `.env` không được commit; `.env.example` chỉ chứa placeholder rõ ràng.

## 6. Quy tắc theo dõi tiến độ

Trạng thái hợp lệ trong `IMPLEMENTATION_STATUS.md`:

- `NOT_STARTED`: chưa bắt đầu;
- `IN_PROGRESS`: đã có work item/branch hoặc thay đổi đang thực hiện;
- `BLOCKED`: có dependency/decision bên ngoài cụ thể;
- `DONE`: code, test, docs và evidence hoàn thành;
- `DEFERRED`: chủ động đưa ra ngoài phạm vi technical demo hiện tại.

Không đánh dấu `DONE` chỉ vì có thiết kế hoặc UI mock. Mỗi milestone `DONE` phải có
link tới code/test/report hoặc lệnh kiểm chứng. Khi trạng thái thay đổi phải cập nhật
ngày, evidence, blocker và next action trong `IMPLEMENTATION_STATUS.md`.

## 7. Quyết định còn cần owner

- nơi lưu benchmark data và license record ngoài Git;
- target false-recapture rate cho document quality technical demo;
- quyền cụ thể để reviewer unmask PII và xem biometric trong technical demo;
- thời hạn disclosure grant và retention của benchmark report nhạy cảm;
- production population/risk target dùng để thay operating target evaluation;
- KMS/secret manager, V-ID auth và threshold production vẫn nằm ngoài technical demo.
