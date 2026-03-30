# CP4 Validation Checklist — Mobile noVNC Customization

### CHECK-01: Custom mobile VNC page ton tai

```bash
curl -I http://127.0.0.1:6080/mobile.html
```

### CHECK-02: Fallback noVNC pages van ton tai

```bash
curl -I http://127.0.0.1:6080/vnc.html && curl -I http://127.0.0.1:6080/vnc_lite.html
```
