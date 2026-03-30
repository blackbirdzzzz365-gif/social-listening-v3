# Deployment Guide - Production v1

## AI Facebook Social Listening v3

**Updated:** 2026-03-30
**Deployment model:** 1 VM + Docker Compose + Cloudflare Tunnel
**Related decision doc:** [docs/architecture-split-proposal.md](/Users/thong.nguyen/project/social-listening-v3/docs/architecture-split-proposal.md)

---

## 1. Muc tieu

Tai lieu nay mo ta cach deploy he thong len production theo phuong an da chot:

- 1 VM tren ChiaseGPU
- 1 container Docker cho app
- Cloudflare Tunnel de expose app va noVNC
- 2 public URLs:
  - `https://social-listening-v3.blackbirdzzzz.art`
  - `https://live-browser.blackbirdzzzz.art/vnc.html`

Day la deployment nhanh, gon, va phu hop nhat voi codebase hien tai.

---

## 2. Kien truc production

```text
Phone / Laptop
      |
      | HTTPS
      v
Cloudflare
  |- DNS
  |- SSL
  |- Tunnel
  |- Public Hostname
      |
      v
VM
  |- cloudflared
  |- docker compose
      |- FastAPI + React UI      :8000
      |- Camoufox browser
      |- Xvfb + x11vnc + noVNC   :6080
      |- SQLite data volume
      |- browser profile volume
```

### Mapping

| Public URL | Internal target |
|------------|-----------------|
| `social-listening-v3.blackbirdzzzz.art` | `http://localhost:8000` |
| `live-browser.blackbirdzzzz.art` | `http://localhost:6080` |

---

## 3. Yeu cau

### Cloudflare

- Domain `blackbirdzzzz.art` da active tren Cloudflare
- Tunnel `social-listening` da duoc tao va `connected`

### VM

- Ubuntu/Debian hoac Linux tuong duong
- Docker Engine da cai
- Docker Compose v2 da cai
- `git` co san

### Secrets

Can co it nhat:

- `ANTHROPIC_API_KEY`
- `OPAQUE_ID_SECRET`

Khuyen nghi them:

- `VNC_PASSWORD`

---

## 4. Cac file lien quan

- [Dockerfile](/Users/thong.nguyen/project/social-listening-v3/Dockerfile)
- [docker-compose.yml](/Users/thong.nguyen/project/social-listening-v3/docker-compose.yml)
- [entrypoint.sh](/Users/thong.nguyen/project/social-listening-v3/entrypoint.sh)
- [.env.example](/Users/thong.nguyen/project/social-listening-v3/.env.example)

Luu y:

- Repo khong bundle CA noi bo cua to chuc
- Neu VM nam sau mang co TLS interception dac thu, trust store phai duoc xu ly o cap VM/network, khong commit vao app

---

## 5. Chuan bi `.env` tren VM

Tren VM:

```bash
cd /path/to/social-listening-v3
cp .env.example .env
```

Dien cac gia tri toi thieu:

```bash
ANTHROPIC_API_KEY=...
OPAQUE_ID_SECRET=...
VNC_PASSWORD=...
APP_PORT=8000
VNC_PORT=6080
CAMOUFOX_HEADLESS=false
```

Neu chua co `OPAQUE_ID_SECRET`, tao bang:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 6. Build va start app tren VM

```bash
cd /path/to/social-listening-v3
docker compose up -d --build
```

Kiem tra:

```bash
docker compose ps
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/runtime/metadata
curl -s http://localhost:8000/api/browser/status
```

**Expected**

- container `social-listening-v3` o trang thai `healthy`
- `/health` tra JSON `status=ok`
- API runtime va browser status tra JSON hop le

Co the test browser local tren VM bang browser/SSH tunnel:

```bash
curl -I http://localhost:6080/vnc.html
```

---

## 7. Cloudflare Tunnel routing

Vao Cloudflare Zero Trust:

- `Networks`
- `Tunnels`
- chon tunnel `social-listening`
- `Public hostnames`

Tao 2 hostname:

### Hostname 1 - App UI

- Subdomain: `app`
- Domain: `blackbirdzzzz.art`
- Type: `HTTP`
- URL: `localhost:8000`

### Hostname 2 - Browser view

- Subdomain: `browser`
- Domain: `blackbirdzzzz.art`
- Type: `HTTP`
- URL: `localhost:6080`

Khuyen nghi:

- Dat `live-browser.blackbirdzzzz.art` sau Cloudflare Access
- Neu chua bat Access, it nhat phai co `VNC_PASSWORD`

---

## 8. Validate public URLs

Sau khi tao public hostname:

```bash
curl -I https://social-listening-v3.blackbirdzzzz.art
curl -I https://live-browser.blackbirdzzzz.art/vnc.html
```

**Expected**

- ca 2 URL tra ve HTTPS response hop le
- app URL mo duoc tren browser ngoai internet
- browser URL mo duoc noVNC

---

## 9. Validate AI key

Kiem tra key da duoc load vao container:

```bash
docker exec social-listening-v3 sh -lc 'test -n "$ANTHROPIC_API_KEY" && echo SET || echo MISSING'
```

Kiem tra key goi duoc flow that:

```bash
curl -s -X POST https://social-listening-v3.blackbirdzzzz.art/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"topic":"phan hoi khach hang ve the tin dung TPBank EVO"}'
```

**Expected**

- container in `SET`
- API tao session thanh cong
- khong loi auth model/provider

---

## 10. Dang nhap Facebook qua noVNC

1. Mo `https://social-listening-v3.blackbirdzzzz.art`
2. Trigger browser setup tren app
3. Mo `https://live-browser.blackbirdzzzz.art/vnc.html`
4. Dang nhap Facebook
5. Quay lai app va check session

Kiem tra bang API:

```bash
curl -s https://social-listening-v3.blackbirdzzzz.art/api/browser/status
curl -s https://social-listening-v3.blackbirdzzzz.art/api/health/status
```

**Expected**

- `session_status` thanh `VALID`
- `account_id_hash` khac `null`
- `health_status` la `HEALTHY`

---

## 11. Smoke test production

Khi browser session da `VALID`, chay:

```bash
python backend/tests/e2e_smoke.py --base-url https://social-listening-v3.blackbirdzzzz.art
```

Neu da co `run_id` thuc te va muon test labeling:

```bash
python backend/tests/labeling_smoke.py --base-url https://social-listening-v3.blackbirdzzzz.art --run-id <run_id>
```

---

## 12. Van hanh co ban

### Start / rebuild

```bash
docker compose up -d --build
```

### Restart app

```bash
docker compose restart app
```

### Xem logs

```bash
docker compose logs -f app
```

### Stop

```bash
docker compose down
```

### Kiem tra tunnel

```bash
sudo systemctl status cloudflared --no-pager
sudo journalctl -u cloudflared -n 50 --no-pager
```

---

## 13. Tieu chi go-live

Chi nen xem la production-ready khi tat ca dieu sau deu dung:

- `https://social-listening-v3.blackbirdzzzz.art` mo duoc
- `https://live-browser.blackbirdzzzz.art/vnc.html` mo duoc
- Browser hostname da co bao ve phu hop
- `ANTHROPIC_API_KEY` da duoc load va goi duoc
- Facebook session da `VALID`
- `backend/tests/e2e_smoke.py` pass tren base URL public

---

## 14. Loai tru

Deployment guide nay **khong** bao gom:

- multi-node architecture
- remote browser worker
- PostgreSQL
- CI/CD day du
- secret manager chuyen nghiep

Tat ca cac muc do la phase sau, khong phai dieu kien de production v1 chay that.
