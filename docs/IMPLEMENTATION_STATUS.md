# Trạng thái triển khai

Cập nhật: 2026-07-30.

## Đã triển khai và kiểm chứng

- Session state machine, one-time QR handoff, chống replay/revoke và capture token có thời hạn.
- Mobile upload cho CCCD 2021, căn cước 2024 hoặc passport TD3, voice challenge và selfie video.
- Evidence adapter dùng encrypted local storage, opaque key và purge idempotent theo `purge_after`.
- PostgreSQL, audit event, manual review queue và quyết định approve/reject.
- Frontend mới cho desktop/mobile/admin; không sao chép frontend tham chiếu.
- Model manifest chung, checksum pin, downloader build/local, CCCD qua BuildKit secret và offline runtime flags; binary không nằm trong Git.
- SyncNet/S3FD lip-sync service load pretrained weights cục bộ và expose `POST /api/lip-sync`.
- Docker image cho frontend/backend/lip-sync và Compose stack đầy đủ.

## Chưa hoàn tất trong inference orchestrator

`OfflineModelAnalyzer` hiện xác minh integrity của artifact rồi luôn trả `MANUAL_REVIEW`. Nó chưa đọc evidence hoặc gọi chuỗi inference dưới đây:

- CCCD layout + OCR/extraction cho hai mẫu thẻ.
- Passport MRZ detection/OCR và TD3 parser/check digit.
- Face extraction/alignment/embedding/matching.
- MiniFASNet liveness và visual deepfake ONNX.
- Voice challenge ASR/speech verification.
- Gọi lip-sync service từ luồng submit và tổng hợp risk signal.

Lý do fail-safe: dự án tham chiếu có một số module tự tải RapidOCR/InsightFace khi runtime và pipeline extraction mặc định gọi LLM. Hai hành vi này trái quyết định của dự án mới, nên không sao chép nguyên khối. Chỉ bật auto-decision sau khi đã có đủ artifact pin trong manifest, fixture synthetic/hợp lệ, benchmark và threshold được phê duyệt.

## Contract chưa triển khai hoàn chỉnh

- Webhook callback mới có port và trường `callback_url`; dispatcher/outbox có signature, retry, replay protection và idempotency chưa được nối. Polling đã hoạt động.
- Auth local dùng shared development token; V-ID auth provider thực tế chưa nối.
- Chưa có migration framework; bảng được tạo từ SQLModel khi startup. Cần migration trước production.
- Raw-evidence viewer/decrypt/export không được mở cho admin vì quyền production chưa được quyết định.

## Điều kiện để gọi là MVP feature-complete

1. Pin thêm toàn bộ OCR, MRZ, face embedding và speech artifacts cùng license/revision/SHA-256.
2. Viết adapter inference không mạng và nối evidence decrypted theo memory-bounded stream/temp file.
3. Thêm fixture/benchmark riêng cho CCCD 2021, căn cước 2024 và passport Việt Nam TD3.
4. Nối lip-sync, liveness, deepfake, face và voice thành result schema version hóa.
5. Triển khai webhook outbox; kiểm thử retry/idempotency/signature.
6. Chốt threshold để auto-decision hoặc tiếp tục manual-review-only.
