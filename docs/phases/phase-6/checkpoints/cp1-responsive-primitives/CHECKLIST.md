# CP1 Validation Checklist — Responsive Primitives

### CHECK-01: Shell primitives co responsive behavior ro rang

```bash
rg -n "visibleFrom|hiddenFrom|SimpleGrid|Stack|wrap=|gap=|px=|py=" frontend/src/app/shell frontend/src/components/ui
```

### CHECK-02: Build frontend thanh cong

```bash
cd frontend && npm run build
```
