# Phase 7 — Retrieval Quality Gating Before AI Cost
## AI Facebook Social Listening & Engagement v3

**Status:** Brainstorm docs drafted for analysis-first alignment
**Depends on:** Phase 6 — Responsive Mobile Web for All Web Surfaces
**Updated:** 2026-03-30

---

## Goal

Phase 7 tap trung vao chat luong du lieu truoc khi goi AI:

- giam phu thuoc vao Facebook global search cold-start
- loc post/comment hop le bang co che rule-based truoc khi crawl sau va truoc khi goi AI
- lam sach payload crawl de labeling/theme analysis khong bi garbage-in

Phase nay chua phai implementation scope cuoi cung. Muc tieu truoc tien la khoa framing, phan tich, phan bien, va huong solution.

---

## Core Questions

- Lam sao de khong bi le thuoc vao viec account da tung tham gia dung group hay chua?
- Lam sao de post/comment chi duoc di tiep neu da vuot qua 1 relevance gate ro rang?
- Lam sao de chi records co gia tri moi di vao AI labeling/theme analysis?

---

## Expected Outcomes

- Co phan tich ro tung root cause cho `search miss`, `filter yeu`, va `dirty crawl`
- Co phan bien ro rang cho y tuong mandatory keywords + related-keyword matching
- Co user stories va technical solution cho Phase 7 theo huong:
  - retrieval da nguon
  - deterministic relevance engine
  - selective expansion
  - clean payload builder
  - chi goi AI cho records da dat chat luong toi thieu

---

## Documents

- [BA Problem Brief](./ba-problem-brief.md)
- [User Stories](./user-stories.md)
- [Technical Solution](./technical-solution.md)

BA brief la source of truth cho problem framing va phan bien.  
User stories la source of truth cho implementation scope sau khi brainstorm khoa scope.  
Technical solution la de xuat kien truc cho giai doan implementation tiep theo.
