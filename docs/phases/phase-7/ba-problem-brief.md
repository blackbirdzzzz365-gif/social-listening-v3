# BA Problem Brief / BRD — Phase 7

## Metadata

- Initiative: Phase 7 — Retrieval Quality Gating Before AI Cost
- Owner: Social Listening v3 product + research workflow team
- Primary layers:
  - planner query generation
  - browser retrieval layer
  - pre-AI validation / gating
  - crawl payload normalization

## Problem

- Problem statement:
  Social Listening v3 da crawl duoc post/comment va da co labeling/theme pipeline, nhung chat luong retrieval dau vao van chua du on dinh. Neu account Facebook chua co dung graph/group context, global search co the ra rat it post lien quan. Khi da lay duoc candidates, system hien tai chua co relevance gate manh truoc persist/crawl-comments/AI labeling. Ket qua la du lieu ban dau vua thieu vua ban, gay ton chi phi AI va lam theme analysis giam do tin cay.
- Who is affected:
  researcher, marketer, founder, va team van hanh muon dung social listening cho insight that su lien quan
- Why this matters:
  chat luong insight khong the cao hon chat luong retrieval. Neu retrieval cold-start + dirty-input khong duoc giai quyet, moi phase labeling/theme sau do deu phai "don rac" va van ton cost.
- Current cost of problem:
  search miss, crawl nhieu record khong lien quan, crawl comments tu post yeu, AI labeling/analyze ton them cost, theme output nhieu noise va can doc thu cong de xac minh

## Current-State Analysis

### A. Search coverage van phu thuoc qua nhieu vao account context

- `SEARCH_POSTS` hien tai di vao Facebook global search va ap `Most recent`
- Neu account chua tung o dung he sinh thai group/topic, recall co the rat thap
- Flow hien tai moi chi partly exploit `SEARCH_GROUPS -> SEARCH_IN_GROUP -> CRAWL_FEED`

### B. Candidate validation chua du chat

- Browser retrieval layer hien dang accept kha nhieu article chi can co text + URL
- Chua co co che:
  - `must-have anchors`
  - `related topic coverage`
  - `negative keyword / promo penalty`
  - `quality score`
  - `accept / reject / uncertain`

### C. Dirty crawl payload di thang xuong labeling/theme

- Nhieu extraction hien tai dua tren `inner_text()` rong
- Payload de bi lan:
  - UI chrome
  - group title
  - menu text
  - duplicate fragments
  - noisy thread context
- Hien tai Phase 2 label/filter xu ly sau crawl, nen neu input ban thi AI van phai "ganh"

## Root Causes By Problem

### Problem 1 — "Search khong co bai viet lien quan neu account chua tung tham gia group dung topic"

Root causes:

- Facebook search mang tinh ca nhan hoa
- cold account khong co graph/context du de expose dung content
- query generation hien dang ngan va chua da dang theo intent
- chua co seed-source strategy ro rang

### Problem 2 — "Chua filter duoc hieu qua ket qua search post"

Root causes:

- retrieval layer chua co deterministic relevance gate
- post validity dang bi xac dinh qua long leo
- comment crawl dang duoc trigger tu discovered posts ma chua qua gate chat luong
- khong co negative/promo patterns de tru diem som

### Problem 3 — "Crawl data khong chuan gay ton cost AI va phan tich sai"

Root causes:

- extraction text qua rong va chua co payload cleaning stage rieng
- chua co quality flags / extraction score
- chua co candidate-state ro rang truoc khi vao labeling/theme
- raw candidate va accepted record dang bi xem nhu cung 1 loai du lieu

## Phan Bien Y Tuong Hien Tai

Y tuong cua user:

- sau buoc 1, xac dinh list tu khoa bat buoc
- post phai co cac tu khoa nay moi valid
- sau do check them cum tu khoa lien quan va doi hoi match toi thieu x%
- step nay khong qua AI

### Diem manh

- dung huong voi muc tieu giam cost AI
- tang precision som o retrieval layer
- tao duoc logic minh bach, de debug, de audit
- rat hop de quyet dinh `co crawl comment tiep hay khong`

### Diem can phan bien

- Neu "bat buoc phai co exact keywords" qua cung, recall se giam manh
- Comment hay post user that su lien quan nhieu khi khong nhac dung keyword chinh
- Tieng Viet thuc te co:
  - khong dau
  - viet tat
  - slang
  - typo
  - cach dien dat gian tiep
- Comment khong the danh gia doc lap hoan toan khoi parent post

### Ket luan phan bien

Huong dung khong phai la `exact mandatory keyword filter` thuong truc, ma la:

- `anchor terms` phai cham toi thieu 1 cluster
- `related context terms` dong vai tro score tang cuong
- `negative patterns` dong vai tro tru diem / reject som
- `quality signals` quyet dinh co dang crawl tiep hay khong
- comment duoc cham diem voi parent context

Noi cach khac: y tuong cua user nen duoc nang cap thanh **deterministic relevance engine**, khong nen dung o exact keyword gate don gian.

## Desired Outcome

- Target user/business outcome:
  he thong lay duoc dung hon, loc som hon, va chi ton AI cost cho records da co kha nang tao insight
- Success signals:
  - tang precision cua accepted posts/comments
  - giam AI calls moi accepted insight run
  - giam duplicate/noise rate
  - tang ti le theme "doc vao thay dung van de user dang noi"

## Proposed Decision Direction

### D-70 — Retrieval khong duoc chi dua vao Facebook global search

Can co strategy da nguon:

- global search
- search groups
- search in group
- feed crawl trong group da xac dinh
- seed groups tu lich su / user curation

### D-71 — Chi valid posts moi duoc expansion tiep

`crawl_comments` va `search_in_group` bo sung chi nen chay tren nguon hoac post da vuot relevance gate.

### D-72 — Persist candidate va accepted record theo 2 tang

Khong nen bat moi record retrieval di thang vao cung lifecycle voi records san sang labeling/theme.

2 lua chon:

- Option A: them `retrieval_candidates` rieng
- Option B: giu 1 bang nhung them `processing_stage`, `pre_ai_status`, `rejection_reason`

Khuyen nghi:

- Option A sach hon ve kien truc
- Option B nhanh ship hon neu muon it schema change

### D-73 — AI chi danh cho accepted hoac uncertain band

Rule-based gate la default.
AI chi xu ly:

- accepted records cho labeling/theme
- hoac uncertain records neu muon can bang recall

## Requirement Split

### Retrieval

- query diversification theo intent
- seed source strategy
- source scoring cho group/post source

### Validation

- anchor/related/negative/quality scoring
- accept/reject/uncertain states
- parent-aware comment validation

### Expansion

- chi crawl comments tu posts da valid
- chi search/crawl sau tren groups da du relevance

### Clean Payload

- text normalization
- UI-noise stripping
- duplicate detection
- extraction quality flags

### Cost Control

- chi accepted records di vao labeling/theme
- dashboard thong ke chi phi / accepted record

## Constraints

- Khong duoc lam retrieval logic qua mo ho de khong debug duoc
- Khong duoc lam recall giam manh vi overfitting exact keyword
- Van phai ton trong Phase 2 principle ve explainability va auditability
- Khong nen dua AI quay lai lam "bo loc dau tien"

## Non-goals

- Khong co gang giai bai toan "Facebook search hoan hao"
- Khong co gang xac dinh danh tinh that cua tac gia
- Khong lam full semantic search engine ben ngoai Facebook trong Phase 7
- Khong thay the toan bo theme/labeling pipeline bang rules

## Recommendation

- Next artifact:
  khoa scope Phase 7 thanh 5 lop delivery:
  1. retrieval strategy
  2. deterministic relevance engine
  3. selective expansion
  4. clean payload builder
  5. AI budget guardrails + audit metrics
