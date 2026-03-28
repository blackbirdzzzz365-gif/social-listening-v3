# User Stories — AI Facebook Social Listening & Engagement

**Product:** AI-powered Facebook research & engagement tool
**Account type:** Personal Facebook account (non-business)
**Primary users:** Researcher, Marketer, Sales/BD person
**Created:** 2026-03-28

---

## Story Map (User Journey)

```
PLAN                  →   CRAWL & LISTEN       →   ENGAGE             →   SELL
──────────────────────────────────────────────────────────────────────────────────
US-01 Input topic         US-04 Insight từ feed   US-06 Tạo bài post    US-08a Tạo sales post
US-02 AI research plan    US-05 Insight từ        US-07 Bình luận        US-08b Follow-up lead
US-03a Approve plan             comment                  giải thích      US-08c Sales dashboard
US-03b Monitor execution
```

---

## Recommended Sprint Breakdown

| Sprint | Stories | Focus |
|--------|---------|-------|
| **Sprint 1 (MVP Core)** | US-01, US-02, US-03a, US-03b | AI planning loop — nền tảng cho toàn bộ product |
| **Sprint 2 (Listen)** | US-04, US-05 | Crawl & phân tích insight |
| **Sprint 3 (Engage)** | US-06, US-07 | Tạo nội dung & tương tác |
| **Sprint 4 (Convert)** | US-08a, US-08b, US-08c | Sales workflow (3 stories độc lập) |

---

## User Stories

---

### US-01: Nhập topic và AI phân tích keyword

**As a** researcher
**I want to** nhập một topic hoặc câu hỏi nghiên cứu bằng ngôn ngữ tự nhiên
**So that** AI tự động phân tích và đề xuất danh sách từ khoá và góc độ nghiên cứu phù hợp

**Acceptance Criteria:**

- Given tôi mở app và chưa có research nào đang chạy
  When tôi nhập một topic (ví dụ: "khách hàng nghĩ gì về TPBank EVO")
  Then AI trả về danh sách từ khoá gợi ý (tối thiểu 10 từ khoá), phân loại theo nhóm (thương hiệu, cảm xúc, hành vi, so sánh)

- Given AI đã trả về danh sách từ khoá
  When tôi muốn điều chỉnh
  Then tôi có thể thêm, xoá hoặc sửa từng từ khoá trước khi xác nhận

- Given tôi nhập topic không rõ ràng hoặc quá rộng (ví dụ: "tài chính")
  When AI xử lý
  Then AI hỏi clarifying question để thu hẹp phạm vi (ví dụ: "Bạn muốn nghiên cứu sản phẩm cụ thể nào? Đối tượng khách hàng nào?")

- Given tôi nhập topic bằng tiếng Việt
  When AI phân tích
  Then từ khoá gợi ý phải bao gồm cả biến thể tiếng Việt có dấu và không dấu, tiếng lóng phổ biến

**Out of scope:** Tự động chạy crawl ngay khi submit topic (xem US-03)

**Dependencies:** None

**Notes:** AI backbone dùng Claude API. Cần support cả input tiếng Việt và tiếng Anh. Từ khoá output cần có thể export để dùng lại.

---

### US-02: AI tạo research plan

**As a** researcher
**I want to** nhận một research plan chi tiết từ AI sau khi đã xác nhận từ khoá
**So that** tôi biết chính xác AI sẽ làm gì, ở đâu, và trong bao lâu trước khi cho phép chạy

**Acceptance Criteria:**

- Given tôi đã xác nhận danh sách từ khoá (US-01)
  When AI tạo plan
  Then plan phải liệt kê rõ: (1) danh sách action sẽ thực hiện, (2) nhóm/trang Facebook cụ thể sẽ crawl, (3) số lượng post/comment dự kiến, (4) thứ tự thực hiện

- Given AI tạo xong plan
  When tôi đọc plan
  Then mỗi bước trong plan phải có trạng thái ước lượng (ví dụ: "~50 bài đăng", "~200 comment") để tôi đánh giá scope

- Given plan đã được hiển thị
  When tôi muốn điều chỉnh
  Then tôi có thể yêu cầu AI thu hẹp hoặc mở rộng scope bằng ngôn ngữ tự nhiên (ví dụ: "Bỏ bước join group, chỉ search keyword thôi")

- Given AI không tìm được group/page phù hợp với topic
  When tạo plan
  Then AI cảnh báo và đề xuất hướng tiếp cận thay thế thay vì tạo plan rỗng

**Out of scope:** Tự động execute plan (xem US-03); lưu plan vào database (sprint sau)

**Dependencies:** US-01

**Notes:** Plan format nên có thể render dạng checklist. Cân nhắc hiển thị estimated time và risk level cho mỗi bước (ví dụ: "bước này có thể bị Facebook giới hạn tốc độ").

---

### US-03a: User xem và duyệt plan trước khi chạy

> **Tại sao split khỏi US-03b?** Approve plan là một _decision point_ — user cần đọc, chỉnh sửa, và ra quyết định. Đây là UX riêng biệt với việc theo dõi tiến trình. Hai việc này có thể xảy ra ở hai màn hình khác nhau và có thể dev/test độc lập.

**As a** researcher
**I want to** xem lại plan chi tiết và chọn approve toàn bộ hoặc từng bước riêng lẻ
**So that** tôi hiểu rõ AI sẽ làm gì trên account Facebook của mình trước khi cho phép bất kỳ action nào chạy

**Acceptance Criteria:**

- Given plan đã được AI tạo (US-02)
  When tôi mở màn hình Review Plan
  Then plan hiển thị dạng checklist với từng bước: tên action, mô tả ngắn, loại action (read-only hay write), và ước tính số lượng

- Given tôi đọc plan và muốn bỏ một số bước
  When tôi uncheck các bước không muốn chạy
  Then chỉ những bước được check mới được đưa vào execution queue; dependencies bị ảnh hưởng phải được AI cảnh báo (ví dụ: "Bỏ bước search sẽ khiến bước classify không có data")

- Given plan có chứa action write (đăng bài, comment, join group)
  When hiển thị plan
  Then các bước write phải được đánh dấu badge "Write Action" màu vàng để phân biệt với read-only steps

- Given tôi click "Approve & Run"
  When không có bước nào được check
  Then button bị disable và hiển thị tooltip "Chọn ít nhất một bước để chạy"

- Given tôi click "Approve & Run" với ít nhất một bước được chọn
  When confirm
  Then app chuyển sang màn hình Monitor (US-03b) và bắt đầu thực thi

- Given tôi muốn quay lại chỉnh sửa plan
  When click "Edit Plan"
  Then trở về US-02 với plan hiện tại, không mất các thay đổi đã chỉnh

**Out of scope:** Chạy plan và theo dõi tiến trình (US-03b); lưu plan để dùng lại sau; schedule chạy định kỳ

**Dependencies:** US-01, US-02

**Notes:** Màn hình này là **safety gate** quan trọng nhất của app. Write actions phải được làm nổi bật rõ ràng. Không có nút "Approve All without review" — user phải scroll qua toàn bộ plan.

---

### US-03b: Monitor tiến trình thực thi plan

> **Tại sao split khỏi US-03a?** Monitor execution là _async real-time tracking_ — UI polling, error recovery, pause/resume. Đây là technical complexity riêng, có thể phát triển độc lập sau khi US-03a xong. QA cũng test hai luồng này riêng biệt.

**As a** researcher
**I want to** theo dõi tiến trình plan đang chạy theo thời gian thực và can thiệp khi cần
**So that** tôi biết chính xác chuyện gì đang xảy ra và có thể dừng nếu có vấn đề

**Acceptance Criteria:**

- Given plan đã được approve (US-03a) và bắt đầu chạy
  When tôi ở màn hình Monitor
  Then thấy danh sách các bước với trạng thái: Pending / Running / Done / Failed / Skipped — cập nhật realtime

- Given một bước đang chạy
  When bước đó hoàn thành
  Then trạng thái chuyển sang "Done" kèm số liệu thực tế (ví dụ: "Crawled 47 posts") và tự động bắt đầu bước tiếp theo

- Given plan đang chạy
  When tôi click "Pause"
  Then AI hoàn thành action hiện tại (không cắt ngang giữa chừng), sau đó dừng và chờ; button đổi thành "Resume"

- Given plan đang bị pause
  When tôi click "Resume"
  Then plan tiếp tục từ bước đang dở (không chạy lại bước đã Done)

- Given một bước thất bại (ví dụ: Facebook trả 429 Too Many Requests)
  When AI phát hiện lỗi
  Then bước đó đánh dấu "Failed" + hiển thị error message cụ thể + hỏi user: [Retry] [Skip] [Stop All]

- Given plan chạy xong toàn bộ
  When tất cả bước hoàn thành
  Then hiển thị Execution Summary: tổng bước chạy, số Done/Failed/Skipped, tổng số posts crawled, thời gian chạy; kèm nút "View Insights" dẫn sang US-04

- Given app bị đóng hoặc mất kết nối trong khi plan đang chạy
  When mở lại app
  Then hiển thị thông báo "Plan bị gián đoạn" với trạng thái cuối cùng đã lưu, hỏi user muốn tiếp tục hay huỷ

**Out of scope:** Tự động retry không giới hạn; chạy nhiều plan song song; notifications qua email/Slack

**Dependencies:** US-03a

**Notes:** Mỗi action phải ghi audit log với timestamp, action type, và result. Log cần export được để debug. Nếu phát hiện CAPTCHA từ Facebook, dừng toàn bộ plan ngay và alert user — không retry tự động.

---

### US-04: Phân tích insight từ bài đăng Facebook

**As a** researcher
**I want to** AI tự động đọc, phân loại và tóm tắt insight từ các bài đăng trong Facebook groups
**So that** tôi hiểu được xu hướng, cảm xúc và vấn đề phổ biến của khách hàng mà không cần đọc thủ công

**Acceptance Criteria:**

- Given AI đã crawl xong một batch bài đăng
  When chạy phân tích
  Then mỗi bài được gán: chủ đề (theme), cảm xúc (sentiment: tích cực/tiêu cực/trung tính), và relevance score (0-1)

- Given tôi xem kết quả phân tích
  When lọc theo theme hoặc sentiment
  Then danh sách bài đăng cập nhật realtime theo filter đã chọn

- Given AI phân tích xong toàn bộ batch
  When tôi xem summary
  Then AI hiển thị: top 5 chủ đề phổ biến nhất, tỉ lệ sentiment, và 3-5 insight nổi bật kèm trích dẫn nguyên văn từ bài đăng

- Given có bài đăng là spam hoặc của sales agent
  When AI phân loại
  Then bài đó bị đánh dấu "excluded" và không tính vào insight summary (có thể xem lại trong tab "Excluded")

- Given tôi muốn export kết quả
  When click Export
  Then file CSV được tải về với columns: post_url, author, theme, sentiment, key_quote, date

**Out of scope:** Phân tích insight từ comment (xem US-05); real-time streaming crawl

**Dependencies:** US-03

**Notes:** Theme taxonomy nên configurable — user có thể thêm/sửa category. Cần xử lý tiếng Việt không dấu và tiếng lóng tài chính.

---

### US-05: Đọc comment để lấy insight

**As a** researcher
**I want to** AI đọc và phân tích comment trong các bài đăng liên quan
**So that** tôi lấy được insight chi tiết hơn từ phần thảo luận, không chỉ từ nội dung bài gốc

**Acceptance Criteria:**

- Given tôi chọn một bài đăng từ kết quả phân tích (US-04)
  When click "Analyze Comments"
  Then AI crawl toàn bộ comment (bao gồm nested reply) và phân tích sentiment + theme từng comment

- Given AI phân tích xong comment của một bài
  When tôi xem kết quả
  Then AI highlight comment nổi bật nhất (highest insight value) và nhóm các comment tương đồng lại

- Given tôi muốn phân tích comment trên nhiều bài cùng lúc (batch)
  When chọn nhiều bài và click "Batch Analyze Comments"
  Then AI xử lý lần lượt và hiển thị progress, kết quả tổng hợp sau khi xong

- Given một bài đăng có hơn 500 comment
  When AI crawl
  Then AI cảnh báo về thời gian ước tính và hỏi user muốn giới hạn số comment hay crawl hết

- Given comment có chứa thông tin nhạy cảm (số điện thoại, CCCD)
  When AI xử lý
  Then thông tin đó tự động bị mask trong output (hiển thị dạng `***`)

**Out of scope:** Reply trực tiếp vào comment từ màn hình này (xem US-07)

**Dependencies:** US-04

**Notes:** Facebook giới hạn load comment — cần implement scroll-to-load-more logic. Comment từ admin/page owner nên được đánh dấu riêng.

---

### US-06: Tạo bài viết trong group theo chủ đề

**As a** marketer
**I want to** AI soạn sẵn nội dung bài đăng phù hợp với từng group Facebook
**So that** tôi đăng bài chất lượng nhanh hơn mà vẫn phù hợp với tone và quy định của từng group

**Acceptance Criteria:**

- Given tôi chọn một group và nhập chủ đề muốn đăng
  When click "Generate Post"
  Then AI tạo ra 3 phiên bản nội dung bài đăng khác nhau (formal, casual, storytelling) để tôi chọn

- Given AI tạo xong nội dung
  When tôi xem preview
  Then preview hiển thị đúng format sẽ thấy trên Facebook (xuống dòng, emoji, hashtag)

- Given tôi chỉnh sửa nội dung
  When submit bài
  Then AI hỏi xác nhận một lần nữa với nội dung cuối cùng trước khi thực sự đăng lên Facebook

- Given bài đăng đã được đăng thành công
  When kiểm tra
  Then app lưu lại: group_id, post_url, nội dung, thời gian đăng, và trạng thái (posted/failed)

- Given group có quy định về nội dung (ví dụ: không được quảng cáo)
  When AI soạn bài
  Then AI nhắc nhở user về risk và điều chỉnh nội dung để giảm khả năng bị admin xoá

- Given Facebook từ chối đăng bài (spam filter hoặc group không cho phép)
  When xảy ra lỗi
  Then app thông báo lỗi cụ thể và không retry tự động

**Out of scope:** Schedule đăng bài theo lịch; đăng lên Page (chỉ dành cho Group); auto-repost

**Dependencies:** US-03 (session đã đăng nhập)

**Notes:** Tần suất đăng nên có rate limit do user cấu hình (ví dụ: không quá 3 bài/ngày/group) để tránh bị Facebook hạn chế account. Không dùng tài khoản Business — cần mô phỏng hành vi người dùng thường.

---

### US-07: Bình luận để giải thích hoặc tương tác

**As a** marketer hoặc support person
**I want to** AI đề xuất nội dung comment phù hợp cho từng bài đăng cụ thể
**So that** tôi tương tác tự nhiên với cộng đồng mà không mất nhiều thời gian viết từng comment

**Acceptance Criteria:**

- Given tôi chọn một bài đăng và muốn comment
  When click "Suggest Comment"
  Then AI đọc nội dung bài + thread comment hiện có và đề xuất 2-3 phiên bản comment phù hợp context

- Given AI đề xuất comment
  When tôi chọn một phiên bản
  Then tôi có thể chỉnh sửa trước khi submit; không thể submit mà không đọc qua

- Given tôi submit comment
  When AI đăng lên Facebook
  Then comment xuất hiện trên bài đăng gốc và app lưu log: bài đăng nào, comment gì, lúc mấy giờ

- Given bài đăng là của người đang than phiền về sản phẩm
  When AI đề xuất comment
  Then AI ưu tiên tone đồng cảm và giải thích, không phải defensive hay sales-y

- Given tôi muốn reply vào một comment cụ thể (không phải comment cấp 1)
  When chọn comment đó và click "Reply"
  Then AI đọc context của thread đó và tạo reply phù hợp

- Given account bị Facebook cảnh báo về spam behaviour
  When app phát hiện signal (ví dụ: CAPTCHA, rate limit response)
  Then app dừng mọi action write và alert user ngay lập tức

**Out of scope:** Auto-comment không có human review; bulk comment vào nhiều bài cùng lúc

**Dependencies:** US-03, US-04 hoặc US-05

**Notes:** Mỗi comment phải được human approve trước khi post — đây là hard requirement, không được bypass. Cần implement delay ngẫu nhiên 30-120s giữa các comment để tránh pattern phát hiện.

---

### US-08a: Tạo soft-sell post dựa trên insight của group

> **Tại sao split khỏi US-08b và US-08c?** Tạo post là _content creation flow_ hoàn chỉnh và có value ngay cả khi chưa có follow-up hay dashboard. Một marketer có thể dùng US-08a độc lập trong nhiều tuần trước khi cần US-08b. Đây là MVP của sales workflow.

**As a** sales/BD person
**I want to** AI soạn bài viết bán hàng tự nhiên, được điều chỉnh theo insight thực tế của từng group
**So that** nội dung tôi đăng phù hợp với pain points của cộng đồng trong group đó, tránh bị report là spam

**Acceptance Criteria:**

- Given tôi chọn một group đã có dữ liệu insight (US-04) và nhập sản phẩm/dịch vụ muốn quảng bá
  When click "Create Sales Post"
  Then AI tạo 3 phiên bản nội dung theo 3 góc độ: (1) chia sẻ trải nghiệm cá nhân, (2) câu hỏi mở kéo thảo luận, (3) tư vấn giải pháp — mỗi bản dưới 300 từ

- Given AI tạo nội dung
  When tôi đọc preview
  Then nội dung phải reference ít nhất một pain point phổ biến từ insight của group đó (không phải bài generic)

- Given group có lịch sử insight cho thấy đây là group cấm quảng cáo
  When AI tạo nội dung
  Then AI tự động chọn góc độ ít sales-y nhất và thêm cảnh báo: "Group này có dấu hiệu cấm quảng cáo trực tiếp — nội dung đã được điều chỉnh"

- Given tôi chỉnh sửa và approve một phiên bản
  When click "Post to Group"
  Then flow chuyển sang US-06 (create post flow) để confirm lần cuối và đăng

- Given tôi muốn đăng cùng một nội dung vào nhiều group khác nhau
  When chọn nhiều group
  Then AI tạo biến thể nội dung riêng cho từng group (không copy-paste y hệt) để tránh duplicate content detection

**Out of scope:** Follow-up với người đã comment (US-08b); tracking dashboard (US-08c); auto-schedule đăng bài

**Dependencies:** US-03b, US-04, US-06

**Notes:** Nội dung phải pass "does this look like a real person wrote it?" check. Hard limit: không đăng quá 2 sales posts/group/tuần — enforce ở app level.

---

### US-08b: Follow-up cá nhân hoá với người đã thể hiện interest

> **Tại sao split khỏi US-08a?** Follow-up là _engagement loop_ xảy ra sau khi post đã đăng, có thể cách nhau nhiều ngày. Nó require UI notification + comment suggestion riêng, hoàn toàn khác UX với việc tạo post. Có thể dev sau US-08a mà không block.

**As a** sales/BD person
**I want to** AI nhận diện người dùng đã thể hiện interest và đề xuất comment follow-up cá nhân hoá cho từng người
**So that** tôi nurture lead một cách tự nhiên mà không cần theo dõi thủ công từng bình luận

**Acceptance Criteria:**

- Given bài sales post đã đăng (US-08a) và đã qua ít nhất 30 phút
  When app scan comment mới
  Then AI tự động phân loại comment thành: Interested (hỏi giá, hỏi thêm thông tin), Neutral (like, emoji), Negative (phản đối) — và chỉ flag "Interested" để follow-up

- Given AI phát hiện comment "Interested"
  When tôi mở notification
  Then thấy: tên người comment, nội dung comment gốc, và 2 đề xuất reply được cá nhân hoá (reference đúng câu hỏi họ hỏi, tag tên họ)

- Given tôi chọn một đề xuất reply
  When submit
  Then comment được đăng sau delay ngẫu nhiên 45-90s (không đăng ngay để tránh bot detection); app lưu log: post_id, commenter_name, reply_content, timestamp

- Given tôi đã reply một người
  When người đó comment lần 2 trên cùng bài
  Then AI tự động tạo đề xuất reply tiếp theo với context của cả thread trước đó (không hỏi lại thông tin đã cung cấp)

- Given một người đã được follow-up 3 lần mà không có phản hồi tích cực
  When AI đánh giá
  Then người đó bị đánh dấu "Cold lead" và không còn được đề xuất follow-up thêm trong 14 ngày

- Given tôi muốn xem tất cả leads đang được nurture
  When mở tab "Active Leads"
  Then thấy danh sách: tên, bài đăng liên quan, số lần đã tương tác, trạng thái (Hot/Warm/Cold), lần tương tác gần nhất

**Out of scope:** Auto DM/inbox; CRM export; lead scoring phức tạp (US-08c); reply vào comment tiêu cực

**Dependencies:** US-08a, US-07

**Notes:** Tất cả reply phải được human approve — không có auto-reply. Delay ngẫu nhiên là bắt buộc. Không follow-up quá 1 lần/ngày/người để tránh harassment và bot detection.

---

### US-08c: Sales tracking dashboard

> **Tại sao split khỏi US-08a và US-08b?** Dashboard là _reporting layer_ — nó consume data từ US-08a và US-08b nhưng không block chúng. Sales team có thể operate tốt với US-08a + US-08b trước khi có dashboard. Đây là story có thể làm cuối sprint hoặc đầu sprint sau.

**As a** sales/BD person
**I want to** xem tổng quan hiệu quả của các bài sales posts và leads đang nurture
**So that** tôi biết kênh nào, group nào, và nội dung nào đang hoạt động tốt nhất để tập trung nguồn lực

**Acceptance Criteria:**

- Given tôi mở Sales Dashboard
  When không có data nào
  Then hiển thị empty state với hướng dẫn: "Bắt đầu bằng cách tạo sales post đầu tiên (US-08a)"

- Given đã có ít nhất một bài đăng và dữ liệu engagement
  When tôi xem Dashboard
  Then thấy các metrics: tổng số posts đã đăng, tổng reactions, tổng comments, số leads identified (Interested), số leads đã follow-up, tỉ lệ reply/total-comment

- Given tôi muốn so sánh hiệu quả theo group
  When chọn view "By Group"
  Then thấy bảng ranking các group theo engagement rate — giúp xác định group nào phù hợp nhất với sản phẩm

- Given tôi muốn biết loại nội dung nào hiệu quả nhất
  When chọn view "By Content Type"
  Then thấy so sánh 3 góc độ (trải nghiệm cá nhân / câu hỏi mở / tư vấn giải pháp) theo engagement rate

- Given tôi muốn xem timeline của một lead cụ thể
  When click vào tên lead trong danh sách
  Then thấy toàn bộ lịch sử tương tác: bài đăng gốc → comment của họ → các reply đã gửi → trạng thái hiện tại

- Given tôi muốn export data
  When click "Export"
  Then tải về CSV với columns: post_url, group_name, post_date, content_type, reactions, comments, leads_count, follow_up_count

**Out of scope:** Real-time dashboard (refresh mỗi 5 phút là đủ); predictive analytics; CRM integration; revenue tracking

**Dependencies:** US-08a, US-08b

**Notes:** Dashboard chỉ đọc — không có action nào từ màn hình này. Metrics đủ đơn giản để đọc trong 30 giây — không cần charts phức tạp ở MVP.

---

## Open Questions

| # | Question | Priority | Owner |
|---|----------|----------|-------|
| OQ-1 | Facebook session management: khi session hết hạn giữa chừng, UX xử lý thế nào? Re-login flow ra sao? | High | Tech |
| OQ-2 | Rate limiting strategy: app có tự động throttle hay để user cấu hình? Ngưỡng an toàn là bao nhiêu action/giờ? | High | Tech |
| OQ-3 | AI model nào cho task classification và content generation? Claude API? Local model? Chi phí per-request? | High | Tech |
| OQ-4 | Dữ liệu crawl lưu ở đâu? Local file hay cloud? Có cần encryption không (vì chứa data người dùng Facebook)? | High | Tech/Legal |
| OQ-5 | Multi-account support có cần không? (nhiều người dùng app với Facebook account khác nhau) | Medium | Product |
| OQ-6 | Facebook ToS compliance: app sẽ được distribute thế nào? Internal tool hay SaaS? | High | Legal |
| OQ-7 | Với US-08 (sales), có cần CTA tracking (link rút gọn, UTM) để đo conversion không? | Medium | Product |
| OQ-8 | Language support: app có cần support tiếng Anh hay chỉ tiếng Việt? | Low | Product |

---

## INVEST Check Summary

| Story | I | N | V | E | S | T | Status |
|-------|---|---|---|---|---|---|--------|
| US-01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready |
| US-02 | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready — nên dev cùng sprint với US-01 |
| US-03a | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready — safety gate, UX độc lập |
| US-03b | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready — async monitoring, dev sau US-03a |
| US-04 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready |
| US-05 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready |
| US-06 | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | Rate limiting logic có thể cần story riêng |
| US-07 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready — hard requirement: human approve |
| US-08a | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready — MVP của sales workflow |
| US-08b | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready — dev sau US-08a |
| US-08c | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Ready — reporting layer, dev cuối sprint |
