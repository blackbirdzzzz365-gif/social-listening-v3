# Kien truc Production da chot

**Ngay:** 2026-03-30
**Status:** Accepted decision
**Pham vi:** Production v1 cho Social Listening v3
**Thay the:** de xuat cu "tach Browser Worker ra server rieng"

---

## 1. Ket luan ngan

Phuong an da chot cho production v1 **khong tach browser worker thanh server rieng**.

Thay vao do, he thong chay theo mo hinh:

- 1 VM tren ChiaseGPU
- 1 Docker app duy nhat
- Cloudflare lo DNS + SSL + Tunnel
- 2 hostname public di vao 2 cong trong container:
  - `social-listening-v3.blackbirdzzzz.art` -> `localhost:8000`
  - `live-browser.blackbirdzzzz.art` -> `localhost:6080`

Muc tieu cua phuong an nay la:

- Ra production nhanh
- Giu deployment don gian
- Van dang nhap Facebook duoc tren dien thoai qua noVNC
- Chua phai dau tu som vao bai toan 2 server, remote worker, SSE cross-service

---

## 2. Kien truc duoc chon

```text
Phone / Laptop
      |
      | HTTPS
      v
Cloudflare
  |- DNS
  |- SSL/TLS
  |- Tunnel
  |- Public Hostname
      |
      | outbound tunnel
      v
VM ChiaseGPU
  |- cloudflared
  |- Docker container: social-listening-v3
       |- FastAPI + React UI      :8000
       |- Camoufox browser
       |- Xvfb + x11vnc + noVNC   :6080
       |- SQLite                  /data
       |- browser_profile volume
```

### Mapping hostnames

| Public URL | Target trong VM | Muc dich |
|------------|-----------------|----------|
| `https://social-listening-v3.blackbirdzzzz.art` | `http://localhost:8000` | App UI + API |
| `https://live-browser.blackbirdzzzz.art` | `http://localhost:6080` | noVNC browser view |

---

## 3. Dieu nay co nghia gi ve mat kien truc

Phuong an nay la **single-node production**, khong phai distributed architecture.

Noi de hieu:

- Cloudflare chi la lop "cua ngo"
- VM la noi chay app that
- Docker container van gom ca UI, API, browser, noVNC, va DB nhe
- Tunnel chi tao duong noi an toan tu Cloudflare vao VM, khong tu dong tach app thanh nhieu service

### Thanh phan nao chay o dau

**Cloudflare**
- Quan ly DNS cua domain
- Cap HTTPS public
- Dinh tuyen request vao tunnel
- Co the them Access policy cho browser hostname

**VM**
- Chay `cloudflared`
- Chay Docker va volumes
- Giu browser session cookies va SQLite data

**Docker app**
- Serve React UI va FastAPI tren port `8000`
- Chay Camoufox + Xvfb + x11vnc + noVNC cho browser tren port `6080`
- Luu session Facebook trong volume `browser_profile`
- Luu data app trong volume `sqlite_data`

---

## 4. Tai sao phuong an nay dung voi hien trang repo

Repo hien tai da duoc thiet ke theo huong **1 container + noVNC**:

- [docker-compose.yml](/Users/thong.nguyen/project/social-listening-v3/docker-compose.yml)
  - expose `8000` va `6080`
  - co 2 volume `browser_profile` va `sqlite_data`
- [Dockerfile](/Users/thong.nguyen/project/social-listening-v3/Dockerfile)
  - build frontend
  - chay Python app
  - copy Camoufox cache
- [entrypoint.sh](/Users/thong.nguyen/project/social-listening-v3/entrypoint.sh)
  - start Xvfb
  - start x11vnc
  - start noVNC
  - migrate DB
  - start uvicorn

Noi ngan gon: deployment da san sang cho model "1 app container sau Cloudflare Tunnel". Viec tach Browser Worker chi nen xem la phase sau, neu production v1 that su gap gioi han.

---

## 5. Khac biet so voi de xuat cu

### De xuat cu

- App server rieng
- Browser worker rieng
- RunnerService goi worker qua HTTP
- noVNC o server browser rieng

### Phuong an da chot

- Tat ca van o 1 VM
- Cloudflare Tunnel tro thanh lop expose production
- Khong co giao tiep service-to-service noi bo
- Khong can `RemoteBrowserClient` o production v1

### He qua thiet ke

**Uu diem**
- Don gian hon rat nhieu
- It moving parts
- De debug hon
- Di production nhanh

**Trade-off**
- Browser crash van co the anh huong toi container duy nhat
- noVNC va app cung chia se tai nguyen 1 VM
- Khong scale ngang browser doc lap

---

## 6. Bo sung bat buoc de xem la "production-ready"

Phuong an chot tu support la hop ly, nhung can them 2 luu y de tai lieu dung voi production that:

### 6.1 Browser hostname khong nen de mo hoan toan

`live-browser.blackbirdzzzz.art` la man hinh browser Facebook co the tuong tac duoc.

Neu de public hoan toan thi rui ro rat cao:

- Lo man hinh dang nhap Facebook
- Lo session dang su dung
- Lo thao tac browser realtime

**Khuyen nghi production:**

- `social-listening-v3.blackbirdzzzz.art`: co the public binh thuong
- `live-browser.blackbirdzzzz.art`: nen dat sau **Cloudflare Access**
- repo khong bundle CA noi bo cua to chuc; trust store dac thu, neu can, phai duoc xu ly o cap VM/mang thay vi commit vao app

Neu chua bat Access ngay, it nhat phai co:

- `VNC_PASSWORD`
- subdomain khong de doan
- thoi gian public ngan trong luc setup

Nhung muc "production-ready" nen la: **browser hostname co Access policy**.

### 6.2 Anthropic API key can duoc validate bang ca "loaded" va "usable"

Chi dien key vao `.env` la chua du.

Can validate 2 lop:

- app da nap duoc key vao runtime
- key goi duoc flow AI that

---

## 7. Ke hoach validate tung checkpoint

Bang duoi day giu nguyen tinh than cac buoc 1-9 da chot, nhung them cach xac thuc cu the.

| # | Checkpoint | Trang thai hien tai | Can validate gi | PASS khi nao |
|---|------------|---------------------|-----------------|--------------|
| 1 | Cloudflare account + domain active | Done | Domain da active tren Cloudflare, nameserver da tro dung | Dashboard hien Active |
| 2 | Nameserver da doi sang Cloudflare | Done | WHOIS / registrar / Cloudflare dashboard khop nhau | Khong con nameserver cu |
| 3 | VM da san sang | Done | VM dung cau hinh, SSH duoc, con du RAM/disk | Dang nhap duoc, tai nguyen du |
| 4 | Docker da san sang tren VM | Done | `docker` va `docker compose` chay duoc | Version OK, compose OK |
| 5 | Cloudflare Tunnel da connected | Done | `cloudflared` online va khong reconnect loop | Tunnel status = healthy/connected |
| 6 | Clone repo + build Docker image | Done | Container len duoc va health endpoint xanh | `/health` = 200, noVNC mo duoc local |
| 7 | Public hostname tren Cloudflare | Pending | 2 hostname map dung toi `8000` va `6080` | URL public mo duoc qua HTTPS |
| 8 | Anthropic API key trong `.env` | Pending | Key da load + flow AI goi that | Session/planner flow chay that |
| 9 | Test tren dien thoai | Pending | App UI + browser UI + login session + flow API | Dung duoc that tren mobile |

---

## 8. Commands va tieu chi validate chi tiet

### CP-1 / CP-2: Cloudflare + domain

**Validate**
- Cloudflare dashboard hien domain `blackbirdzzzz.art` o trang thai Active
- Nameserver tai nha cung cap domain khop voi nameserver Cloudflare

**PASS**
- DNS tren Cloudflare co hieu luc
- Co the tao DNS/public hostname cho tunnel

### CP-3: VM baseline

**Commands tren VM**

```bash
uname -a
nproc
free -h
df -h /
```

**PASS**
- VM dung dung may du kien
- Con du tai nguyen de chay Docker + browser

### CP-4: Docker runtime

**Commands tren VM**

```bash
docker --version
docker compose version
```

**PASS**
- Docker Engine va Compose chay binh thuong

### CP-5: Cloudflare Tunnel

**Commands tren VM**

```bash
sudo systemctl status cloudflared --no-pager
cloudflared tunnel list
sudo journalctl -u cloudflared -n 50 --no-pager
```

**PASS**
- Tunnel `social-listening` o trang thai connected
- Log khong bi reconnect loop lien tuc

### CP-6: App local tren VM

**Commands tren VM**

```bash
docker compose ps
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/runtime/metadata
curl -s http://localhost:8000/api/browser/status
```

**PASS**
- Container `social-listening-v3` o trang thai `healthy`
- `/health` tra ve `{"status":"ok"}`
- `/api/runtime/metadata` tra ve metadata runtime
- `/api/browser/status` tra ve JSON hop le

**Manual local**
- Mo `http://localhost:6080/vnc.html`
- Xac nhan noVNC len desktop/browser view

### CP-7: Public hostname

**Public hostnames can tao**

1. App UI
- Subdomain: `app`
- Domain: `blackbirdzzzz.art`
- Type: `HTTP`
- URL: `localhost:8000`

2. Browser view
- Subdomain: `browser`
- Domain: `blackbirdzzzz.art`
- Type: `HTTP`
- URL: `localhost:6080`

**Validate sau khi tao**

```bash
curl -I https://social-listening-v3.blackbirdzzzz.art
curl -I https://live-browser.blackbirdzzzz.art/vnc.html
```

**PASS**
- Ca 2 URL tra ve response HTTPS hop le
- App UI mo duoc tu internet
- noVNC mo duoc tu internet

**Production-hardening**
- Bat Cloudflare Access cho `live-browser.blackbirdzzzz.art`
- Test lai browser URL sau khi policy duoc ap

### CP-8: Anthropic API key

**Validate key da duoc load**

```bash
docker exec social-listening-v3 sh -lc 'test -n "$ANTHROPIC_API_KEY" && echo SET || echo MISSING'
```

**Validate key goi duoc flow that**

```bash
curl -s -X POST https://social-listening-v3.blackbirdzzzz.art/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"topic":"phan hoi khach hang ve the tin dung TPBank EVO"}'
```

**PASS**
- Container tra `SET`
- API tao session thanh cong
- Flow clarification / keyword analysis khong loi

Neu muon validate sau hon:

```bash
python backend/tests/e2e_smoke.py --base-url https://social-listening-v3.blackbirdzzzz.art
```

Luu y: e2e smoke day du chi pass khi Facebook session da `VALID`.

### CP-9: Browser login + mobile validation

**Bai test tren dien thoai**

1. Mo `https://social-listening-v3.blackbirdzzzz.art`
2. Mo `https://live-browser.blackbirdzzzz.art/vnc.html`
3. Tren app, trigger browser setup
4. Dang nhap Facebook trong noVNC
5. Quay lai app va check session status

**API check sau login**

```bash
curl -s https://social-listening-v3.blackbirdzzzz.art/api/browser/status
curl -s https://social-listening-v3.blackbirdzzzz.art/api/health/status
```

**PASS**
- `session_status = VALID`
- `account_id_hash != null`
- `health_status = HEALTHY`

**Smoke test sau login**

```bash
python backend/tests/e2e_smoke.py --base-url https://social-listening-v3.blackbirdzzzz.art
```

**PASS**
- Planner flow OK
- Browser flow OK
- Run co the bat dau hoac doc duoc status hop le

---

## 9. Thu tu rollout thuc te de tranh loi

Thu tu khuyen nghi:

1. Xac nhan local app tren VM da xanh (`localhost:8000`, `localhost:6080`)
2. Xac nhan tunnel connected
3. Tao `social-listening-v3.blackbirdzzzz.art`
4. Test `app` public truoc
5. Tao `live-browser.blackbirdzzzz.art`
6. Bat Access cho `browser` neu co the
7. Dien API key
8. Test planner flow
9. Dang nhap Facebook qua mobile/noVNC
10. Test e2e smoke

Ly do: neu public hostname chua dung ma da doi sang test mobile ngay, rat de nham la app loi trong khi thuc ra chi la route tunnel chua dung.

---

## 10. Dinh nghia "go-live"

Chi nen xem la san sang go-live khi tat ca dieu sau deu dung:

- `https://social-listening-v3.blackbirdzzzz.art` mo duoc tren mobile
- `https://live-browser.blackbirdzzzz.art/vnc.html` mo duoc tren mobile
- Browser hostname da co lop bao ve phu hop
- `ANTHROPIC_API_KEY` da duoc load va goi duoc
- Facebook login session chuyen sang `VALID`
- `backend/tests/e2e_smoke.py` pass o base URL public

---

## 11. Nhung gi chua nam trong phuong an nay

Phuong an production v1 nay **chua** giai quyet cac bai toan sau:

- Tach browser thanh worker rieng
- Chay nhieu browser node
- Chuyen DB sang PostgreSQL
- CI/CD deployment day du
- Secret manager chuyen nghiep

Tat ca cac muc tren van co the la phase sau, nhung khong can de app chay that lan dau.

---

## 12. Ket luan

Kien truc production da chot khong phai "2 server orchestration", ma la:

- **1 VM**
- **1 Docker app**
- **Cloudflare Tunnel lam cua ngo production**

Day la kien truc phu hop nhat voi codebase hien tai va muc tieu di production nhanh.

Neu can tang do ben hoac scale sau nay, luc do moi nen mo lai de xuat tach Browser Worker thanh phase kien truc tiep theo.
