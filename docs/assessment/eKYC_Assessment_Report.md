# eKYC Assessment Report — V-ID-eKYC đối chiếu yêu cầu eyePass

| Thuộc tính | Giá trị |
|---|---|
| Trạng thái | **DRAFT — single-assessor first pass, chưa calibration với assessor thứ hai** |
| Dùng cùng | [`../EKYC_COMPARATIVE_ASSESSMENT_RUBRIC.md`](../EKYC_COMPARATIVE_ASSESSMENT_RUBRIC.md) v3.0, [`../EKYC_COMPARATIVE_ASSESSMENT_BASELINE.md`](../EKYC_COMPARATIVE_ASSESSMENT_BASELINE.md) |
| Phạm vi đã chấm | C01–C10 (toàn bộ 10 domain) — 56 dòng capability |
| Phạm vi chưa chấm | Không còn domain nào chưa chấm; vẫn cần calibration với assessor thứ hai (xem cảnh báo cuối trang) |
| Đây KHÔNG phải | Một xếp hạng "V-ID tốt hơn/kém eyePass", hay chứng nhận production-readiness/compliance/độ chính xác model. Đánh giá một chiều: V-ID là đối tượng được chấm, eyePass chỉ là nguồn yêu cầu tham chiếu (đặc tả bàn giao, không có source/test/runtime access) — xem baseline §1. |
| Cấu trúc tài liệu | **Phần A** Executive Summary · **Phần B** eyePass — đặc tả tham chiếu · **Phần C** V-ID-eKYC — đánh giá năng lực · **Phần D** Gap & Traceability Matrix (evidence đầy đủ, từng dòng capability) |

Định nghĩa thuật ngữ, nguyên tắc đọc và FAQ nằm ở Phụ lục đánh giá — tài liệu
này chỉ trình bày kết quả.

---

## Phần A — Executive Summary

### Bức tranh tổng thể (56 dòng, C01–C10)

56 dòng, chia theo nhận định:

| Nhận định | Số dòng | Ý nghĩa |
|---|---|---|
| `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | 18 (+ 3 một phần) | V-ID đạt `Implemented`/`Hardened`, confidence `Source-reviewed`/`Test-verified`, cho yêu cầu eyePass có nêu. |
| `NGOÀI YÊU CẦU EYEPASS` | 17 | V-ID có năng lực này (từ `Designed` trở lên) nhưng eyePass không hề đề cập — không phải "cải tiến", chỉ là bổ sung của V-ID, đứng độc lập. |
| `GAP` | 12 (+ 3 một phần) | Trong scope, chưa đạt mức mong đợi, không có lý do chủ đích được ghi nhận cho việc chưa làm. |
| `ĐÃ ĐÁP ỨNG — THEO THIẾT KẾ` | 2 | Đã thiết kế đúng hướng nhưng chưa triển khai hoặc chỉ `Doc-only`/`Self-reported`. |
| `DEFERRED_BY_DESIGN` | 3 | V-ID chủ động chưa quyết định, có lý do/owner/governance note — không phải thiếu sót. |
| `KẾ THỪA CÓ CHỌN LỌC` | 1 | eyePass có rule/kinh nghiệm hữu ích (cấu trúc UAT checklist), đáng tham khảo cấu trúc trước khi V-ID hình thức hóa acceptance test, không sao chép trực tiếp. |

Ba dòng rơi vào diện "vừa đáp ứng vừa gap" ngay trong cùng một capability, nên
tách ra nói riêng: **C01.4** (retry cơ bản ổn, quality-gated recapture thì
chưa), **C02.2** (Passport MRZ xong, CCCD structured field thì chưa), và
**C09.4** (formatter/linter sạch, type-checker còn 19 lỗi thật).

### V-ID đã đáp ứng được (chọn lọc)

Danh sách dưới đây chỉ gồm những gì đã triển khai đầy đủ và có bằng chứng người
đánh giá tự đọc được — nghĩa là tự đọc code hoặc tự chạy test, không dựa vào
tài liệu tự báo cáo của dự án.

- Kết quả phân tích, tín hiệu dành cho người duyệt, và quyết định cuối cùng đã
  được tách thành ba phần riêng biệt trong code — điểm số không còn đóng vai
  trò quyết định, và có test tự động xác nhận điều này (C04.1).
- Hệ thống chỉ để con người quyết định duyệt hay từ chối; không có đường nào
  tự động approve hoặc reject. Hành vi này được viết cứng trong code, và test
  bao phủ cả trường hợp thành công lẫn thất bại (C04.2).
- Khi chuyển từ máy tính sang điện thoại qua mã QR, mã đó chỉ dùng được một
  lần và không thể bị dùng lại — có test xác nhận nếu ai đó cố dùng lại cùng
  một mã QR lần thứ hai, hệ thống sẽ từ chối (C01.1).
- Việc so khớp khuôn mặt tổng hợp kết quả từ nhiều frame (tối đa 12) bằng
  median, nên một frame đọc sai không làm lệch kết quả cuối — có test xác
  nhận điều này (C03.1).
- Thông tin trả về cho bên ngoài qua API công khai được giới hạn ở mức tối
  thiểu: không có dữ liệu cá nhân thô, không có kết quả OCR thô, không có
  điểm số nội bộ của mô hình (C05.1, C07.1).
- Ảnh và bằng chứng gốc được mã hóa khi lưu trữ, tên file lưu trữ không phải
  là một đường dẫn công khai đoán được, và hệ thống chặn được kiểu tấn công
  dò đường dẫn để truy cập file khác — có hai test trực tiếp xác nhận (C07.2).
- Việc đưa một mô hình AI vào sử dụng phải qua hai lớp phê duyệt, có checksum
  để xác minh đúng file mô hình, và hệ thống từ chối chạy thay vì tự tải model
  về khi không có kết nối mạng. Ba trên bốn hạng mục trong nhóm này đã đạt mức
  cao nhất và có test xác nhận (C06.1–C06.3).
- Việc kiểm tra check-digit trên MRZ của hộ chiếu đã làm đầy đủ theo đúng
  chuẩn ICAO và có test bao phủ (C02.3).
- Những tài khoản có quyền cao — hệ thống tích hợp gọi vào V-ID, hoặc người
  duyệt hồ sơ — phải xác thực bằng một khóa bí mật gửi kèm trong mỗi request;
  thiếu hoặc sai khóa sẽ bị từ chối ngay (C08.1).
- Có bộ test tự động cho toàn bộ pipeline AI (đọc giấy tờ, đọc MRZ,
  chống giả mạo khuôn mặt, so khớp khuôn mặt) và cho luồng người dùng
  đầu-cuối chính: 17 test cho phần AI, 8 test cho luồng end-to-end, và toàn
  bộ 40 test của hệ thống đều pass khi người đánh giá tự chạy lại (C09.2,
  C09.3).
- Ba mảng liên quan tới quản trị tiến độ dự án đều được xác nhận là có thật
  khi đọc trực tiếp tài liệu, không chỉ là lời khẳng định suông: một checklist
  tám điều kiện phải đạt trước khi được coi là sẵn sàng bàn giao bản demo tích
  hợp, một sơ đồ thể hiện việc nào phải xong trước việc nào trong roadmap, và
  một nơi ghi lại các quyết định kỹ thuật đã chốt (C10.1, C10.2, C10.4).

### Năng lực V-ID có mà eyePass không hề đề cập (`NGOÀI YÊU CẦU EYEPASS`)

Đây là những phần V-ID tự xây thêm mà đặc tả bàn giao của eyePass hoàn toàn
không nhắc tới. Không nên đọc đây là "cải tiến so với eyePass" — eyePass
không hề yêu cầu những thứ này, nên không có gì để so sánh hơn/kém; V-ID chỉ
đơn giản là chọn làm thêm.

- Phiên làm việc có state machine tường minh, phân biệt rõ trạng thái nào là
  terminal state thật sự của một phiên (C01.2).
- Một loạt tín hiệu chống giả mạo nâng cao: yêu cầu người dùng quay đầu theo
  hướng dẫn, phát hiện deepfake, phát hiện video quay lại cảnh cũ, phát hiện
  máy quay giả, thử thách bằng giọng nói, và kiểm tra khớp môi với lời nói.
  Nhưng chính dự án cũng đã ghi nhận rõ: các tín hiệu này chưa được đo lường
  và hiệu chỉnh đủ kỹ để coi là bằng chứng chống giả mạo dùng được cho môi
  trường production thật — cùng phụ thuộc vào việc xây xong nền tảng benchmark
  và việc chốt vòng đời threshold, cả hai đều chưa bắt đầu, nên xử lý chung
  với threshold ở C04.5 (C03.3–C03.6).
- Một review queue có cấu trúc: có endpoint riêng để lấy danh sách hồ sơ
  đang chờ duyệt, và mỗi quyết định đi kèm một mã lý do cụ thể (C04.3).
- Một kế hoạch phân quyền chi tiết cho từng thao tác nhạy cảm với bằng chứng
  gốc — ai được xem, được giải mã, được xuất ra, được xóa — đã thiết kế xong
  (thuộc giai đoạn mở rộng admin/duyệt hồ sơ sắp tới) nhưng chưa được xây dựng
  thật (C04.4).
- API có đánh số phiên bản qua tiền tố trong đường dẫn, và cho phép hỏi lại
  trạng thái của một phiên đang xử lý bất cứ lúc nào (C05.2, C05.4).
- Trước khi một mô hình hoặc nhà cung cấp AI được phép chạy, phải qua hai
  bước phê duyệt riêng biệt; và nếu mất kết nối mạng, hệ thống từ chối chạy
  thay vì tự động tải model về (C06.2, C06.3).
- Cơ chế purge chạy định kỳ có ghi lại lịch sử thao tác, và một audit trail
  riêng ghi lại toàn bộ vòng đời của bằng chứng đã thu thập, từ lúc tạo ra
  đến lúc bị xóa (C07.3, C07.4).
- Có test tự động cho abstraction layer — nơi hệ thống chọn và chuyển đổi
  (fallback) giữa các provider AI khác nhau (C09.1).
- Một sơ đồ thể hiện việc nào phải hoàn thành trước việc nào trong roadmap, và
  một nơi ghi lại các quyết định kỹ thuật đã chốt để sau này không phải giải
  thích lại từ đầu (C10.1, C10.4).

### eyePass đã làm rồi, V-ID nên tham khảo

Đây là những capability mà V-ID chưa có, nhưng eyePass đã từng xây dựng và vận
hành với đặc tả đủ chi tiết để tham khảo cách tiếp cận — không phải sao chép
trực tiếp (V-ID có nguyên tắc và ràng buộc dữ liệu khác), mà là tránh mất công
đi lại đúng con đường eyePass đã đi qua và biết rõ vướng ở đâu.

- Hướng dẫn thời gian thực khi chụp selfie: eyePass có state machine hướng
  dẫn cụ thể (khung hình → vật che chắn → khoảng cách → góc mặt), kèm timeout
  10s/20s rõ ràng; V-ID hiện mới ở mức ý định thiết kế chung (C01.5).
- Document quality gate: eyePass có mã lỗi cụ thể theo từng loại lỗi ảnh
  (kích thước, mờ/tối/sáng, cắt góc), mỗi mã kèm message và action riêng cho
  cả backend lẫn frontend; V-ID đã thiết kế nhưng chưa triển khai (C02.4).
- Phát hiện nhiều giấy tờ trong khung hình: eyePass có bộ test case cụ thể
  với 6 kịch bản — dù chính QC của eyePass cũng ghi nhận 2/6 case chưa đạt kỳ
  vọng, nên đây còn là vùng khó ngay cả với eyePass; V-ID chưa đề cập ở đâu
  (C02.5).
- Cho phép end-user tự sửa/skip-validate trường OCR: eyePass có hai cấu hình
  bật/tắt độc lập và khoảng 40 test case field-level, gồm cả case cố tình
  nhập giá trị phi lý để kiểm tra hệ thống có chặn đúng không; V-ID chưa có
  contract cho việc này (C02.6).
- Phân công owner theo vai trò: eyePass có bản đồ vai trò cụ thể (PO, BA,
  Tech Lead, AI Lead, DevOps, Security, Data Owner, Compliance) kèm tên/email
  liên hệ thật; V-ID hiện chỉ có một người quyết định cho mọi việc (C10.5).
- Cấu trúc UAT checklist: phân cấp Category → Function → Sub-function → Item,
  dùng chung cho cả QC và khách hàng ký nhận bàn giao — một khuôn mẫu đáng
  tham khảo khi V-ID hình thức hóa acceptance test, xếp `KẾ THỪA CÓ CHỌN LỌC`
  (C09.7).

### Rủi ro/gap đáng lo ngại nhất

Không có mục nào ở mức chặn cứng. Bảng dưới là những gap có rủi ro thật đáng
xử lý sớm — chi tiết vì sao từng mục đáng lo ngại nằm trong ghi chú của dòng
ma trận tương ứng ở Phần D:

| Chủ đề | Dòng ma trận |
|---|---|
| Webhook dispatch chưa tồn tại (chỉ có field lưu trữ + allowlist, không có lệnh gọi HTTP ra ngoài nào) | C05.5 |
| Phân quyền chi tiết cho từng thao tác nhạy cảm với bằng chứng (xem/giải mã/xuất/xóa) đã thiết kế, chưa triển khai | C04.4 |
| CCCD chưa có structured field extraction (Passport đã có) | C02.2 |
| Document quality gate & reason-code recapture chưa bắt đầu | C02.4 |
| Idempotency key đã thiết kế nhưng chưa nối vào schema hiện tại | C05.3 |
| `VID_CLIENT_KEY`/`REVIEWER_TOKEN` fallback về giá trị mặc định công khai khi thiếu cấu hình, không có gate theo `environment` | C08.2 |
| `mypy` có 19 lỗi type thật (một phần nằm trong `purge_due()`, cùng vùng code C07.3 đã thiếu test), vi phạm điều kiện hoàn thiện trước khi bàn giao demo tích hợp | C09.4 |

### Quyết định phạm vi cần xác nhận (không phải mức độ ưu tiên kỹ thuật)

Đây là những câu hỏi "có làm hay không", không phải "làm cái gì trước":

| Câu hỏi | Dòng ma trận |
|---|---|
| End-user có được tự sửa/skip-validate trường OCR trước khi submit không? (eyePass cho phép; V-ID chưa quyết) | C02.6 |
| Threshold + các signal sinh trắc học nâng cao: cùng phụ thuộc nền tảng benchmark chưa xây xong — xử lý như một quyết định gộp | C04.5, C03.2–C03.6 |
| Mốc thời gian cho dataset registry record (thuộc workstream dataset license/provenance, cũng cần nền tảng benchmark xong trước) | C06.4 |
| Retention matrix production (Legal/DPO + business owner chốt) | C07.5 |
| Có nên phân vai trò owner theo chức năng (security/compliance/AI...) trước khi mở rộng đội, hay giữ một owner chung tới khi nào | C10.5 |

### Bước tiếp theo

Cần xác nhận thứ tự xử lý các mục đáng lo ngại ở bảng trên, và trả lời các câu hỏi phạm vi ở bảng dưới. Trong đó secret fallback và lỗi mypy đáng làm trước vì rẻ — chạy lại đúng lệnh đã dùng để tìm ra chúng là xác nhận được ngay, không cần điều tra gì thêm. Và trước khi đưa báo cáo này ra ngoài phạm vi nội bộ dự án, cần bố trí calibration với một assessor thứ hai.

---

## Phần B — eyePass: Đặc tả tham chiếu theo tài liệu bàn giao

### C01 — Luồng và UX

- **Cross-device handoff qua QR** (`Nêu chưa đầy đủ`) — UAT checklist xác nhận có luồng "Full Onboarding → Verify on mobile → Scan QR Code", nhưng không mô tả cơ chế bảo mật (hết hạn, dùng một lần, chống replay, revoke). *(→ matrix C01.1)*
- **Session/state machine tường minh** (`Không đề cập`) — luồng được trình bày tuyến tính (happy path + nhánh lỗi), không có tên trạng thái. *(→ C01.2)*
- **Chọn loại giấy tờ trước khi chụp** (`Nêu rõ`) — BRD UC2 + UAT checklist mô tả hai flow riêng: chọn thủ công ("Identity Document Processing") và tự động phân loại ("Auto Detect Document Type"), một tính năng V-ID hiện chưa có tương đương. *(→ C01.3)*
- **Retry/recapture** (`Nêu rõ`) — flow diagram: mỗi bước chụp có nhánh lỗi rõ ràng dẫn tới "Retake", không thấy giới hạn số lần thử trên sơ đồ. *(→ C01.4)*
- **Hướng dẫn thời gian thực khi chụp selfie** (`Nêu rõ`) — BRD UC3.1 đặc tả chi tiết state machine hướng dẫn (khung hình → vật che chắn → khoảng cách → góc mặt), guideline text cụ thể, timeout 10s/20s. *(→ C01.5)*

### C02 — Giấy tờ/OCR/MRZ

- **Phạm vi loại giấy tờ** (`Nêu rõ`) — Business rules "Thông tin theo loại giấy tờ": 6 loại (CCCD gắn chip, CCCD thường, CMND chip/thường/giấy, Hộ chiếu VN/nước ngoài) + CMND Quân đội, mỗi loại có field OCR/MRZ/chip riêng. *(→ C02.1)*
- **Validate trường có cấu trúc theo field** (`Nêu rõ`) — ~20 mã lỗi field-level (`InvalidIDNumber`, `InvalidDOB`, `InvalidFullname`...), có cả logic tính hạn theo mốc tuổi 25/40/58/60. *(→ C02.2)*
- **MRZ/passport check-digit** (`Nêu rõ`) — mã `1015 ErrorMRZcode`/`1016 MismatchMRZdata`; MRZ hộ chiếu 2 dòng 44 ký tự, CCCD gắn chip 3 dòng 30 ký tự, đối chiếu với visible zone. *(→ C02.3)*
- **Document quality gate & error/recapture** (`Nêu rõ`) — mã lỗi cụ thể theo từng loại lỗi ảnh (kích thước, mờ/tối/sáng, cắt góc), mỗi mã có message + action riêng cho BE/FE. *(→ C02.4)*
- **Phát hiện nhiều giấy tờ trong khung hình** (`Nêu rõ`) — file test case riêng với 6 kịch bản cụ thể và routing theo `many_docs` flag; ghi chú: chính QC eyePass từng nhận 2/6 case chưa đạt kỳ vọng — chỉ để biết đây là vùng khó, không suy ra maturity thực tế của eyePass. *(→ C02.5)*
- **End-user tự sửa/skip-validate trường OCR** (`Nêu rõ`) — 2 config flag độc lập, ~40 test case field-level ở cả SDK và BE, gồm cả case cố tình nhập giá trị phi lý để kiểm tra BE có chặn không. *(→ C02.6)*
- **Fixture/benchmark OCR độc lập session** (`Không đề cập`) — các file kiểm thử chỉ là test case pass/fail thủ công, không phải benchmark dataset có metric. *(→ C02.7)*

### C03 — Sinh trắc học & anti-spoof

- **Face matching (embedding/similarity/multi-frame)** (`Nêu rõ`) — API trả `matching_score`/`is_matching_face`; 4 mức threshold đặt tên sẵn (`Loose`/`Normal`/`Strict`/`Very Strict`) trong Business rules "Ngưỡng Face". *(→ C03.1)*
- **Passive liveness** (`Nêu rõ`) — flow diagram: "Auto chụp 3 ảnh Passive"; BRD UC3.7 kiểm tra vị trí/vật che/khoảng cách/góc trước khi tự động chụp, không có thử thách chủ động. *(→ C03.2)*
- **Active liveness / challenge-response** (`Không đề cập`) — không xuất hiện ở bất kỳ nguồn nào; hướng dẫn capture chỉ có "Hold Steady" (khung passive). *(→ C03.3)*
- **Deepfake / replay / camera-injection** (`Nêu chưa đầy đủ`) — chỉ có mã lỗi `1009` "Face is spoof" không kèm mô tả cơ chế; không dùng thuật ngữ "deepfake"/"replay"/"camera injection". *(→ C03.4)*
- **Voice challenge** (`Không đề cập`) — không có "voice"/audio ở bất kỳ tài liệu nào. *(→ C03.5)*
- **Lip-sync challenge** (`Không đề cập`) — không xuất hiện ở bất kỳ tài liệu nào. *(→ C03.6)*
- **Failure-mode routing khi tín hiệu sinh trắc học mơ hồ** (`Nêu chưa đầy đủ`) — mã lỗi rời rạc theo từng signal (`1000`–`1009`) trả phẳng, không có chính sách routing khi tín hiệu mơ hồ (không có khái niệm tương đương `INCONCLUSIVE`). *(→ C03.7)*

### C04 — Decision & manual review

- **Tách execution/review-signal/decision** (`Nêu rõ`) — `POST /ekyc/auth_face` trả một `code`+`message` phẳng, chính là verdict — mô tả cụ thể một thiết kế không tách biệt. *(→ C04.1)*
- **Bước duyệt con người bắt buộc** (`Nêu rõ`) — BRD/API doc cho thấy code pass/fail phía client, không có bước con người bắt buộc. *(→ C04.2)*
- **Review queue (assignment/reason/idempotency)** (`Không đề cập`) — không xuất hiện ở bất kỳ tài liệu nào; không có khái niệm review queue. *(→ C04.3)*
- **Phân quyền chi tiết cho từng thao tác nhạy cảm với bằng chứng (xem/giải mã/xuất/xóa)** (`Không đề cập`) — không có tài liệu nào đề cập. *(→ C04.4)*
- **Threshold versioned/approved** (`Nêu chưa đầy đủ`) — Business rules ghi ngưỡng `< 0.8` confidence nhưng không có quy trình version/approval đi kèm. *(→ C04.5)*

### C05 — API & integration

- **Response tối thiểu, không lộ raw OCR/PII** (`Nêu rõ`) — ngược lại: response mẫu `POST /ekyc/idcard` trả chi tiết OCR field-by-field kèm confidence, và thuộc tính khuôn mặt (`age`/`gender`/`glass`/`matching_score`) trực tiếp cho caller — một contract "trả chi tiết" được đặc tả rõ. *(→ C05.1)*
- **API versioning** (`Không đề cập`) — endpoint liệt kê tuyệt đối, không tiền tố version, không chính sách versioning. *(→ C05.2)*
- **Idempotency key cho state-changing request** (`Không đề cập`) — không có tham số idempotency ở bất kỳ endpoint nào. *(→ C05.3)*
- **Polling trạng thái phiên** (`Không đề cập`) — kiến trúc hoàn toàn đồng bộ (flow diagram: mỗi bước chờ response ngay) — không phải thiếu sót, chỉ là kiến trúc khác. *(→ C05.4)*
- **Webhook/callback signature/replay/retry** (`Nêu chưa đầy đủ`) — Handover checklist liệt kê "callback/webhook" là đã bàn giao, nhưng không tài liệu kỹ thuật nào (API doc, Integration Architecture diagram) mô tả cơ chế cụ thể. *(→ C05.5)*
- **CORS / kiểm soát domain** (`Nêu rõ`) — web console có màn hình quản trị CORS domain đầy đủ (thêm/sửa/xóa, wildcard, active/inactive), 22/25 test case pass. *(→ C05.6)*

### C06 — Model governance & offline

- **Adapter/provider abstraction** (`Nêu chưa đầy đủ`) — High-Level Architecture diagram cho thấy Domain Services gọi HTTP tới "Internal AI/ML Services" dùng chung ("Triton + Milvus") — chỉ là ranh giới hạ tầng, không có adapter spec. *(→ C06.1)*
- **Approval hai lớp cho provider/model** (`Không đề cập`) — không có tài liệu nào mô tả quy trình duyệt model/provider. *(→ C06.2)*
- **Manifest checksum & offline runtime** (`Không đề cập`) — không xuất hiện ở bất kỳ tài liệu nào, kể cả 2 diagram kiến trúc. Không phải thiếu sót — eyePass kiến trúc như dịch vụ luôn online (Base URL cố định, AI service "shared"), không có nhu cầu offline runtime. *(→ C06.3)*
- **Dataset registry (nguồn/license/sensitivity/approval)** (`Không đề cập`) — "Ngưỡng Face" chỉ là một giá trị ngưỡng đơn, không có provenance dataset đi kèm. *(→ C06.4)*

### C07 — Data, evidence & privacy

- **PII minimization trong response** (`Nêu rõ`) — ngược lại: response mẫu trả toàn bộ trường OCR (per-character confidence) và thuộc tính khuôn mặt chi tiết trực tiếp cho caller. *(→ C07.1)*
- **Mã hóa evidence / opaque storage key** (`Không đề cập`) — sơ đồ kiến trúc cho thấy ghi trực tiếp vào MinIO/S3 qua S3/HTTPS (transport only), không chú thích mã hóa at-rest hay key scheme. *(→ C07.2)*
- **Cơ chế purge/retention** (`Không đề cập`) — không có quy tắc xóa/retention hệ thống nào; các mục "hết hạn" trong Business rules chỉ nói về hạn của *giấy tờ tùy thân*, không phải retention của eyePass. *(→ C07.3)*
- **Audit trail cho vòng đời evidence** (`Không đề cập`) — không có khái niệm audit log nào; sơ đồ kiến trúc chỉ có logger app chung. *(→ C07.4)*
- **Retention matrix production được phê duyệt** (`Không đề cập`) — không có lịch lưu trữ nào trong tài liệu bàn giao. *(→ C07.5)*

### C08 — Security & operations

- **Xác thực cho actor có quyền cao** (`Nêu rõ`) — API key bắt buộc trên mỗi request, cộng một luồng SDK Android riêng đổi `app_id`/`app_secret` lấy token, có kiểm tra thiết bị root trước khi cho dùng SDK. *(→ C08.1)*
- **Secret management an toàn/fail-closed** (`Không đề cập`) — không tài liệu bàn giao nào mô tả quy trình quản lý secret. *(→ C08.2)*
- **Không rò rỉ credential qua bundle client** (`Không đề cập`). *(→ C08.3)*
- **Logging/monitoring không lộ PII** (`Không đề cập`) — chỉ có nhắc "audit của quyết định" như một phần bàn giao, không mô tả kỹ thuật cụ thể. *(→ C08.4)*
- **Quy trình incident/change control** (`Nêu chưa đầy đủ`) — có đầu mối Security/Compliance trong danh sách stakeholder và nhắc "defect còn mở/đã đóng", nhưng không đính kèm quy trình chi tiết. *(→ C08.5)*

### C09 — Quality & verification

- **Unit/contract test tầng abstraction** (`Không đề cập`) — không có khái niệm test tự động ở tầng kiến trúc trong tài liệu bàn giao. *(→ C09.1)*
- **Test model/AI pipeline** (`Nêu rõ`) — Face Matching 1-N checklist và sheet Face Management ghi kết quả thực tế theo từng kịch bản (29 pass/16 fail/1 đang xem xét trên 46 case), không chỉ mô tả kỳ vọng. *(→ C09.2)*
- **Test end-to-end capture → phân tích → kết quả** (`Nêu rõ`) — UAT checklist đặc tả đầy đủ hai luồng e2e (QR và tại chỗ), có cột kết quả mong đợi từng bước. *(→ C09.3)*
- **Formatter/linter/type-checker sạch** (`Không đề cập`) — công cụ phát triển nội bộ, không phải nội dung khách hàng thường nhận trong bàn giao. *(→ C09.4)*
- **CI tự động** (`Không đề cập`). *(→ C09.5)*
- **Test tự động cho frontend** (`Nêu rõ`) — Web Console TCs và Web Demo checklist là bộ test case UI có theo dõi Pass/Fail/Pending/Blocked, dù thực hiện bằng tay. *(→ C09.6)*
- **Acceptance-criteria có cấu trúc, theo dõi được** (`Nêu rõ`) — UAT checklist phân cấp Category → Function → Sub-function → Item, dùng chung cho QC và khách hàng ký nhận. *(→ C09.7)*

### C10 — Delivery governance

- **Roadmap có cấu trúc phụ thuộc giữa milestone** (`Không đề cập`) — bộ tài liệu bàn giao là checklist cho sản phẩm đã xong, không phải roadmap thực thi hướng tới tương lai. *(→ C10.1)*
- **Release gate/definition of done nhiều điều kiện** (`Nêu chưa đầy đủ`) — có cột "Trạng thái" theo hạng mục (đều "Đã bàn giao"), nhưng không gộp thành một gate tổng hợp cho một lần release cụ thể. *(→ C10.2)*
- **Cơ chế theo dõi quyết định còn mở có cấu trúc** (`Không đề cập`) — đây là tài liệu bàn giao sản phẩm đã xong, không phải tài liệu quản lý quyết định đang chờ. *(→ C10.3)*
- **Cơ chế ghi quyết định đã chốt (ADR)** (`Không đề cập`). *(→ C10.4)*
- **Phân công owner/stakeholder theo vai trò** (`Nêu rõ`) — mục 1.1.2 liệt kê cụ thể PO/BA/Tech Lead/AI Lead/DevOps/Security/Data Owner/Compliance kèm tên/email liên hệ. *(→ C10.5)*

---

## Phần C — V-ID-eKYC: Đánh giá năng lực theo đặc tả và implementation hiện tại

### C01 — Luồng và UX

- QR handoff cross-device đã `Implemented`/`Test-verified`: token dùng một lần, replay-protected, test xác nhận từ chối claim thứ hai với 401. Expiry/revoke thì chưa có test riêng. *(→ C01.1)*
- Session/state machine: `Implemented`/`Source-reviewed`, 6+ trạng thái vận hành thật — bản rút gọn của thiết kế mục tiêu 13-trạng-thái, phần còn lại vẫn `Designed`. *(→ C01.2)*
- Chọn loại giấy tờ và khóa lựa chọn sau khi chụp: `Implemented`/`Test-verified`, đổi loại giữa chừng trả `409`, có test. V-ID không có flow tự động phân loại như eyePass. *(→ C01.3)*
- Retry/recapture chia làm hai: phần retry cơ bản `Implemented`/`Source-reviewed`; quality-gated recapture (blur/glare/reason code) mới `Designed`/`Doc-only`, chưa bắt đầu triển khai. *(→ C01.4)*
- Hướng dẫn thời gian thực khi chụp selfie mới ở mức `Conceptual`/`Source-reviewed` — có ý định thiết kế chung, chưa có vòng lặp phản hồi thời gian thực nào trong source. *(→ C01.5)*

### C02 — Giấy tờ/OCR/MRZ

- Phạm vi loại giấy tờ: `Implemented`/`Source-reviewed`. CCCD chạy YOLO11 + RapidOCR PP-OCRv6, Passport chạy TD3 OCR + MRZ parser — phần nền tảng xử lý cho cả hai loại giấy tờ này đã xong. NFC/chip là `OUT_OF_SCOPE` MVP có chủ đích; CMND/military ID chưa trong scope. *(→ C02.1)*
- Structured field extraction thì tách hai: CCCD mới `Conceptual`/`Source-reviewed` — đọc code xác nhận chưa lưu trường có cấu trúc, chỉ trả metadata OCR/layout. Passport MRZ thì `Implemented`/`Test-verified` rồi. *(→ C02.2)*
- MRZ/passport check-digit: `Implemented`/`Test-verified`, check digit ICAO đầy đủ, có test. CCCD MRZ (chip) dùng chung giới hạn với C02.2. *(→ C02.3)*
- Document quality gate còn `Designed`/`Doc-only` — đặc tả đầy đủ (reason code, state `RECAPTURE_DOCUMENT`) nhưng chưa bắt đầu triển khai, capability `document_quality` chưa có provider nào đăng ký. *(→ C02.4)*
- Multi-document-in-frame detection: `Absent`/`Doc-only`, chưa đề cập ở bất kỳ tầng nào. *(→ C02.5)*
- End-user tự sửa trường OCR cũng `Absent`/`Doc-only` — không có contract cho việc này, nguyên tắc gần nhất chỉ nói về reviewer correction. *(→ C02.6)*
- Fixture/benchmark OCR: `Conceptual`/`Self-reported`. Kế hoạch có đặc tả dataset/metric cụ thể (MIDV-2020, DocXPand-25k, CER/WER...) nhưng chưa bắt đầu. *(→ C02.7)*

### C03 — Sinh trắc học & anti-spoof

- Face matching (similarity/aggregation) là `Hardened`/`Test-verified` — median trên tối đa 12 frame, test resist một frame lạc quan. *(→ C03.1)*
- Passive liveness: `Implemented`/`Source-reviewed`, MiniFASNetV2 đang active nhưng chưa có test đặt tên riêng cho nó. *(→ C03.2)*
- Active liveness (quay đầu trái/phải/về giữa) đạt `Implemented`/`Test-verified`, có test cho cả happy path và skip case. Tự dự án ghi nhận rõ: signal này chưa benchmark/calibrate thành bằng chứng chống spoof production. *(→ C03.3)*
- Deepfake/replay/camera-injection thì lẫn lộn — `Implemented`/`Source-reviewed` tổng thể, deepfake detector chưa có test riêng, còn replay và camera-injection thì đã `Test-verified`. Cùng cảnh báo chưa-benchmark như trên. *(→ C03.4)*
- Voice challenge: `Implemented`/`Source-reviewed`. Verify chuỗi 6 số qua ASR (Vosk, local) — nhưng đây là kiểm tra nội dung đọc, không phải speaker verification (không đối chiếu đặc trưng giọng theo danh tính). Voice-spoof đúng nghĩa thì `DEFERRED_BY_DESIGN`, chờ approval mục đích/dữ liệu audio. *(→ C03.5)*
- Lip-sync challenge: `Implemented`/`Source-reviewed`, chạy qua service HTTP riêng (SyncNetV2/S3FD), fail-closed nếu chưa cấu hình. Chưa có test riêng. *(→ C03.6)*
- Failure-mode routing (không suy diễn fraud từ tín hiệu mơ hồ) đã `Implemented`/`Test-verified` — `INCONCLUSIVE`/`UNAVAILABLE` tường minh, và nguyên tắc này lặp lại nhất quán ở cả 3 nguồn đọc được. *(→ C03.7)*

### C04 — Decision & manual review

- Tách execution/review-signal/decision: `Hardened`/`Test-verified`. *(→ C04.1)*
- Manual-review-only, không có đường auto approve/reject nào: cũng `Hardened`/`Test-verified`, hard-coded và test phủ cả happy lẫn failure path. *(→ C04.2)*
- Review queue phần core (`/reviews`, decisions, reason codes) đã `Implemented`/`Source-reviewed`; assignment, idempotency, `ESCALATE` thì còn `Designed`/`Doc-only`, chưa bắt đầu triển khai. *(→ C04.3)*
- Phân quyền chi tiết cho từng thao tác nhạy cảm với bằng chứng mới `Designed`/`Doc-only` — mask mặc định đã đúng nhưng phân quyền chi tiết chưa triển khai. *(→ C04.4)*
- Threshold versioned/approved: `Conceptual`/`Self-reported`. Seed threshold đang `evaluation_only`, lifecycle đã thiết kế nhưng việc chốt threshold chưa bắt đầu — việc chưa phê duyệt cho production là quyết định chủ đích. *(→ C04.5)*

### C05 — API & integration

- Response tối thiểu, không lộ raw data: `Implemented`/`Source-reviewed`, `SessionPublic` không có PII/raw OCR/model score. *(→ C05.1)*
- API versioning: `Implemented`/`Source-reviewed`, có version prefix `/api/v2`, nhưng chưa xác nhận có chính sách deprecation hay không. *(→ C05.2)*
- Idempotency key mới `Designed`/`Doc-only` — thiết kế chi tiết ở §6.2/§11.2 nhưng chưa nối vào `CreateSessionRequest` hiện tại. *(→ C05.3)*
- Polling trạng thái phiên: `Implemented`/`Source-reviewed`, đang hoạt động bình thường. *(→ C05.4)*
- Webhook dispatch (signature/replay/retry): `Conceptual`/`Source-reviewed`. `callback_url` hiện chỉ là field lưu trữ kèm allowlist check — rà toàn bộ source không thấy lệnh gọi HTTP ra ngoài nào, nên dispatch thật chưa tồn tại. *(→ C05.5)*
- CORS: `Implemented`/`Source-reviewed`, allowlist tĩnh qua config. Chưa có admin self-service như eyePass. *(→ C05.6)*

### C06 — Model governance & offline

Domain này khá vững — ba trong bốn mục đã `Hardened`/`Test-verified`.

- Adapter/provider abstraction: domain/use case chỉ gọi capability ports, provider chọn tại composition root, có test config-swap/fallback/circuit-breaker. *(→ C06.1)*
- Approval hai lớp cho provider/model: `manifest.json` có `approval_status`, fail-closed nếu chưa approved, đối chiếu 3 lớp code/manifest/.env qua script riêng. *(→ C06.2)*
- Manifest checksum & offline runtime: SHA-256 cho từng artifact, `HF_HUB_OFFLINE=1`, readiness tách public/authenticated (`admin_readiness` nằm sau `require_reviewer`). *(→ C06.3)*
Mục còn lại — dataset registry — dừng ở `Designed`/`Doc-only`: schema/quy trình 5 bước đã chốt (phần governance/contract nền tảng đã xong), nhưng dataset record cụ thể chủ động để lại workstream dataset license/provenance, chờ nền tảng benchmark xong trước. *(→ C06.4)*

### C07 — Data, evidence & privacy

- PII minimization trong response/storage: `Implemented`/`Source-reviewed` (riêng MRZ đã `Test-verified`) — raw OCR/MRZ/transcript/embedding không nằm trong analysis response mặc định. *(→ C07.1)*
- Mã hóa evidence / opaque storage key: `Hardened`/`Test-verified`. AES-GCM, key không phải path công khai, chặn path-traversal, 2 test trực tiếp. *(→ C07.2)*
- Cơ chế purge chạy thật theo chu kỳ, idempotent ở mức guard truy vấn — nhưng không có test nào đặt tên cho `purge_due`, nên giữ ở `Implemented`/`Source-reviewed` thay vì `Hardened`. *(→ C07.3)*
- Audit trail: `Implemented`/`Source-reviewed`, ghi cho submit/purge/decide, `details` không chứa PII ở các call site đã đọc — nhưng chưa test riêng. *(→ C07.4)*
- Retention matrix production: `Designed`/`Doc-only`, 8 data class × 4 outcome, phần lớn ô `TBD` có chủ đích. *(→ C07.5)*

### C08 — Security & operations

- Xác thực actor quyền cao: `Implemented`/`Source-reviewed`, shared-secret trên header cho cả tích hợp V-ID lẫn reviewer, thiếu/sai bị từ chối `401`. *(→ C08.1)*
- Secret management thì lệch nhau giữa hai cặp secret: `TOKEN_SECRET`/`EVIDENCE_KEY` đã `Implemented`/`Source-reviewed` (fail-closed qua `${VAR:?...}`), nhưng `VID_CLIENT_KEY`/`REVIEWER_TOKEN` mới `Designed`/`Doc-only` — fallback êm về giá trị mặc định công khai, không có gate nào theo `environment`. *(→ C08.2)*
- Không rò rỉ credential qua bundle client: `Designed`/`Source-reviewed`. Chưa rò rỉ thật, nhưng tên biến `NEXT_PUBLIC_VID_CLIENT_KEY` là một cái bẫy đặt tên đang chờ sẵn. *(→ C08.3)*
- Logging/monitoring: `Absent`. Không có module `logging` nào được import trong `backend/app/` ngoài một dòng đếm ở `purge_worker.py` — an toàn PII hiện tại chỉ vì chưa log gì cả. *(→ C08.4)*
- Quy trình incident/change control: `Conceptual`/`Doc-only`, chỉ có một dòng ý định trong roadmap (thuộc giai đoạn integrated demo hardening), chưa có runbook thật. *(→ C08.5)*

### C09 — Quality & verification

- Unit/contract test tầng abstraction: `Implemented`/`Test-verified`, 13 test cho registry/governance, tự chạy xác nhận pass. *(→ C09.1)*
- Test model/AI pipeline: `Implemented`/`Test-verified`, 17 test tự động cho MRZ/liveness/replay/face-match. *(→ C09.2)*
- Test end-to-end: `Implemented`/`Test-verified`, 8 test qua `TestClient` gồm luồng QR-claim → capture → manual review đầy đủ. *(→ C09.3)*
- Formatter/linter/type-checker tách hai kết quả khác nhau: formatter/linter `Implemented`/`Test-verified` (tự chạy `ruff check`/`ruff format --check` sạch), còn type-checker thì `GAP` — `mypy` có 19 lỗi thật, một phần nằm ngay trong `purge_due()`. *(→ C09.4)*
- CI tự động: `Absent`/`Source-reviewed`, không có `.github/workflows` hay cấu hình CI nào khác trong repo. *(→ C09.5)*
- Test tự động frontend: `Absent`/`Source-reviewed` — không framework test, không file `*.test.*`/`*.spec.*`, dù lint/typecheck tĩnh thì sạch. *(→ C09.6)*
- Acceptance-criteria có cấu trúc: `Designed`/`Doc-only`, điều kiện hoàn thành rải rác theo milestone trong roadmap, không theo khuôn mẫu chuẩn hóa, không có cơ chế theo dõi pass/fail. *(→ C09.7)*

### C10 — Delivery governance

- Roadmap có sơ đồ phụ thuộc: `Implemented`/`Source-reviewed` — một hạng mục nền tảng governance/contract làm cơ sở cho toàn bộ các nhánh phía sau, nối tiếp nhau từ demo sẵn sàng, kiến trúc capability/provider, quality gate, benchmark, threshold, mở rộng admin/duyệt hồ sơ, tới bàn giao demo tích hợp; cộng hai workstream chạy song song ngoài chuỗi chính (hardening config/secret; dataset license/provenance). *(→ C10.1)*
- Release gate nhiều điều kiện: `Implemented`/`Source-reviewed`, gate bàn giao demo tích hợp liệt kê 8 điều kiện phải đạt đồng thời. *(→ C10.2)*
- Theo dõi quyết định còn mở có cấu trúc: `Designed`/`Source-reviewed` — hiện chỉ có hai danh sách gạch đầu dòng rải rác (`AGENTS.md`, roadmap §7), không ID/trạng thái/owner theo từng mục; chưa có nơi tập trung theo dõi có cấu trúc thật sự. *(→ C10.3)*
- Ghi quyết định đã chốt (ADR): `Implemented`/`Source-reviewed`, bốn ADR trong hợp đồng capability §5. *(→ C10.4)*
- Phân công owner theo vai trò: `Conceptual`/`Source-reviewed` — hiện chỉ có "người dùng là owner cuối cùng" cho mọi thứ, chưa phân vai trò theo chức năng. *(→ C10.5)*

### Đọc tổng hợp (toàn bộ C01–C10 đã chấm)

Vài điểm đáng nêu ra sau khi chấm hết 10 domain. Không có dòng nào ở `Absent` mà thiếu lý do — C02.5 (multi-doc detection), C02.6 (end-user self-edit), C08.4 (logging/monitoring), C09.5/C09.6 (CI, frontend test) đều đã gắn `GAP` hoặc câu hỏi phạm vi trong ma trận, không phải bị bỏ sót giữa chừng. `Hardened`/`Test-verified` tập trung nhiều nhất ở C04, C06, C07 — decision separation, model governance, evidence encryption/opaque-key là ba mảng có test trực tiếp dày nhất. Khoảng cách lớn nhất giữa thiết kế và triển khai rơi vào bốn mảng: document quality gate, benchmark, threshold, và phân quyền chi tiết/review queue mở rộng — tất cả `NOT_STARTED` nhưng đều có đặc tả rõ trong kế hoạch, và tự dự án đã liệt kê các mảng này là điều kiện cho `MVP feature-complete`, nên không tính là gap ẩn.

Hai phát hiện đáng chú ý nhất domain C08/C09 không đến từ bất kỳ tài liệu nào — cả hai chỉ lộ ra khi tự chạy lệnh thật: `VID_CLIENT_KEY`/`REVIEWER_TOKEN` fallback về giá trị mặc định công khai (C08.2), và `mypy` có 19 lỗi type thật, một phần nằm ngay trong `purge_due()` — cùng hàm mà C07.3 đã ghi nhận thiếu test (C09.4).
- Toàn bộ 10 domain (C01–C10) hiện đã có dòng chính thức — xem Phần D (Gap & Traceability Matrix).

---

## Phần D — Gap & Traceability Matrix

### 1. Domain C01 — Luồng và UX

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C01.1 | Cross-device handoff: tạo token dùng một lần, chống replay, revoke, desktop theo dõi trạng thái | `Nêu chưa đầy đủ` — UAT checklist, "Full Onboarding \| Verify on mobile \| Get QR code \| Scan the QR Code" (dòng 49-52 trong file checklist): xác nhận có luồng quét QR để chuyển từ desktop sang mobile, nhưng không mô tả cơ chế bảo mật (hết hạn, dùng một lần, chống replay, revoke). Không tài liệu nào khác trong bộ bàn giao (BRD, business rules, API doc) nhắc lại luồng QR này. | Thiết kế rút gọn §6.1-6.3 mô tả rõ: QR chỉ chứa URL + token ngẫu nhiên dùng một lần, không chứa PII, có vòng đời token và bốn endpoint riêng (`POST /sessions/{id}/handoffs`, `POST /handoffs/claim`, `GET /sessions/{id}/handoff-status`, `POST /sessions/{id}/handoffs/{id}/revoke}`). Implementation khớp thiết kế — `backend/app/api.py` dòng 167-270 (`create_handoff`/`claim_handoff`/`handoff_status`/`revoke_handoff`). Test `test_full_cccd_qr_capture_and_manual_review` (`backend/tests/test_ekyc_flow.py:43-51`) xác nhận claim thành công và replay cùng token bị từ chối 401. `Implemented`/`Test-verified`, dù chưa thấy test riêng cho expired-token hay revoke-rồi-claim nên chưa đủ để gọi `Hardened` toàn phần. |
| C01.2 | Session/state machine: các trạng thái phiên tách biệt, terminal state, hết hạn | `Không đề cập` — không tài liệu bàn giao nào (BRD, flow diagram, UAT checklist, API doc) mô tả một khái niệm session-stage/state machine tường minh; luồng eyePass được trình bày như một kịch bản tuyến tính (happy path + nhánh lỗi), không có tên trạng thái. | `Implemented`/`Source-reviewed`. `backend/app/domain/models.py:21` có field `stage`, và `services/ekyc.py` hiện thực chuỗi `AWAITING_MOBILE → CAPTURING → PROCESSING → MANUAL_REVIEW/PROCESSING_FAILED → COMPLETED → PURGED`, cộng `EXPIRED`/`CANCELLED` nằm trong `TERMINAL_STAGES` (dòng 15, 355-358). Đây là bản rút gọn của state machine mục tiêu 13-trạng-thái ở thiết kế chính §8.4 (`AWAITING_LAWFUL_BASIS`, `RESTRICTED`, `PURGING` tách riêng), phần đó vẫn `Designed`/`Doc-only`. Có test dùng `TERMINAL_STAGES` gián tiếp qua các flow test khác nhưng chưa có test đặt tên riêng cho transition `EXPIRED`. |
| C01.3 | Chọn loại giấy tờ trước khi chụp; loại đã chọn không đổi giữa chừng | `Nêu rõ` — BRD UC2 (Bước 2) và UAT checklist mô tả **hai flow riêng biệt**: "Identity Document Processing" (dòng 31: người dùng tự chọn loại giấy tờ) và "Auto Detect Document Type" (dòng 35: hệ thống tự phân loại). Không đề cập việc khóa lựa chọn sau khi đã bắt đầu chụp. | `POST /ekyc/capture/document-type` (`backend/app/api.py:205`) đã triển khai và test-covered: `test_capture_client_selects_cccd_without_choosing_card_revision`, và `test_document_type_cannot_change_after_capture_starts` xác nhận đổi loại giấy tờ sau khi đã upload mặt trước sẽ bị trả về `409`. `Implemented`/`Test-verified`. V-ID chỉ có flow chọn thủ công — chưa có gì tương đương "Auto Detect Document Type" của eyePass. |
| C01.4 | Retry/recapture khi ảnh lỗi hoặc chất lượng kém | `Nêu rõ` — sơ đồ luồng của eyePass vẽ rõ một nhánh lỗi cho mỗi bước chụp, luôn dẫn về nút "Click 'Retake'" để quay lại đúng màn hình chụp đó. Sơ đồ không thể hiện bất kỳ giới hạn nào về số lần được thử lại. | Retry cơ bản đã có: trang chụp ảnh (`frontend/app/capture/page.tsx`) có nút "Quay lại thay đổi giấy tờ" (dòng 231-233) để chọn lại ảnh trước khi gửi, và nút "Thử gửi lại" (dòng 271-273) khi submit lỗi — `Implemented`/`Source-reviewed`. Nhưng endpoint nhận evidence (`POST /ekyc/capture/evidence/{type}`) chưa có quality gate thật: không kiểm tra ảnh mờ hay lóa, không giới hạn số lần thử. §6.5 của thiết kế chính đã vẽ ra một phiên bản đầy đủ hơn — state riêng cho recapture, reason code, thu hồi token cũ, kiểm tra chất lượng ảnh — nhưng tài liệu đó vẫn là bản draft chưa duyệt nên dừng ở `Designed`/`Doc-only`. Đây chính là hạng mục document quality gate còn dang dở; source hiện tại không có state `RECAPTURE_DOCUMENT` nào, xác nhận được luôn từ việc đọc code là hạng mục này chưa bắt đầu. |
| C01.5 | Hướng dẫn thời gian thực khi chụp selfie (vị trí khuôn mặt, khoảng cách, góc, vật che chắn) | `Nêu rõ` — BRD UC3.1 mô tả chi tiết state machine hướng dẫn theo thời gian thực (khung → vật che chắn → khoảng cách → góc mặt), mỗi điều kiện có guideline text cụ thể, timeout 10s/20s. | Thiết kế chính §6.8 chỉ nêu ý định chung, không có state machine/guideline/timeout cụ thể — `Conceptual`/`Source-reviewed`. `frontend/components/camera-capture.tsx` và `frontend/app/capture/page.tsx` chỉ có một dòng tip tĩnh và timeout ẩn 75s cho recording, không có vòng lặp phản hồi thời gian thực nào. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C01.1 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass chỉ nêu tên tính năng QR, không có chi tiết bảo mật. V-ID có thiết kế, implementation, và test cho negative case cốt lõi (replay); expiry/revoke chưa có test riêng, đáng theo dõi thêm nhưng không gấp. |
| C01.2 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không có khái niệm state machine — năng lực V-ID tự thêm. State machine hiện tại đơn giản hơn thiết kế mục tiêu 13-trạng-thái, nhưng đó là gap nội bộ, không liên quan gì eyePass. |
| C01.3 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Test-covered. eyePass có thêm flow "Auto Detect Document Type" mà V-ID chưa có, nhưng đó là ghi nhận riêng, không hạ nhận định ở đây. |
| C01.4 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` (retry cơ bản) · phần quality-gated recapture: `GAP` | Retry cơ bản đọc trực tiếp từ source, đủ điều kiện đáp ứng. Quality-gated recapture (document quality gate) đã thiết kế rõ nhưng chưa triển khai và không ai giải thích vì sao hoãn, nên `GAP` chứ không phải `DEFERRED_BY_DESIGN` — đáng làm nhưng không chặn happy path hiện tại. |
| C01.5 | `IN_SCOPE` | `GAP` | eyePass mô tả rất cụ thể; V-ID mới dừng ở ý định thiết kế chung, chưa có ghi nhận quyết định nào để gọi đây là hoãn có chủ đích. Chưa cấp bách vì chưa chặn technical demo. |

### 2. Domain C02 — Giấy tờ/OCR/MRZ

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C02.1 | Phạm vi loại giấy tờ được hỗ trợ và cách phân biệt revision/loại | `Nêu rõ` — Business rules, sheet "Thông tin theo loại giấy tờ": bảng field-by-field cho 6 loại (CCCD gắn chip, CCCD thường/White Card, CMND chip/thường/giấy, Hộ chiếu VN, Hộ chiếu nước ngoài) + "Validation OCR ver 2/3" thêm CMND Quân đội. | Thiết kế chính §3.1/§6.4 chỉ cho hai lựa chọn ở UI, `CCCD`/`Hộ chiếu`, tự nhận diện revision. CCCD chạy YOLO11 layout + RapidOCR PP-OCRv6; Passport chạy TD3 OCR + parser MRZ + toàn bộ check digit ICAO — phần nền tảng xử lý cho cả hai loại giấy tờ này đã xong. `Implemented`/`Source-reviewed`. NFC/chip data đã `OUT_OF_SCOPE` MVP có ghi rõ ở thiết kế chính §3.2. CMND/military ID không có trong scope — hẹp hơn eyePass ở điểm này. |
| C02.2 | Trích xuất & validate trường có cấu trúc (structured field) theo từng loại giấy tờ, có version | `Nêu rõ` — sheets "Validation OCR ver 2"/"ver 3": ~20 mã lỗi field-level (`InvalidIDNumber`, `InvalidDOB`, `InvalidFullname`...) với rule cụ thể theo từng field × từng loại giấy tờ. | Hai kết quả khác nhau tùy loại giấy tờ. CCCD: `Conceptual`/`Source-reviewed` — thiết kế chính §6.6 mới nêu nguyên tắc chung, chưa có bảng field-rule chi tiết như eyePass; đọc trực tiếp `DocumentOcrResult`/`DocumentLayoutResult` (`capability_ports.py`) xác nhận hai dataclass này chỉ có `lines`/`region_count`/`class_counts`, không có field tên riêng nào (`id_number`, `date_of_birth`...), nên demo chỉ trả metadata OCR/layout an toàn, chưa lưu PII có cấu trúc. Passport MRZ thì ngược lại: `PassportMrzResult.all_check_digits_valid` đã `Implemented`/`Test-verified`, test `test_icao_td3_check_digits_are_valid_without_exposing_mrz` (`test_ai_pipeline.py:36`). |
| C02.3 | MRZ / passport check-digit validation | `Nêu rõ` — sheet "Validation OCR ver 2/3", mã `1015 ErrorMRZcode`/`1016 MismatchMRZdata`. | `backend/ai_modules/ekyc/passport_mrz.py` hiện thực đúng nhánh Passport MRZ-first của thiết kế chính §6.7, test `test_icao_td3_check_digits_are_valid_without_exposing_mrz` và `test_passport_requires_single_td3_page` (`test_ekyc_flow.py:202`) — `Implemented`/`Test-verified`. CCCD MRZ (chip, 3 dòng 30 ký tự) chưa có evidence triển khai riêng, dùng chung giới hạn với C02.2. |
| C02.4 | Document quality gate (blur/glare/corner/occlusion) và error/recapture UX | `Nêu rõ` — sheet "Message lỗi (OOD)"/"Sprint 1": mã lỗi cụ thể `1001`–`1008`/`2001` (kích thước, mờ/tối/sáng, cắt góc), mỗi mã có BE/FE message và action cụ thể. | Kế hoạch có đặc tả đầy đủ `document_quality` capability (blur/glare/corner/brightness/contrast/occlusion), reason code cụ thể, state `RECAPTURE_DOCUMENT`, fixture synthetic — nhưng chỉ `Designed`/`Doc-only`. `document_quality` tồn tại trong enum (`capability_ports.py:24`) nhưng chưa có provider nào đăng ký (`NOT_REGISTERED`), xác nhận được trực tiếp từ source là hạng mục này chưa bắt đầu. |
| C02.5 | Phát hiện nhiều giấy tờ trong khung hình (multi-document-in-frame) | `Nêu rõ` — file test case riêng "More than Document": 6 case cụ thể, `many_docs` flag và routing theo cấu hình CMS. (QC của chính eyePass ghi nhận 2/6 case chưa đạt kỳ vọng — chỉ trích dẫn để biết đây là vùng khó, không dùng để suy ra maturity thực tế của eyePass.) | `Absent`/`Doc-only`. Không tìm thấy đề cập ở thiết kế chính, kế hoạch, trạng thái, hay source. |
| C02.6 | Cho phép end-user tự sửa (manual edit) hoặc skip validate trường OCR trước khi submit | `Nêu rõ` — sheets "Manual Edit OCR"/"Skip Validation Rule"/"MANUAL_SKIP_SMART_TESTCASES": 2 config flag độc lập, ~40 test case field-level ở cả SDK và BE. | `Absent`/`Doc-only`. Không có màn hình hay contract nào cho end-user tự sửa trường OCR trước khi submit; nguyên tắc gần nhất (§6.10.7) nói về reviewer correction, chứ không phải end-user tự sửa. |
| C02.7 | Fixture synthetic và benchmark có metric (OCR/MRZ) độc lập với session | `Không đề cập` — không có tài liệu bàn giao nào mô tả benchmark suite hay dataset registry cho OCR; các file kiểm thử chỉ là test case pass/fail thủ công. | Kế hoạch mô tả nền tảng benchmark khá chi tiết: CLI/registry riêng biệt session, dataset candidate (MIDV-2020, DocXPand-25k, MIDV-500/SmartDoc), metric cụ thể (field exact match, CER/WER, MRZ exact/check digit) — nhưng đó vẫn chỉ là mô tả trong tài liệu lập kế hoạch. `Conceptual`/`Self-reported`, không có CLI/registry/benchmark runner nào trong `backend/`. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C02.1 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Đáp ứng cho CCCD + Passport, đúng phạm vi MVP. CMND/military ID hẹp hơn eyePass, nhưng CMND đang bị thay thế bởi CCCD tại VN nên không tính là regression; NFC/chip đã loại khỏi scope có chủ đích. |
| C02.2 | `IN_SCOPE` | `GAP` (CCCD) / `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` (Passport MRZ) | Đáng lo ngại: CCCD chưa có structured field extraction, xác nhận qua source, không ai gán lý do/owner riêng cho khoảng trống này. Vì CCCD là loại giấy tờ chính, cả document quality gate (theo field) lẫn phần hiển thị structured field đã mask (thuộc giai đoạn mở rộng admin/duyệt hồ sơ) đều đang chờ dữ liệu này. |
| C02.3 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Passport MRZ check-digit test-verified rồi. CCCD MRZ dùng chung giới hạn với C02.2. |
| C02.4 | `IN_SCOPE` | `GAP` | Đáng lo ngại: eyePass nêu rõ với error code/message cụ thể; V-ID mới ở mức `Designed`, document quality gate chưa bắt đầu. Đơn giản là chưa tới lượt làm sau khi phần kiến trúc capability/provider nền tảng đã xong, chứ không phải quyết định hoãn có chủ đích — ảnh hưởng trực tiếp trải nghiệm technical demo, và các bước hiển thị structured field sau này đều cần dữ liệu từ đây trước. |
| C02.5 | `IN_SCOPE` | `GAP` | eyePass có đặc tả và test case rõ; V-ID chưa đề cập ở đâu cả. Edge case, không chặn happy path, không gấp. |
| C02.6 | `IN_SCOPE`? — cần quyết định phạm vi | `GAP` (không phải `KHÔNG KẾ THỪA`) | eyePass cho end-user tự sửa trường OCR có validate; V-ID chưa nói rõ end-user có được tự sửa lúc capture hay không — §6.10.7 chỉ nói về reviewer. Chưa đủ căn cứ để biết đây là từ chối chủ đích hay đơn giản chưa thiết kế tới: đánh đổi thật là giảm ma sát capture so với rủi ro data subject "sửa" để né rule validate. |
| C02.7 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — THEO THIẾT KẾ` | Nền tảng benchmark có đặc tả rõ nhưng chưa bắt đầu, self-reported only. Không gấp vì việc này hợp lý đứng sau phần kiến trúc nền tảng và document quality gate, không chặn technical demo hiện tại. |

### 3. Domain C03 — Sinh trắc học & anti-spoof

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C03.1 | Face matching: embedding, similarity, multi-frame aggregation contract (không tính quyết định pass/fail theo threshold — xem C04.5) | `Nêu rõ` — API doc: `POST /ekyc/idcard` trả `matching_score`/`is_matching_face`; `POST /ekyc/auth_face`; `POST /ekyc/search_by_img` (1:N). Business rules, sheet "Ngưỡng Face": 4 mức threshold đặt tên sẵn (`Loose`/`Normal`/`Strict`/`Very Strict`). | `ArcFaceEmbeddingProvider`/`MedianFaceMatchingProvider` (`ekyc_providers.py`) cộng `select_face_match_candidates`/`aggregate_face_similarities` (`face_matching.py:13,20`) — tối đa 12 frame, tổng hợp bằng median. Hai test: `test_face_match_selects_multiple_high_confidence_frames_with_a_limit`, `test_face_match_uses_median_to_resist_one_optimistic_frame`. `Hardened`/`Test-verified`. Quyết định match/no-match theo threshold production nằm ở C04.5 riêng (`DEFERRED_BY_DESIGN`) — dòng này chỉ chấm phần tính similarity. |
| C03.2 | Passive liveness signal | `Nêu rõ` — flow diagram: "Auto chụp 3 ảnh Passive"; BRD UC3.7: kiểm tra vị trí/vật che chắn/khoảng cách/góc mặt trước khi auto-capture, không có thử thách chủ động; API `liveness_check`; mã lỗi `1005`/`1009`. | `MiniFasNetLivenessProvider`/`MiniFasNetEngine` (`ekyc_providers.py:189`, `ai_modules/ekyc/passive_liveness.py`), model `MiniFASNetV2` đang active, profile `technical_demo`/`evaluation_only`. `Implemented`/`Source-reviewed` — chưa có test đặt tên riêng cho passive liveness nên chưa lên được `Hardened`. |
| C03.3 | Active liveness / challenge-response (quay đầu + đọc dãy số) | `Không đề cập` — không xuất hiện trong flow diagram, BRD hay API doc; hướng dẫn capture của eyePass chỉ có "Hold Steady" (passive framing). | `HeadPoseActiveLivenessProvider`/`inspect_head_turn_sequence` (`ai_modules/ekyc/active_liveness.py`) có hai test: `test_head_turn_sequence_requires_both_turns_and_return_to_center`, `test_head_turn_sequence_is_inconclusive_when_user_skips_a_turn` — `Implemented`/`Test-verified`. Tự dự án ghi rõ tín hiệu này chưa benchmark/calibrate thành bằng chứng chống spoof production; nền tảng benchmark và việc chốt threshold/calibration đều `NOT_STARTED` theo kế hoạch (liên quan C04.5), và không có registry hay benchmark CLI nào trong source. Toàn bộ các signal sinh trắc học nâng cao trong domain này — C03.2 đến C03.6 — chia sẻ đúng caveat này, nên chỉ ghi chi tiết một lần ở đây thay vì lặp lại từng dòng. |
| C03.4 | Visual deepfake / anti-spoof signal (deepfake detector, replay attack, camera injection heuristic) | `Nêu chưa đầy đủ` — API doc chỉ có mã lỗi `1009` "Face is spoof" không kèm mô tả cơ chế; không có thuật ngữ "deepfake"/"replay attack"/"camera injection" ở bất kỳ tài liệu bàn giao nào. | Ba sub-signal, hai mức độ chín khác nhau: `DeepfakeDetectorProvider` (Deep-Fake-Detector-v2 ONNX) chưa có test riêng; `HeuristicReplayProvider`/`HeuristicCameraInjectionProvider` (`ekyc_providers.py:277,304`) thì đã `Test-verified` — `test_replay_heuristic_flags_duplicate_frames`, `test_camera_injection_heuristic_exposes_metadata_and_timing_signals`. Tổng thể `Implemented`/`Source-reviewed`. |
| C03.5 | Voice challenge / voice spoof signal | `Không đề cập` — không có "voice"/audio ở bất kỳ tài liệu bàn giao nào. | `VoskVoiceChallengeProvider`/`VoiceVerifier` (`ai_modules/ekyc/voice_challenge.py`) chạy Vosk Vietnamese small 0.4 local — `Implemented`/`Source-reviewed`. Nhưng tự dự án đã ghi rõ giới hạn: "Voice hiện kiểm tra chuỗi sáu chữ số bằng ASR, chưa phải speaker verification". Voice-spoof detection đúng nghĩa bị khóa có chủ đích, chờ approval mục đích/dữ liệu audio/benchmark (thiết kế chính §3.1, §6.8) — đó là phần `DEFERRED_BY_DESIGN`, không phải phần đã triển khai ở dòng này. |
| C03.6 | Lip-sync challenge | `Không đề cập` — không xuất hiện ở bất kỳ tài liệu bàn giao nào. | `HttpLipSyncProvider`/`call_lipsync` (`ai_modules/ekyc/media.py`) chạy qua service HTTP riêng, backing `SyncNetV2`/`S3FD`. Nếu chưa cấu hình `LIPSYNC_URL`, capability báo `UNAVAILABLE`/`PROVIDER_NOT_REGISTERED` thay vì âm thầm bỏ qua — `Implemented`/`Source-reviewed`, chưa có test đặt tên riêng. |
| C03.7 | Failure-mode: tín hiệu sinh trắc học không rõ ràng không được tự động diễn giải thành "fraud" | `Nêu chưa đầy đủ` — API doc có mã lỗi rời rạc theo từng signal (`1000`–`1009`) trả phẳng, không có chính sách routing khi tín hiệu mơ hồ (hành vi tổng quát "không có bước duyệt bắt buộc" đã chấm ở C04.2). | `INCONCLUSIVE`/`UNAVAILABLE` là trạng thái tường minh trong result dataclass (`capability_ports.py`), test `test_model_output_marks_incomplete_active_liveness_challenge`, `test_model_output_preserves_unavailable_ocr_without_false_success`, `test_model_output_derives_reason_codes_from_failed_attempts` — `Implemented`/`Test-verified`. Nguyên tắc này được nêu tường minh ở thiết kế chính §6.8 và lặp lại nhất quán ở trạng thái dự án. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C03.1 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Chỉ chấm phần tính similarity/aggregation; quyết định threshold đã ở C04.5. |
| C03.2 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Source-reviewed đủ để đạt ngưỡng "kiểm chứng được", nhưng nên bổ sung test đặt tên riêng để lên `Hardened`. |
| C03.3 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không có active liveness. Năng lực V-ID tự thêm, có code và test, nhưng chưa benchmark/calibrate làm bằng chứng chống spoof production — gộp chung với C04.5 vì cùng phụ thuộc nền tảng benchmark và việc chốt threshold. |
| C03.4 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass chỉ có mã lỗi "Face is spoof" không rõ cơ chế, không đủ cụ thể để coi là một yêu cầu — nhưng V-ID vẫn có 3 sub-signal thật, một phần đã test-verified. |
| C03.5 | `IN_SCOPE` (digit-challenge) / `DEFERRED_BY_DESIGN` (voice-spoof đúng nghĩa) | `NGOÀI YÊU CẦU EYEPASS` | eyePass không đề cập voice. V-ID hiện chỉ verify chuỗi 6 số qua ASR — tách rõ khỏi voice-spoof để không tuyên bố quá mức. |
| C03.6 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không đề cập lip-sync. V-ID có provider thật, fail-closed khi chưa cấu hình, nhưng chưa có test đặt tên riêng. |
| C03.7 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Cả thiết kế và test đều chứng minh nguyên tắc "không suy diễn fraud từ INCONCLUSIVE" nhất quán. |

### 4. Domain C04 — Decision & manual review

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C04.1 | `execution_status` / `review_signal` / public reason / final decision tách biệt; score không là verdict | `Nêu rõ` — API doc: `POST /ekyc/auth_face` trả một `code`+`message` phẳng, chính là verdict, không có sự tách biệt. Đặc tả mô tả cụ thể hành vi này, chỉ là không đáp ứng yêu cầu tách biệt. | `backend/app/adapters/analyzer.py` tách riêng `execution_status`/`review_signal` theo từng capability, test `test_model_output_separates_execution_from_review_signal` cùng assertion riêng trong `test_capability_registry.py`. Chạy trực tiếp `cd backend && uv run pytest -q` ngày 2026-08-10 xác nhận toàn bộ 40 test pass. `Hardened`/`Test-verified`. |
| C04.2 | Demo không auto approve/reject; unavailable/inconclusive route đúng | `Nêu rõ` — BRD/API doc cho thấy code pass/fail phía client, không có bước con người bắt buộc. Mô tả cụ thể, không mơ hồ. | `submit()` (`services/ekyc.py:213`) hard-code `stage = "MANUAL_REVIEW"` mỗi lần, không có nhánh nào khác — `Hardened`/`Test-verified`, test phủ cả happy path và failure path. |
| C04.3 | Review queue: assignment, allowed action, reason, idempotency | `Không đề cập` — không xuất hiện trong bất kỳ tài liệu bàn giao nào; không có khái niệm review queue. | Core đã triển khai: `/reviews`, `/reviews/{id}`, `/reviews/{id}/decisions` với `ReviewTask.status`/`reason_codes` — `Implemented`/`Source-reviewed`. Phần còn thiếu (assignment, idempotency khi decide hai lần, `ESCALATE`) có đặc tả rõ ở giai đoạn mở rộng admin/duyệt hồ sơ sắp tới nhưng chưa bắt đầu, nên vẫn `Designed`/`Doc-only`. |
| C04.4 | Mask mặc định; reveal/decrypt/export/delete/decision tách quyền + audit | `Không đề cập` — không có tài liệu nào đề cập. | Giai đoạn mở rộng admin/duyệt hồ sơ sắp tới thiết kế tách riêng quyền `review:read`/`pii:unmask`/`evidence:view`/`biometric:view`/`review:decide`/`evidence:export`/`evidence:delete`, reason/purpose bắt buộc, grant ngắn hạn, response `no-store`, audit mọi lần cấp/xem/giải mã/playback/từ chối — nhưng implementation hiện tại (`review_detail`) chỉ trả metadata qua một role `require_reviewer` phẳng. Mask mặc định đúng, phân quyền chi tiết thì chưa, nên `Designed`/`Doc-only`. |
| C04.5 | Threshold/policy versioned/approved; đổi model/preprocess/aggregation làm threshold cũ hết hiệu lực | `Nêu chưa đầy đủ` — business rules ghi ngưỡng `< 0.8` confidence nhưng không có quy trình version/approval. | Seed threshold đang `evaluation_only`, lifecycle chọn/freeze/benchmark/approve đã thiết kế nhưng chưa bắt đầu triển khai — `Conceptual`/`Self-reported`. Chưa phê duyệt threshold production là quyết định chủ đích, không phải thiếu sót âm thầm. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C04.1 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Tách execution/review/decision, có test. |
| C04.2 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Manual-review-only hard-coded và test-covered. |
| C04.3 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không đề cập review queue. Core đã `Implemented`; assignment/idempotency/`ESCALATE` còn `Designed` (giai đoạn mở rộng admin/duyệt hồ sơ chưa bắt đầu) — gap nội bộ, không liên quan eyePass, không gấp. |
| C04.4 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | Đáng lo ngại: eyePass không đề cập phân quyền chi tiết cho từng thao tác nhạy cảm với bằng chứng (xem/giải mã/xuất/xóa). V-ID tự thêm, đặc tả rõ ở giai đoạn mở rộng admin/duyệt hồ sơ sắp tới nhưng chưa triển khai; nên làm trước khi coi dự án feature-complete vì các bước sau đều cần phần này xong trước. |
| C04.5 | `DEFERRED_BY_DESIGN` | `DEFERRED_BY_DESIGN` | V-ID để threshold production `TBD` có chủ đích, chưa có mốc thời gian quyết định lại. eyePass có ghi ngưỡng nhưng thiếu versioning/approval process — cần owner quyết định trước khi coi mục này xong. |

### 5. Domain C05 — API & integration

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C05.1 | Public response chỉ trả metadata tối thiểu, không lộ raw OCR/PII/model score | `Nêu rõ` — API doc: response mẫu `POST /ekyc/idcard` trả chi tiết OCR field-by-field kèm confidence, và thuộc tính khuôn mặt (`age`/`gender`/`glass`/`matching_score`) trực tiếp cho caller. | `SessionPublic` (`backend/app/domain/schemas.py:54-63`) chỉ có `id`/`document_type`/`stage`/`decision`/`voice_challenge`/`next_action`/timestamps — không PII, không raw OCR, không model score. Khớp nguyên tắc "API bên ngoài chỉ trả metadata tối thiểu" ở thiết kế chính §11. `Implemented`/`Source-reviewed`; `reason_codes`/`correlation_id` (target v2 §11.1) vẫn `Designed`/`Doc-only`. |
| C05.2 | API versioning theo path/header, không đổi ngầm ảnh hưởng integrator | `Không đề cập` — API doc liệt kê endpoint tuyệt đối, không tiền tố version; không tài liệu nào mô tả chính sách versioning. | Có version prefix `/api/v2` (`app.include_router(router, prefix=settings.api_prefix)`, `backend/app/main.py:35`), trích từ phần kiến trúc capability/provider nền tảng. `Implemented`/`Source-reviewed`, nhưng chưa thấy chính sách deprecation/breaking-change cho version cũ. |
| C05.3 | State-changing request (create/complete/decision) bắt buộc idempotency key, dedupe theo actor+endpoint+request hash | `Không đề cập` — API doc không có tham số idempotency key ở bất kỳ endpoint nào. | Thiết kế chi tiết ở §6.2/§11.2 của thiết kế chính: idempotency key, `expected_version`/`If-Match`, dedupe theo `job_id+evidence_hash+analyzer_version`. `CreateSessionRequest` hiện tại (`schemas.py:13-16`) chưa có trường này — `Designed`/`Doc-only`. |
| C05.4 | Polling trạng thái phiên qua opaque ID | `Không đề cập` — flow eyePass hoàn toàn đồng bộ (flow diagram: mỗi bước chờ response ngay) — không phù hợp kiến trúc của họ, không phải thiếu sót. | `GET /ekyc/sessions/{session_id}` (`backend/app/api.py:221`) đã triển khai, trả `SessionPublic` — `Implemented`/`Source-reviewed`. |
| C05.5 | Webhook/callback: chữ ký, chống replay, retry, idempotency khi dispatch | `Nêu chưa đầy đủ` — Handover checklist 1.4.1 "API catalogue" liệt kê callback/webhook là đã bàn giao, nhưng API doc thực tế và Integration Architecture diagram không mô tả bất kỳ cơ chế callback/signature nào — mọi luồng đều là request/response đồng bộ. | `callback_url` chỉ là field lưu trữ (`backend/app/domain/models.py`) với kiểm tra prefix-allowlist (`api.py:154-158`). Rà toàn bộ `backend/app/` — không `requests`/`httpx`/dispatcher/outbox, không một lệnh gọi HTTP ra ngoài nào dùng `callback_url`. Capability "gửi webhook" chưa tồn tại, chỉ có trường dữ liệu và validation input; kế hoạch liệt kê việc này là điều kiện #5 cho "MVP feature-complete", chưa đạt. `Conceptual`/`Source-reviewed` — giữ ở mức này thay vì `Designed` vì chưa có tài liệu mô tả chi tiết cơ chế dispatch (payload shape, retry backoff, HMAC scheme) ngoài một dòng liệt kê trong điều kiện MVP. |
| C05.6 | CORS / kiểm soát domain gọi API từ trình duyệt | `Nêu rõ` — Web console eyePass có màn hình quản trị CORS domain đầy đủ (thêm/sửa/xóa, wildcard subdomain, active/inactive), 22/25 test case pass. | `CORSMiddleware` với `settings.cors_origins` (`backend/app/main.py:29-30`, `core/config.py:27`) — allowlist tĩnh qua config/`.env`. `Implemented`/`Source-reviewed`, chưa có admin UI tự phục vụ như eyePass. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C05.1 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Nguyên tắc "không lộ raw data" đã triển khai và source-reviewed; `reason_codes`/`correlation_id` (target v2) vẫn chưa triển khai. |
| C05.2 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không có khái niệm versioning. V-ID có version prefix nhưng chưa xác nhận quy trình deprecation — gap nội bộ, không gấp. |
| C05.3 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — THEO THIẾT KẾ` | Đáng lo ngại: eyePass không đề cập idempotency, nhưng V-ID có thiết kế chi tiết chưa nối vào schema hiện tại — cần trước khi mở API cho hệ thống ngoài phụ thuộc retry an toàn. |
| C05.4 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không cần polling, kiến trúc đồng bộ khác. V-ID polling đã chạy, source-reviewed. |
| C05.5 | `IN_SCOPE` | `GAP` | Đáng lo ngại nhất domain này: `callback_url` đã expose cho integrator dùng nhưng dispatch thật chưa tồn tại, và không có lý do chủ đích nào được ghi nhận cho việc đó — nếu hệ thống ngoài bắt đầu dựa vào field này trước khi dispatch thật xong, đây là rủi ro tích hợp thật, không chỉ thiếu tính năng. |
| C05.6 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | CORS an toàn (allowlist), source-reviewed. Thiếu admin self-service so với eyePass, nhưng đó là vận hành, không phải rủi ro bảo mật. |

### 6. Domain C06 — Model governance & offline

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C06.1 | Provider/model được trừu tượng qua adapter/port, không hard-code trong domain/use case; provider cụ thể chọn tại composition root | `Nêu chưa đầy đủ` — High-Level Architecture diagram: Domain Services (`ocr`/`face`/`auth`/`general_info`/`third_party`) gọi HTTP tới "Internal AI/ML Services" ("Triton + Milvus" trong hạ tầng của họ). Đây chỉ là ranh giới hạ tầng (service boundary), không có adapter spec hay quy tắc composition root như V-ID. | ADR-M0-001 (hợp đồng capability §5) yêu cầu domain/use case chỉ gọi capability ports, provider chọn tại composition root theo profile/config — `backend/app/domain/capability_ports.py`, `adapters/capability_registry.py`, `adapters/ekyc_providers.py`, `core/capability_config.py` hiện thực đúng như vậy. `test_capability_registry.py` phủ config-swap, fallback, `UNAVAILABLE`, circuit breaker, timeout; chạy `uv run pytest -q` ngày 2026-08-10 xác nhận cả 40 test pass. `Hardened`/`Test-verified`. |
| C06.2 | Provider/model phải qua approval hai lớp (đăng ký code + duyệt governance) trước khi chạy; fail-closed nếu chưa approved | `Không đề cập` — không có tài liệu bàn giao nào mô tả quy trình duyệt/approval cho model hoặc provider. | ADR-M0-002. `models/manifest.json` có mảng `providers[]` (`approval_status`/`usage_scope`/`approval_reference`), `ManifestReader.provider_ready()` bắt buộc approve trước `model_ready()`, và `scripts/validate_capability_providers.py` đối chiếu 3 lớp code/manifest/.env. Test `test_provider_not_approved_in_manifest_fails_closed`, `test_manifest_provider_ids_reads_providers_array`. `Hardened`/`Test-verified`. |
| C06.3 | Model manifest có checksum artifact; runtime không tự download model; readiness fail-closed nếu artifact thiếu/sai checksum | `Không đề cập` — không có tài liệu nào (kể cả 2 architecture diagram) mô tả manifest, checksum hay offline runtime. Không phải thiếu sót của eyePass — sản phẩm kiến trúc như dịch vụ luôn online (Base URL cố định, AI service "shared" trong hạ tầng của họ), không có nhu cầu offline runtime. | `backend/app/adapters/manifest.py:59-107` — `_sha256()` tính và so khớp checksum, gắn cờ invalid nếu sai. Dockerfile đặt `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1`, README xác nhận runtime không tải model. Readiness tách hai lớp: `GET /api/v2/utils/health-check` không auth, `GET /api/v2/admin/readiness` (`api.py:139-145`) nằm sau `require_reviewer`. Test `test_analyzer_readiness_checks_every_grouped_artifact`, `test_runtime_manifest_strips_governance_only_fields`. `Hardened`/`Test-verified`. |
| C06.4 | Dataset dùng cho benchmark/eval phải có record: nguồn, license, sensitivity, approval_status trước khi dùng | `Không đề cập` — không có dataset registry, license record hay approval lifecycle nào được nêu; "Ngưỡng Face" chỉ là một giá trị ngưỡng đơn, không có provenance dataset đi kèm. | Hợp đồng capability §6 có schema đầy đủ (`dataset_id`/`license_name`/`sensitivity`/`checksum_sha256`/`split_policy`/`approval_status`) và quy trình 5 bước — phần governance/contract nền tảng đã xong. Nhưng dataset record thật và record store thuộc workstream dataset license/provenance, chờ nền tảng benchmark xong trước, chưa triển khai — `Designed`/`Doc-only`. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C06.1 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass chỉ nêu vị trí hạ tầng AI service; V-ID có adapter spec đầy đủ, test-covered. |
| C06.2 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không đề cập approval workflow. Năng lực V-ID tự thêm, đã hardened. |
| C06.3 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass kiến trúc như dịch vụ luôn online nên không cần offline runtime — không đề cập không phải là gap của họ. V-ID hardened, test-verified. |
| C06.4 | `DEFERRED_BY_DESIGN` | `DEFERRED_BY_DESIGN` | Schema/process đã thiết kế đầy đủ, phần governance/contract nền tảng đã xong, dataset record cụ thể chủ động để lại workstream dataset license/provenance (chờ nền tảng benchmark xong trước), chưa có mốc thời gian cụ thể hơn — quyết định có chủ đích, không phải gap. eyePass không đề cập dataset governance nên không có gì để đối chiếu. |

Không có gì đáng lo ngại trong domain C06 — ba trong bốn mục đã `Hardened`/`Test-verified`, mục còn lại là governance chủ đích để mở, có owner/workstream rõ.

### 7. Domain C07 — Data, evidence & privacy

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C07.1 | Response/storage mặc định không chứa raw OCR, MRZ, transcript, embedding — chỉ metadata/signal an toàn | `Nêu rõ` — API doc (`POST /ekyc/idcard`) response mẫu đầy đủ: toàn bộ trường OCR (per-character confidence), thuộc tính khuôn mặt chi tiết (`age`/`gender`/`glass`/`matching_score`) trả thẳng cho caller. | Hợp đồng capability §3 (đã chốt trong phần governance/contract nền tảng) quy định raw OCR/MRZ/transcript/embedding/raw evidence path không thuộc analysis response mặc định. `services/ekyc.py:213` (`submit()`) chỉ gán `item.analysis` từ kết quả `analyzer.analyze()`, không có field OCR text/MRZ raw nào. `Implemented`/`Source-reviewed`, riêng MRZ đã `Test-verified` (`test_icao_td3_check_digits_are_valid_without_exposing_mrz`) — phần OCR/embedding còn lại chỉ dựa vào đọc code, chưa có test riêng cho từng loại. |
| C07.2 | Evidence lưu trữ mã hóa, storage key không phải path công khai, chống path-traversal | `Không đề cập` — không có tài liệu bàn giao nào nhắc tới mã hóa evidence hoặc opaque storage key. Sơ đồ kiến trúc cho thấy ghi trực tiếp vào MinIO/S3 qua S3/HTTPS (transport), không chú thích mã hóa at-rest hay key scheme. | `EncryptedLocalEvidenceStorage` (`backend/app/adapters/storage.py`) dùng AES-GCM, storage key dạng `{session_id}/{evidence_type}-{uuid4}.enc`, `_resolve()` chặn path-traversal. Hai test trực tiếp: `test_local_evidence_is_encrypted_and_round_trips`, `test_storage_rejects_path_traversal` (raise `ValueError` khi key chứa `../`). `Hardened`/`Test-verified`. |
| C07.3 | Cơ chế purge/xóa evidence theo trigger (retention, hủy session, yêu cầu xóa), idempotent, có audit | `Không đề cập` — không có quy tắc xóa/retention nào trong Business rules/Handover checklist/BRD; các mục "hết hạn" chỉ nói về ngày hết hạn *của giấy tờ tùy thân*, không phải retention hệ thống. | `backend/app/purge_worker.py` chạy `EkycService.purge_due()` theo chu kỳ; `services/ekyc.py:305-330` xóa file evidence, xóa row `Evidence`/`Handoff`/`ReviewTask`, anonymize `subject_ref`, đặt `stage = "PURGED"` (guard tạo idempotency), ghi `_audit(..., "session.purge")`. Cơ chế chạy thật trong code — nhưng không có test nào đặt tên cho `purge_due` trong `backend/tests/`, nên giữ ở `Implemented`/`Source-reviewed` thay vì `Hardened`. Đáng lưu ý: một tài liệu tiến độ nội bộ từng ghi cơ chế này là "đã kiểm chứng", nhưng đọc trực tiếp test suite không xác nhận được điều đó — nên coi khẳng định tự báo cáo đó là chưa đủ căn cứ. |
| C07.4 | Audit trail cho vòng đời evidence (tạo, submit, purge) — không chứa PII | `Không đề cập` — không có khái niệm audit log nào trong tài liệu bàn giao; sơ đồ kiến trúc chỉ có logger app chung, không phải audit trail riêng cho dữ liệu nhạy cảm. | `_audit()` (`services/ekyc.py:365`) ghi `AuditEvent`, gọi từ `submit()`/`purge_due()`/`review_decide()`; `details` truyền vào không chứa PII ở các call site đã đọc. `Implemented`/`Source-reviewed`, chưa có test đặt tên riêng cho nội dung/tính đầy đủ của audit event. Audit cho xem/giải mã/export raw evidence là phần thiết kế riêng thuộc C04.4, không lặp lại ở đây. |
| C07.5 | Retention matrix production (thời hạn lưu theo data class × outcome) được phê duyệt | `Không đề cập` — không có lịch lưu trữ/retention nào trong tài liệu bàn giao. | Thiết kế chính §14.1 có bảng retention 8 data class × 4 outcome, phần lớn ô `TBD`; "Raw OCR/MRZ" và "Face crop/embedding" mặc định `Ephemeral`, khớp C07.1. `Designed`/`Doc-only` — quyết định governance chủ đích, chưa chốt. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C07.1 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass trả raw OCR/face-attribute chi tiết trong response; V-ID minimize theo hợp đồng capability nền tảng (đã xong) và code review, một phần test-verified (MRZ). Đáng thêm test riêng cho các capability còn lại, nhưng không gấp. |
| C07.2 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không đề cập mã hóa/opaque key. Năng lực bảo mật V-ID tự thêm, đã hardened. |
| C07.3 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không đề cập purge/retention. Cơ chế chạy thật nhưng chưa có test đặt tên riêng — nên thêm test cascade-delete và idempotency (chạy hai lần liên tiếp) để lên `Hardened`, không gấp. |
| C07.4 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không có khái niệm audit trail. Audit event ghi cho submit/purge/decide đã chạy nhưng chưa test-verified; audit cho xem/giải mã/export raw evidence là phần riêng của C04.4, đã đáng lo ngại ở đó nên không lặp lại ở đây. |
| C07.5 | `DEFERRED_BY_DESIGN` | `DEFERRED_BY_DESIGN` | eyePass không đề cập retention matrix. Quyết định chủ đích của V-ID, chưa có mốc thời gian cụ thể, cần Legal/DPO và business owner chốt — không phải gap. |

### 8. Domain C08 — Security & operations

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C08.1 | Cơ chế xác thực cho các actor có quyền cao (hệ thống tích hợp, reviewer/admin) | `Nêu rõ` — API doc yêu cầu một `api_key` ("Private api key") bắt buộc trên mỗi request; tài liệu hướng dẫn SDK Android mô tả một luồng riêng cho ứng dụng di động, nơi `app_id`/`app_secret` được đổi lấy token qua một API login trước khi gọi `setupSdk(token, ...)`, kèm bước kiểm tra thiết bị đã root hay chưa trước khi cho phép dùng SDK, và một mã lỗi riêng (`ACTION_NOT_AUTHORIZED`) khi token hết hạn hoặc không hợp lệ. | Hai actor có quyền cao của V-ID xác thực bằng shared-secret trong header: `require_vid_client` (`backend/app/api.py:85-91`) so khớp `X-V-Id-Client-Key` với `settings.vid_client_key`, `require_reviewer` (dòng 94-100) so khớp `Authorization: Bearer <reviewer_token>`. Đơn giản nhưng đúng chức năng — thiếu hoặc sai giá trị bị từ chối `401`. `Implemented`/`Source-reviewed`. V-ID không có SDK di động riêng nên không có bước root-detection tương đương eyePass — khác biệt kiến trúc, không phải thiếu sót. |
| C08.2 | Secret quản lý an toàn: không có giá trị mặc định lộ ra ngoài, fail-closed nếu secret chưa được thiết lập đúng cho môi trường ngoài development | `Không đề cập` — không tài liệu bàn giao nào mô tả quy trình quản lý secret hay yêu cầu fail-closed khi thiếu cấu hình. | Đọc `config.py`, `compose.yml`, `.env.example`, và `env/.env.local` cùng lúc thì thấy rõ hai secret nhạy cảm nhất (`TOKEN_SECRET` ký HMAC, `EVIDENCE_KEY` mã hóa evidence) bắt buộc phải khác rỗng khi deploy qua Compose nhờ cú pháp `${TOKEN_SECRET:?Set TOKEN_SECRET in .env}` (dòng 40-41 của `compose.yml`) — phần này `Implemented`/`Source-reviewed`. Nhưng `VID_CLIENT_KEY` và `REVIEWER_TOKEN` dùng cú pháp fallback `${VID_CLIENT_KEY:-local-vid-client-key}` (dòng 42-43): không set thì container vẫn khởi động bình thường với giá trị mặc định công khai trong `.env.example`/`config.py`. `env/.env.local` hiện tại xác nhận đúng rủi ro này — `TOKEN_SECRET`/`EVIDENCE_KEY` đã random hóa, còn `VID_CLIENT_KEY` vẫn giữ nguyên `local-vid-client-key`. `Settings.environment` được định nghĩa nhưng không có chỗ nào trong code đọc lại giá trị đó để chặn secret mặc định ngoài development — phần "an toàn ngoài development" vẫn `Designed`/`Doc-only`. |
| C08.3 | Không rò rỉ credential nội bộ qua bundle phía client | `Không đề cập` | `frontend/lib/api.ts:2` đọc `process.env.NEXT_PUBLIC_VID_CLIENT_KEY` — biến `NEXT_PUBLIC_*` trong Next.js luôn bake thẳng vào bundle JavaScript công khai bất kể giá trị. Biến này chưa được set ở đâu cả nên code đang rơi về fallback `"local-vid-client-key"`, chưa rò rỉ thật. `Designed`/`Source-reviewed`. Nhưng đặt tên `NEXT_PUBLIC_` trùng với credential server-side (`VID_CLIENT_KEY` ở `require_vid_client`) là một cái bẫy: nếu sau này ai đó set biến này bằng giá trị thật để "sửa lỗi kết nối", credential đó sẽ bị public vĩnh viễn trong mọi bundle đã build. |
| C08.4 | Logging và giám sát vận hành không lộ PII, có khả năng phát hiện sự cố | `Không đề cập` — tài liệu bàn giao có nhắc "audit của quyết định" như một phần của luồng verification (mục 1.3.3 handover checklist) nhưng không mô tả logging hay monitoring kỹ thuật cụ thể. | Toàn bộ `backend/app/` không import module `logging` ở đâu cả, ngoại trừ một dòng đếm session đã purge trong `purge_worker.py`; `main.py` không có access log, error log, hay log có cấu trúc nào ngoài hành vi mặc định của FastAPI. `Absent` cho giám sát/observability. Nguyên tắc "không ghi PII/token/evidence vào log" ở `AGENTS.md` đúng, nhưng chỉ vì gần như không có gì được log — không có công cụ nào phát hiện bất thường hay điều tra sự cố ngoài readiness endpoint đã chấm ở C06.3 (chỉ trả trạng thái model, không phải log vận hành). |
| C08.5 | Quy trình incident response / change control | `Nêu chưa đầy đủ` — handover checklist liệt kê đầu mối Security và Compliance trong danh sách stakeholder (mục 1.1.2) và có nhắc "defect còn mở/đã đóng" như một phần bàn giao kiểm thử (mục 1.5.1), nhưng không có tài liệu quy trình incident response hay change control nào được đính kèm hay mô tả chi tiết. | Không tìm thấy runbook, quy trình incident response hay change-control gate nào trong repo. Kế hoạch chỉ nhắc "demo runbook hoàn chỉnh" như một next action còn mở của giai đoạn integrated demo hardening — mới ở mức ý định. `Conceptual`/`Doc-only`. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C08.1 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | Xác thực cho cả hai actor có quyền cao đã triển khai và source-reviewed — đơn giản nhưng đúng chức năng. eyePass có thêm bước root-detection cho SDK di động mà V-ID không cần vì không có SDK riêng. |
| C08.2 | `IN_SCOPE` | `GAP` | Đáng lo ngại nhất domain này: `TOKEN_SECRET`/`EVIDENCE_KEY` fail-closed đúng, nhưng `VID_CLIENT_KEY`/`REVIEWER_TOKEN` fallback êm về giá trị mặc định công khai và không có gate nào theo `environment` để chặn việc đó ngoài development. Không tìm thấy quyết định chủ đích nào cho khoảng hở này — rủi ro thật nếu ai đó deploy ngoài máy dev mà quên set hai biến. |
| C08.3 | `IN_SCOPE` | `GAP` | Chưa rò rỉ thật, nhưng thiết kế đặt tên hiện tại là bẫy chờ sẵn cho lần sửa lỗi tiếp theo. Nên đổi tên hoặc bỏ hẳn biến `NEXT_PUBLIC_` này trước khi ai đó "sửa" sai cách. |
| C08.4 | `IN_SCOPE` | `GAP` | Không có access/error logging hay observability nào ngoài readiness endpoint. An toàn PII hiện tại là hệ quả của việc chưa log gì, không phải kiểm soát chủ động — cần thiết kế logging có chủ đích (kèm quy tắc redact) trước khi thêm log thật. |
| C08.5 | `IN_SCOPE` | `GAP` | Chưa có runbook hay quy trình incident/change-control nào, kể cả ở mức thiết kế. Hợp lý cho giai đoạn technical demo hiện tại, nhưng cần trước khi mở rộng ngoài demo nội bộ. |

### 9. Domain C09 — Quality & verification

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C09.1 | Unit/contract test cho lớp abstraction (provider registry, fallback, governance) | `Không đề cập` — không có tài liệu bàn giao nào mô tả test tự động ở tầng kiến trúc/contract; các checklist chỉ kiểm thử hành vi chức năng từ góc nhìn người dùng, không có khái niệm unit/contract test theo nghĩa kỹ thuật phần mềm. | `cd backend && uv run pytest --collect-only -q` liệt kê 13 test cho lớp registry/governance: `test_capability_registry.py` (9 test — config-swap, fallback primary→secondary, all-fail trả `UNAVAILABLE`, circuit breaker, timeout, provider chưa approved bị chặn) và `test_validate_capability_providers.py` (4 test, phân loại lỗi artifact-only vs governance). `Implemented`/`Test-verified` — `uv run pytest -q` xác nhận cả 40 test của suite pass (2026-08-10, tự chạy, không trích tài liệu tiến độ nội bộ). |
| C09.2 | Test cho model/AI pipeline (OCR, MRZ, liveness, face match, anti-spoof) | `Nêu rõ` — Face Matching 1-N checklist ghi kết quả thực tế theo từng kịch bản (Liveness Pass/Fail, Face result), không phải chỉ mô tả kỳ vọng; sheet "Face Management" của Web Console cũng có cột kết quả thực thi (29 pass/16 fail/1 đang xem xét trên 46 case) — đây là quy trình kiểm thử model bằng tay có ghi nhận kết quả, không phải chỉ đặc tả suông. | `test_ai_pipeline.py` có 17 test tự động: check-digit MRZ không lộ nội dung MRZ, readiness theo từng artifact, active-liveness (đủ hai lượt quay và trở về giữa, báo `INCONCLUSIVE` khi bỏ bước), replay heuristic (phát hiện frame trùng lặp, không báo nhầm frame chuyển động), face match (chọn nhiều frame tin cậy cao có giới hạn, dùng median chống một frame lạc quan), cộng các test xác nhận `execution_status`/`review_signal` tách biệt đúng theo từng capability. `Implemented`/`Test-verified`. |
| C09.3 | Test end-to-end cho luồng capture → phân tích → kết quả | `Nêu rõ` — UAT checklist đặc tả cả hai luồng end-to-end đầy đủ ("Full Onboarding" qua QR và "Stay on this device"), mỗi luồng đi từ capture giấy tờ tới OCR result tới selfie tới eKYC result, có cột kết quả mong đợi cho từng bước (Passed/User error/Bad quality). | `test_ekyc_flow.py` có 8 test qua `TestClient`, gồm một luồng đầy đủ QR-claim → capture CCCD → manual review (`test_full_cccd_qr_capture_and_manual_review`), test xác nhận response end-user không lộ danh tính provider/model, test giới hạn passport chỉ một trang TD3, và test khóa loại giấy tờ sau khi đã bắt đầu capture. `Implemented`/`Test-verified`. |
| C09.4 | Formatter/linter/type-checker sạch cho toàn bộ codebase, theo đúng gate mà `PROJECT_ROADMAP.md` (giai đoạn integrated demo hardening) yêu cầu | `Không đề cập` — không có khái niệm formatter/linter/type-checker trong bộ tài liệu bàn giao (đây là công cụ phát triển nội bộ, không phải thứ một gói bàn giao cho khách hàng thường liệt kê). | `cd backend && uv run ruff check .` báo "All checks passed!" và `uv run ruff format --check .` báo 51 file đã đúng định dạng — formatter/linter `Implemented`/`Test-verified`. Nhưng `uv run mypy app ai_modules` trả về 19 lỗi trên 9 file: phần lớn là thiếu type stub cho thư viện ngoài (`vosk`, `onnxruntime`, `syncnet_python`, mức độ thấp), nhưng 6 lỗi nằm ngay trong `app/services/ekyc.py:63,309-321` — đúng vùng code của `purge_due()` mà C07.3 cũng ghi nhận thiếu test — và 3 lỗi khác ở `app/api.py:245,352,463` do cách SQLModel khai báo cột `created_at` mà mypy không suy luận đúng kiểu. Type-checker này `GAP`, không phải mơ hồ hay tùy nghi diễn giải: `PROJECT_ROADMAP.md` (giai đoạn integrated demo hardening) liệt kê "formatter, linter, type checker... pass" là điều kiện hoàn thành rõ ràng, và điều kiện đó hiện chưa đạt. Đáng nói thêm: một bản trước đây của báo cáo này trích số liệu "35 passed" từ tài liệu tự báo cáo — số thật khi tự chạy là 40. |
| C09.5 | CI tự động chạy test/lint/type-check trên mỗi thay đổi | `Không đề cập` — bộ tài liệu bàn giao không mô tả pipeline CI nào (không phải nội dung khách hàng thường nhận trong bàn giao). | Không có thư mục `.github/workflows` hay cấu hình CI nào khác trong repo — `Absent`/`Source-reviewed`. `AGENTS.md` mục "Hoàn thành công việc" yêu cầu chạy formatter/linter/type-checker/test cho mỗi thay đổi, nhưng đó là kỷ luật thao tác thủ công của người/agent đang code, không phải cơ chế tự động trên mỗi commit. |
| C09.6 | Test tự động cho frontend | `Nêu rõ` — Web Console TCs và Web Demo checklist là các bộ test case UI có theo dõi kết quả theo màn hình/chức năng (cột Pass/Fail/Pending/Blocked), dù thực hiện bằng tay. | Không có framework test nào (Jest/Vitest/Playwright/Testing Library) trong `frontend/package.json`, không file nào tên `*.test.*`/`*.spec.*` trong toàn bộ `frontend/` — `Absent`/`Source-reviewed`. Lint và type-check thì sạch (`npm run lint`, `npm run typecheck` không báo lỗi), nhưng đó là kiểm tra tĩnh, không phải test hành vi. |
| C09.7 | Tài liệu acceptance-criteria / kịch bản chấp nhận có cấu trúc, theo dõi được trạng thái pass/fail | `Nêu rõ` — UAT checklist là một artifact acceptance-criteria khá chính quy: phân cấp Category → Function → Sub-function → Item, mỗi dòng có kết quả mong đợi cụ thể, dùng chung cho cả QC lẫn khách hàng ký nhận bàn giao. | Không có artifact acceptance-criteria độc lập. Điều kiện hoàn thành nằm rải rác trong `PROJECT_ROADMAP.md` dưới dạng bullet "Đầu ra và tiêu chí hoàn thành" cho từng giai đoạn — giai đoạn integrated demo hardening làm ví dụ có 10 bullet cụ thể, kiểm chứng được, nhưng không theo khuôn mẫu chuẩn hóa và không có cơ chế theo dõi pass/fail như bảng UAT của eyePass. `Designed`/`Doc-only`. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C09.1 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không có khái niệm unit/contract test ở tầng kiến trúc. Kỷ luật kỹ thuật V-ID tự đặt ra, đã test-verified đầy đủ. |
| C09.2 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass kiểm thử model bằng tay và ghi kết quả; V-ID tự động hóa toàn bộ nhóm này với test đặt tên rõ theo từng hành vi. |
| C09.3 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass đặc tả rõ hai luồng e2e thủ công; V-ID có test tự động cho luồng chính và các nhánh khóa/giới hạn quan trọng. |
| C09.4 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` (formatter/linter) · `GAP` (type-checker) | Đáng lo ngại: formatter/linter sạch, verified trực tiếp, nhưng type-checker có 19 lỗi thật, một phần ngay trong code purge chưa có test (C07.3), và không ai giải thích vì sao mypy chưa sạch — đây là điều kiện của giai đoạn integrated demo hardening nêu rõ nên `GAP` chứ không phải hoãn có chủ đích. Nên xử lý trước "integrated demo hardening". |
| C09.5 | `IN_SCOPE` | `GAP` | Chưa có CI tự động, hiện dựa hoàn toàn vào kỷ luật thủ công. Chấp nhận được ở quy mô solo-dev/technical-demo hiện tại, không gấp, nhưng nên nâng cấp trước khi nhiều người cùng đóng góp code. |
| C09.6 | `IN_SCOPE` | `GAP` | Frontend chưa có test hành vi tự động, dù lint/typecheck sạch. Bề mặt UI còn nhỏ nên rủi ro chưa cao, nhưng nên bổ sung trước khi luồng capture/review phức tạp thêm. |
| C09.7 | `IN_SCOPE` | `KẾ THỪA CÓ CHỌN LỌC` | Cấu trúc UAT checklist của eyePass (phân cấp category/function, cột kết quả mong đợi, theo dõi pass/fail/pending) là một khuôn mẫu đáng tham khảo khi V-ID hình thức hóa acceptance test cho giai đoạn integrated demo hardening — không sao chép nội dung, chỉ tham khảo cấu trúc. |

### 10. Domain C10 — Delivery governance

| ID | Expectation | eyePass — Mức nêu trong đặc tả / Trích dẫn | V-ID-eKYC — Maturity / Confidence / Evidence |
|---|---|---|---|
| C10.1 | Roadmap thực thi có cấu trúc phụ thuộc rõ ràng giữa các milestone (không chỉ một danh sách phẳng) | `Không đề cập` — bộ tài liệu bàn giao là một checklist bàn giao cho sản phẩm đã hoàn thiện, không phải một roadmap thực thi hướng tới tương lai; không có tài liệu nào trong bộ bàn giao trình bày thứ tự phụ thuộc giữa các hạng mục. | `PROJECT_ROADMAP.md` §3 vẽ sơ đồ phụ thuộc tường minh: một hạng mục governance/contract nền tảng làm cơ sở cho cả bước demo di động sẵn sàng lẫn nhánh kiến trúc capability/provider, nhánh đó tiếp tục dẫn tới quality gate, benchmark, threshold, và mở rộng admin/duyệt hồ sơ, cuối cùng là bàn giao demo tích hợp — còn hai workstream (hardening config/secret; dataset license/provenance) chạy song song ngoài chuỗi chính. Mỗi giai đoạn có mục tiêu, đầu ra, tiêu chí hoàn thành viết thành đoạn văn riêng, không chỉ là tên hạng mục. `Implemented`/`Source-reviewed`. |
| C10.2 | Release gate / definition of done cho lần đóng gói demo tiếp theo, gồm nhiều điều kiện cụ thể chứ không phải một dòng mô tả chung | `Nêu chưa đầy đủ` — checklist bàn giao có cột "Trạng thái" theo từng hạng mục (tất cả đang ghi "Đã bàn giao"), nên có tồn tại một hình thức theo dõi hoàn thành, nhưng không có nơi nào gộp các điều kiện đó thành một gate tổng hợp nhiều tiêu chí cho một lần release cụ thể. | Giai đoạn integrated demo hardening trong `PROJECT_ROADMAP.md` liệt kê 8 điều kiện phải đạt đồng thời: chạy end-to-end ba lần liên tiếp trên thiết bị chỉ định, quality gate route đúng mặt lỗi, đổi provider bằng config và chứng minh được fallback, mọi provider lỗi trả `UNAVAILABLE`, benchmark/threshold hiển thị đúng provenance, audit đầy đủ cho thao tác reviewer, test tải/resource/timeout, và formatter/linter/type-checker/test/model-verify/Docker-smoke đều pass trước khi purge dữ liệu rehearsal. Một gate nhiều điều kiện thật, `Implemented`/`Source-reviewed`. |
| C10.3 | Cơ chế theo dõi quyết định còn mở có cấu trúc: định danh riêng, trạng thái, owner đề xuất — không chỉ một danh sách gạch đầu dòng | `Không đề cập` — không có khái niệm "quyết định còn mở" nào xuất hiện trong bộ tài liệu bàn giao; đây là tài liệu bàn giao một sản phẩm đã xong, không phải tài liệu quản lý quyết định đang chờ. | Trước đợt đánh giá này, V-ID đã có thói quen ghi lại quyết định còn mở nhưng rải rác ở hai nơi: `AGENTS.md` mục "Các quyết định còn mở" liệt kê 7 câu hỏi lớn về production (lawful basis, retention, region, KMS, threshold, SLA, quyền thao tác evidence), còn `PROJECT_ROADMAP.md` §7 liệt kê 6 câu hỏi khác thiên về thực thi (nơi lưu benchmark data, target false-recapture rate, quyền reviewer unmask, thời hạn disclosure grant...). Cả hai chỉ là danh sách gạch đầu dòng, không ID, không trạng thái, không owner theo từng mục. `Designed`/`Source-reviewed`. |
| C10.4 | Cơ chế ghi lại quyết định kiến trúc/kỹ thuật đã chốt (ADR hoặc tương đương), tách biệt với danh sách quyết định còn mở | `Không đề cập` — không có định dạng ADR hay tương đương nào trong bộ tài liệu bàn giao. | `M0_CONTRACT_GOVERNANCE_BASELINE.md` §5 có bốn ADR đã chốt: ADR-M0-001 (capability provider và composition root), ADR-M0-002 (fallback có giới hạn và fail-closed), ADR-M0-003 (controlled disclosure), ADR-M0-004 (threshold lifecycle). Một cơ chế ghi quyết định-đã-chốt thật, khác với danh sách quyết định-còn-mở ở C10.3. `Implemented`/`Source-reviewed`. |
| C10.5 | Mô hình phân công owner/stakeholder theo vai trò (PO, tech lead, security, compliance...), không chỉ một người ra quyết định | `Nêu rõ` — checklist bàn giao mục 1.1.2 liệt kê cụ thể từng vai trò và đầu mối liên hệ: PO, BA, Tech Lead, AI Lead (VinBigData), DevOps, Security, Data Owner, Compliance và đầu mối PnL liên quan, kèm tên/email liên hệ thật cho một số vai trò. | `M0_CONTRACT_GOVERNANCE_BASELINE.md` và `AGENTS.md` chỉ nói "người dùng là owner quyết định cuối cùng" cho mọi milestone và mọi quyết định còn mở — không phân vai trò theo chức năng, không ai được gán riêng cho security/compliance/AI. `Conceptual`/`Source-reviewed`. |

#### Status và nhận định

| ID | Status (V-ID) | Nhận định | Ghi chú |
|---|---|---|---|
| C10.1 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass bàn giao sản phẩm đã xong nên không có roadmap thực thi hướng tới tương lai — hai loại tài liệu khác nhau, không phải khoảng trống của eyePass. Sơ đồ phụ thuộc của V-ID là năng lực tự có, đã đọc trực tiếp và xác nhận tồn tại. |
| C10.2 | `IN_SCOPE` | `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass theo dõi hoàn thành theo từng hạng mục nhưng không gộp thành gate nhiều điều kiện; V-ID có gate bàn giao demo tích hợp tám điều kiện, đã xác nhận nội dung. |
| C10.3 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không có khái niệm quyết định còn mở. V-ID đã ghi nhận nhưng rải rác, không ID/trạng thái/owner theo từng mục — đáng gộp `AGENTS.md` và `PROJECT_ROADMAP.md` §7 vào một nơi duy nhất, nhưng không cấp bách ở quy mô hiện tại. |
| C10.4 | `IN_SCOPE` | `NGOÀI YÊU CẦU EYEPASS` | eyePass không có định dạng ghi quyết định đã chốt. Bốn ADR của V-ID là cơ chế thật, đã xác nhận nội dung. |
| C10.5 | `IN_SCOPE` | `GAP` | eyePass có bản đồ vai trò/đầu mối liên hệ cụ thể; V-ID hiện chỉ có một owner chung cho mọi quyết định. Hợp lý ở quy mô một người/đội nhỏ làm technical demo, nhưng không có ghi chú quản trị nào chủ động hoãn việc này nên xếp `GAP` chứ không phải hoãn có chủ đích — cần xử lý trước khi mở rộng đội hoặc chuyển sang pilot nhiều bên liên quan hơn. |

Không có gì đáng lo ngại trong domain này. Đáng nói minh bạch: repo hiện không có `CODEOWNERS`, không template PR/issue, không cấu hình CI — nhưng phần đó thuộc phạm vi C08 (đã xử lý ở đó) nên không lặp lại. Lịch sử `git log` cho thấy commit message không theo quy ước cố định, phù hợp giai đoạn technical demo một người làm chính, không phải phát hiện bất ngờ.
