# Dự án eKYC cho V-ID

## Tổng quan

Đây là dự án eKYC được tham chiếu từ [dự án eKYC đã làm trước đó](../C2-App-036).
Dự án tập trung vào eKYC và nâng cấp luồng eKYC của dự án tham chiếu.

## Giai đoạn hiện tại

Mục tiêu gần nhất của dự án là technical demo nội bộ, không phải pilot hoặc
production.

- Technical demo ưu tiên chứng minh kiến trúc, API contract, orchestration,
khả năng chạy offline và khả năng thay model.
- Dữ liệu synthetic hoặc dữ liệu kiểm thử hợp lệ là mặc định.
- Technical demo không được dùng để tuyên bố production-ready, độ chính xác
production, tuân thủ pháp lý hoặc khả năng tự động xác minh danh tính.
- Kết quả AI trong technical demo không được tự động approve/reject; session
phải đi vào manual review hoặc trả trạng thái model unavailable.
- Model chưa được phê duyệt không được coi là hợp lệ cho pilot hoặc production
chỉ vì đã hoạt động trong technical demo.

## Công nghệ

- Backend framework và phiên bản được kế thừa từ dự án tham chiếu.
- Frontend framework, package manager và phiên bản Node được kế thừa từ dự án tham chiếu.
- Database, queue, cache, object storage, ORM và migration tool được kế thừa từ dự án tham chiếu.
- Authentication, authorization, test framework, formatter, linter và type checker được kế thừa từ dự án tham chiếu.
- Không tự thay framework hoặc dependency nền tảng nếu chưa có lý do kỹ thuật được ghi lại. Khi sao chép dependency, phải giữ phiên bản tương thích hoặc ghi rõ migration cần thiết.

## Kiến trúc

Cấu trúc thư mục của dự án đã được tạo sẵn. Khác với dự án tham chiếu, `ai_modules` nằm trong cùng một backend nhưng vẫn tách biệt với `app`.

Dự án áp dụng dependency inversion và dependency injection:

- `backend/app` chứa domain, use case và các interface/port.
- `backend/ai_modules` chứa implementation/adapter cho các model AI và không chứa business workflow.
- Database, evidence storage, queue, cache, encryption/KMS, notification và model phải nằm sau interface để có thể thay implementation.
- Composition root là nơi lựa chọn implementation cụ thể theo environment.
- Khả năng thay frontend được bảo đảm bằng API contract ổn định và version hóa; frontend không phụ thuộc vào implementation nội bộ của backend.

## Luồng eKYC và phạm vi MVP

Luồng eKYC có thay đổi so với dự án tham chiếu. Xem [Tài liệu triển khai](<../C2-App-036/Report/Project Planning>).

- Desktop khởi tạo phiên, hiển thị QR và theo dõi trạng thái.
- Luồng chuẩn thực hiện capture trên mobile web qua QR dùng một lần.
- Trong technical demo local, desktop được phép hiển thị thêm lựa chọn `eKYC bằng
  web` để mở cùng capture URL dùng một lần trong tab trình duyệt mới. Lựa chọn này
  phải nằm sau feature flag, không tạo phiên độc lập, không bỏ qua handoff claim
  và mặc định tắt ngoài cấu hình demo.
- Hỗ trợ cả CCCD gắn chip mẫu 2021 và thẻ căn cước mẫu áp dụng từ 01/07/2024.
- Passport MVP hỗ trợ passport phổ thông theo ICAO TD3.
- MRZ parser phải trung lập với quốc gia, xử lý hai dòng 44 ký tự và kiểm tra check digit theo ICAO.
- Việt Nam là quốc gia được benchmark và bật chính thức đầu tiên. Quốc gia khác chỉ được bật sau khi có fixture, benchmark và rule tương ứng.
- Chưa tuyên bố hỗ trợ NFC/chip passport hoặc xác thực thật/giả của passport.
- MVP gồm face matching, liveness, deepfake, voice challenge và lip-sync.
- Không sử dụng LLM để OCR, extraction, manual review hoặc đưa ra quyết định.

## Frontend

Không tái sử dụng frontend của dự án tham chiếu.

Agent tự thiết kế các màn hình dựa trên luồng eKYC và nhận diện chung, ưu tiên:

- Desktop khởi tạo phiên, hiển thị/tạo lại/revoke QR và theo dõi tiến trình.
- Mobile web chụp giấy tờ, thực hiện voice challenge, liveness và submit.
- Admin và manual review.

## Tích hợp V-ID

- Desktop tạo session, hiển thị QR và có thể theo dõi trạng thái bằng polling.
- Backend đồng thời cung cấp webhook/callback adapter cho hệ thống V-ID.
- Polling và webhook dùng cùng một session state machine.
- Webhook phải có signature, timestamp, replay protection, retry và idempotency.
- Chỉ gửi session ID, trạng thái, public reason code và metadata tối thiểu; không gửi raw OCR, ảnh/video, token hoặc model result chi tiết.
- Authentication provider phải nằm sau interface để hỗ trợ cả local auth và V-ID auth.
- Backend chỉ nhận `subject_ref` opaque khi có thể; không đưa PII tài khoản V-ID vào operational metadata nếu không cần thiết.

## Dữ liệu trong giai đoạn phát triển

- Dữ liệu synthetic là lựa chọn mặc định cho development và automated test.
- Hệ thống không chủ động cung cấp hoặc đóng gói dữ liệu định danh thật.
- Developer có thể tự dùng dữ liệu của chính mình để kiểm thử thủ công và tự chịu trách nhiệm về quyền sử dụng dữ liệu đó.
- Dữ liệu thật không được commit vào Git, đưa vào fixture, Docker image, log, screenshot, artifact CI hoặc tài liệu.
- Không dùng dữ liệu của người khác khi chưa có quyền và mục đích xử lý phù hợp.
- Việc tạm hoãn các hạng mục P0 không đồng nghĩa hệ thống đã production-ready.
- Không ghi PII, token, signed URL hoặc raw evidence vào log.
- Runtime mặc định không được kết nối Internet, ngoại trừ external service đã được cấu hình và allowlist rõ ràng.

## Evidence storage và purge

- Evidence storage phải được truy cập thông qua interface để có thể thay local filesystem bằng object storage.
- Local filesystem được phép dùng trong development và MVP.
- Evidence không được nằm trong public/static directory.
- Tên file và storage key phải là opaque ID, không chứa PII và phải chống path traversal.
- Database chỉ lưu opaque storage key/path, không dùng đường dẫn do client cung cấp.
- Mọi thao tác xem, tải, giải mã hoặc xóa raw evidence phải được phân quyền và audit.
- Xóa session phải idempotent và bao phủ database, evidence file, private record và derived artifact. Phải có cơ chế phát hiện/xử lý orphan.
- Purge scheduler chạy mặc định mỗi 24 giờ và phải cấu hình được.
- Scheduler chỉ xóa dữ liệu đã đến `purge_after`; tần suất chạy purge không phải retention period.
- Retention production vẫn để cấu hình/TBD cho đến khi có quyết định pháp lý.
- Khi chạy nhiều replica, không phụ thuộc local filesystem riêng của một container; dùng shared volume hoặc object storage adapter.

## Quản lý pretrained model

`./models/` là nơi chứa model và artifact AI dùng chung cho toàn dự án. Phải tạo model manifest để lưu metadata của toàn bộ model.

- Manifest phải ghi tên model, chức năng, nguồn, repository/revision, filename,
SHA-256, license, required/optional, approval status, usage scope,
distribution permission và approval reference nếu có.

- Model xuất hiện trong manifest không đồng nghĩa đã được phê duyệt về license,
pháp lý, bảo mật, chất lượng hoặc production. Không được suy luận quyền sử dụng
chỉ từ việc model có thể tải công khai, source code có open-source license hoặc
model đã được dùng trong dự án tham chiếu.

Mỗi model phải có hai trạng thái độc lập:

- `required/optional`: mức độ cần thiết về mặt chức năng đối với build profile.
- `approval_status`: phạm vi được phép sử dụng, gồm:
- `quarantined`: chưa rõ provenance/license; không được bật hoặc đóng gói mặc định.
- `evaluation_only`: chỉ dùng trong technical demo theo phạm vi đã được ghi nhận.
- `production_approved`: đã có phê duyệt cần thiết và benchmark đạt yêu cầu.
- `rejected`: không được sử dụng.

- Docker build được phép truy cập Internet để tải model.
- Chạy local dùng script chung để tải model vào `./models/`.
- Docker build và local downloader phải đọc cùng một model manifest.
- Manifest phải ghi tên model, chức năng, nguồn, repository/revision, filename, SHA-256, license và trạng thái required/optional.
- Mọi checksum phải được pin; không kế thừa entry có checksum trống từ dự án cũ.
- Toàn bộ weights, tokenizer, config và artifact phụ thuộc phải được tải trong local setup hoặc Docker build.
- Runtime chỉ được load model từ local path và không được tự tải artifact còn thiếu từ Hugging Face Hub, GitHub, model registry hoặc nguồn Internet khác.
- API như `from_pretrained()` được phép nếu trỏ tới local artifact và bật chế độ offline tương ứng, ví dụ `local_files_only=True`.
- Cache framework phải nằm trong `./models/` hoặc thư mục cache được quản lý, không phụ thuộc cache ngầm trong home directory.
- Production image phải chứa toàn bộ model required; không mount model từ nguồn không kiểm soát.
- Startup/readiness phải thất bại với thông báo rõ ràng nếu thiếu model required hoặc checksum sai; không tự fallback sang download hay model khác.

Các nhóm model required trong MVP gồm:

- CCCD layout/detection và OCR.
- Passport MRZ detection/OCR.
- Face detection, alignment và embedding.
- Liveness.
- Visual deepfake.
- Voice challenge và speech verification.
- Lip-sync/deepfake audio-video.

## Docker và chứng chỉ CA

Dự án được triển khai bằng Docker. Model có thể lớn nên Dockerfile phải dùng cache phù hợp, timeout/retry hợp lý và multi-stage build để tránh tải lại không cần thiết.

- Custom CA `.crt` được truyền vào Docker build bằng BuildKit secret.
- Không commit certificate nội bộ, CA bundle của môi trường, secret hoặc private key vào Git.
- Build stage cài certificate vào `/usr/local/share/ca-certificates/` và chạy `update-ca-certificates`.
- Build secret không được copy sang image layer hoặc runtime image và không được in nội dung ra build log.
- Pip, curl, Python requests và model downloader dùng system trust store sau khi được cập nhật.
- Nếu runtime cần custom CA để gọi dịch vụ nội bộ, certificate phải được cung cấp riêng tại runtime; không tái sử dụng BuildKit secret như runtime secret.

## Admin và manual review

Tái sử dụng có chọn lọc backend, role, audit và nghiệp vụ manual review từ dự án tham chiếu. Không tái sử dụng frontend admin cũ.

- Frontend admin phải được thiết kế mới theo nhận diện V-ID.
- Không tái sử dụng LLM admin review, LLM recommendation hoặc `ai_admin_review`.
- Manual reviewer xem hồ sơ đã mask theo mặc định.
- Xem raw evidence, decrypt, approve, reject, retry, export hoặc delete phải được phân quyền và ghi audit.

## Thứ tự ưu tiên tài liệu

1. `AGENTS.md` và quyết định mới nhất của người dùng.
2. `EKYC_FLOW_DESIGN.md`.
3. `M0_CONTRACT_GOVERNANCE_BASELINE.md`.
4. `PROJECT_ROADMAP.md`.
5. `IMPLEMENTATION_STATUS.md`.
6. `EKYC_FLOW_DESIGN_SIMPLIFIED.md` chỉ dùng để diễn giải.

Các tài liệu chính thức của dự án hiện nằm trong `docs/`. Tài liệu từ dự án
tham chiếu hoặc từ bản kế hoạch 2.0 cũ chỉ được dùng khi người dùng chỉ định rõ
trong ngữ cảnh hiện tại; không được tự coi là nguồn ưu tiên hoặc nguồn ràng
buộc cho dự án này.

Không tự giải quyết mâu thuẫn giữa các tài liệu.

## Các quyết định còn mở

Các mục sau không chặn scaffold và phát triển MVP bằng dữ liệu synthetic hoặc dữ liệu kiểm thử hợp lệ, nhưng không được tự mặc định là đã sẵn sàng cho production:

- Mục đích nghiệp vụ, controller, lawful basis và phạm vi người dùng production.
- Retention production cho từng loại dữ liệu và từng kết quả phiên.
- Region của production, backup, monitoring và DR.
- External processor, KMS và cơ chế quản lý secret production.
- Threshold production và điều kiện auto-approve/auto-reject/manual review.
- SLA, timeout, retry, session expiry và recapture limit production.
- Quyền production cho decrypt, export, correct và approve deletion.

Khi implementation phụ thuộc trực tiếp vào một quyết định còn mở, phải thiết kế qua interface/configuration, đọc lại tài liệu tham chiếu và hỏi người dùng nếu không thể tiếp tục mà không hard-code quyết định đó. Không tự hợp lý hóa quyết định production.

## Hoàn thành công việc

Mọi thay đổi phải:

- Có test phù hợp.
- Chạy formatter, linter, type checker và test liên quan thành công.
- Không tạo runtime model download.
- Không đưa PII hoặc secret vào source, log, fixture, image hay artifact CI.
- Cập nhật README/docs khi thay đổi kiến trúc, API, data model, luồng UX, model hoặc cách triển khai.
