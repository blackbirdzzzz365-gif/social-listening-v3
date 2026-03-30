# BA Problem Brief / BRD — Phase 6

## Metadata

- Initiative: Phase 6 — Responsive Mobile Web for All Web Surfaces
- Owner: Social Listening v3 product + frontend + browser surface team
- Primary layers:
  - main app frontend
  - browser entry/help pages
  - noVNC web surface

## Problem

- Problem statement:
  San pham da chay duoc tren VPS va co public hostname, nhung khi mo tren mobile thi app shell va browser surfaces van con desktop-biased. Main app co nhieu cards va action bars de bi chat, browser host root hien directory listing, va noVNC mac dinh khong toi uu cho touch use.
- Who is affected:
  operator, researcher, founder, va moi user can setup / monitor tu dien thoai
- Why this matters:
  day la product phuc vu Facebook workflow, ma phan lon thao tac thuc te xay ra tren mobile. Neu web surfaces khong responsive tot thi production adoption bi nghen ngay tu entry points.
- Current cost of problem:
  user phai zoom, kho bam CTA, kho doc metadata dai, kho tim dung browser URL, va remote browser surface khong than thien tren mobile

## Desired Outcome

- Target user/business outcome:
  tat ca web surface trong du an dung duoc tren mobile ma khong doi product sang app-like UX
- Success signals:
  main app khong overflow ngang, browser host root mo dung landing page, noVNC control/canvas dung duoc bang touch, desktop khong bi regressions

## Stakeholders

| Stakeholder | Need | Power | Risk if ignored |
|---|---|---|---|
| Mobile operator | thao tac nhanh tren phone | High | web “chay duoc” nhung khong “dung duoc” |
| Product owner | pham vi ro rang, khong truot sang credential automation | High | scope phase bi lech muc tieu |
| Frontend engineer | responsive rules dung chung | High | page fix roi rac, khong dong nhat |
| Browser surface engineer | browser/noVNC web co entry flow ro rang | High | user vao nham path, browser UX tiep tuc vo |

## Current State

- Main app hien dung Mantine shell nhung van desktop-first o nhieu cho
- Browser host root hien directory listing tu noVNC static dir
- noVNC mac dinh giu upstream UI, chua co project-specific mobile customization
- Manual login flow qua browser van la flow dung va phai duoc giu nguyen

## Future State

- Main app duoc redesign theo responsive mobile web rules
- Browser host root tro thanh mot responsive web landing page co links/help ro rang
- noVNC duoc customize o layer HTML/CSS/JS static de toi uu mobile touch use
- Manual login flow de tim, de vao, de tiep tuc hon tren mobile

## Requirement Split

### Main App Web

- header, cards, action bars, metadata rows responsive tot
- section order hop ly hon cho viewport hep
- release notes page va health/setup surfaces cung nam trong same responsive standard

### Browser Entry Web

- root browser host khong duoc hien directory listing
- phai co entry page, help, reconnect/fullscreen/keyboard guidance

### noVNC Web

- duoc xem la mot web surface thuoc implementation scope
- duoc phep customize HTML/CSS/JS static layer
- khong doi protocol/backend VNC

## Constraints

- Khong ship credential automation trong Phase 6
- Khong doi business logic API/state flow cua app frontend
- Khong fork VNC protocol stack; chi sua FE/static integration layer

## Non-goals

- Assisted login
- Secret storage
- MFA automation
- Native app shell

## Recommendation

- Ship theo 6 checkpoints: setup/docs, responsive primitives, main app responsive pass, browser entry web, noVNC mobile customization, va build/smoke gate
