# User Stories — Phase 6: Responsive Mobile Web for All Web Surfaces
## AI Facebook Social Listening & Engagement v3

**Product:** AI-powered Facebook research and engagement assistant
**Primary users:** Researcher, Marketer, Sales/BD, Mobile operator
**Language:** Vietnamese first, English supported
**Phase:** 6 — Responsive Mobile Web for All Web Surfaces
**Updated:** 2026-03-30

---

## Tai sao can Phase 6

Phase 5 da on dinh shell va release-note flow, nhung tra nghiem mobile van chua dat muc production-ready:

- main app van desktop-biased
- browser host root van la noVNC raw directory listing
- noVNC mac dinh chua du than thien cho touch/mobile

Phase 6 giai quyet toan bo phan responsive mobile web cua du an.

---

## Cross-Cutting Rules

**R-60 — Web-first responsive, not app-like**  
Moi be mat duoc toi uu cho mobile nhu mot web page/chat panel thong thuong, khong bien thanh native-app mimic.

**R-61 — No horizontal overflow by accident**  
Header, cards, action bars, metadata rows, va log blocks khong duoc tao horizontal scroll ngoai nhung vung chu dong cho phep.

**R-62 — Browser root must be intentional**  
Browser hostname root phai dua user vao mot web surface co chu dich, khong phai directory listing.

**R-63 — noVNC is in scope as a web surface**  
Phase 6 duoc phep customize noVNC HTML/CSS/JS static layer neu can de dat mobile usability.

**R-64 — Manual Facebook login remains the contract**  
Phase 6 khong thay doi login model; user van dang nhap thu cong trong browser.

---

## User Stories

### US-60: Use the Main App Comfortably on Mobile

**As a** mobile operator  
**I want** all core app pages to remain readable and tappable on a phone  
**So that** I can continue the workflow without desktop-only friction

**Acceptance Criteria:**

- Given the app opens at 360-430px width
  When the shell and workflow cards render
  Then there is no accidental horizontal overflow

- Given a page has multiple actions
  When viewed on mobile
  Then buttons wrap or stack cleanly and remain easy to tap

- Given a page shows hashes, IDs, status, or log text
  When rendered on mobile
  Then long values wrap safely and do not break layout

- Given I move across setup, health, keyword, plan, approve, monitor, themes, and release notes
  When using the app on mobile
  Then the section order and spacing feel intentional for mobile web

### US-61: Open the Browser Host Through a Real Web Entry Surface

**As a** user opening the browser hostname  
**I want** to land on a project-owned browser entry page  
**So that** I immediately know how to open the remote browser and what controls matter on mobile

**Acceptance Criteria:**

- Given I open the browser hostname root
  When the page loads
  Then I see a responsive browser landing page instead of directory listing

- Given I need to continue to noVNC
  When I use the browser entry page
  Then primary and fallback links are obvious and mobile-friendly

- Given I need help
  When I am on the entry page
  Then reconnect/fullscreen/keyboard guidance is visible without long docs

### US-62: Use the Remote Browser on Mobile Without Constant Zooming

**As a** user controlling the remote browser on a phone  
**I want** the noVNC surface to be customized for touch use  
**So that** I can navigate and type with less friction

**Acceptance Criteria:**

- Given the customized noVNC page opens on mobile
  When the VNC session connects
  Then the canvas and top controls fit the screen better than the upstream default

- Given I need keyboard/fullscreen/reconnect actions
  When I use the customized noVNC surface
  Then those controls are discoverable and tappable

- Given the mobile viewport is narrow
  When the session is active
  Then the remote browser remains usable without constant zoom/pan

### US-63: Keep Desktop Behavior Safe While Improving Mobile

**As a** desktop user  
**I want** Phase 6 mobile improvements to avoid breaking current desktop usage  
**So that** production does not regress for current operators

**Acceptance Criteria:**

- Given the app or browser surfaces are opened on desktop
  When the new responsive design is applied
  Then layout remains stable and usable

- Given the browser manual login flow works today
  When Phase 6 ships
  Then the same manual login flow still works end-to-end
