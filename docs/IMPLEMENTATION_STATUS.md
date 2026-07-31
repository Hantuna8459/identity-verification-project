# Trạng thái triển khai

Cập nhật: 2026-07-31.

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
- Voice challenge dùng Vosk Vietnamese small 0.4 local; transcript chỉ tồn tại
  trong memory và không được lưu vào analysis.
- SyncNetV2/S3FD lip-sync service được gọi từ pipeline khi `LIPSYNC_URL` cấu hình.
- Submit đọc evidence qua storage port và chỉ lưu capability status/score/engine;
  không lưu OCR text, MRZ, transcript, embedding hoặc raw evidence.
- Docker backend/lip-sync images build thành công, verify mọi artifact trong
  runtime layer và smoke-load mọi engine bằng user không đặc quyền.
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
  `INCONCLUSIVE` với reason code riêng. Signal này chưa benchmark/calibrate và
  chưa chứng minh khả năng chống replay hoặc camera injection.
- Lỗi capability trả `INCONCLUSIVE`/`UNAVAILABLE` và không được diễn giải là fraud.

## Contract chưa triển khai hoàn chỉnh

- Webhook callback mới có port và trường `callback_url`; dispatcher/outbox có signature, retry, replay protection và idempotency chưa được nối. Polling đã hoạt động.
- Auth local dùng shared development token; V-ID auth provider thực tế chưa nối.
- Chưa có migration framework; bảng được tạo từ SQLModel khi startup. Cần migration trước production.
- Raw-evidence viewer/decrypt/export không được mở cho admin vì quyền production chưa được quyết định.

## Việc còn lại để đóng gói technical demo

1. Bổ sung fixture synthetic/media hợp lệ để chạy full submit qua tất cả engine,
   thay vì chỉ unit test và smoke inference từng model.
2. Hiển thị capability status/score an toàn trong admin UI nếu cần cho buổi demo.
3. Benchmark riêng cho CCCD 2021, căn cước 2024 và passport Việt Nam TD3.
4. Kiểm thử tải đồng thời/resource limit và timeout của pipeline trên máy demo.
5. Chốt cách trình bày license notice cho các artifact được phép dùng nội bộ.

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
