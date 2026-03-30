# CP3 Validation Checklist — Browser Entry Web

### CHECK-01: Browser root khong con directory listing

```bash
curl -s http://127.0.0.1:6080/ | head -n 20
```

### CHECK-02: Browser entry page co links noVNC/help

```bash
curl -s http://127.0.0.1:6080/ | rg -n "noVNC|fullscreen|keyboard|Reconnect|Open Browser"
```
