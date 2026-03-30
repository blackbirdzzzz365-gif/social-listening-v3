# CP6 — AI Provider Failover + Telemetry

1. Refactor `AIClient` de tach retryable provider failure ra khoi deterministic validation bugs
2. Them retry ngan tren primary provider neu loi retryable
3. Cho phep Claude fallback chi sau khi primary that bai theo nhom loi duoc phep
4. Ghi provider metadata de phuc vu audit cost va reliability
5. Them tests cho timeout, 429/5xx, invalid envelope, va invalid payload/prompt cases
