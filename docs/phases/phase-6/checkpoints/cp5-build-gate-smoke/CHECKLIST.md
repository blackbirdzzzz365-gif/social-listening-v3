# CP5 Validation Checklist — Build Gate + Smoke

### CHECK-01: Frontend build xanh

```bash
cd frontend && npm run build
```

### CHECK-02: Browser smoke routes xanh

```bash
curl -I http://127.0.0.1:6080/ && curl -I http://127.0.0.1:6080/mobile.html && curl -I http://127.0.0.1:6080/vnc.html
```
