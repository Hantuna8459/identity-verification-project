# V-ID eKYC

MVP foundation cho luồng xác minh danh tính V-ID: desktop tạo phiên và QR một lần, mobile capture giấy tờ/video, backend quản lý state machine và evidence mã hóa, cùng giao diện manual review mới.

> Trạng thái hiện tại: nền tảng ứng dụng và Docker stack chạy được end-to-end đến manual review. SyncNet lip-sync đã có service inference thật. Orchestrator AI tổng hợp cho OCR/MRZ, face matching, liveness, visual deepfake và voice verification vẫn là adapter fail-safe và chưa được phép auto-approve/auto-reject. Xem `docs/IMPLEMENTATION_STATUS.md`.

## Thành phần

- `frontend/`: Next.js 16, UI mới tông trắng/đỏ cho desktop, mobile capture và admin.
- `backend/app/`: FastAPI, domain/use case, API v2, PostgreSQL, evidence storage mã hóa AES-GCM và purge worker.
- `backend/ai_modules/lipsync/`: microservice SyncNet/S3FD độc lập.
- `models/`: chỉ chứa manifest; model binaries không được commit.
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

## Model

Git lưu `models/manifest.json` và `models/cccd_layout_yolov11.pt` như một ngoại lệ. Docker model-fetcher dùng YOLO CCCD từ build context, tải các pretrained artifact còn lại có URL, rồi kiểm tra size/SHA-256 cho toàn bộ model.

Tải model cho local development bằng cùng manifest:

```bash
python3 scripts/models.py \
  --artifact cccd-layout-yolov11=models/cccd_layout_yolov11.pt
python3 scripts/models.py --verify-only
```

Downloader ghi file tạm rồi replace atomically và retry có giới hạn. Production container đặt `HF_HUB_OFFLINE=1` và `TRANSFORMERS_OFFLINE=1`; runtime không tải model và readiness kiểm tra tồn tại, size cùng SHA-256 của toàn bộ artifact required.

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
npm run dev
```

## Kiểm tra

```bash
cd backend
uv run ruff check app tests
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
- Mobile capture: `Authorization: Bearer <capture_token>` sau khi claim QR token một lần.
- Reviewer: `Authorization: Bearer <reviewer_token>`.

Các token cấu hình trong `.env.example` chỉ dành cho local. Production phải thay bằng authentication provider/KMS/secret manager qua adapter, không đưa client credential bí mật vào bundle frontend.

## Dữ liệu và an toàn

- Evidence local nằm trong private volume và được mã hóa AES-GCM trước khi ghi.
- Storage key là opaque và được kiểm tra chống path traversal.
- Không commit dữ liệu thật, `.env`, certificate, key hoặc evidence.
- Purge scheduler mặc định chạy mỗi 24 giờ và chỉ xóa session đến `purge_after`; retention production vẫn chưa được quyết định.
- Manual review hiện không cung cấp endpoint tải/decrypt raw evidence.
- Hệ thống hiện chưa production-ready; các quyết định pháp lý, retention production, threshold và quyền truy cập vẫn mở theo `AGENTS.md`.
