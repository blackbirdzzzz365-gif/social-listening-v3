# CP2 — Post Candidate Scoring

1. Chot minimal-change path: mo rong `crawled_posts`, khong tao bang candidates rieng o slice dau
2. Them migration + model fields cho pre-AI status, score, reason, query/source metadata
3. Implement deterministic scoring cho post theo `anchor`, `related`, `negative`, `quality`, `source`
4. Viet tests cho states `ACCEPTED`, `REJECTED`, `UNCERTAIN`
