# Baseline đánh giá V-ID-eKYC đối chiếu yêu cầu/đặc tả eyePass

Cập nhật: 2026-08-09.  
Thời lượng đánh giá: 5 ngày làm việc, bắt đầu từ ngày kế tiếp khi owner xác nhận.

## 1. Mục đích

Đây **không phải** một đánh giá ngang hàng giữa hai hệ thống đang vận hành. Đây
là một đánh giá **một chiều**: V-ID-eKYC là đối tượng được đánh giá; eyePass chỉ
đóng vai trò **nguồn yêu cầu/đặc tả tham chiếu** để rút ra checklist năng lực cần
đối chiếu. Lý do:

- **eyePass**: là sản phẩm eKYC đã được xây dựng và vận hành trước đây, nhưng
  người đánh giá **chỉ tiếp cận được tài liệu bàn giao** (BRD, flow, API/SDK doc,
  checklist) — **không có quyền truy cập source code, test, database hay
  runtime**. eyePass vì vậy không được chấm maturity/confidence như một hệ thống
  — nó chỉ được ghi nhận theo mức độ đặc tả **nêu rõ yêu cầu** tới đâu (rubric
  §4: `Không đề cập` / `Nêu chưa đầy đủ` / `Nêu rõ`), luôn ở confidence `Doc-only`
  cố định. Đây là giới hạn evidence, không phải nhận định eyePass "không thật"
  hay "yếu".
- **V-ID-eKYC**: dự án hiện tại, đang ở giai đoạn **technical demo**, chưa
  `MVP feature-complete`, chưa production. Đánh giá theo tài liệu chính thức và
  evidence triển khai hiện có; nhiều capability chỉ ở mức thiết kế (`Designed`,
  rubric §3) hoặc chủ động để `TBD`.

Vì cả hai giới hạn trên, **không có công bố "hệ thống nào tốt hơn"** ở cấp tổng
thể. Đầu ra hợp lệ duy nhất của đánh giá này là: với từng yêu cầu/năng lực rút ra
từ đặc tả eyePass, V-ID-eKYC đang **đáp ứng, vượt, thiếu, hay chủ động không kế
thừa** yêu cầu đó — kèm evidence và mức tin cậy cho từng nhận định. eyePass không
được chấm "thắng/thua"; nó chỉ được dùng để tạo checklist.

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
   hoặc giới hạn nêu trong đặc tả eyePass, kể cả khi capability đó chưa hoàn thiện.
4. Với V-ID-eKYC, `technical demo`, `MVP feature-complete` và `production` là ba
   mức riêng biệt. Không gộp chúng thành một nhận định readiness.
5. Không đưa PII, raw evidence, token, private API key hoặc response OCR/model
   chi tiết từ tài liệu cũ vào báo cáo, spreadsheet, Git hoặc presentation.
6. Đây là đánh giá **một chiều** (§1): không viết hoặc suy luận bất kỳ câu nào có
   dạng "V-ID tốt hơn/kém eyePass" ở cấp hệ thống hay cấp tổng hợp. Mọi nhận định
   phải gắn với một yêu cầu cụ thể rút ra từ đặc tả eyePass, kèm maturity và
   confidence của V-ID cho yêu cầu đó.

## 3. Nguồn evidence và thứ tự ưu tiên

### 3.1 V-ID-eKYC

1. `AGENTS.md` và quyết định mới nhất của project owner.
2. [`EKYC_FLOW_DESIGN.md`](./EKYC_FLOW_DESIGN.md).
3. [`M0_CONTRACT_GOVERNANCE_BASELINE.md`](./M0_CONTRACT_GOVERNANCE_BASELINE.md).
4. [`PROJECT_ROADMAP.md`](./PROJECT_ROADMAP.md).
5. [`IMPLEMENTATION_STATUS.md`](./IMPLEMENTATION_STATUS.md) — chỉ để định hướng
   đọc source ở đâu; **không được trích dẫn làm evidence** trong bất kỳ dòng
   đánh giá nào (rubric §2, §5; `AGENTS.md` mục "Thứ tự ưu tiên tài liệu").
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

Rubric chấm chi tiết (V-ID: capability maturity §3 + evidence confidence §5;
eyePass: mức độ nêu trong đặc tả §4; kiến trúc so sánh riêng §8) được chuẩn hóa
tại [EKYC_COMPARATIVE_ASSESSMENT_RUBRIC.md](./EKYC_COMPARATIVE_ASSESSMENT_RUBRIC.md).
Tài liệu này giữ baseline, phạm vi và kế hoạch đánh giá; khi có khác biệt về cách
chấm, rubric chi tiết là nguồn áp dụng.

### 4.1 Capability maturity (V-ID) và mức nêu trong đặc tả (eyePass)

V-ID và eyePass **không dùng chung một thang chấm**: V-ID được chấm trên trục
maturity + confidence (rubric §3, §5, từ ngữ thuần, không có mã `L0`–`L4`);
eyePass chỉ được ghi nhận theo mức độ đặc tả nêu rõ yêu cầu (rubric §4, 3 mức).
Không copy lại bảng ở đây để tránh hai tài liệu lệch nhau theo thời gian — khi
cần tra cứu mức cụ thể, mở rubric.

### 4.2 Nhận định đối chiếu

Xem rubric §9 (`ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC`, `ĐÃ ĐÁP ỨNG — THEO THIẾT KẾ`,
`NGOÀI YÊU CẦU EYEPASS`, `KẾ THỪA CÓ CHỌN LỌC`, `GAP`, `DEFERRED_BY_DESIGN`,
`KHÔNG KẾ THỪA`, `OUT_OF_SCOPE`, `CHƯA KẾT LUẬN`).

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

Mỗi capability C01--C10 có một hoặc nhiều dòng trong Phần D (Gap & Traceability
Matrix) của
[`assessment/eKYC_Assessment_Report.md`](./assessment/eKYC_Assessment_Report.md)
(markdown, không phải workbook xlsx) với các cột sau:

| Cột | Nội dung |
|---|---|
| `Capability ID` | C01--C10 và capability con. |
| `Yêu cầu/năng lực` | Mô tả ngắn, trung lập. |
| `Trích dẫn eyePass` | Tên tài liệu, section/sheet/cell; không chép PII. |
| `Mức nêu trong đặc tả eyePass` | `Không đề cập` / `Nêu chưa đầy đủ` / `Nêu rõ` (rubric §4). Confidence eyePass luôn cố định `Doc-only`, không cần cột riêng. |
| `Evidence V-ID` | File, section, test hoặc commit/run evidence. |
| `Maturity V-ID` | `Absent` / `Conceptual` / `Designed` / `Implemented` / `Hardened` (rubric §3). |
| `Confidence V-ID` | Doc-only / Self-reported / Source-reviewed / Test-verified (rubric §5). |
| `Status` | IN_SCOPE / OUT_OF_SCOPE / DEFERRED_BY_DESIGN / GAP (rubric §6, mô tả lập trường của V-ID). |
| `Nhận định` | Một giá trị ở rubric §9. |
| `Lợi ích/cải tiến V-ID` | Nêu rõ V-ID đáp ứng/vượt yêu cầu eyePass thế nào, hoặc năng lực nào V-ID có ngoài yêu cầu eyePass (`NGOÀI YÊU CẦU EYEPASS`) — không viết "tốt hơn eyePass" nếu eyePass không nêu yêu cầu đó. |
| `Gap hoặc việc cần làm` | Chỉ nêu phần chưa đủ evidence/scope, tách riêng khỏi `DEFERRED_BY_DESIGN`. |
| `Ưu tiên` | P0/P1/P2/DEFERRED. |
| `Owner đề xuất` | Product, Backend, AI, Security/Privacy, Platform hoặc Integration. |
| `Quyết định cần chốt` | Liên kết ID trong decision log nếu cần. |

## 7. Deliverable cuối tuần

Một file duy nhất,
[`assessment/eKYC_Assessment_Report.md`](./assessment/eKYC_Assessment_Report.md),
gồm 5 phần theo đúng thứ tự đọc (gộp lại từ 5 deliverable tách file trước đây để
dễ theo dõi, nội dung tương đương):

1. Phần A — Executive Summary (hoặc presentation 8--12 slide song song).
2. Phần B — eyePass As-Is (đặc tả tham chiếu theo tài liệu bàn giao).
3. Phần C — V-ID-eKYC To-Be (đánh giá năng lực theo đặc tả và implementation).
4. Phần D — Gap & Traceability Matrix.
5. Phần E — Risk & Decision Log.

Mỗi kết luận trong Executive Summary phải link tới một dòng ma trận (Phần D) hoặc
một nguồn evidence. Báo cáo phải có riêng hai phần: **cải tiến của V-ID-eKYC** và
**việc cần hoàn thiện**, không chỉ có danh sách gap.

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
