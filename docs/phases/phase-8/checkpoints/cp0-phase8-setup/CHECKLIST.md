# CP0 Validation Checklist — Phase 8 Setup

### CHECK-01: Bo doc Phase 8 da day du

```bash
find docs/phases/phase-8 -maxdepth 2 -type f | sort
```

### CHECK-02: He thong checkpoint Phase 8 ton tai

```bash
find docs/phases/phase-8/checkpoints -maxdepth 2 -type f | sort
```

### CHECK-03: Scope Phase 8 da khoa dung huong

```bash
rg -n "API models|validity_spec|hybrid|self-host" docs/phases/phase-8
```
