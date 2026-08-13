# Capability/Provider — Hướng dẫn vận hành

Cập nhật: 2026-08-06.

Tài liệu này là hướng dẫn thao tác cho việc đổi, thêm hoặc gỡ provider của một
capability (M2, xem `PROJECT_ROADMAP.md` và `IMPLEMENTATION_STATUS.md`). Không
thay thế `docs/M0_CONTRACT_GOVERNANCE_BASELINE.md` — tài liệu đó định nghĩa
capability chuẩn và contract; tài liệu này chỉ hướng dẫn **cách thao tác** trên
kiến trúc đã có.

## 1. Ba lớp cần hiểu trước khi đổi bất kỳ thứ gì

```text
.env (Settings.provider_*)        "capability nào chạy provider nào" — operational, per-deployment
        |
capability_config.py               parse .env thành ProviderChain (primary[,secondary])
        |
models/manifest.json#providers[]   "provider này có được duyệt chạy ở profile này không" — governance
        |
ekyc_providers.py                  "provider này implement bằng code gì" — catalog, versioned trong git
        |
CapabilityRegistry                 gộp cả ba lớp trên, chạy provider, ghi attempts
```

Ba câu hỏi khác nhau, ba nơi trả lời khác nhau:

| Câu hỏi | Trả lời ở đâu |
|---|---|
| Provider nào đang active cho capability này, ở deployment này? | `.env` (`PROVIDER_<CAPABILITY>`) |
| Provider này có được phép chạy ở profile này không? | `models/manifest.json#providers[]` |
| Provider này implement thế nào, phụ thuộc model/engine nào? | `backend/app/adapters/ekyc_providers.py` |

Một provider **phải đi qua cả ba lớp** mới chạy được: có trong `.env` chain →
có entry trong `providers[]` với `usage_scope` khớp profile đang chạy → có
`ProviderRegistration` trong `ekyc_providers.py`. Thiếu một trong ba, hoặc
`usage_scope` không khớp profile, `CapabilityRegistry` trả về `UNAVAILABLE` —
không có provider nào chạy "ngầm" chỉ vì code tồn tại. `providers[]` không có
trường trạng thái phê duyệt nào khác - rủi ro pháp lý/license của model đứng
sau provider được ghi ở `notes` trong `models[]` và ở
`docs/model_license_risk_matrix.html`, tách khỏi câu hỏi "có chạy được không".

## 2. Đổi provider đang active (không đổi code)

Chỉ áp dụng khi provider đích **đã có sẵn** trong cả `ekyc_providers.py` và
`providers[]` — tức đây là việc chọn lại trong tập đã được duyệt, không phải
thêm implementation mới.

1. Mở `.env` (hoặc `env/.env.local`, KHÔNG commit) và đổi dòng tương ứng, ví dụ:
   ```bash
   PROVIDER_DOCUMENT_OCR=rapidocr-ppocrv6-small,some-other-approved-ocr-id
   ```
   Định dạng: `primary` hoặc `primary,secondary`. Danh sách 13 biến (tên +
   default hiện tại) nằm ở `backend/app/core/config.py` (`provider_*` fields)
   và được liệt kê mẫu trong `.env.example`.
2. Restart backend (registry được build một lần khi request đầu tiên chạm
   `capability_registry` dependency sau khi `Settings` đổi — xem
   `backend/app/api.py::capability_registry`).
3. Kiểm tra `GET /api/v2/admin/readiness` (cần reviewer token —
   `/utils/health-check` không có auth nên chỉ trả `{"status": "ok"}`, không
   lộ provider/model detail) → `capabilities.<capability>` phải
   `"registered": true`, `primary.provider_id` đúng giá trị mới,
   `primary.ready: true`.
4. Chạy một session thật hoặc `uv run pytest` để chắc chắn không có regression.

**Không cần sửa code cho bước này.** Nếu `primary.ready` vẫn `false` sau khi
đổi `.env`, xem mục 6 (troubleshooting) — khả năng cao là thiếu governance
entry hoặc thiếu artifact.

## 3. Thêm một provider mới cho capability đã có

Ví dụ: thêm một OCR vendor thứ hai cho `document_ocr` để dùng làm `secondary`.

### 3.1. Viết class provider

Trong `backend/app/adapters/ekyc_providers.py`, mỗi provider implement
`CapabilityProvider[ReqT, ResT]` (`backend/app/domain/capability_ports.py`):

```python
class SomeVendorOcrProvider:
    provider_id = "some-vendor-ocr-v1"
    model_id: str | None = "some-vendor-ocr-v1"  # hoặc None nếu không có model artifact
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: SomeVendorEngine) -> None:
        self._engine = engine

    def run(self, request: DocumentOcrRequest) -> DocumentOcrResult:
        raw = self._engine.something(request.payload)
        return DocumentOcrResult(
            status="OK" if raw["text"] else "INCONCLUSIVE",
            engine="some-vendor-ocr/1.0",
            line_count=len(raw["text"]),
            mean_confidence=raw.get("confidence"),
            lines=raw["text"],
        )
```

Quy tắc bắt buộc:

- **`run()` phải trả về đúng typed result dataclass của capability đó**
  (`DocumentOcrResult`, `PassiveLivenessResult`, ... định nghĩa trong
  `capability_ports.py`) — không trả `dict` tự do. Provider là nơi map raw
  output của model/engine sang field chuẩn; đây là "adapter" theo
  `M0_CONTRACT_GOVERNANCE_BASELINE.md` §4 — xem mục 5 bên dưới.
- Raise exception kỹ thuật bình thường (network lỗi, model crash, ...) khi
  provider fail — `CapabilityRegistry` tự phân loại fallback-eligible hay
  không. **Không tự raise `InvalidEvidenceError`** trừ khi đó thật sự là lỗi
  chất lượng input (ảnh không decode được, không có mặt trong video, ...) —
  raise sai loại sẽ tắt fallback không đúng chỗ (ADR-M0-002).

### 3.2. Đăng ký trong `build_capability_registry()`

Thêm một `ProviderRegistration` mới vào dict `registrations` trong
`ekyc_providers.py::build_capability_registry`:

```python
"some-vendor-ocr-v1": ProviderRegistration(
    provider_id="some-vendor-ocr-v1",
    capability="document_ocr",
    factory=lambda: SomeVendorOcrProvider(SomeVendorEngine(settings.some_vendor_api_key)),
    model_id="some-vendor-ocr-v1",
    adapter_spec_version=ADAPTER_SPEC_VERSION,
    config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
),
```

`factory` phải **lazy** (không load model/kết nối network ngay khi
`build_capability_registry()` chạy) — `CapabilityRegistry` chỉ gọi `factory()`
lần đầu tiên provider thật sự được `.run()`/`.resolve()`, sau khi cả hai khóa
governance/artifact đã pass. Nếu provider dùng chung engine với provider khác
(như `shared_ocr()`/`shared_signals()` hiện tại), viết theo đúng pattern
memoization đó, không construct engine ở top-level function.

### 3.3. Khai báo governance trong `manifest.json`

Thêm entry vào `models/manifest.json#providers[]`:

```json
{
  "id": "some-vendor-ocr-v1",
  "usage_scope": ["technical_demo"]
}
```

Chỉ 2 field. `capability`/`model_id`/`adapter_spec_version` **không** khai báo
lại ở đây — `ManifestReader` chưa từng đọc chúng, chúng chỉ lặp lại thứ đã có
trong `ProviderRegistration` ở `ekyc_providers.py` (mục 3.2). Governance file
chỉ trả lời một câu: id này có đăng ký chạy, ở profile nào — code catalog
trả lời "nó implement thế nào". `id` ở đây phải khớp *chính xác* chuỗi
`provider_id` đã đăng ký ở mục 3.2 — đây là sợi dây duy nhất nối hai file,
và `scripts/validate_capability_providers.py` (mục 3.5) kiểm tra đúng chỗ
này trước khi bạn phải tự dò bằng mắt.

Không có trường trạng thái phê duyệt nào ở đây - rủi ro pháp lý/license
(license/provenance của model đứng sau provider) được ghi ở `notes` trong
`models[]` cho model tương ứng, và ở `docs/model_license_risk_matrix.html`,
tách hẳn khỏi câu hỏi "có chạy được không". Nếu
provider có model artifact riêng (file cần verify sha256/size), thêm entry
tương ứng vào
`models[]` như một model bình thường, với `id` riêng của nó (không nhất thiết
trùng `provider_id`) và gán vào `model_id` trong `ProviderRegistration` ở
code — hai mảng độc lập, provider governance không thay thế model artifact
governance.

Sửa `models/manifest.json` (bản đầy đủ, chỉ nằm trong source repo) như bình
thường — không cần lo về việc file này bị đưa vào image: `backend/Dockerfile`
tự động chạy `scripts/models.py --emit-runtime-manifest` để ghi đè bằng bản
rút gọn (bỏ `source`/`source_repository`/`license`/`purpose`/
`distribution_permission`/`notes`) trước khi copy sang runtime
stage. Trường mới thêm vào entry chỉ xuất hiện trong image đã deploy nếu nó
nằm trong `RUNTIME_MODEL_FIELDS`/`RUNTIME_PROVIDER_FIELDS`
(`scripts/models.py`) — nếu cần một field mới thực sự phải đọc lúc runtime,
thêm vào đúng set đó, đừng giả định field cứ có trong `manifest.json` là sẽ
lên image. Provider/model id vẫn tự mô tả (`minifasnet-v2`, ...) và vẫn có
mặt trong cả manifest rút gọn lẫn `ekyc_providers.py` — xem mục 8 của
`IMPLEMENTATION_STATUS.md` "MVP feature-complete" về quyết định đổi sang
opaque id, hiện đang chủ động hoãn.

`usage_scope` là điều kiện vận hành duy nhất — không có trường trạng thái phê
duyệt riêng để set/đổi ở đây nữa. Rủi ro pháp lý/license cho model đứng sau
provider ghi ở `notes` của entry tương ứng trong `models[]`.

### 3.4. Bật làm secondary (chưa đổi primary)

```bash
PROVIDER_DOCUMENT_OCR=rapidocr-ppocrv6-small,some-vendor-ocr-v1
```

Primary vẫn chạy bình thường; `some-vendor-ocr-v1` chỉ được gọi khi primary
fail vì lỗi kỹ thuật (timeout, exception, manifest invalid) — không bao giờ vì
score thấp hay input quality kém.

### 3.5. Kiểm tra

Chạy trước khi khởi động app — không cần boot server, không cần model thật
trên đĩa (trừ khi thêm `--require-artifacts`):

```bash
python3 scripts/validate_capability_providers.py
```

Lệnh này đối chiếu cả 3 lớp một lượt: provider có đăng ký code không, có
governance entry đã duyệt không, chain đang cấu hình trong `.env` có resolve
được không — in rõ provider/capability nào fail và vì sao (thiếu governance
hay chỉ thiếu artifact). Đây là bước đầu tiên khi thêm/đổi provider, thay vì
boot app rồi tự đọc `/admin/readiness` bằng mắt. Thêm `--profile`/`--model-dir`
nếu cần kiểm tra một profile/máy khác với default.

Sau khi lệnh trên sạch:

- Viết test theo mẫu `backend/tests/test_capability_registry.py` nếu logic
  fallback/timeout riêng cho provider này cần xác nhận cụ thể (dùng fake
  provider, không cần model thật).
- `uv run ruff check . && uv run ruff format --check . && uv run mypy app ai_modules && uv run pytest`.
- Nếu muốn xác nhận cả artifact thật (model đã tải): `GET
  /api/v2/admin/readiness` (reviewer token) sau khi boot app, capability
  tương ứng có `secondary.ready: true`.

## 4. Thêm một capability hoàn toàn mới

(Ví dụ tương lai: `document_quality` ở M3.)

1. Thêm tên vào `CapabilityName` (`backend/app/domain/capability_ports.py`).
2. Định nghĩa `<Capability>Request`/`<Capability>Result` dataclass trong
   cùng file — `Result` chính là contract mà mọi provider tương lai của
   capability này phải tuân theo (xem mục 5).
3. Viết provider(s) + đăng ký trong `ekyc_providers.py` như mục 3.
4. Thêm field `provider_<capability>: str = "<default-provider-id>"` vào
   `Settings` (`backend/app/core/config.py`) và vào
   `_CAPABILITY_SETTINGS_FIELDS` (`backend/app/core/capability_config.py`).
5. Thêm governance entry vào `manifest.json#providers[]`.
6. Nếu capability chạy qua orchestrator (không phải resolve trực tiếp như
   `face_detection`/`face_embedding`), gọi `self._run("<capability>", ...)`
   ở đúng chỗ trong `EkycOrchestrator.analyze()`
   (`backend/app/adapters/ekyc_orchestrator.py`) và thêm key tương ứng vào
   dict trả về cuối hàm.
7. Cập nhật `OfflineModelAnalyzer._normalize_capability()`
   (`backend/app/adapters/analyzer.py`) nếu capability cần review_signal/metric
   riêng cho reviewer — không bắt buộc nếu dùng `_base_output` mặc định là đủ.

## 5. Vì sao mỗi provider phải trả typed result, không trả dict

Trước M2, tầng phân tích (`analyzer.py`) đọc field theo **tên capability**
(`value.get("live_probability")` cho mọi provider của `passive_liveness`).
Nếu provider thứ hai dùng field khác (`p_live` chẳng hạn), việc đổi provider
qua `.env` sẽ **âm thầm sai** — không exception, không log, chỉ `None` lặng lẽ
chảy vào kết quả review.

Từ M2, contract của mỗi capability là một dataclass cố định
(`PassiveLivenessResult(status, engine, live_probability)`, ...). Provider
nào cũng phải tự map raw output của model/engine mình sang đúng field đó bên
trong `run()`. Nếu provider mới không khớp, đó là lỗi kiểu (type error) ngay
tại chỗ viết provider — không phải bug ẩn lúc chạy production. Đây chính là
vai trò "adapter" mô tả ở `M0_CONTRACT_GOVERNANCE_BASELINE.md` §4.

Khi viết `run()` cho provider mới: xem danh sách field bắt buộc của
`<Capability>Result` trong `capability_ports.py` trước, map raw output vào
đúng field đó — không thêm field ngoài dataclass (không thể, dataclass
`frozen=True`) và không bỏ field bắt buộc (thiếu tham số sẽ lỗi ngay lúc
construct).

## 6. Troubleshooting

`python3 scripts/validate_capability_providers.py` là nơi tra cứu đầu tiên —
không cần boot app. `GET /api/v2/admin/readiness` (reviewer token,
`capabilities.<capability>`) cho cùng thông tin nếu app đã chạy —
`/utils/health-check` không có auth nên chỉ trả `{"status": "ok"}`, không
lộ provider/model detail. Các giá trị `invalid`/reason thường gặp:

| Reason | Nghĩa là gì | Sửa ở đâu |
|---|---|---|
| `<provider_id>:not_found` | Provider không có entry trong `providers[]` | Thêm entry vào `manifest.json#providers[]` |
| `<provider_id>:not_in_profile_scope` | Có entry nhưng `usage_scope` không chứa profile đang chạy | Sửa `usage_scope` trong `providers[]`, hoặc đổi `MODEL_PROFILE` |
| `<model_id>:not_found` | Governance provider pass nhưng model backing không có trong `models[]` | Thêm/khớp `model_id` trong `models[]` |
| `<model_id>:missing` / `:size` / `:sha256` | Model đã duyệt nhưng artifact trên đĩa thiếu/sai | Tải lại artifact đúng bằng `scripts/models.py`, kiểm tra `MODEL_DIR` |
| `PROVIDER_NOT_REGISTERED` | Chain trỏ tới `provider_id` không có `ProviderRegistration` trong code | Thêm registration trong `ekyc_providers.py`, hoặc sửa lại `.env` cho đúng id |
| `PROVIDER_CIRCUIT_OPEN` | Provider fail liên tiếp đủ ngưỡng (`CAPABILITY_CIRCUIT_FAILURE_THRESHOLD`), đang trong thời gian cooldown | Xem log lỗi thật sự của provider; đợi cooldown hoặc restart nếu đã fix |
| `PROVIDER_TIMEOUT` | Provider chạy quá `CAPABILITY_PROVIDER_TIMEOUT_SECONDS` | Tăng timeout nếu model chậm hợp lý, hoặc điều tra hiệu năng provider |

`CapabilityUnavailableError` (chỉ áp dụng cho `face_detection`/`face_embedding`,
được `resolve()` thay vì `run()`) mang cùng vocabulary reason ở trên qua
`.reason`.

Nhắc lại nguyên tắc fail-closed: thiếu bất kỳ lớp nào trong 3 lớp ở mục 1,
provider không chạy — không có "provider mặc định" nào chạy ngầm khi thiếu
cấu hình.

## 7. Việc KHÔNG làm khi đổi provider

- Đừng thêm lại bất kỳ trường trạng thái phê duyệt nào (`approval_status` hay
  tương đương) vào `manifest.json`/`Attempt`/adapter spec để "mở khoá"
  capability - hệ thống không còn khái niệm đó nữa, chỉ có `usage_scope`.
  Ghi rủi ro pháp lý/license vào `notes` của entry, không phải một enum trạng
  thái mới.
- Không hardcode provider_id vào code ngoài `ekyc_providers.py` — mọi lựa chọn
  active provider đi qua `.env`.
- Không commit `.env`/`env/.env.local` thật — chỉ `.env.example` với giá trị
  placeholder được commit.
- Không để provider trả dict tự do trong `run()` — luôn là typed result
  dataclass (mục 5).
- Không set `secondary` bằng chính `primary` hoặc một provider chưa có
  governance entry — registry sẽ không raise ở thời điểm cấu hình, chỉ fail
  closed lặng lẽ lúc chạy.

## 8. Tham chiếu

- `docs/M0_CONTRACT_GOVERNANCE_BASELINE.md` — capability chuẩn, contract
  `ekyc-analysis/1.0`, ADR-M0-001/002/004.
- `docs/PROJECT_ROADMAP.md` §M2 — mục tiêu và tiêu chí hoàn thành milestone.
- `docs/IMPLEMENTATION_STATUS.md` — bảng M2, evidence và next action hiện tại.
- `backend/app/domain/capability_ports.py` — mọi Request/Result/Protocol.
- `backend/app/adapters/capability_registry.py` — cơ chế fallback/circuit
  breaker/timeout/readiness.
- `backend/app/adapters/manifest.py` — governance/artifact check.
- `backend/tests/test_capability_registry.py` — ví dụ test cho từng cơ chế.
- `scripts/validate_capability_providers.py` — kiểm tra nhất quán cả 3 lớp,
  chạy trước khi boot app; `backend/tests/test_validate_capability_providers.py`
  test logic phân loại lỗi governance vs artifact của nó.
- `scripts/models.py --emit-runtime-manifest` — sinh bản `manifest.json` rút
  gọn baked vào Docker image; field nào lên image xem
  `RUNTIME_MODEL_FIELDS`/`RUNTIME_PROVIDER_FIELDS` trong file đó.
