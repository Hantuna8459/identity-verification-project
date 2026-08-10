# Rubric đánh giá V-ID-eKYC đối chiếu eyePass

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 3.0 |
| Cập nhật | 2026-08-09 |
| Lịch sử | v2.0 tách "mức độ chắc chắn về evidence" khỏi "mức độ năng lực/kiến trúc" nhưng vẫn chấm **cả hai hệ thống** trên cùng một thang `L0`–`L4`. v3.0 bỏ thang đó cho eyePass: chữ+số (`L3`, `L1`...) đọc như một điểm số định lượng, khiến người đọc so `L3` với `L3` mà bỏ qua confidence đi kèm — trong khi `L3` của eyePass chỉ nghĩa là "tài liệu mô tả nó đã triển khai", còn `L3` của V-ID có thể là source-reviewed. eyePass không còn được chấm maturity; nó chỉ là **nguồn yêu cầu tham chiếu** (baseline §1), có trục riêng ở §4. Không giữ bản v2.0 riêng, xem lịch sử git. |
| Lý do đổi (v1.0 → v2.0, để tham khảo) | v1.0 gộp "mức độ chắc chắn về evidence" và "mức độ năng lực/kiến trúc" vào một điểm số duy nhất — phạt eyePass chỉ vì chỉ có tài liệu, và phạt V-ID chỉ vì đang ở giai đoạn demo. |
| Mục đích | Đối chiếu **năng lực (capability)** và **kiến trúc (architecture)** của V-ID-eKYC với yêu cầu/đặc tả rút ra từ eyePass. Đây là đánh giá một chiều: V-ID là đối tượng duy nhất được chấm maturity (§3); eyePass chỉ được ghi nhận theo mức độ nó **nêu rõ yêu cầu** (§4), không theo mức độ năng lực của chính nó — xem baseline §1. |

## 1. Mục đích và giới hạn

Rubric này dùng để trả lời ba câu hỏi tách biệt cho mỗi hạng mục, không được gộp
hay quy đổi thành một điểm:

1. **Đặc tả eyePass có nêu yêu cầu này không, và nêu rõ tới đâu?** (Trục eyePass
   — mức độ nêu trong đặc tả, §4)
2. **V-ID-eKYC có năng lực này ở mức nào?** (Trục V-ID — Capability maturity, §3)
3. **Chúng ta tin vào nhận định maturity đó của V-ID đến đâu?** (Evidence
   confidence, §5)

eyePass **không có** trục maturity/confidence của riêng nó trong rubric này —
nó không phải đối tượng được đánh giá, chỉ là nguồn để rút ra checklist yêu cầu
cho V-ID (baseline §1). Ví dụ minh họa: một yêu cầu có thể được ghi
"eyePass: Nêu rõ — V-ID: Implemented, confidence Doc-only" — nghĩa là "đặc tả cũ
mô tả rõ yêu cầu này, và tài liệu V-ID mô tả nó đã triển khai, nhưng ta chưa tự
đọc source để xác nhận" — không bị ép giảm xuống mức thấp chỉ vì thiếu quyền
truy cập source.

Đây vẫn không phải benchmark độ chính xác model, chứng nhận security/compliance
hay production-readiness assessment. Không suy ra maturity cao là được phép dùng
production; không suy ra confidence thấp là năng lực yếu.

## 2. Nguồn evidence

Nguồn V-ID-eKYC được đọc theo **vai trò của tài liệu**, không phải một danh sách
ưu tiên tuyến tính đơn thuần:

- **`AGENTS.md`** — hiến chương quản trị: nguyên tắc bắt buộc, giai đoạn hiện tại
  (technical demo, không phải pilot/production), thứ tự ưu tiên tài liệu và quyết
  định owner mới nhất. Đây **không phải nguồn chính cho chi tiết năng lực/kiến
  trúc** — nội dung của nó phần lớn là quy tắc vận hành và con trỏ tới các tài
  liệu khác, không phải đặc tả.
- **`EKYC_FLOW_DESIGN.md`** — nguồn chính cho chi tiết năng lực, kiến trúc, state
  machine, data model, API contract, reason code và routing quyết định. Phải đọc
  toàn văn trước khi chấm bất kỳ tiêu chí nào liên quan đến C01–C08 — tài liệu
  này tự nêu rõ trong §24 rằng phần "Ghi chú thực thi sau technical demo" mới là
  áp dụng cho trạng thái hiện tại, còn phần thiết kế v2 chính (§1–§23) là target
  design đang chờ review, **không phải mô tả những gì đã chạy**. Không được chấm
  maturity dựa trên việc chỉ grep từ khóa — phải đọc đủ ngữ cảnh để tránh gán
  `GAP` cho những phần thực ra **đã có thiết kế (Designed)** chỉ chưa triển khai.
- **`EKYC_FLOW_DESIGN_SIMPLIFIED.md`** — bản rút gọn của `EKYC_FLOW_DESIGN.md`. Dùng song song, không thay thế: một số chi tiết (vd. cơ chế QR handoff §6.1–6.3 — token một lần, vòng đời, endpoint claim/revoke) cụ thể hơn trong bản rút gọn này so với thiết kế chính. Khi thiết kế chính không đủ chi tiết cho một tiêu chí, kiểm tra bản rút gọn trước khi kết luận `Absent`/`Conceptual`.
- **`M0_CONTRACT_GOVERNANCE_BASELINE.md`** — schema/contract cho từng capability.
- **`PROJECT_ROADMAP.md`** — không chỉ timeline. Với các milestone chưa `DONE`
  (M3–M7), đây thường là bản đặc tả **chi tiết và cập nhật hơn**
  `EKYC_FLOW_DESIGN.md` cho đúng phần việc của milestone đó — ví dụ M6 định nghĩa
  danh sách quyền `review:read`/`pii:unmask`/`evidence:view`/`biometric:view`/
  `review:decide`/`evidence:export`/`evidence:delete` cụ thể hơn bảng vai trò ở
  `EKYC_FLOW_DESIGN.md` §4. Khi hai tài liệu cùng mô tả một năng lực, ưu tiên
  trích dẫn `PROJECT_ROADMAP.md` cho phần đó; dùng `EKYC_FLOW_DESIGN.md` cho ngữ
  cảnh kiến trúc tổng thể.
- **`IMPLEMENTATION_STATUS.md`** — nhật ký tiến độ tự báo cáo cho người dùng
  (xem `AGENTS.md`, mục "Thứ tự ưu tiên tài liệu"), **không được trích dẫn làm
  evidence ở bất kỳ dòng đánh giá nào trong deliverable**, kể cả để hạ maturity
  xuống `GAP`/`Absent`. Có thể đọc riêng tư để định hướng nên tìm gì trong
  source/test, nhưng mọi khẳng định trong đó ("đã triển khai và kiểm chứng",
  milestone `DONE`/`NOT_STARTED`...) phải được xác minh lại qua source/test thật
  trước khi xuất hiện trong bất kỳ ô evidence nào — và khi xác minh xong, trích
  dẫn source/test đó, không trích dẫn tài liệu này. Maturity chỉ được nâng lên
  `Implemented`/`Hardened` khi có trích dẫn trực tiếp từ source/config/API/test/
  CI/manifest thật; không tài liệu tự báo cáo nào — kể cả tài liệu này — đủ để
  vượt quá `Designed`.
- **eyePass**: BRD, flow/rule workbook, architecture/deployment/integration
  diagram, API/SDK doc, handover/UAT checklist — không có source/test/runtime
  access. Mọi trích dẫn eyePass được chấm trên trục riêng (§4), không phải §3.

Tài liệu draft/chưa duyệt (`EKYC_FLOW_DESIGN.md` đang ở trạng thái "Draft để
review") vẫn chỉ được dùng làm evidence cho **maturity tối đa Designed** trên
phần chưa được source/test thật xác nhận — nhưng `Designed` là một mức hợp lệ
và phải được ghi nhận đầy đủ, không được bỏ sót hay hạ xuống `Absent`/`GAP` chỉ
vì tài liệu ở trạng thái draft.

Trước khi ghi một mục là `DISPUTED` do "tài liệu A cũ hơn tài liệu B", phải đọc
đủ ngữ cảnh của cả hai để loại trừ khả năng đây là target-design-vs-current-state
(được tài liệu tự phân biệt, ví dụ §24 của `EKYC_FLOW_DESIGN.md`) chứ không phải
mâu thuẫn sự kiện thật. Chỉ ghi `DISPUTED` khi hai nguồn khẳng định hai sự kiện
loại trừ nhau ở cùng một thời điểm áp dụng.

## 3. Trục V-ID — Capability maturity

Trục này **chỉ áp dụng cho V-ID-eKYC**. Dùng từ ngữ thuần, không có mã chữ+số,
để không bị đọc như một điểm số trên thang 0–4.

| Mức | Ý nghĩa |
|---|---|
| `Absent` (Chưa có) | Không có, không được nhắc tới trong bất kỳ tài liệu hay source nào của V-ID. |
| `Conceptual` (Mới là ý định) | Được nêu ý định/mục tiêu nhưng chưa có thiết kế cụ thể (vd. một dòng trong roadmap). |
| `Designed` (Đã thiết kế) | Có contract, sơ đồ, data/state design hoặc acceptance criteria rõ ràng, chưa triển khai. |
| `Implemented` (Đã triển khai) | Có source/config/API thật sự hiện thực hóa thiết kế đó. |
| `Hardened` (Đã triển khai & kiểm chứng) | `Implemented` cộng xử lý lỗi/negative case, test hoặc vận hành thực tế bao phủ. |

`Implemented`/`Hardened` không yêu cầu chúng ta đã tự chạy hoặc đọc source — chỉ
yêu cầu **có evidence rằng nó tồn tại ở mức đó**, kể cả evidence gián tiếp (API
doc mô tả chi tiết field/response của một endpoint đang chạy production là
evidence hợp lệ cho `Implemented`, xem §5).

## 4. Trục eyePass — mức độ nêu trong đặc tả

Trục này **thay thế hoàn toàn** việc chấm maturity cho eyePass. Nó không đo
"eyePass làm tốt tới đâu" — chúng ta không có source/test access nên không thể
tự xác nhận điều đó (§2). Nó chỉ đo **đặc tả bàn giao nêu yêu cầu rõ tới đâu**,
để dùng làm checklist đối chiếu với V-ID.

| Mức | Ý nghĩa |
|---|---|
| `Không đề cập` | BRD, flow/rule workbook, API/SDK doc, checklist bàn giao không đề cập tới yêu cầu này. |
| `Nêu chưa đầy đủ` | Có đề cập nhưng thiếu chi tiết, mơ hồ, hoặc chỉ có một phần (vd. có ngưỡng số nhưng không có quy trình version/approval). |
| `Nêu rõ` | Yêu cầu được đặc tả cụ thể, trích dẫn được trực tiếp section/sheet/cell. |

Mọi trích dẫn eyePass mặc định ở confidence `Doc-only` (§2, §5) — không cần ghi
lặp lại cột confidence riêng cho eyePass trong deliverable (§10).

## 5. Evidence confidence

Áp dụng cho maturity của **V-ID** (§3). eyePass không có cột confidence riêng vì
luôn cố định ở `Doc-only` (§4) — nếu sau này có được cấp quyền truy cập
source/test/runtime của eyePass, rubric này phải được cập nhật trước khi đổi
điều đó.

| Mức | Ý nghĩa | Ví dụ (V-ID) |
|---|---|---|
| `Doc-only` | Chỉ có tài liệu mô tả, không có source/test | Roadmap mô tả một milestone nhưng chưa có contract chi tiết |
| `Self-reported` | Owner/team tự nhận định trực tiếp (trao đổi, phiên làm việc), không kèm artifact kiểm chứng và không trích dẫn được | Owner xác nhận bằng lời một hướng đi chưa có tài liệu ghi lại |
| `Source-reviewed` | Đã đọc source/config phù hợp | Đọc trực tiếp `backend/app/**` |
| `Test-verified` | Có test/run/CI output truy vết được | pytest assertion cụ thể được trích dẫn |

`IMPLEMENTATION_STATUS.md` **không phải nguồn hợp lệ cho bất kỳ mức confidence
nào ở trên** — xem §2. Một khẳng định chỉ lấy từ tài liệu đó, chưa đối chiếu
source/test, không được ghi vào deliverable dưới bất kỳ mức confidence nào,
kể cả `Self-reported`.

Confidence là **thông tin đi kèm**, không giới hạn maturity. Ghi rõ cả maturity
và confidence cho mọi dòng V-ID; không được chỉ ghi một trục.

## 6. Applicability / status

Mô tả **V-ID đứng ở đâu** với một yêu cầu (dù yêu cầu đó rút ra từ đặc tả eyePass
hay từ nguồn khác).

| Trạng thái | Dùng khi |
|---|---|
| `IN_SCOPE` | Yêu cầu nằm trong phạm vi V-ID cần đáp ứng ở giai đoạn hiện tại. |
| `OUT_OF_SCOPE` | V-ID không cần năng lực này ở giai đoạn hiện tại (vd. NFC/chip passport với V-ID technical demo), bất kể eyePass có nêu hay không. |
| `DEFERRED_BY_DESIGN` | V-ID **chủ động** chưa quyết định/triển khai vì lý do governance đã ghi nhận (vd. threshold production `TBD` theo `AGENTS.md`). Khác với `GAP`: đây là quyết định có chủ đích, có owner, có lý do. |
| `GAP` | Yêu cầu cần thiết trong scope nhưng V-ID chưa có evidence ở mức mong đợi, không có lý do chủ đích nào được ghi nhận. |

`DEFERRED_BY_DESIGN` và `GAP` **không được gộp chung** khi tổng hợp — báo cáo
phải đếm và liệt kê riêng.

## 7. Domain

Giữ nguyên 10 domain và các tiêu chí nguyên tử (danh sách năng lực không đổi so
với v1.0/v2.0, chỉ đổi cách chấm):

`C01` Luồng & UX · `C02` Giấy tờ/OCR/MRZ · `C03` Sinh trắc học & anti-spoof ·
`C04` Decision & manual review · `C05` API & integration · `C06` Model
governance & offline · `C07` Data, evidence & privacy · `C08` Security &
operations · `C09` Quality & verification · `C10` Delivery governance.

Không dùng trọng số số học để tính điểm tổng hợp — nếu cần sắp xếp mức độ quan
trọng, dùng nhãn định tính `Rủi ro cao/trung bình/thấp` gắn theo domain trong
executive summary, không nhân vào công thức.

## 8. Kiến trúc — so sánh riêng, không chấm điểm

Mỗi trục kiến trúc dưới đây được viết theo dạng **quyết định – lý do – đánh đổi**,
không có điểm số, không có "ai thắng". Đây là phần duy nhất trong rubric mô tả
cả hai hệ thống song song, vì kiến trúc là lựa chọn thiết kế có thể mô tả trung
lập mà không cần chấm maturity của eyePass.

| Trục kiến trúc | Câu hỏi |
|---|---|
| Trust & decision model | Ai/cái gì ra quyết định cuối (verdict) — API caller, hệ thống, hay con người? |
| Integration pattern | Đồng bộ request/response hay stateful session + handoff/webhook? |
| Tenancy | Đơn tenant hay multi-tenant, ranh giới cách ly ở đâu? |
| Extensibility | Có thay được provider/model/implementation qua interface không, hay hard-code? |
| Deployment topology | Đơn vị triển khai, scale, blast radius khi một thành phần lỗi. |
| Data/evidence handling | Dữ liệu nhạy cảm đi qua đâu, lưu ở đâu, ai xóa được, log gì. |

Mỗi trục viết 1 đoạn ngắn cho eyePass, 1 đoạn cho V-ID, và 1 dòng "đánh đổi" nêu
rõ chọn cái này thì mất gì — không kết luận cái nào "tốt hơn" một cách chung
chung.

## 9. Vocabulary kết luận

Mọi nhãn dưới đây được đọc theo hướng **V-ID đối chiếu với yêu cầu rút ra từ đặc
tả eyePass** — chủ ngữ luôn là V-ID. Không có nhãn nào mô tả "eyePass thắng/thua";
eyePass không có maturity để thua.

| Trạng thái | Điều kiện |
|---|---|
| `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass `Nêu rõ`/`Nêu chưa đầy đủ`; V-ID đạt `Implemented`/`Hardened` với confidence `Source-reviewed`/`Test-verified`. |
| `ĐÃ ĐÁP ỨNG — THEO THIẾT KẾ` | eyePass `Nêu rõ`/`Nêu chưa đầy đủ`; V-ID đạt `Designed` trở lên nhưng confidence chỉ `Doc-only`/`Self-reported`, hoặc maturity mới dừng ở `Designed` (chưa triển khai). |
| `NGOÀI YÊU CẦU EYEPASS` | eyePass `Không đề cập`; V-ID vẫn có năng lực này ở mức `Designed` trở lên. Đây là năng lực V-ID tự thêm — không viết là "cải tiến so với eyePass" (không có gì để cải tiến khi eyePass không nêu); chỉ ghi nhận evidence và lý do V-ID cần năng lực này. |
| `KẾ THỪA CÓ CHỌN LỌC` | eyePass có rule/kinh nghiệm vận hành hữu ích, cần rà soát trước khi áp dụng cho V-ID, không sao chép trực tiếp. |
| `GAP` | Xem §6. |
| `DEFERRED_BY_DESIGN` | Xem §6. |
| `KHÔNG KẾ THỪA` | Cách làm mô tả trong đặc tả eyePass trái nguyên tắc/scope V-ID — V-ID chủ động không theo. |
| `OUT_OF_SCOPE` | Xem §6. |
| `CHƯA KẾT LUẬN` | Evidence về V-ID mâu thuẫn (`DISPUTED`) hoặc chưa đủ để xếp vào nhóm nào ở trên. |

Không viết "V-ID tốt hơn eyePass" hay bất kỳ câu xếp hạng hệ thống nào ở cấp tổng
hợp (baseline §2 nguyên tắc 6). Mỗi nhãn chỉ có nghĩa gắn với một dòng capability
cụ thể, nêu rõ mức nêu trong đặc tả eyePass, maturity của V-ID, confidence của
V-ID, và giới hạn evidence của cả hai phía.

## 10. Deliverable

Một file duy nhất theo domain, dạng markdown (không bắt buộc workbook 4-sheet
của v1.0). Mỗi dòng capability gồm: ID, mô tả, [eyePass: mức độ nêu trong đặc tả
(§4) + trích dẫn], [V-ID: maturity (§3) + confidence (§5) + evidence + status
(§6)], nhận định (§9), gap/action nếu có, ưu tiên (`P0`/`P1`/`P2`/`DEFERRED`).

Không có gate hay domain score/band riêng để tổng hợp — mỗi dòng capability đứng
độc lập. Một `P0` không được phép "chìm" trong domain khác trông tốt vì không có
domain nào được rút gọn thành một con số để so sánh; **mọi `P0` phải được owner
xác nhận trước khi coi là chốt**, đây là điểm không được bỏ qua để tiết kiệm
thời gian.

Không bắt buộc 2 assessor độc lập + calibration cho toàn bộ 47 tiêu chí.
