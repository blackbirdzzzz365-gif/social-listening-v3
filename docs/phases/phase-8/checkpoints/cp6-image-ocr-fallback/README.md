# CP6 — Image OCR / Vision Fallback

**Code:** cp6-image-ocr-fallback
**Order:** 6
**Depends On:** cp5-comment-policy-gating
**Estimated Effort:** 1-1.5 ngay

## Muc tieu

Them image-aware gating co dieu kien, chi goi OCR/vision khi can de nang precision cho image-bearing posts ma khong no cost.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/infra/*` | modified | OCR / vision fallback adapter neu can |
| `backend/app/services/*` | modified | Trigger policy va result aggregation |
| `backend/tests/*` | modified | Test cho image-present uncertain flow |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | OCR/vision khong chay cho moi post mac dinh | ✓ |
| CHECK-02 | Co trigger ro rang cho uncertain + image hoac spec yeu cau visual evidence | ✓ |
| CHECK-03 | Final judge result ghi nhan viec co dung image understanding | ✓ |
