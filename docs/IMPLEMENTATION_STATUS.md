# Trạng thái triển khai

Cập nhật: 2026-08-03.

Roadmap thực thi chi tiết nằm tại [`PROJECT_ROADMAP.md`](./PROJECT_ROADMAP.md).
Tài liệu hiện tại là nguồn theo dõi trạng thái, evidence, blocker và next action.
Khi tiến độ thay đổi phải cập nhật bảng ở mục **Tiến độ roadmap đang hoạt động**;
không đánh dấu `DONE` nếu chưa có code, test, docs và evidence kiểm chứng tương ứng.

## Mục tiêu và phạm vi hiện tại

Mục tiêu gần nhất là technical demo nội bộ, không phải pilot hoặc production.
Demo dùng để chứng minh kiến trúc, API contract, orchestration, khả năng chạy
offline và khả năng thay model qua adapter/configuration.

- Dữ liệu synthetic hoặc dữ liệu kiểm thử hợp lệ là mặc định.
- Kết quả AI không tự động approve/reject; session phải đi vào `MANUAL_REVIEW`
  hoặc trả trạng thái model `UNAVAILABLE`.
- Technical demo không chứng minh độ chính xác production, tuân thủ pháp lý hoặc
  khả năng tự động xác minh danh tính.
- Model chạy được trong demo không mặc nhiên trở thành model được phép dùng cho
  pilot, production hoặc artifact được phép phân phối.

## Đã triển khai và kiểm chứng

- Session state machine, one-time QR handoff, capture token và manual review.
- Màn hình desktop hiển thị QR và lựa chọn `eKYC bằng web` trong technical demo.
  Cả hai dùng chung handoff token một lần; web capture không tạo session riêng
  và được kiểm soát bằng build-time feature flag.
- Loại giấy tờ được chọn ngay trong màn hình capture với hai lựa chọn `CCCD` và
  `Hộ chiếu`; người dùng không phải biết revision CCCD 2021/2024.
- CCCD trên web cho phép upload ảnh mặt trước/mặt sau hoặc chụp trực tiếp bằng
  camera; hộ chiếu tiếp tục dùng camera. Challenge khuôn mặt dùng camera và
  microphone trên cả desktop/mobile. Luồng chỉ yêu cầu một lần quay mỗi bên theo
  chuỗi nhìn thẳng → quay trái → trở về giữa → quay phải → trở về giữa → đọc số;
  người dùng tự xác nhận từng bước, không hiển thị bộ đếm thời gian và không cho
  chọn hoặc upload video có sẵn. Sau bước cuối, UI chuyển ngay sang màn hình xử
  lý trước khi upload và inference hoàn tất.
- Evidence mã hóa, opaque storage key và purge idempotent theo `purge_after`.
- Manifest schema 1.1 với source/revision/SHA-256/license, `approval_status`,
  `usage_scope`, distribution permission và approval reference.
- Downloader dùng chung cho host/Docker, hỗ trợ archive nhiều artifact, cache,
  extraction an toàn và profile; runtime không tải model.
- CCCD YOLO11 layout và RapidOCR PP-OCRv6 small cho OCR full-page/region.
- Passport TD3 OCR, parser hai dòng 44 ký tự và toàn bộ check digit ICAO.
- InsightFace `buffalo_l` load trực tiếp SCRFD/ArcFace bằng ONNX Runtime, không
  dùng runtime registry/download của package InsightFace.
- MiniFASNetV2 liveness và Deep-Fake-Detector-v2 inference ONNX.
- Replay attack và camera injection heuristic chạy offline, không cần thêm pretrained weight; kết quả được expose trong `capabilities.replay_attack` và `capabilities.camera_injection`.
- Voice challenge dùng Vosk Vietnamese small 0.4 local; transcript chỉ tồn tại
  trong memory và không được lưu vào analysis.
- SyncNetV2/S3FD lip-sync service được gọi từ pipeline khi `LIPSYNC_URL` cấu hình.
- Analysis dùng contract `model-analysis/1.2`: `execution_status` chỉ phản ánh model
  có chạy được hay không; `review_signal` phản ánh tín hiệu cho reviewer; score,
  hướng diễn giải và trạng thái phê duyệt threshold được tách riêng. Face match,
  liveness và visual deepfake không bị gán pass/fail khi threshold production chưa
  được phê duyệt; voice challenge, active liveness, lip-sync và anti-injection có
  reason code rõ ràng khi mismatch, thiếu bước hoặc đáng ngờ.
- Submit đọc evidence qua storage port và chỉ lưu execution/review signal, metric và
  metadata an toàn; không lưu OCR text, MRZ, transcript, embedding hoặc raw evidence.
- Docker backend/lip-sync images build thành công, verify mọi artifact trong
  runtime layer và smoke-load mọi engine bằng user không đặc quyền.
- Reviewer dùng full-screen dialog với typography phù hợp, tách kết quả OCR khỏi
  model telemetry và chỉ đặt score chưa có threshold trong chi tiết kỹ thuật.
  Feature flag `DEMO_OCR_RERUN_ENABLED` cho phép reviewer chủ động giải mã document
  evidence trong memory và chạy lại riêng OCR; response không cache, output không
  persist và audit không chứa OCR text.
- Mọi kết quả technical demo luôn route sang `MANUAL_REVIEW`.

## Trạng thái model và governance

Các model active dùng profile `technical_demo` và có trạng thái
`evaluation_only`; vì vậy readiness báo `pipeline_ready=true` nhưng
`production_ready=false`. Cụ thể: CCCD YOLO11, RapidOCR PP-OCRv6, InsightFace
`buffalo_l`, MiniFASNetV2, visual deepfake ONNX, Vosk Vietnamese, SyncNetV2 và
S3FD.

VietOCR `vgg_transformer` đã được inventory với filename/size/SHA-256 nhưng giữ
`quarantined`, không tải và không load vì license của weight chưa rõ. InsightFace
`buffalo_l` chỉ được dùng cho đánh giá nội bộ theo hạn chế non-commercial
research/evaluation; không được phân phối hoặc đưa sang pilot/production nếu chưa
có approval mới. SyncNet/S3FD và custom CCCD YOLO vẫn còn rủi ro license/provenance
được thể hiện trực tiếp trong manifest; technical demo không giải quyết rủi ro đó.

## Giới hạn inference hiện tại

- Chưa có benchmark/threshold được phê duyệt; score chỉ để quan sát kỹ thuật.
- CCCD chưa lưu structured PII extraction; demo chỉ trả metadata OCR/layout an toàn.
- MRZ parser kiểm tra format/check digit nhưng không lưu nội dung MRZ.
- Voice hiện kiểm tra chuỗi sáu chữ số bằng ASR, chưa phải speaker verification.
- Active-liveness kỹ thuật dùng landmark SCRFD để kiểm tra đủ chuỗi chính diện,
  hai hướng quay đối nhau và các lần trở về giữa; kết quả thiếu bước là
  `INCONCLUSIVE` với reason code riêng. Replay attack và camera injection heuristic
  đã được nối vào pipeline, dùng duplication/flicker, motion, video metadata và
  challenge timing; output có score, threshold, suspicious, reason codes và warnings.
  Các signal này chưa benchmark/calibrate và chưa được coi là bằng chứng chống spoof
  production.
- Lỗi capability trả `INCONCLUSIVE`/`UNAVAILABLE` và không được diễn giải là fraud.
- Heuristic replay/camera dựa trên tối đa 36 frame sample; cần benchmark thêm với replay màn hình, frame freeze và camera injection thực tế.
- Face matching dùng tối đa 12 frame có detection confidence cao nhất trong số
  frame đã lấy mẫu và tổng hợp cosine similarity bằng median. Hai giới hạn được
  cấu hình độc lập qua `MAX_VIDEO_FRAMES` và `MAX_FACE_MATCH_FRAMES`; số lượng và
  cách tổng hợp được trả trong metadata để phục vụ benchmark technical demo.

## Contract chưa triển khai hoàn chỉnh

- Webhook callback mới có port và trường `callback_url`; dispatcher/outbox có signature, retry, replay protection và idempotency chưa được nối. Polling đã hoạt động.
- Auth local dùng shared development token; V-ID auth provider thực tế chưa nối.
- Chưa có migration framework; bảng được tạo từ SQLModel khi startup. Cần migration trước production.
- Raw-evidence viewer/decrypt/export không được mở cho admin vì quyền production chưa được quyết định.

## Tiến độ roadmap đang hoạt động

Trạng thái hợp lệ: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `DEFERRED`.
Thứ tự và tiêu chí hoàn thành đầy đủ của từng milestone nằm trong
[`PROJECT_ROADMAP.md`](./PROJECT_ROADMAP.md).

| ID | Milestone | Trạng thái | Evidence hiện tại | Blocker/gap chính | Next action |
|---|---|---|---|---|---|
| M0 | Contract, governance và baseline config | `IN_PROGRESS` | Roadmap hợp nhất đã được tạo; model manifest và analysis contract 1.2 hiện có | Chưa có ADR capability/fallback/disclosure; chưa chốt điện thoại demo và dataset approval owner | Chốt `demo_device_profile`, capability list, contract kế tiếp và dataset registry schema |
| M1 | Mobile demo-ready trên thiết bị chỉ định | `IN_PROGRESS` | QR claim, capture CCCD/passport, camera/microphone challenge và submit đã chạy ở web | URL/port đang thiên về localhost/loopback; chưa có local HTTPS, preflight, codec matrix và E2E trên thiết bị chỉ định | Ghi model/OS/browser của điện thoại; dựng same-origin HTTPS; chạy device preflight và ba lượt E2E |
| M2 | Capability/provider architecture và fallback | `NOT_STARTED` | Có `EkycAnalyzer` port tổng và capability error isolation | Pipeline vẫn khởi tạo trực tiếp model implementation; chưa có provider registry/fallback attempts | Tách capability contracts, composition registry và fake provider tests |
| M3 | Document quality gate và recapture | `NOT_STARTED` | Flow design đã mô tả blur/glare/corner/occlusion | Chưa có implementation, reason-code contract, fixture hoặc state recapture trong runtime hiện tại | Implement quality contract trước OCR và fixture synthetic rõ/mờ/lóa/mất góc |
| M4 | Benchmark foundation và dataset intake | `NOT_STARTED` | Implementation status đã xác định metric OCR/liveness cần có; candidate dataset được inventory trong roadmap | Chưa có runner/registry/split/report; license dataset chưa được review | Tạo dataset manifest schema, benchmark CLI skeleton và smoke synthetic subset |
| M5 | Seed threshold và calibration | `NOT_STARTED` | Replay/camera heuristic có threshold evaluation; seed đề xuất được ghi trong roadmap | Face/liveness/deepfake chưa có calibrated threshold hoặc benchmark reference | Chỉ chạy threshold sweep sau M4; freeze `technical-demo-v1` trên development split và report test split |
| M6 | Admin/manual review controlled disclosure | `NOT_STARTED` | Có review queue, model telemetry, OCR rerun tạm thời và approve/reject | Chưa có masked structured PII, biometric/evidence grant, quyền tách biệt hoặc output recapture/retry/escalate | Chốt review input/output contract; thiết kế disclosure grant/audit trước khi mở raw evidence |
| M7 | Integrated demo hardening | `NOT_STARTED` | Docker/model smoke và các unit/integration test nền hiện có | Phụ thuộc M1-M6; chưa có full synthetic E2E, load/resource test và demo runbook hoàn chỉnh | Lập acceptance suite và chỉ bắt đầu gate tích hợp khi milestone phụ thuộc có evidence |
| X1 | Config và secret hardening xuyên suốt | `IN_PROGRESS` | Backend dùng typed settings và `.env`; model/runtime offline flags đã có | Còn placeholder development, credential trong `NEXT_PUBLIC_*`, threshold/hằng số rải rác và chưa có `SecretProvider` | Loại secret khỏi browser bundle; phân loại config; fail placeholder ngoài development/test |
| X2 | Dataset license/provenance review | `NOT_STARTED` | Danh sách candidate và yêu cầu manifest đã được ghi | Chưa có approval owner, nơi lưu data hoặc license record | Chỉ định owner; review MIDV/DocXPand/OULU/ASVspoof/deepfake candidates trước download |

### Quy tắc cập nhật bảng

- `IN_PROGRESS` phải có work item và next action cụ thể.
- `BLOCKED` phải ghi dependency/decision bên ngoài và owner nếu đã biết.
- `DONE` phải dẫn được tới code/test/report hoặc lệnh kiểm chứng; thiết kế hoặc UI
  mock riêng lẻ không đủ để đánh dấu hoàn thành.
- Nếu đổi model, preprocessing, aggregation hoặc device profile, M5 phải quay lại
  `IN_PROGRESS` cho capability bị ảnh hưởng.
- Mọi dataset mới phải cập nhật X2 trước khi được dùng trong M4/M5.

### Gate technical demo tiếp theo

Technical demo kế tiếp chỉ được coi là đóng gói xong khi:

1. mobile chạy end-to-end ba lần liên tiếp trên điện thoại được chỉ định qua HTTPS;
2. ảnh mờ/lóa/thiếu góc yêu cầu chụp lại đúng mặt;
3. có thể đổi provider bằng config và chứng minh fallback có provenance;
4. all-provider-failure trả `UNAVAILABLE`, không tự approve/reject;
5. benchmark chạy độc lập session và threshold có report `evaluation_only`;
6. reviewer xem dữ liệu mask mặc định; disclosure PII/biometric được phân quyền và audit;
7. full synthetic/test E2E, resource/timeout test, formatter, linter, type checker,
   model verification và Docker smoke đều đạt;
8. session/evidence dùng trong rehearsal và demo được purge.

## Điều kiện để gọi là MVP feature-complete

Các điều kiện này nằm sau technical demo và không được suy ra là đã đạt chỉ vì
demo chạy end-to-end.

1. Hoàn tất benchmark, model card, provenance/license review và approval reference
   cho từng artifact muốn dùng ngoài đánh giá nội bộ.
2. Chuyển xử lý evidence/video lớn sang interface memory-bounded stream hoặc temp
   storage được kiểm soát thay vì giữ toàn bộ payload trong memory.
3. Thêm fixture/benchmark riêng cho CCCD 2021, căn cước 2024 và passport Việt Nam TD3.
4. Benchmark/calibrate từng capability và version hóa threshold theo profile; không
   suy ra auto-decision khi chưa có quyết định nghiệp vụ/pháp lý.
5. Triển khai webhook outbox; kiểm thử retry/idempotency/signature.
6. Hoàn thiện speaker verification và benchmark/calibrate active-liveness, replay,
   camera-injection ngoài rule sequence kỹ thuật và đối chiếu nội dung voice
   challenge hiện tại.
7. Chỉ dùng model `production_approved` trong production build profile; readiness
   phải fail closed nếu thiếu model required hoặc approval không hợp lệ.
