# CP1 — Browser Run Safety

**Code:** cp1-browser-run-safety
**Order:** 1
**Depends On:** cp0-phase9-setup
**Estimated Effort:** 1 ngay

## Muc tieu

Chan concurrent browser-backed runs dung chung persistent profile, them lease/admission control, va tach ro infra browser failure khoi logic failure.

## Artifacts du kien

| File/Path | Action | Mo ta |
|-----------|--------|-------|
| `backend/app/infra/browser_agent.py` | modified | Lease-safe browser profile startup / shutdown |
| `backend/app/services/runner.py` | modified | Run admission, queued/busy state, release on terminal |
| `backend/app/models/*` | modified | Run failure class / admission state neu can |
| `backend/alembic/versions/*` | created | Migration cho state moi |
| `backend/tests/*` | modified | Test lease, busy admission, infra failure taxonomy |

## Checklist Validator

| ID | Mo ta | Blocker |
|----|-------|---------|
| CHECK-01 | Chi co 1 run browser-backed active tren 1 execution slot | ✓ |
| CHECK-02 | Run thu 2 duoc queue/block voi reason ro rang | ✓ |
| CHECK-03 | Browser boot failure co failure class rieng, khong danh dong voi logic failure | ✓ |
