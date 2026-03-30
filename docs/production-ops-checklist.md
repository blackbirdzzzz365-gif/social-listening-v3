# Production Ops Checklist

Checklist ngan gon de team follow khi setup va deploy production v1.

## A. Cloudflare

### 1. Domain va tunnel

- [ ] Domain `blackbirdzzzz.art` dang `Active` trong Cloudflare
- [ ] Tunnel `social-listening` dang `connected`

Kiem tra:

```bash
cloudflared tunnel list
```

### 2. Public hostnames

- [ ] `social-listening-v3.blackbirdzzzz.art` -> `http://localhost:8000`
- [ ] `live-browser.blackbirdzzzz.art` -> `http://localhost:6080`

Validate:

```bash
curl -I https://social-listening-v3.blackbirdzzzz.art
curl -I https://live-browser.blackbirdzzzz.art/vnc.html
```

### 3. Access policy

- [ ] `live-browser.blackbirdzzzz.art` da co Cloudflare Access policy hoac co co che bao ve thay the

---

## B. VM

### 4. Runtime

- [ ] SSH vao VM duoc
- [ ] Docker OK
- [ ] Docker Compose OK

Validate:

```bash
docker --version
docker compose version
free -h
df -h /
```

### 5. cloudflared

- [ ] service dang chay on dinh

Validate:

```bash
sudo systemctl status cloudflared --no-pager
sudo journalctl -u cloudflared -n 50 --no-pager
```

---

## C. App

### 6. Secrets

- [ ] `.env` da co `ANTHROPIC_API_KEY`
- [ ] `.env` da co `OPAQUE_ID_SECRET`
- [ ] `.env` da co `VNC_PASSWORD`

Validate:

```bash
docker exec social-listening-v3 sh -lc 'test -n "$ANTHROPIC_API_KEY" && echo SET || echo MISSING'
```

### 7. Build va start

- [ ] app build xong
- [ ] container dang `healthy`

Commands:

```bash
docker compose up -d --build
docker compose ps
```

### 8. API local

- [ ] local health pass
- [ ] runtime metadata pass
- [ ] browser status pass

Validate:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/runtime/metadata
curl -s http://localhost:8000/api/browser/status
```

### 9. noVNC local

- [ ] `localhost:6080/vnc.html` mo duoc

Validate:

```bash
curl -I http://localhost:6080/vnc.html
```

---

## D. Public validation

### 10. App public

- [ ] `https://social-listening-v3.blackbirdzzzz.art` mo duoc

Validate:

```bash
curl -I https://social-listening-v3.blackbirdzzzz.art
```

### 11. Browser public

- [ ] `https://live-browser.blackbirdzzzz.art/vnc.html` mo duoc

Validate:

```bash
curl -I https://live-browser.blackbirdzzzz.art/vnc.html
```

---

## E. Functional validation

### 12. AI flow

- [ ] session creation pass
- [ ] planner flow pass

Validate:

```bash
curl -s -X POST https://social-listening-v3.blackbirdzzzz.art/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"topic":"phan hoi khach hang ve the tin dung TPBank EVO"}'
```

### 13. Facebook login

- [ ] browser setup trigger duoc
- [ ] user login duoc qua noVNC
- [ ] browser status thanh `VALID`

Validate:

```bash
curl -s https://social-listening-v3.blackbirdzzzz.art/api/browser/status
curl -s https://social-listening-v3.blackbirdzzzz.art/api/health/status
```

### 14. E2E smoke

- [ ] e2e smoke pass

Validate:

```bash
python backend/tests/e2e_smoke.py --base-url https://social-listening-v3.blackbirdzzzz.art
```

---

## F. Van hanh nhanh

### Logs

```bash
docker compose logs -f app
```

### Restart

```bash
docker compose restart app
```

### Stop

```bash
docker compose down
```
