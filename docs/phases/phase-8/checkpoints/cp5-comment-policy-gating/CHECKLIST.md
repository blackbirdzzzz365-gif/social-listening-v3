# CP5 Validation Checklist — Comment Policy Gating

### CHECK-01: Co comment policy rieng

```bash
rg -n "comment policy|transactional|parent context|end-user insight" backend/app/services
```

### CHECK-02: Co luat chan transactional-only comments

```bash
rg -n "xin gia|ib|check inbox|transactional" backend/app
```

### CHECK-03: Co test cho comment gating

```bash
rg -n "comment policy|parent context|transactional comment|xin gia|ib" backend/tests
```
