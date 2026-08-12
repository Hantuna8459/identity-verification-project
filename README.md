# V-ID eKYC

MVP foundation cho luồng xác minh danh tính V-ID: desktop tạo phiên và QR một lần,
capture giấy tờ bằng camera hoặc upload ảnh CCCD trên web, cùng challenge camera trên mobile/desktop,
lựa chọn web-capture dành cho technical demo,
backend quản lý state machine và evidence mã hóa, cùng giao diện manual review mới.

**Tài liệu dự án:** xem tại [`docs/`](docs/). Roadmap thực thi nằm ở [`docs/PROJECT_ROADMAP.md`](docs/PROJECT_ROADMAP.md) và tiến độ được duy trì tại [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md).

> Trạng thái hiện tại: technical demo nội bộ. Luồng submit đã gọi offline inference cho CCCD layout/OCR, passport TD3 MRZ, face matching, liveness, visual deepfake, voice challenge và lip-sync. Kết quả chỉ là tín hiệu kỹ thuật và luôn đi vào manual review; không model nào được phép auto-approve/auto-reject. Xem `docs/IMPLEMENTATION_STATUS.md`.

## Thành phần

- `frontend/`: Next.js 16, UI mới tông trắng/đỏ cho desktop, responsive camera capture và admin.
- `backend/app/`: FastAPI, domain/use case, API v2, PostgreSQL, evidence storage mã hóa AES-GCM và purge worker.
- `backend/ai_modules/ekyc/`: adapter inference offline cho document, face, video và voice; không chứa business decision.
- `backend/ai_modules/lipsync/`: microservice SyncNet/S3FD độc lập.
- `models/`: nguồn artifact cho runtime chạy trực tiếp trên host; Git chỉ lưu manifest và model YOLO CCCD như một ngoại lệ.
- `scripts/models.py`: tải/kiểm tra model ở local hoặc build time; runtime không tải model.
- `compose.yml`: PostgreSQL, backend, purge worker, lip-sync và frontend.

## Chạy bằng Docker

Yêu cầu Docker có BuildKit. Node trên host không cần thiết khi chạy Docker.

```bash
cp .env.example .env
```

Đổi toàn bộ secret/password trong `.env`. `HOST_CA_BUNDLE` phải trỏ tới CA bundle có thật. CA được mount bằng BuildKit secret và không được đưa vào Git. Riêng model YOLO CCCD được lưu trong Git để một bản clone mới có thể build ngay.

```bash
DOCKER_BUILDKIT=1 docker compose --env-file .env build
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

Mặc định:

- Frontend: `http://127.0.0.1:3000`
- API docs: `http://127.0.0.1:8000/api/v2/docs`
- Health: `http://127.0.0.1:8000/api/v2/utils/health-check`
- Admin: `http://127.0.0.1:3000/admin`

Sau khi tạo phiên, màn hình hiển thị đồng thời QR và lựa chọn `eKYC bằng web`.
Lựa chọn web mở chính capture URL dùng một lần của QR trong tab mới; nó vẫn phải
claim handoff token và không tạo session độc lập. Compose bật lựa chọn này qua
`WEB_CAPTURE_ENABLED=true` cho technical demo. Đặt `false` và build lại frontend
để trở về luồng chỉ dùng QR; Dockerfile mặc định tắt nếu build ngoài Compose mà
không truyền build arg.

Các cổng dev chỉ bind vào loopback. Nếu Docker daemon của môi trường không hỗ trợ host port forwarding, probe trực tiếp trong container:

```bash
docker exec vid-ekyc-backend-1 curl -f http://localhost:8000/api/v2/utils/health-check
docker exec vid-ekyc-frontend-1 node -e "fetch('http://127.0.0.1:3000').then(r => console.log(r.status))"
```

Dừng stack (không xóa volume):

```bash
docker compose --env-file .env down
```

Không dùng `down -v` nếu cần giữ database/evidence development.

Nếu database volume đã được tạo bằng mật khẩu khác, thay đổi `POSTGRES_PASSWORD` trong `.env` không tự đổi password role PostgreSQL. Hãy dùng đúng một env file cho mọi lần chạy, đồng bộ lại role `vid` bằng `ALTER ROLE` trong container database, rồi recreate backend. Không commit `.env` và không dùng song song `.env`, shell environment và `--env-file` với các giá trị khác nhau.

## Model

`models/manifest.json` là nguồn sự thật chung về model ID, nguồn tải, revision,
đường dẫn, kích thước và SHA-256. Local runtime và Docker dùng cùng manifest
nhưng không dùng chung một bản sao vật lý của model:

- Khi chạy backend/inference trực tiếp trên host, downloader lưu artifact vào
  `./models/` và local runtime đọc từ thư mục này.
- Khi Docker build, stage `model-fetcher` tải và xác minh artifact trong build
  filesystem, sau đó copy chúng vào runtime image.
- Docker runtime đọc model đã được bake trong image tại `/app/models` hoặc
  `/app/weights`; Compose không tạo model volume và không bind mount `./models`.
- Docker build không đồng bộ model ngược từ image/build cache về `./models` trên
  host. Vì vậy việc host chỉ có manifest và CCCD YOLO sau khi build là bình thường.

Git lưu `models/manifest.json` và `models/cccd_layout_yolov11.pt` như các ngoại
lệ. Các binary model khác trong `./models` được ignore và không được commit.

Tải model cho local development bằng cùng manifest:

```bash
python3 scripts/models.py
python3 scripts/models.py --verify-only
```

Downloader ghi file tạm rồi replace atomically và retry có giới hạn. Container
đặt `HF_HUB_OFFLINE=1` và `TRANSFORMERS_OFFLINE=1`; runtime không tải model và
readiness kiểm tra tồn tại, size cùng SHA-256 của toàn bộ artifact required.

Profile `technical_demo` hiện bật:

- CCCD YOLO11 layout + RapidOCR PP-OCRv6 small;
- passport TD3 dùng RapidOCR và parser/check digit ICAO trung lập quốc gia;
- InsightFace `buffalo_l` qua SCRFD/ArcFace ONNX trực tiếp;
- MiniFASNetV2 và Deep-Fake-Detector-v2 ONNX;
- Vosk Vietnamese small 0.4 cho voice challenge;
- SyncNetV2/S3FD qua service lip-sync.

`vietocr_vgg_transformer.pth` có entry/checksum trong manifest, `approval_status`
`evaluation_only` với `usage_scope: [benchmark_only]` (quyết định owner 2026-08-11,
license vẫn `WEIGHT_LICENSE_REVIEW_REQUIRED` - chưa review) - vẫn không được
downloader/Docker build tải cho profile `technical_demo` vì `usage_scope` không khớp
profile đó, chỉ dùng được cho benchmark nội bộ ngoài runtime path. InsightFace
`buffalo_l` chỉ là `evaluation_only` cho demo nội bộ, không được hiểu là đã có quyền
phân phối hoặc dùng production.

Khi manifest thay đổi, cần build lại image và recreate container bằng đúng env
file; running container không tự nhận manifest mới:

```bash
docker compose --env-file .env build backend lipsync
docker compose --env-file .env up -d --force-recreate backend purge lipsync
```

Model có trong manifest hoặc load thành công chỉ chứng minh integrity/kỹ thuật,
không đồng nghĩa model đã được phê duyệt cho distribution, pilot hoặc production.
Xem policy `approval_status` và `usage_scope` trong `AGENTS.md`.

## Kết quả inference technical demo

Khi mobile submit, backend giải mã evidence trong memory, truyền bytes qua
`EkycAnalyzer`, rồi xóa file media tạm sau inference. Analysis được lưu chỉ gồm
status, engine, confidence/score, số lượng vùng OCR và kết quả check digit; không
lưu raw OCR text, MRZ, transcript, face embedding hoặc evidence đã giải mã.

Face matching lấy tối đa `MAX_VIDEO_FRAMES` frame phân bố đều từ video (mặc định
36), chọn tối đa `MAX_FACE_MATCH_FRAMES` face có detection confidence cao nhất
(mặc định 12), rồi dùng median cosine similarity làm score quan sát. Các giá trị
này phục vụ technical demo và vẫn cần benchmark trước khi chọn cấu hình production.

Nếu evidence không đọc được, model/service thiếu hoặc inference lỗi, capability
trả `INCONCLUSIVE`/`UNAVAILABLE`; session vẫn vào `MANUAL_REVIEW`. Readiness sẽ
trả 503 khi `REQUIRE_MODELS=true` và artifact required thiếu/sai checksum.

Trong technical demo, `DEMO_OCR_RERUN_ENABLED=true` bật thao tác reviewer chạy
lại riêng OCR giấy tờ. Backend giải mã document evidence trong memory, không đọc
selfie/video, không persist OCR text, trả `Cache-Control: no-store` và audit chỉ
ghi loại giấy tờ/evidence. Feature này phải tắt ngoài technical demo và được thay
bằng encrypted structured-result store cùng controlled disclosure.

## Phát triển local

Backend (Python 3.11+):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Frontend yêu cầu Node >= 20.9 (Docker dùng Node 22):

```bash
cd frontend
npm ci
NEXT_PUBLIC_WEB_CAPTURE_ENABLED=true npm run dev
```

## Kiểm tra

```bash
cd backend
uv run ruff check app ai_modules tests
uv run mypy app/adapters/analyzer.py app/domain/ports.py ai_modules/ekyc --ignore-missing-imports
uv run pytest -q

cd ../frontend
npm audit --omit=dev
npm run typecheck
npm run lint
npm run build

cd ..
python3 scripts/models.py --verify-only
docker compose --env-file .env.example config --quiet
```

## API và auth development

API base là `/api/v2`.

- V-ID client: header `X-V-ID-Client-Key`.
- Desktop polling/session action: header `X-Session-Token` trả về khi tạo session.
- Capture client trên mobile hoặc desktop: `Authorization: Bearer <capture_token>` sau khi claim QR token một lần.
- `POST /ekyc/capture/document-type`: người dùng chọn nhóm `CCCD` hoặc `PASSPORT` ngay tại màn hình chụp; không chọn revision CCCD.
- CCCD trên web cho phép upload ảnh mặt trước/mặt sau hoặc chụp trực tiếp; hộ chiếu dùng camera.
- Challenge dùng camera/microphone trực tiếp qua browser; UI không cung cấp input chọn video có sẵn.
- Reviewer: `Authorization: Bearer <reviewer_token>`.

Các token cấu hình trong `.env.example` chỉ dành cho local. Production phải thay bằng authentication provider/KMS/secret manager qua adapter, không đưa client credential bí mật vào bundle frontend.

## Dữ liệu và an toàn

- Evidence local nằm trong private volume và được mã hóa AES-GCM trước khi ghi.
- Storage key là opaque và được kiểm tra chống path traversal.
- Không commit dữ liệu thật, `.env`, certificate, key hoặc evidence.
- Purge scheduler mặc định chạy mỗi 24 giờ và chỉ xóa session đến `purge_after`; retention production vẫn chưa được quyết định.
- Manual review hiện không cung cấp endpoint tải/decrypt raw evidence.
- Hệ thống hiện chưa production-ready; các quyết định pháp lý, retention production, threshold và quyền truy cập vẫn mở theo `AGENTS.md`.
