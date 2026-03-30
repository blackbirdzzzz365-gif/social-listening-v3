# CP5 — Clean Payload + AI Guardrail

**Code:** cp5-clean-payload-ai-guardrail
**Order:** 5
**Depends On:** cp4-selective-expansion-comments
**Estimated Effort:** 1 ngay

## Muc tieu

Lam sach payload truoc labeling/theme va chi cho phep records dat chat luong toi thieu di vao AI theo mode `strict` hoac `balanced`.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/services/*` | modified | Clean payload builder, dedupe, quality flags, AI eligibility |
| `backend/app/models/*` | modified | Fields neu can de luu quality flags / AI queue state |
| `backend/tests/*` | modified | Tests cho clean payload va strict/balanced guardrail |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Co clean payload stage cho accepted records | ✓ |
| CHECK-02 | Co quality flags / dedupe logic toi thieu | ✓ |
| CHECK-03 | Rejected records khong vao AI queue; uncertain records phu thuoc mode | ✓ |
