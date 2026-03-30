# Phase 6 — Responsive Mobile Web for All Web Surfaces
## AI Facebook Social Listening & Engagement v3

**Status:** Scope locked for implementation
**Depends on:** Phase 5 — Resilient AI Routing & Release Notes
**Updated:** 2026-03-30

---

## Goal

Phase 6 tap trung 100% vao responsive mobile web design cho moi web surface trong du an:

- app frontend tai `https://social-listening-v3.blackbirdzzzz.art/`
- browser entry/help web tai host browser
- noVNC web surface duoc serve trong container

Phase nay van la web thong thuong, khong doi sang native hay app-like shell.

---

## Expected Outcomes

- Main app doc duoc, bam duoc, khong tran layout tren viewport hep
- Browser host root mo vao mot web page dung nghia, khong con directory listing
- noVNC co mobile control surface dung duoc bang touch ma khong can zoom/pan lien tuc
- Manual Facebook login flow van giu nguyen va de tiep can hon tren mobile

---

## Out of Scope

- Assisted login / credential automation
- Secret-file flow
- MFA / CAPTCHA bypass
- Native mobile app

---

## Documents

- [BA Problem Brief](./ba-problem-brief.md)
- [User Stories](./user-stories.md)
- [Technical Solution](./technical-solution.md)
- [Checkpoints](./checkpoints/README.md)

BA brief la source of truth cho problem framing.  
User stories la source of truth cho implementation scope.  
Technical solution la source of truth cho implementation shape.  
Checkpoint docs la source of truth cho execution order va validation.
