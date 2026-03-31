from __future__ import annotations


def build_context_map(posts: list[dict[str, str | None]]) -> dict[str, dict[str, str | None]]:
    context_map: dict[str, dict[str, str | None]] = {}
    for post in posts:
        post_id = str(post["post_id"])
        context_map[post_id] = {
            "post_id": post_id,
            "record_type": str(post.get("record_type") or "POST"),
            "summary": str(post.get("content_masked") or post.get("content") or "")[:240],
            "parent_post_id": str(post.get("parent_post_id") or "") or None,
        }
    return context_map


def build_record_context(
    post: dict[str, str | None],
    context_map: dict[str, dict[str, str | None]],
) -> dict[str, str | None]:
    if str(post.get("record_type") or "POST") != "COMMENT":
        return {
            "parent_post_summary": None,
            "parent_comment_summary": None,
            "thread_context": None,
        }

    parent_comment_summary: str | None = None
    parent_post_summary: str | None = None
    visited: set[str] = set()
    parent_id = str(post.get("parent_post_id") or "")
    current = context_map.get(parent_id)

    while current is not None:
        current_id = str(current.get("post_id") or "")
        if not current_id or current_id in visited:
            break
        visited.add(current_id)
        summary = str(current.get("summary") or "")[:240] or None
        record_type = str(current.get("record_type") or "POST")
        if record_type == "COMMENT" and parent_comment_summary is None:
            parent_comment_summary = summary
        if record_type == "POST":
            parent_post_summary = summary
            break
        next_parent_id = str(current.get("parent_post_id") or "")
        current = context_map.get(next_parent_id) if next_parent_id else None

    thread_parts: list[str] = []
    if parent_post_summary:
        thread_parts.append(f"Parent post: {parent_post_summary}")
    if parent_comment_summary:
        thread_parts.append(f"Parent comment: {parent_comment_summary}")
    return {
        "parent_post_summary": parent_post_summary,
        "parent_comment_summary": parent_comment_summary,
        "thread_context": "\n".join(thread_parts) if thread_parts else None,
    }
