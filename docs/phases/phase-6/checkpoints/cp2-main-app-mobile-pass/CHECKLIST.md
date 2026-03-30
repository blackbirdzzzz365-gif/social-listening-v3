# CP2 Validation Checklist — Main App Mobile Pass

### CHECK-01: App frontend build xanh

```bash
cd frontend && npm run build
```

### CHECK-02: Khong con overflow-prone layout patterns ro rang

```bash
rg -n "justify-content: space-between|maw=|Group justify=\"space-between\"" frontend/src
```
