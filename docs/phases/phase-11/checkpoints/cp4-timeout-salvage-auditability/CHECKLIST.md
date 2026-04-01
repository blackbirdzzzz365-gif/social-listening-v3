# CP4 Validation Checklist - Timeout Salvage And Auditability

### CHECK-01: Co salvage metadata hoac snapshot path

```bash
rg -n "salvage|collected_count|persisted_count|lost_before_persist" backend
```
