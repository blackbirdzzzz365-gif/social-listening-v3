# CP3 — Batch Health Gating

1. Gan query execution vao loop nho theo batch ~20 posts
2. Sau moi batch, tinh accepted ratio, uncertain ratio, strong accept count
3. Implement decision `continue`, `downgrade`, `stop`
4. Dam bao path yeu dung som de chuyen sang query/source path khac
5. Them tests cho 2 consecutive weak batches va healthy batch continuation
