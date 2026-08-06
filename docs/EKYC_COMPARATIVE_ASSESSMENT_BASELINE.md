# Baseline đánh giá so sánh eyePass và V-ID-eKYC

Cập nhật: 2026-08-04.  
Thời lượng đánh giá: 5 ngày làm việc, bắt đầu từ ngày kế tiếp khi owner xác nhận.

## 1. Mục đích

Tạo một đánh giá có bằng chứng về hai hệ thống:

- **eyePass**: sản phẩm eKYC cũ, chỉ dùng làm baseline tham chiếu.
- **V-ID-eKYC**: dự án hiện tại, đánh giá theo tài liệu chính thức và evidence
  triển khai hiện có.

Đánh giá này không phải chứng nhận chất lượng model, compliance, pilot hoặc
production readiness. Không suy luận rằng một capability đã tồn tại chỉ vì nó
được nêu trong tài liệu; không suy luận rằng model chạy được trong technical demo
đã được phê duyệt cho production.

## 2. Nguyên tắc đánh giá

1. Đánh giá theo **năng lực, evidence và mức sẵn sàng**, không theo tuổi đời hay
   mức độ hoàn thiện bề ngoài của dự án.
2. eyePass không phải chuẩn bắt buộc. Rule, test case và kinh nghiệm vận hành từ
   eyePass chỉ được kế thừa có chọn lọc.
3. V-ID-eKYC phải được ghi nhận là cải tiến khi thiết kế giải quyết được rủi ro
   hoặc giới hạn của eyePass, kể cả khi capability đó chưa hoàn thiện.
4. Với V-ID-eKYC, `technical demo`, `MVP feature-complete` và `production` là ba
   mức riêng biệt. Không gộp chúng thành một nhận định readiness.
5. Không đưa PII, raw evidence, token, private API key hoặc response OCR/model
   chi tiết từ tài liệu cũ vào báo cáo, spreadsheet, Git hoặc presentation.

## 3. Nguồn evidence và thứ tự ưu tiên

### 3.1 V-ID-eKYC

1. `AGENTS.md` và quyết định mới nhất của project owner.
2. [`EKYC_FLOW_DESIGN.md`](./EKYC_FLOW_DESIGN.md).
3. [`M0_CONTRACT_GOVERNANCE_BASELINE.md`](./M0_CONTRACT_GOVERNANCE_BASELINE.md).
4. [`PROJECT_ROADMAP.md`](./PROJECT_ROADMAP.md).
5. [`IMPLEMENTATION_STATUS.md`](./IMPLEMENTATION_STATUS.md).
6. Source code, test, CI/run output, model manifest và cấu hình đã được phép xem.

### 3.2 eyePass

Nguồn tham chiếu đặt ngoài repository tại `Tài liệu bàn giao eKYC`:

- BRD, `eyePass_Flow.xlsx` và `Business rules.xlsx`.
- Architecture design, high-level/deployment/integration diagrams.
- API documents và SDK integration guide.
- Handover checklist, UAT checklist, web demo, web console và face matching test
  checklist.

Nếu một nhận định chỉ có trong checklist bàn giao mà không có source/test/deployment
evidence đi kèm, phải ghi rõ là **được mô tả, chưa xác minh**.

## 4. Rubric chuẩn

Rubric chấm chi tiết, trọng số, critical gate, evidence card và template workbook
được chuẩn hóa tại
[EKYC_COMPARATIVE_ASSESSMENT_RUBRIC.md](./EKYC_COMPARATIVE_ASSESSMENT_RUBRIC.md).
Tài liệu này giữ baseline, phạm vi và kế hoạch đánh giá; khi có khác biệt về cách
chấm, rubric chi tiết là nguồn áp dụng.

### 4.1 Mức evidence

| Mã | Nghĩa | Điều kiện tối thiểu |
|---|---|---|
| `E0` | Chưa có evidence | Không có tài liệu hoặc artifact kiểm chứng. |
| `E1` | Được mô tả | Có BRD, diagram, checklist hoặc roadmap. |
| `E2` | Đã thiết kế | Có contract, ADR, data/state design hoặc acceptance criteria rõ. |
| `E3` | Đã triển khai | Có source/configuration phù hợp với thiết kế. |
| `E4` | Đã kiểm chứng | Có test, run output hoặc review evidence có thể truy vết. |

### 4.2 Nhận định so sánh

| Trạng thái | Cách dùng |
|---|---|
| `CẢI TIẾN ĐÃ THIẾT KẾ` | V-ID có thiết kế tốt hơn eyePass nhưng chưa đủ E3/E4. |
| `CẢI TIẾN ĐÃ KIỂM CHỨNG` | V-ID có cải tiến và evidence đạt E4. |
| `KẾ THỪA CÓ CHỌN LỌC` | Rule/test/kinh nghiệm eyePass nên đưa vào V-ID sau khi rà soát. |
| `CẦN HOÀN THIỆN` | Năng lực cần cho scope V-ID nhưng evidence/implementation chưa đủ. |
| `KHÔNG KẾ THỪA` | Cách làm eyePass không phù hợp nguyên tắc hoặc scope V-ID. |
| `NGOÀI PHẠM VI` | Không thuộc technical demo/MVP đang đánh giá. |

### 4.3 Mức ưu tiên hành động

- `P0`: chặn technical demo an toàn/đúng contract hoặc làm sai nguyên tắc bắt buộc.
- `P1`: cần trước khi gọi MVP feature-complete hoặc trước integration mục tiêu.
- `P2`: cải tiến sau MVP, discovery hoặc chờ quyết định production.
- `TBD`: phụ thuộc owner/quyết định mở, không tự hard-code.

## 5. Phạm vi đánh giá sâu

| ID | Năng lực | Câu hỏi trọng tâm |
|---|---|---|
| C01 | Luồng và UX | Handoff, capture, retry, state machine, reviewer flow xử lý ra sao? |
| C02 | Giấy tờ/OCR/MRZ | Phạm vi giấy tờ, rule validation, error/recapture, fixture và benchmark? |
| C03 | Sinh trắc học | Face match, liveness, deepfake, voice, lip-sync: contract và failure mode? |
| C04 | Decision & review | Có auto-verdict không; manual review, reason code và audit thế nào? |
| C05 | API & integration | API versioning, auth, polling/webhook, signature, retry/idempotency? |
| C06 | Model governance | Adapter, manifest, checksum, approval, offline runtime, readiness? |
| C07 | Data & evidence | PII minimization, encrypted evidence, storage port, purge, export/audit? |
| C08 | Security & operations | RBAC, secret, logging, deployment, monitoring, incident/change control? |
| C09 | Quality | Unit/contract/e2e/security/model tests, acceptance criteria và gaps? |
| C10 | Delivery governance | Roadmap, owner, release gate, quyết định mở và dependencies? |

Các phần eyePass có thể nêu NFC, C06/CSDLQG, face search hoặc blacklist phải đánh
dấu riêng là scope cũ/ngoài scope, trừ khi owner quyết định đưa vào scope V-ID.

## 6. Ma trận đánh giá bắt buộc

Mỗi capability C01--C10 có một hoặc nhiều dòng trong workbook
`04_Gap_and_Traceability_Matrix.xlsx` với các cột sau:

| Cột | Nội dung |
|---|---|
| `Capability ID` | C01--C10 và capability con. |
| `Yêu cầu/năng lực` | Mô tả ngắn, trung lập. |
| `Evidence eyePass` | Tên tài liệu, section/sheet/cell; không chép PII. |
| `Mức evidence eyePass` | E0--E4. |
| `Evidence V-ID` | File, section, test hoặc commit/run evidence. |
| `Mức evidence V-ID` | E0--E4. |
| `Nhận định` | Một giá trị ở mục 4.2. |
| `Lợi ích/cải tiến V-ID` | Nêu rõ thiết kế/implementation tốt hơn eyePass nếu có. |
| `Gap hoặc việc cần làm` | Chỉ nêu phần chưa đủ evidence/scope. |
| `Ưu tiên` | P0/P1/P2/TBD. |
| `Owner đề xuất` | Product, Backend, AI, Security/Privacy, Platform hoặc Integration. |
| `Quyết định cần chốt` | Liên kết ID trong decision log nếu cần. |

## 7. Deliverable cuối tuần

1. `01_Executive_Summary.md` (hoặc presentation 8--12 slide).
2. `02_EyePass_AsIs_Assessment.md`.
3. `03_VID_eKYC_ToBe_Assessment.md`.
4. `04_Gap_and_Traceability_Matrix.xlsx`.
5. `05_Risk_and_Decision_Log.md`.

Mỗi kết luận trong executive summary phải link tới một dòng ma trận hoặc một nguồn
evidence. Báo cáo phải có riêng hai phần: **cải tiến của V-ID-eKYC** và **việc cần
hoàn thiện**, không chỉ có danh sách gap.

## 8. Kế hoạch 5 ngày

| Ngày | Hoạt động | Definition of done |
|---|---|---|
| D1 | Kickoff, source register, xác nhận scope và tạo matrix trống. | 100% nguồn được liệt kê; owner xác nhận rubric/scope. |
| D2 | Đánh giá eyePass theo C01--C10. | Có evidence/rating cho mọi capability; phân biệt mô tả và kiểm chứng. |
| D3 | Đánh giá V-ID-eKYC theo nguồn ưu tiên và implementation status. | Có evidence/rating, cải tiến và thiếu hụt cho mọi capability. |
| D4 | Hoàn tất matrix, risk/decision log và ưu tiên P0/P1/P2. | Không còn nhận định không có nguồn; owner đề xuất cho mọi P0/P1. |
| D5 | Review liên chức năng, xử lý phản biện và xuất executive summary. | Bản final được xác nhận về fact; quyết định mở có owner/next step. |

## 9. Baseline nhận định ban đầu cần kiểm chứng

Các nhận định này là điểm xuất phát, không phải kết luận cuối:

- eyePass có coverage hữu ích về OCR/document rule, error UX và UAT/test
  scenarios; các rule cần được rà soát lại trước khi tái sử dụng.
- V-ID-eKYC đã có các cải tiến thiết kế/triển khai đáng kể: QR handoff một lần,
  session state machine, manual review mặc định, adapter/DI, model manifest và
  runtime offline, encrypted evidence + purge, webhook security và PII
  minimization.
- API eyePass dùng API key, ảnh Base64 và trả result OCR/model chi tiết; cách này
  không được coi là contract mục tiêu cho V-ID-eKYC.
- Các production decision như threshold, legal basis, retention cụ thể, region,
  KMS/secret production và quyền thao tác raw evidence vẫn phải giữ `TBD` theo
  tài liệu ưu tiên của V-ID-eKYC.

## 10. Kickoff ngày D1

1. Chỉ định một owner phê duyệt fact và một owner điều phối tài liệu.
2. Tạo năm deliverable ở mục 7 từ template này.
3. Lập source register: tài liệu, phiên bản/ngày, owner, phạm vi, mức tin cậy và
   hạn chế truy cập.
4. Điền matrix trước cho C01--C03, C05--C07 từ các evidence đã biết.
5. Đưa mọi thiếu nguồn, mâu thuẫn hoặc production decision vào decision log; không
   tự giải quyết bằng giả định.
