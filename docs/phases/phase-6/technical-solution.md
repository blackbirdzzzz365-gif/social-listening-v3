# Technical Solution — Phase 6
## Responsive Mobile Web for All Web Surfaces

**Updated:** 2026-03-30  
**Status:** Implementation-ready

---

## Locked Decisions

- Phase 6 chi ship responsive mobile web improvements
- Assisted login va credential automation khong nam trong scope
- Browser root phai tro thanh project-owned entry page
- noVNC duoc customize o static FE layer, khong doi protocol/backend stack

---

## Current-State Findings

### Main App

- shell va cards da dung Mantine nhung van desktop-biased
- `ActionBar` va `KeyValueRow` qua don gian cho mobile
- `App.tsx` sap xep sections dung duoc tren desktop nhung tren mobile scroll kha dai va kho dinh huong

### Browser Root

- 6080 root hien directory listing vi `websockify --web "$NOVNC_PATH"` tro thang vao noVNC static dir
- user de vao sai path thay vi vao dung browser surface

### noVNC

- upstream `vnc_lite.html` rat gon nhung chua co project-specific mobile controls
- upstream `vnc.html` day du hon nhung control density va framing chua toi uu cho mobile touch use

---

## Implementation Strategy

## 1. Main App Responsive Layer

Files touched:

- `frontend/src/App.tsx`
- `frontend/src/app/shell/AppLayout.tsx`
- `frontend/src/app/shell/AppHeader.tsx`
- `frontend/src/components/ui/*`
- `frontend/src/pages/*`

Direction:

- dua shell ve responsive web layout that ro rang hon tren mobile
- header 2 tang tren viewport hep
- action bars stack/wrap theo kich thuoc man hinh
- metadata rows wrap va cho value xuong dong an toan
- page spacing/padding/gap giam o `base`
- release notes va workflow pages theo cung mot responsive language

## 2. Browser Entry Web

Files touched:

- `entrypoint.sh`
- `Dockerfile`
- browser static assets moi trong repo

Direction:

- tao browser web root page rieng
- root page co CTA vao:
  - customized mobile VNC page
  - fallback standard VNC page
- them text guidance cho reconnect/fullscreen/keyboard/manual login

## 3. Customized noVNC Surface

Files touched:

- custom browser static HTML/CSS/JS duoc ship cung image
- runtime assembly trong `entrypoint.sh`

Direction:

- dung `vnc_lite.html` lam base behavior cho mobile page
- tao custom mobile VNC page su dung `RFB` truc tiep va top controls do du an so huu
- giu `vnc.html` va `vnc_lite.html` upstream lam fallback/debug routes
- root browser page dua user vao custom mobile page theo mac dinh

Expected controls:

- reconnect
- fullscreen
- keyboard help
- optional Ctrl-Alt-Del / refresh session shortcut
- clear status line

---

## Runtime Shape

- App UI van duoc serve boi FastAPI tu `/app/static`
- Browser UI van duoc serve boi `websockify`
- `entrypoint.sh` se copy/prepare mot custom web root cho browser host:
  - index entry page
  - custom mobile VNC page
  - access den upstream noVNC assets/fallback pages

---

## Testing Strategy

### Main App

- `cd frontend && npm run build`
- viewport checks: 360, 390, 430, 768
- khong overflow ngang
- action bars, metadata rows, release notes, va workflow cards dung duoc tren mobile

### Browser Root / noVNC

- `curl -I http://127.0.0.1:6080/`
- `curl -I http://127.0.0.1:6080/mobile.html`
- `curl -I http://127.0.0.1:6080/vnc.html`
- `curl -I http://127.0.0.1:6080/vnc_lite.html`

- root tra ve browser entry page
- mobile VNC page connect duoc
- fallback noVNC pages van ton tai

### Regression

- desktop app van dung duoc
- manual login flow van khong doi
- container build/deploy van xanh
