# Phụ lục — Định nghĩa và nguyên tắc đọc bảng đối chiếu V-ID-eKYC với eyePass

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 2.0 |
| Cập nhật | 2026-08-09 |
| Đi kèm | [`EKYC_COMPARATIVE_ASSESSMENT_RUBRIC.md`](./EKYC_COMPARATIVE_ASSESSMENT_RUBRIC.md) phiên bản 3.0 (V-ID chấm trên trục maturity từ ngữ thuần + confidence; eyePass chấm trên trục riêng "mức độ nêu trong đặc tả", không dùng chung thang với V-ID). Nếu rubric thay đổi version mà tài liệu này chưa được cập nhật theo, rubric là nguồn áp dụng. |
| Mục đích | Định nghĩa thống nhất các thuật ngữ và nguyên tắc đọc dùng trong ma trận đối chiếu, nhằm giảm sai lệch khi các bên liên quan diễn giải kết quả đánh giá. |
| Áp dụng cho | Mọi bên đọc `assessment/eKYC_Assessment_Report.md` (đặc biệt Phần D — Gap & Traceability Matrix) hoặc bất kỳ deliverable nào trích dẫn kết quả từ rubric. |

## 1. Mục đích và phạm vi

Tài liệu này quy định cách đọc và diễn giải các ký hiệu trong ma trận đối chiếu
V-ID-eKYC với eyePass. Đây **không phải** một ma trận so sánh ngang hàng hai hệ
thống: V-ID-eKYC là đối tượng duy nhất được chấm maturity, eyePass chỉ đóng vai
trò nguồn yêu cầu/đặc tả tham chiếu (baseline §1). eyePass là sản phẩm đã được
xây dựng và vận hành trước đây, nhưng người đánh giá chỉ tiếp cận được tài liệu
bàn giao, không có source/test/runtime — nên eyePass **không có cột maturity
hay confidence riêng**; nó chỉ được ghi nhận theo mức độ đặc tả nêu rõ yêu cầu
tới đâu (§3b), luôn ngầm định confidence `Doc-only`.

Đây không phải là tài liệu thay thế rubric chấm điểm — mọi định nghĩa kỹ thuật
chi tiết, công thức và tiêu chí nguyên tử vẫn lấy rubric làm nguồn chính thức.
Tài liệu này chỉ đảm bảo mọi người đọc kết quả theo cùng một cách hiểu, tránh
việc mỗi người tự suy diễn ý nghĩa của một ký hiệu — đặc biệt tránh đọc bảng này
như một xếp hạng "hệ thống nào tốt hơn".

## 2. Nguyên tắc đọc

1. Mỗi tiêu chí V-ID được đánh giá theo **hai trục độc lập**: mức độ năng lực đã
   đạt được (`maturity`, §3) và mức độ tin cậy của bằng chứng dùng để đánh giá
   (`confidence`, §4). Hai trục này không được gộp hoặc quy đổi thành một chỉ số
   duy nhất, và **không có mã chữ+số** (không dùng `L0`–`L4`) để tránh bị đọc
   như một điểm số định lượng trên thang 0–4.
2. eyePass **không được chấm trên trục maturity/confidence** của V-ID. eyePass
   chỉ có một trục riêng: mức độ đặc tả nêu rõ yêu cầu (§3b) — `Không đề cập` /
   `Nêu chưa đầy đủ` / `Nêu rõ`. Không đọc trục này như một "maturity thấp" của
   eyePass; nó chỉ mô tả độ rõ của tài liệu, không mô tả năng lực thực tế của
   eyePass (mà chúng ta không có cách kiểm chứng).
3. Mức `confidence` thấp không đồng nghĩa với `maturity` thấp. Đây là hai đại
   lượng đo hai việc khác nhau: một việc đo năng lực thực tế của V-ID, một việc
   đo khả năng của người đánh giá trong việc kiểm chứng năng lực đó.
4. Trạng thái "chủ động chưa quyết định" (`DEFERRED_BY_DESIGN`) và "thiếu sót
   chưa có lý do" (`GAP`) phải được phân biệt rõ ràng trong mọi báo cáo tổng
   hợp, không được cộng gộp thành một con số.
5. Không được kết luận "V-ID tốt hơn/kém eyePass" ở cấp hệ thống. Kết luận chỉ
   hợp lệ ở cấp từng yêu cầu: eyePass nêu yêu cầu rõ tới đâu (§3b), V-ID đạt
   `maturity`/`confidence` nào cho yêu cầu đó (§3, §4), và giới hạn evidence đi
   kèm.
6. Không có domain score hay điểm tổng hợp nào để quy đổi — mỗi tiêu chí đứng
   độc lập. Một tiêu chí ở mức `Absent`/`GAP` với ưu tiên `P0` không được xem là
   đã được xử lý chỉ vì các tiêu chí khác trong cùng domain đạt `maturity` cao.

## 3. Capability maturity (chỉ áp dụng cho V-ID)

| Từ ngữ | Định nghĩa |
|---|---|
| `Absent` | Năng lực chưa tồn tại, chưa được đề cập trong bất kỳ tài liệu hay source nào của V-ID. |
| `Conceptual` | Năng lực mới ở mức ý định hoặc mục tiêu, chưa có thiết kế cụ thể. |
| `Designed` | Đã có thiết kế, contract, sơ đồ hoặc acceptance criteria rõ ràng, chưa triển khai. |
| `Implemented` | Đã triển khai; source/config/API hiện thực hóa đúng thiết kế đã nêu. |
| `Hardened` | Đã triển khai và đã được kiểm chứng qua test hoặc dữ liệu vận hành, bao gồm các trường hợp lỗi. |

**Ví dụ minh họa:** Yêu cầu về webhook của V-ID (chữ ký số, chống replay, retry)
hiện chỉ có một điều kiện kiểm tra URL nằm trong danh sách cho phép; chưa có cơ
chế ký, gửi lại hoặc xử lý trùng lặp. Năng lực này được ghi nhận ở mức
`Conceptual`: tồn tại dưới dạng một trường dữ liệu trong schema, tương đương một
ý định, chưa có phần triển khai thực tế tương ứng.

## 3b. Mức độ nêu trong đặc tả (chỉ áp dụng cho eyePass)

Trục này **thay thế hoàn toàn** việc chấm maturity cho eyePass — nó không đo
"eyePass làm tốt tới đâu" (không kiểm chứng được), chỉ đo đặc tả bàn giao nêu
yêu cầu rõ tới đâu.

| Từ ngữ | Định nghĩa |
|---|---|
| `Không đề cập` | Tài liệu bàn giao (BRD, flow/rule workbook, API/SDK doc, checklist) không đề cập tới yêu cầu này. |
| `Nêu chưa đầy đủ` | Có đề cập nhưng thiếu chi tiết, mơ hồ, hoặc chỉ có một phần. |
| `Nêu rõ` | Yêu cầu được đặc tả cụ thể, trích dẫn được trực tiếp section/sheet/cell. |

**Ví dụ minh họa:** Business rules của eyePass ghi ngưỡng face-match `< 0.8`
nhưng không mô tả quy trình version/approval khi đổi ngưỡng. Đây là `Nêu chưa
đầy đủ`, không phải `Nêu rõ` — có giá trị số nhưng thiếu governance đi kèm.

## 4. Evidence confidence (chỉ áp dụng cho V-ID)

| Ký hiệu | Định nghĩa |
|---|---|
| `Doc-only` | Chỉ có tài liệu mô tả, không có quyền truy cập source hoặc test. |
| `Self-reported` | Nhận định do owner/team tự đưa ra, không kèm artifact kiểm chứng. |
| `Source-reviewed` | Đã đọc trực tiếp source/config liên quan. |
| `Test-verified` | Có test, run output hoặc kết quả review có thể truy vết. |

eyePass không có cột confidence riêng: mọi trích dẫn eyePass mặc định
`Doc-only` cố định, vì người đánh giá không có quyền truy cập source code của
hệ thống đó (§3b). Đây là giới hạn về khả năng kiểm chứng của người đánh giá,
không phải đánh giá về chất lượng thực tế của eyePass.

## 5. Trạng thái áp dụng

Mô tả **lập trường của V-ID** với một yêu cầu, dù yêu cầu đó rút ra từ đặc tả
eyePass hay từ nguồn khác.

| Ký hiệu | Điều kiện áp dụng |
|---|---|
| `IN_SCOPE` | Yêu cầu nằm trong phạm vi V-ID cần đáp ứng ở giai đoạn hiện tại. |
| `OUT_OF_SCOPE` | V-ID không cần năng lực này ở giai đoạn hiện tại, bất kể eyePass có nêu hay không. |
| `DEFERRED_BY_DESIGN` | V-ID chủ động chưa quyết định hoặc chưa triển khai, có lý do và owner được ghi nhận. |
| `GAP` | Năng lực cần thiết trong phạm vi nhưng V-ID chưa có evidence ở mức mong đợi, không có lý do chủ đích nào được ghi nhận. |

`DEFERRED_BY_DESIGN` và `GAP` là hai trạng thái khác biệt về bản chất và không
được gộp chung khi tổng hợp. Ví dụ: việc V-ID chưa phê duyệt ngưỡng (threshold)
production là một quyết định có chủ đích, được ghi nhận trong tài liệu quản trị
nội bộ của dự án — xếp loại `DEFERRED_BY_DESIGN`. Ngược lại, việc phân quyền cho
các thao tác xem/tải/xóa dữ liệu gốc chưa được thiết kế chi tiết theo từng vai
trò, và không có lý do chủ đích nào được ghi nhận cho việc này — xếp loại `GAP`.

## 6. Nhận định kết luận

Mọi nhãn dưới đây có chủ ngữ là **V-ID**, đối chiếu với yêu cầu rút ra từ đặc tả
eyePass. Không có nhãn nào chấm điểm ngược lại cho eyePass.

| Ký hiệu | Điều kiện |
|---|---|
| `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC` | eyePass `Nêu rõ`/`Nêu chưa đầy đủ`; V-ID đạt `Implemented`/`Hardened`, confidence `Source-reviewed`/`Test-verified`. |
| `ĐÃ ĐÁP ỨNG — THEO THIẾT KẾ` | eyePass `Nêu rõ`/`Nêu chưa đầy đủ`; V-ID đạt `Designed` trở lên nhưng confidence chỉ `Doc-only`/`Self-reported`, hoặc maturity mới dừng ở `Designed`. |
| `NGOÀI YÊU CẦU EYEPASS` | eyePass `Không đề cập`; V-ID vẫn có năng lực này ở mức `Designed` trở lên. Không viết "cải tiến so với eyePass" — eyePass không nêu yêu cầu này nên không có gì để cải tiến; chỉ ghi nhận evidence và lý do V-ID cần năng lực này. |
| `KẾ THỪA CÓ CHỌN LỌC` | eyePass có rule hoặc kinh nghiệm vận hành hữu ích, cần rà soát trước khi áp dụng cho V-ID, không sao chép trực tiếp. |
| `GAP` | Xem mục 5. |
| `DEFERRED_BY_DESIGN` | Xem mục 5. |
| `KHÔNG KẾ THỪA` | Cách tiếp cận mô tả trong đặc tả eyePass không phù hợp với nguyên tắc hoặc phạm vi của V-ID — V-ID chủ động không theo. |
| `OUT_OF_SCOPE` | Xem mục 5. |
| `CHƯA KẾT LUẬN` | Evidence về V-ID mâu thuẫn nhau; cần owner xác nhận trước khi kết luận. |

## 7. Domain đánh giá (C01–C10)

| Mã | Phạm vi |
|---|---|
| C01 | Luồng thao tác của người dùng từ khởi tạo đến hoàn tất, bao gồm xử lý lỗi và thử lại. |
| C02 | Đọc và xác thực giấy tờ tùy thân (CCCD, hộ chiếu...). |
| C03 | Nhận diện khuôn mặt và phát hiện giả mạo (ảnh tĩnh, video, giọng nói). |
| C04 | Cơ chế ra quyết định cuối cùng và vai trò của xét duyệt thủ công. |
| C05 | Giao tiếp với hệ thống bên ngoài qua API, polling hoặc webhook. |
| C06 | Quản trị model AI: nguồn gốc, quyền sử dụng, khả năng chạy offline. |
| C07 | Xử lý, lưu trữ và xóa dữ liệu nhạy cảm. |
| C08 | Bảo mật vận hành: phân quyền, ghi log, phát hiện sự cố. |
| C09 | Mức độ kiểm thử và độ tin cậy vào tính đúng đắn của hệ thống. |
| C10 | Quản trị tiến độ, quyết định còn mở và phân công trách nhiệm. |

## 8. Diễn giải các điểm thường bị hiểu sai

**Đây có phải một so sánh ngang hàng giữa hai hệ thống không?**
Không. eyePass đã được xây dựng và vận hành trước đây, nhưng đội đánh giá chỉ có
tài liệu bàn giao, không có source/test/runtime access — và V-ID-eKYC hiện mới ở
giai đoạn technical demo, chưa MVP feature-complete. Cộng hai giới hạn này lại,
một bảng "điểm ngang hàng" sẽ đánh lừa người đọc theo cả hai chiều: phạt eyePass
vì chúng ta không kiểm chứng được, và phạt/khen V-ID như thể nó đã là sản phẩm
hoàn thiện. Vì vậy tài liệu này dùng eyePass làm **nguồn yêu cầu tham chiếu** để
tạo checklist, và chấm V-ID theo checklist đó — không chấm điểm ngược lại cho
eyePass so với V-ID (baseline §1, rubric §9).

**Vì sao trục maturity không còn dùng ký hiệu `L0`–`L4`?**
Một mã chữ+số đọc như một điểm số trên thang định lượng, mời người đọc so sánh
trực tiếp (`L3` so với `L1`) mà bỏ qua caveat confidence đứng cạnh nó. Ví dụ cụ
thể từng gây hiểu lầm: một dòng ghi eyePass `L1` khiến người đọc nghĩ "eyePass
yếu ở đây", trong khi `L1` đó chỉ phản ánh eyePass được ghi nhận theo thang cũ
dùng chung với V-ID, chứ không mô tả năng lực thực tế của eyePass — vốn không
kiểm chứng được. Từ rubric v3.0, maturity chỉ dùng từ ngữ thuần cho V-ID
(`Absent`/`Conceptual`/`Designed`/`Implemented`/`Hardened`), và eyePass chuyển
hẳn sang trục khác (`Không đề cập`/`Nêu chưa đầy đủ`/`Nêu rõ`, §3b) để không
còn nằm chung thang với V-ID.

**Vì sao eyePass — một sản phẩm đã từng vận hành thực tế — không được chấm
maturity như trước?**
Vì maturity đo năng lực *thực tế* của một hệ thống, và điều đó chỉ kiểm chứng
được qua source/test/runtime — thứ chúng ta không có cho eyePass. Gán một mức
maturity cho eyePass dựa trên tài liệu bàn giao luôn là suy diễn, dù có ghi kèm
confidence `Doc-only` hay không, vì bản thân con số/chữ đó đã ngụ ý một phép đo
năng lực. Trục `Nêu rõ`/`Nêu chưa đầy đủ`/`Không đề cập` (§3b) tránh ngụ ý đó:
nó chỉ mô tả tài liệu, không mô tả hệ thống.

**V-ID để một mục ở trạng thái `TBD`/`DEFERRED_BY_DESIGN` có được xem là điểm
yếu không?**
Không mặc định như vậy. Khi có lý do được ghi nhận (ai quyết định, thời điểm
quyết định), đây được xem là kỷ luật quản trị phù hợp, không phải một thiếu sót.
Chỉ khi không có lý do chủ đích nào được ghi nhận, tiêu chí đó mới được xếp loại
`GAP`.

**Ai là người xác nhận mức ưu tiên `P0`/`P1`/`P2`?**
Người đánh giá đề xuất mức ưu tiên dựa trên rủi ro quan sát được, nhưng owner dự
án là người xác nhận cuối cùng, đặc biệt đối với mọi mục ở mức `P0`.

**Vì sao không tổng hợp thành một điểm số duy nhất cho toàn hệ thống?**
Một chỉ số tổng hợp duy nhất sẽ xóa bỏ sự khác biệt giữa "chưa kiểm chứng được",
"chủ động chưa triển khai" và "thực sự thiếu sót" — ba trạng thái có ý nghĩa
khác nhau nhưng sẽ trở nên không thể phân biệt nếu quy về cùng một con số. Cấu
trúc ma trận giữ các cột tách biệt để không làm mất thông tin này.

## 9. Ví dụ minh họa cách đọc một dòng

Ví dụ dưới đây trích tiêu chí C04.1 từ
[`eKYC_Assessment_Report.md`](./assessment/eKYC_Assessment_Report.md), Phần D
(Gap & Traceability Matrix) §5 — Domain C04, viết lại theo mô hình hai thang
tách biệt hiện tại (rubric v3.0).

> **C04.1** — Kết quả phân tích, tín hiệu dành cho người duyệt và quyết định
> cuối cùng phải được tách biệt, không gộp làm một.
>
> - eyePass: `Nêu chưa đầy đủ` — tài liệu API cho thấy hệ thống trả về một mã
>   duy nhất đóng vai trò vừa là kết quả xử lý vừa là quyết định, không có sự
>   tách biệt như yêu cầu; đặc tả không tự nhận đây là một thiếu sót cần sửa.
> - V-ID: maturity `Hardened`, confidence `Test-verified` — source code tách
>   riêng rõ ràng ba thành phần này, và có test tự động kiểm chứng.
> - Nhận định: `ĐÃ ĐÁP ỨNG — KIỂM CHỨNG ĐƯỢC`.

Thứ tự đọc: **mức nêu trong đặc tả eyePass trước, rồi maturity + confidence của
V-ID, rồi nhận định sau cùng.** Không đọc trực tiếp vào cột nhận định mà bỏ qua
các trục nền tảng phía trước.
