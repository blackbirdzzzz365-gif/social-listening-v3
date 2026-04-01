from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from camoufox.async_api import AsyncCamoufox
from camoufox.addons import DefaultAddons

from app.infra.event_bus import HealthSignal
from app.infra.pii_masker import PIIMasker
from app.infrastructure.config import Settings


class SessionExpiredException(RuntimeError):
    pass


class BrowserStartupError(RuntimeError):
    pass


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class RawPost(dict):
    post_id: str
    group_id_hash: str
    content: str
    record_type: str
    source_url: str | None
    parent_post_id: str | None
    parent_post_url: str | None
    posted_at: str | None
    reaction_count: int
    comment_count: int


class BrowserAgent:
    def __init__(self, event_queue: asyncio.Queue[HealthSignal], settings: Settings) -> None:
        self._event_queue = event_queue
        self._settings = settings
        self._profile_dir = Path(settings.browser_profile_dir)
        self._mock_session_file = self._profile_dir / "mock-session.json"
        self._pii_masker = PIIMasker()
        self._browser_cm: Any | None = None
        self._browser: Any | None = None
        self._page: Any | None = None
        self._screen_size = (
            settings.browser_screen_width,
            settings.browser_screen_height,
        )

    async def start(self) -> None:
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        if self._settings.browser_mock_mode or self._browser is not None:
            return

        self._prepare_profile_dir()

        exclude_addons: list[DefaultAddons] = []
        if not self._default_ubo_manifest_exists():
            exclude_addons.append(DefaultAddons.UBO)

        self._browser_cm = AsyncCamoufox(
            headless=self._settings.camoufox_headless,
            geoip=True,
            humanize=True,
            persistent_context=True,
            user_data_dir=str(self._profile_dir),
            window=self._screen_size,
            exclude_addons=exclude_addons,
        )
        try:
            self._browser = await self._browser_cm.__aenter__()
            self._page = await self._browser.new_page()
            await self._page.set_viewport_size(
                {
                    "width": self._settings.browser_screen_width,
                    "height": self._settings.browser_screen_height,
                }
            )
            await self._page.route("**/*", self._on_route)
        except Exception as exc:
            self._browser = None
            self._page = None
            if self._browser_cm is not None:
                try:
                    await self._browser_cm.__aexit__(type(exc), exc, exc.__traceback__)
                except Exception:
                    pass
            self._browser_cm = None
            raise BrowserStartupError(f"browser startup failed: {exc}") from exc

    def _prepare_profile_dir(self) -> None:
        cleanup_targets = [
            self._profile_dir / ".parentlock",
            self._profile_dir / "lock",
            self._profile_dir / "cert_override.txt",
            self._profile_dir / "sessionCheckpoints.json",
            self._profile_dir / "xulstore.json",
        ]
        for target in cleanup_targets:
            if target.exists() or target.is_symlink():
                target.unlink()

        sessionstore_dir = self._profile_dir / "sessionstore-backups"
        if sessionstore_dir.exists():
            for child in sessionstore_dir.iterdir():
                if child.is_file() or child.is_symlink():
                    child.unlink()

        user_js = self._profile_dir / "user.js"
        user_js.write_text(
            "\n".join(
                [
                    'user_pref("browser.bookmarks.restore_default_bookmarks", false);',
                    'user_pref("browser.sessionstore.resume_from_crash", false);',
                    'user_pref("browser.sessionstore.max_resumed_crashes", 0);',
                    'user_pref("browser.startup.page", 0);',
                    'user_pref("browser.toolbars.bookmarks.visibility", "never");',
                    'user_pref("sidebar.backupState", "{\\"width\\":\\"\\",\\"command\\":\\"\\",\\"expanded\\":false,\\"hidden\\":true}");',
                    'user_pref("layout.css.devPixelsPerPx", "0.95");',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self._remove_legacy_local_certificates()

    def _remove_legacy_local_certificates(self) -> None:
        certutil_path = shutil.which("certutil")
        cert_db = self._profile_dir / "cert9.db"
        if not certutil_path or not cert_db.exists():
            return

        db_path = f"sql:{self._profile_dir}"
        result = subprocess.run(
            [certutil_path, "-L", "-d", db_path],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return

        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("Certificate Nickname") or stripped.startswith("--"):
                continue
            match = re.match(r"^(?P<nickname>.+?)\s+[A-Za-z,]+$", stripped)
            if not match:
                continue
            nickname = match.group("nickname").strip()
            if not nickname.startswith("local-"):
                continue
            subprocess.run(
                [certutil_path, "-D", "-d", db_path, "-n", nickname],
                check=False,
                capture_output=True,
                text=True,
            )

    def _default_ubo_manifest_exists(self) -> bool:
        return Path("/root/.cache/camoufox/addons/UBO/manifest.json").exists()

    async def stop(self) -> None:
        if self._browser_cm is None:
            return

        await self._browser_cm.__aexit__(None, None, None)
        self._browser_cm = None
        self._browser = None
        self._page = None

    async def is_logged_in(self) -> bool:
        if self._settings.browser_mock_mode:
            return self._mock_session_file.exists()

        await self.start()
        assert self._page is not None
        await self._page.goto("https://www.facebook.com", wait_until="domcontentloaded")
        return await self._get_logged_in_user_id() is not None

    async def wait_for_login(self) -> str:
        await self.start()
        if self._settings.browser_mock_mode:
            account_id_hash = self._hash_account_id(self._settings.browser_mock_user_id)
            self._mock_session_file.write_text(
                json.dumps({"account_id_hash": account_id_hash}, indent=2),
                encoding="utf-8",
            )
            await asyncio.sleep(0.1)
            return account_id_hash

        assert self._page is not None
        await self._open_login_form()
        while True:
            fb_uid = await self._get_logged_in_user_id()
            if fb_uid:
                return self._hash_account_id(fb_uid)
            await asyncio.sleep(2)

    async def assert_session_valid(self) -> None:
        if not await self.is_logged_in():
            await self._event_queue.put(
                HealthSignal(signal_type="SESSION_EXPIRED", raw_signal={"source": "browser_agent"})
            )
            raise SessionExpiredException("Facebook session expired")

    async def emit_signal(self, signal_type: str, raw_signal: dict[str, Any] | None = None) -> None:
        await self._event_queue.put(HealthSignal(signal_type=signal_type, raw_signal=raw_signal))

    def load_persisted_account_hash(self) -> str | None:
        if not self._mock_session_file.exists():
            return None
        payload = json.loads(self._mock_session_file.read_text(encoding="utf-8"))
        return payload.get("account_id_hash")

    async def search_groups(
        self,
        query: str,
        *,
        target_count: int = 3,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        await self.assert_session_valid()
        await self.start()
        assert self._page is not None
        await self._emit_progress(
            progress_callback,
            {
                "activity": "navigating_group_search",
                "query": query,
                "target_count": target_count,
            },
        )
        await self._page.goto(
            f"https://www.facebook.com/search/groups/?q={quote(query)}",
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(3)

        groups: list[dict[str, str]] = []
        seen_group_ids: set[str] = set()
        anchors = await self._page.locator('a[href*="/groups/"]').all()
        for anchor in anchors:
            href = await anchor.get_attribute("href")
            if not href:
                continue
            group_id = self._extract_group_id(href)
            if not group_id or group_id in seen_group_ids:
                continue
            name = (await anchor.inner_text(timeout=1000)).strip() or group_id
            card_text = await anchor.evaluate(
                """(el) => {
                    const parent = el.closest('[role="article"]') || el.parentElement || el;
                    return (parent.innerText || el.innerText || '').trim();
                }"""
            )
            privacy = self._detect_group_privacy(card_text or name)
            groups.append(
                {
                    "group_id": group_id,
                    "name": re.sub(r"\s+", " ", name),
                    "privacy": privacy,
                }
            )
            seen_group_ids.add(group_id)
            await self._emit_progress(
                progress_callback,
                {
                    "activity": "scanning_group_cards",
                    "query": query,
                    "discovered_groups": len(groups),
                },
            )
            if len(groups) >= target_count:
                break

        if not groups:
            normalized = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-") or "research"
            groups = [
                {
                    "group_id": f"{normalized}-community",
                    "name": f"{query} Community",
                    "privacy": "PUBLIC",
                }
            ]
        primary_group = next((group for group in groups if group["privacy"] == "PUBLIC"), groups[0])
        return {
            "groups": groups[:target_count],
            "primary_group_id": primary_group["group_id"],
        }

    async def join_group(
        self,
        group_id: str,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        await self.assert_session_valid()
        if self._settings.browser_mock_mode:
            await asyncio.sleep(0.2)
            return {
                "group_id": group_id,
                "status": "requested",
                "confirmed": True,
            }

        await self.start()
        assert self._page is not None
        await self._emit_progress(progress_callback, {"activity": "opening_group", "group_id": group_id})
        await self._page.goto(f"https://www.facebook.com/groups/{group_id}", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        initial_state = await self._inspect_group_state(group_id)
        if initial_state["status"] == "approved":
            return {
                "group_id": group_id,
                "status": "already_member",
                "confirmed": True,
                "privacy": initial_state["privacy"],
                "can_access": True,
            }
        if initial_state["status"] in {"pending", "blocked", "unanswered"}:
            return {
                "group_id": group_id,
                "status": initial_state["status"],
                "confirmed": initial_state["status"] == "pending",
                "privacy": initial_state["privacy"],
                "can_access": initial_state["can_access"],
                "action_labels": initial_state["action_labels"],
            }

        join_selectors = [
            'div[role="button"]:has-text("Join group")',
            'div[role="button"]:has-text("Tham gia nhóm")',
            'div[role="button"]:has-text("Tham gia")',
            'a[role="button"]:has-text("Join group")',
            'a[role="button"]:has-text("Tham gia nhóm")',
        ]
        clicked = False
        for selector in join_selectors:
            locator = self._page.locator(selector).first
            if await locator.count():
                try:
                    await self._emit_progress(progress_callback, {"activity": "clicking_join", "group_id": group_id})
                    await locator.click(timeout=3000)
                    await asyncio.sleep(2)
                    clicked = True
                    break
                except Exception:
                    continue

        refreshed_state = await self._inspect_group_state(group_id)
        status = refreshed_state["status"]
        if status == "pending":
            response_status = "requested"
        elif status == "approved":
            response_status = "already_member"
        elif not clicked:
            response_status = "not_joined"
        else:
            response_status = status
        return {
            "group_id": group_id,
            "status": response_status,
            "confirmed": response_status in {"requested", "already_member"},
            "privacy": refreshed_state["privacy"],
            "can_access": refreshed_state["can_access"],
            "action_labels": refreshed_state["action_labels"],
        }

    async def check_join_status(
        self,
        group_id: str,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        await self.assert_session_valid()
        if self._settings.browser_mock_mode:
            await asyncio.sleep(0.1)
            approved = int(hashlib.sha256(group_id.encode("utf-8")).hexdigest(), 16) % 2 == 0
            return {
                "group_id": group_id,
                "status": "approved" if approved else "pending",
                "can_access": approved,
                "privacy": "PRIVATE",
                "action_labels": ["Joined"] if approved else ["Pending"],
            }

        await self.start()
        assert self._page is not None
        await self._emit_progress(progress_callback, {"activity": "checking_membership", "group_id": group_id})
        await self._page.goto(f"https://www.facebook.com/groups/{group_id}", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        state = await self._inspect_group_state(group_id)
        return {
            "group_id": group_id,
            "status": state["status"],
            "can_access": state["can_access"],
            "privacy": state["privacy"],
            "action_labels": state["action_labels"],
        }

    async def search_posts(
        self,
        query: str,
        *,
        target_count: int = 10,
        filter_recent: bool = True,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        await self.assert_session_valid()
        if self._settings.browser_mock_mode:
            return self._build_mock_search_posts(query, target_count)

        await self.start()
        assert self._page is not None
        await self._emit_progress(
            progress_callback,
            {
                "activity": "navigating_post_search",
                "query": query,
                "target_count": target_count,
            },
        )
        await self._page.goto(
            f"https://www.facebook.com/search/posts/?q={quote(query)}",
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(3)

        if filter_recent:
            await self._emit_progress(progress_callback, {"activity": "applying_recent_filter", "query": query})
            await self._apply_recent_filter()

        posts: list[dict[str, Any]] = []
        seen_post_ids: set[str] = set()
        discovered_groups: dict[str, dict[str, str]] = {}
        idle_scrolls = 0

        while len(posts) < target_count:
            articles = await self._page.locator('[role="article"]').all()
            before_count = len(posts)

            for article in articles[len(posts):]:
                if len(posts) >= target_count:
                    break
                post_data = await self._extract_post_from_search(article)
                if not post_data or post_data["post_id"] in seen_post_ids:
                    continue
                seen_post_ids.add(post_data["post_id"])
                posts.append(post_data)
                if post_data.get("source_group_id"):
                    gid = post_data["source_group_id"]
                    if gid not in discovered_groups:
                        discovered_groups[gid] = {
                            "group_id": gid,
                            "name": post_data.get("source_group_name") or gid,
                            "privacy": post_data.get("source_group_privacy") or "UNKNOWN",
                            "status": post_data.get("source_group_status") or "unknown",
                            "can_access": bool(post_data.get("source_group_can_access")),
                        }
                await self._emit_progress(
                    progress_callback,
                    {
                        "activity": "scanning_search_results",
                        "query": query,
                        "collected_count": len(posts),
                        "sample_candidates": self._build_progress_samples(posts),
                        "image_candidate_count": self._count_visual_candidates(posts),
                        "discovered_group_count": len(discovered_groups),
                        "idle_scrolls": idle_scrolls,
                    },
                )

            if len(posts) == before_count:
                idle_scrolls += 1
            else:
                idle_scrolls = 0
            if idle_scrolls >= 4 or len(posts) >= target_count:
                break
            await self._page.mouse.wheel(0, 1600)
            await asyncio.sleep(3)

        for group_id, group in list(discovered_groups.items()):
            await self._emit_progress(
                progress_callback,
                {
                    "activity": "inspecting_discovered_group",
                    "group_id": group_id,
                    "query": query,
                },
            )
            await self._page.goto(
                f"https://www.facebook.com/groups/{group_id}",
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(2)
            real_name = await self._extract_group_name_from_page(group_id)
            if real_name:
                group["name"] = real_name
            inspected = await self._inspect_group_state(group_id, fallback_name=group["name"])
            group["privacy"] = inspected["privacy"]
            group["status"] = inspected["status"]
            group["can_access"] = inspected["can_access"]

        return {
            "posts": posts[:target_count],
            "discovered_groups": list(discovered_groups.values()),
        }

    async def crawl_comments(
        self,
        post_url: str,
        *,
        target_count: int = 20,
        parent_post_id: str | None = None,
        source_group_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> list[RawPost]:
        await self.assert_session_valid()
        if self._settings.browser_mock_mode:
            return self._build_mock_comments(post_url, target_count, source_group_id=source_group_id)

        await self.start()
        assert self._page is not None
        await self._emit_progress(
            progress_callback,
            {
                "activity": "opening_post_for_comments",
                "post_url": post_url,
                "target_count": target_count,
            },
        )
        await self._page.goto(post_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        idle_expands = 0
        for _ in range(20):
            expand_selectors = [
                'div[role="button"]:has-text("Xem thêm bình luận")',
                'div[role="button"]:has-text("View more comments")',
                'div[role="button"]:has-text("Xem thêm")',
                'span:has-text("View more comments")',
            ]
            clicked = False
            for selector in expand_selectors:
                locator = self._page.locator(selector).first
                if await locator.count():
                    try:
                        await locator.click(timeout=3000)
                        await asyncio.sleep(2)
                        clicked = True
                        await self._emit_progress(
                            progress_callback,
                            {
                                "activity": "expanding_comments",
                                "post_url": post_url,
                                "idle_expands": idle_expands,
                            },
                        )
                        break
                    except Exception:
                        continue
            if not clicked:
                idle_expands += 1
            else:
                idle_expands = 0
            if idle_expands >= 3:
                break

        reply_selectors = [
            'div[role="button"]:has-text("phản hồi")',
            'div[role="button"]:has-text("replies")',
        ]
        for selector in reply_selectors:
            for locator in await self._page.locator(selector).all():
                try:
                    await locator.click(timeout=2000)
                    await asyncio.sleep(1)
                except Exception:
                    continue

        parent_id = parent_post_id or self._post_id_from_url(post_url)
        source_group = source_group_id or await self._extract_group_id_from_current_page()
        group_hash = self._resolve_group_hash(source_group, fallback_seed=parent_id)
        articles = await self._page.locator('[role="article"]').all()
        comments: list[RawPost] = []
        comment_stack: list[dict[str, Any]] = [
            {
                "post_id": parent_id,
                "source_url": post_url,
                "indent": -1.0,
            }
        ]
        baseline_indent: float | None = None
        for index, article in enumerate(articles[1:], start=1):
            if len(comments) >= target_count:
                break
            text = await article.inner_text(timeout=2000)
            masked = self._pii_masker.mask(text.strip())
            if not masked or len(masked) < 5:
                continue
            comment_url = await self._extract_best_url_from_locator(
                article,
                ['a[href*="comment_id="]', 'a[href*="/posts/"]', 'a[href*="/permalink/"]'],
            )
            bounding_box = await article.bounding_box()
            absolute_indent = float((bounding_box or {}).get("x") or 0.0)
            if baseline_indent is None:
                baseline_indent = absolute_indent
            normalized_indent = max(0.0, absolute_indent - baseline_indent)
            while len(comment_stack) > 1 and normalized_indent <= (comment_stack[-1]["indent"] + 8.0):
                comment_stack.pop()
            parent_ref = comment_stack[0]
            if len(comment_stack) > 1 and normalized_indent >= (comment_stack[-1]["indent"] + 18.0):
                parent_ref = comment_stack[-1]
            else:
                comment_stack = comment_stack[:1]
            comment_id = self._comment_id_from_context(
                parent_post_id=parent_ref["post_id"],
                comment_url=comment_url,
                comment_text=masked,
                ordinal=index,
            )
            comments.append(
                RawPost(
                    post_id=comment_id,
                    group_id_hash=group_hash,
                    content=masked,
                    record_type="COMMENT",
                    source_url=comment_url,
                    parent_post_id=parent_ref["post_id"],
                    parent_post_url=parent_ref.get("source_url") or post_url,
                    posted_at=None,
                    reaction_count=0,
                    comment_count=0,
                    **(await self._extract_image_context_from_locator(article)),
                )
            )
            comment_stack.append(
                {
                    "post_id": comment_id,
                    "source_url": comment_url,
                    "indent": normalized_indent,
                }
            )
            await self._emit_progress(
                progress_callback,
                {
                    "activity": "extracting_comments",
                    "post_url": post_url,
                    "collected_count": len(comments),
                    "sample_candidates": self._build_progress_samples(comments),
                    "image_candidate_count": self._count_visual_candidates(comments),
                },
            )
        return comments

    async def search_in_group(
        self,
        group_id: str,
        query: str,
        *,
        target_count: int = 10,
        progress_callback: ProgressCallback | None = None,
    ) -> list[RawPost]:
        await self.assert_session_valid()
        if self._settings.browser_mock_mode:
            return self._build_mock_in_group_posts(group_id, query, target_count)

        await self.start()
        assert self._page is not None
        url = f"https://www.facebook.com/groups/{group_id}/search/?q={quote(query)}"
        await self._emit_progress(
            progress_callback,
            {
                "activity": "navigating_group_post_search",
                "group_id": group_id,
                "query": query,
                "target_count": target_count,
            },
        )
        await self._page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        if not await self._is_group_accessible():
            return []

        posts: list[RawPost] = []
        idle_scrolls = 0
        group_hash = self.hash_group_id(group_id)

        while len(posts) < target_count:
            articles = await self._page.locator('[role="article"]').all()
            before_count = len(posts)
            for index, article in enumerate(articles[len(posts):], start=len(posts)):
                if len(posts) >= target_count:
                    break
                text = await article.inner_text(timeout=2000)
                masked = self._pii_masker.mask(text.strip())
                if not masked:
                    continue
                post_url = await self._extract_best_url_from_locator(
                    article,
                    ['a[href*="/posts/"]', 'a[href*="/permalink/"]', 'a[href*="story_fbid"]'],
                )
                posts.append(
                    RawPost(
                        post_id=self._post_id_from_context(
                            post_url=post_url,
                            content=masked,
                            fallback_seed=f"{group_id}:{query}:{index}",
                        ),
                        group_id_hash=group_hash,
                        content=masked,
                        record_type="POST",
                        source_url=post_url,
                        parent_post_id=None,
                        parent_post_url=None,
                        posted_at=None,
                        reaction_count=0,
                        comment_count=0,
                        **(await self._extract_image_context_from_locator(article)),
                    )
                )
                await self._emit_progress(
                    progress_callback,
                    {
                        "activity": "scanning_group_results",
                        "group_id": group_id,
                        "query": query,
                        "collected_count": len(posts),
                        "sample_candidates": self._build_progress_samples(posts),
                        "image_candidate_count": self._count_visual_candidates(posts),
                        "idle_scrolls": idle_scrolls,
                    },
                )
            if len(posts) == before_count:
                idle_scrolls += 1
            else:
                idle_scrolls = 0
            if idle_scrolls >= 4 or len(posts) >= target_count:
                break
            await self._page.mouse.wheel(0, 1600)
            await asyncio.sleep(3)

        return posts

    async def crawl_feed(
        self,
        group_id: str,
        target_count: int,
        checkpoint: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> list[RawPost]:
        await self.assert_session_valid()
        start_index = int((checkpoint or {}).get("collected_count", 0))
        if self._settings.browser_mock_mode:
            posts = self._build_mock_posts(group_id)
            collected: list[RawPost] = []
            for post in posts[start_index:target_count]:
                await asyncio.sleep(1)
                collected.append(post)
            return collected

        await self.start()
        assert self._page is not None
        url = f"https://www.facebook.com/groups/{group_id}"
        await self._emit_progress(
            progress_callback,
            {
                "activity": "opening_group_feed",
                "group_id": group_id,
                "target_count": target_count,
                "resume_from": start_index,
            },
        )
        await self._page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        posts: list[RawPost] = []
        idle_scrolls = 0
        while len(posts) + start_index < target_count:
            await asyncio.sleep(5)
            handles = await self._page.locator('[role="article"]').all()
            before_count = len(posts)
            for index, handle in enumerate(handles[start_index + len(posts):], start=start_index + len(posts)):
                text = await handle.inner_text(timeout=2000)
                masked = self._pii_masker.mask(text.strip())
                if not masked:
                    continue
                post_url = await self._extract_best_url_from_locator(
                    handle,
                    ['a[href*="/posts/"]', 'a[href*="/permalink/"]', 'a[href*="story_fbid"]'],
                )
                posts.append(
                    RawPost(
                        post_id=self._post_id_from_context(
                            post_url=post_url,
                            content=masked,
                            fallback_seed=f"{group_id}:{index}",
                        ),
                        group_id_hash=self.hash_group_id(group_id),
                        content=masked,
                        record_type="POST",
                        source_url=post_url,
                        parent_post_id=None,
                        parent_post_url=None,
                        posted_at=None,
                        reaction_count=0,
                        comment_count=0,
                        **(await self._extract_image_context_from_locator(handle)),
                    )
                )
                await self._emit_progress(
                    progress_callback,
                    {
                        "activity": "scanning_feed_posts",
                        "group_id": group_id,
                        "collected_count": len(posts) + start_index,
                        "sample_candidates": self._build_progress_samples(posts, offset=start_index),
                        "image_candidate_count": self._count_visual_candidates(posts),
                        "idle_scrolls": idle_scrolls,
                    },
                )
                if len(posts) + start_index >= target_count:
                    break
            if len(posts) + start_index >= target_count:
                break
            if len(posts) == before_count:
                idle_scrolls += 1
            else:
                idle_scrolls = 0
            if idle_scrolls >= 4:
                break
            await self._page.mouse.wheel(0, 1600)

        return posts

    async def _on_route(self, route: Any) -> None:
        request = route.request
        url = request.url.lower()
        await route.continue_()

        if "captcha" in url or "checkpoint" in url:
            await self.emit_signal("CAPTCHA", {"url": request.url})
        elif "action" in url and "blocked" in url:
            await self.emit_signal("ACTION_BLOCKED", {"url": request.url})
        elif "login" in url:
            await self.emit_signal("SESSION_EXPIRED", {"url": request.url})

    async def _get_logged_in_user_id(self) -> str | None:
        assert self._page is not None
        cookies = await self._page.context.cookies()
        fb_uid = next((cookie["value"] for cookie in cookies if cookie["name"] == "c_user"), "")
        return fb_uid or None

    async def _open_login_form(self) -> None:
        assert self._page is not None
        for url in (
            "https://m.facebook.com/login",
            "https://mbasic.facebook.com/login",
            "https://www.facebook.com/login",
        ):
            try:
                await self._page.goto(url, wait_until="domcontentloaded")
            except Exception:
                # Facebook may redirect between login surfaces while the page is stabilizing.
                pass
            try:
                await self._page.keyboard.press("Escape")
            except Exception:
                pass
            await self._dismiss_cookie_banner()
            email = self._page.locator('input[name="email"]')
            password = self._page.locator('input[name="pass"]')
            try:
                await email.first.wait_for(state="visible", timeout=3000)
                await password.first.wait_for(state="visible", timeout=3000)
                await email.scroll_into_view_if_needed()
                await email.focus()
                return
            except Exception:
                continue

    async def _dismiss_cookie_banner(self) -> None:
        assert self._page is not None
        selectors = [
            '[aria-label="Từ chối cookie không bắt buộc"]',
            'button:has-text("Từ chối cookie không bắt buộc")',
            'div[role="button"]:has-text("Từ chối cookie không bắt buộc")',
            '[aria-label="Reject optional cookies"]',
            'button:has-text("Reject optional cookies")',
            'div[role="button"]:has-text("Reject optional cookies")',
            '[aria-label="Only allow essential cookies"]',
            'button:has-text("Only allow essential cookies")',
            'div[role="button"]:has-text("Only allow essential cookies")',
            'button[aria-label="Close"]',
            'div[aria-label="Close"][role="button"]',
        ]
        for _ in range(4):
            for selector in selectors:
                locator = self._page.locator(selector).first
                if not await locator.count():
                    continue
                try:
                    await locator.wait_for(state="visible", timeout=1000)
                    await locator.click(timeout=2000, force=True)
                    await asyncio.sleep(1)
                    return
                except Exception:
                    continue
            await asyncio.sleep(0.5)

    async def _is_group_accessible(self) -> bool:
        assert self._page is not None
        if await self._page.locator('[role="article"]').count():
            return True
        page_text = (await self._page.locator("body").inner_text(timeout=2000)).lower()
        accessible_markers = ["write something", "viết gì đó", "discussion", "thảo luận", "members"]
        return any(marker in page_text for marker in accessible_markers)

    def _detect_group_privacy(self, text: str, *, default_value: str = "PUBLIC") -> str:
        normalized = text.lower()
        private_markers = ["private", "riêng tư", "closed", "kín"]
        public_markers = ["public", "công khai"]
        if any(marker in normalized for marker in private_markers):
            return "PRIVATE"
        if any(marker in normalized for marker in public_markers):
            return "PUBLIC"
        return default_value

    def _extract_group_id(self, href: str) -> str | None:
        match = re.search(r"/groups/([^/?#]+)/?", href)
        if not match:
            return None
        candidate = match.group(1).strip()
        if candidate in {"feed", "discover", "search", "category", "create", "membership_approval"}:
            return None
        return candidate

    def _hash_account_id(self, facebook_user_id: str) -> str:
        digest = hmac.new(
            self._settings.opaque_id_secret.encode("utf-8"),
            facebook_user_id.encode("utf-8"),
            hashlib.sha256,
        )
        return digest.hexdigest()

    def hash_group_id(self, group_id: str) -> str:
        digest = hmac.new(
            self._settings.opaque_id_secret.encode("utf-8"),
            group_id.encode("utf-8"),
            hashlib.sha256,
        )
        return digest.hexdigest()

    def _hash_stable_value(self, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest[:24]

    def _resolve_group_hash(self, group_id: str | None, *, fallback_seed: str) -> str:
        if group_id:
            return self.hash_group_id(group_id)
        return self.hash_group_id(f"scope:{fallback_seed}")

    async def _extract_best_url_from_locator(
        self,
        locator: Any,
        selectors: list[str],
    ) -> str | None:
        for selector in selectors:
            links = await locator.locator(selector).all()
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    normalized = self._normalize_facebook_content_url(href)
                    if normalized:
                        return normalized
        return None

    def _normalize_facebook_content_url(self, href: str) -> str | None:
        candidate = (href or "").strip()
        if not candidate or candidate.startswith("#"):
            return None
        if candidate.startswith("/"):
            candidate = f"https://www.facebook.com{candidate}"

        parsed = urlsplit(candidate)
        if "facebook.com" not in parsed.netloc:
            return None

        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        query = dict(query_items)
        path = parsed.path or ""

        if "/posts/" in path or "/permalink/" in path:
            kept_query = []
            if "comment_id" in query:
                kept_query.append(("comment_id", query["comment_id"]))
            return urlunsplit((parsed.scheme, parsed.netloc, path, urlencode(kept_query), ""))

        if "/groups/" in path and "multi_permalinks" in query:
            kept_query = [("multi_permalinks", query["multi_permalinks"])]
            if "comment_id" in query:
                kept_query.append(("comment_id", query["comment_id"]))
            return urlunsplit((parsed.scheme, parsed.netloc, path, urlencode(kept_query), ""))

        if path.endswith("/permalink.php") or path.endswith("/story.php"):
            kept_query = []
            for key in ("story_fbid", "fbid", "id", "comment_id"):
                if key in query:
                    kept_query.append((key, query[key]))
            if not kept_query:
                return None
            return urlunsplit((parsed.scheme, parsed.netloc, path, urlencode(kept_query), ""))

        return None

    async def _collect_action_labels(self) -> list[str]:
        assert self._page is not None
        labels: list[str] = []
        selectors = [
            'div[role="button"]',
            'a[role="button"]',
            'button',
        ]
        for selector in selectors:
            for locator in await self._page.locator(selector).all():
                try:
                    text = re.sub(r"\s+", " ", (await locator.inner_text(timeout=500)).strip())
                except Exception:
                    continue
                if not text:
                    continue
                lowered = text.lower()
                if any(
                    marker in lowered
                    for marker in (
                        "join",
                        "pending",
                        "requested",
                        "approved",
                        "member",
                        "tham gia",
                        "đang chờ",
                        "đã gửi",
                        "trả lời",
                        "câu hỏi",
                    )
                ):
                    labels.append(text)
        return self._dedupe_text(labels)

    async def _extract_group_id_from_current_page(self) -> str | None:
        assert self._page is not None
        anchors = await self._page.locator('a[href*="/groups/"]').all()
        for anchor in anchors:
            href = await anchor.get_attribute("href")
            if not href:
                continue
            group_id = self._extract_group_id(href)
            if group_id:
                return group_id
        current_url = self._page.url or ""
        return self._extract_group_id(current_url)

    async def _extract_group_name_from_page(self, group_id: str) -> str | None:
        assert self._page is not None
        try:
            name_selectors = [
                'h1 a[href*="/groups/"]',
                'h1 span',
                'h1',
            ]
            for selector in name_selectors:
                locator = self._page.locator(selector).first
                if await locator.count():
                    text = (await locator.inner_text(timeout=2000)).strip()
                    cleaned = re.sub(r"\s+", " ", text).strip()
                    if cleaned and cleaned != group_id and len(cleaned) > 1:
                        return cleaned

            title = await self._page.title()
            if title:
                cleaned = title.split("|")[0].strip()
                if cleaned and cleaned != group_id and "facebook" not in cleaned.lower():
                    return cleaned
        except Exception:
            pass
        return None

    async def _inspect_group_state(
        self,
        group_id: str,
        *,
        fallback_name: str | None = None,
    ) -> dict[str, Any]:
        assert self._page is not None
        page_text = (await self._page.locator("body").inner_text(timeout=2000)).lower()
        action_labels = await self._collect_action_labels()
        joined_access = await self._is_group_accessible()
        normalized_labels = " | ".join(action_labels).lower()

        privacy = self._detect_group_privacy(
            f"{page_text}\n{normalized_labels}\n{fallback_name or ''}",
            default_value="UNKNOWN",
        )
        status = "unknown"
        if joined_access:
            status = "approved"
        elif self._has_any_marker(page_text, normalized_labels, self._blocked_markers()):
            status = "blocked"
        elif self._has_any_marker(page_text, normalized_labels, self._question_markers()):
            status = "unanswered"
        elif self._has_any_marker(page_text, normalized_labels, self._pending_markers()):
            status = "pending"
        elif self._has_any_marker(page_text, normalized_labels, self._join_markers()):
            status = "not_joined"

        return {
            "group_id": group_id,
            "privacy": privacy,
            "status": status,
            "can_access": joined_access,
            "action_labels": action_labels,
        }

    def _has_any_marker(self, page_text: str, labels_text: str, markers: tuple[str, ...]) -> bool:
        searchable = f"{page_text}\n{labels_text}"
        return any(marker in searchable for marker in markers)

    def _pending_markers(self) -> tuple[str, ...]:
        return (
            "pending",
            "request sent",
            "requested",
            "đang chờ",
            "da gui yeu cau",
            "đã gửi yêu cầu",
            "cancel request",
            "hủy yêu cầu",
        )

    def _join_markers(self) -> tuple[str, ...]:
        return (
            "join group",
            "join",
            "tham gia nhóm",
            "tham gia",
            "become a member",
        )

    def _blocked_markers(self) -> tuple[str, ...]:
        return (
            "you can't do this right now",
            "action blocked",
            "temporarily blocked",
            "không thể thực hiện hành động này",
            "bị chặn",
            "không thể tham gia",
        )

    def _question_markers(self) -> tuple[str, ...]:
        return (
            "answer membership questions",
            "membership questions",
            "answer questions",
            "trả lời câu hỏi",
            "câu hỏi thành viên",
            "hoàn tất câu hỏi",
        )

    def _dedupe_text(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            lowered = value.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            ordered.append(value)
        return ordered

    async def _apply_recent_filter(self) -> None:
        assert self._page is not None
        try:
            filter_selectors = [
                'div[role="button"]:has-text("Bộ lọc")',
                'div[role="button"]:has-text("Filters")',
                'span:has-text("Bộ lọc")',
                'span:has-text("Filters")',
            ]
            for selector in filter_selectors:
                locator = self._page.locator(selector).first
                if await locator.count():
                    await locator.click(timeout=3000)
                    await asyncio.sleep(2)
                    break
            else:
                return

            recent_selectors = [
                'div[role="menuitemradio"]:has-text("Mới đây nhất")',
                'div[role="menuitemradio"]:has-text("Most recent")',
                'div[role="radio"]:has-text("Mới đây nhất")',
                'span:has-text("Mới đây nhất")',
                'span:has-text("Most recent")',
            ]
            for selector in recent_selectors:
                locator = self._page.locator(selector).first
                if await locator.count():
                    await locator.click(timeout=3000)
                    await asyncio.sleep(2)
                    break
        except Exception:
            pass

    async def _extract_post_from_search(self, article: Any) -> dict[str, Any] | None:
        assert self._page is not None
        try:
            text = await article.inner_text(timeout=3000)
            masked = self._pii_masker.mask(text.strip())
            if not masked or len(masked) < 10:
                return None

            post_url = await self._extract_best_url_from_locator(
                article,
                ['a[href*="multi_permalinks="]', 'a[href*="/posts/"]', 'a[href*="/permalink/"]', 'a[href*="story_fbid"]'],
            )
            if not post_url:
                return None
            post_id = self._post_id_from_context(
                post_url=post_url,
                content=masked,
                fallback_seed=masked[:120],
            )

            source_group_id = None
            source_group_name = None
            source_group_privacy = "UNKNOWN"
            source_group_status = "unknown"
            source_group_can_access = False
            group_links = await article.locator('a[href*="/groups/"]').all()
            for group_link in group_links:
                href = await group_link.get_attribute("href")
                if href:
                    gid = self._extract_group_id(href)
                    if gid:
                        source_group_id = gid
                        source_group_name = (await group_link.inner_text(timeout=1000)).strip() or gid
                        source_group_context = await group_link.evaluate(
                            """(el) => {
                                const parent = el.closest('[role="article"]') || el.parentElement || el;
                                return (parent.innerText || el.innerText || '').trim();
                            }"""
                        )
                        source_group_privacy = self._detect_group_privacy(
                            f"{source_group_context}\n{source_group_name}",
                            default_value="UNKNOWN",
                        )
                        source_group_status = "approved" if source_group_privacy == "PUBLIC" else "unknown"
                        source_group_can_access = source_group_privacy == "PUBLIC"
                        break

            return {
                "post_id": post_id,
                "post_url": post_url,
                "source_group_id": source_group_id,
                "source_group_name": source_group_name,
                "source_group_privacy": source_group_privacy,
                "source_group_status": source_group_status,
                "source_group_can_access": source_group_can_access,
                "content": masked,
                "posted_at": None,
                "reaction_count": 0,
                "comment_count": 0,
                **(await self._extract_image_context_from_locator(article)),
            }
        except Exception:
            return None

    async def _extract_image_context_from_locator(self, locator: Any) -> dict[str, Any]:
        image_urls: list[str] = []
        alt_texts: list[str] = []
        try:
            images = await locator.locator("img").all()
        except Exception:
            images = []

        for image in images[:8]:
            try:
                src = (await image.get_attribute("src") or "").strip()
            except Exception:
                src = ""
            if src.startswith("http") and ("fbcdn" in src or "scontent" in src or "cdn" in src):
                image_urls.append(src)
            try:
                alt = (await image.get_attribute("alt") or "").strip()
            except Exception:
                alt = ""
            if alt and len(alt) > 1:
                alt_texts.append(re.sub(r"\s+", " ", alt))

        image_urls = self._dedupe_text(image_urls)[:3]
        alt_texts = self._dedupe_text(alt_texts)[:3]
        if not image_urls and not alt_texts:
            return {}
        return {
            "image_urls": image_urls,
            "image_alt_text": " | ".join(alt_texts)[:500],
            "image_summary": (f"{len(image_urls)} image(s) detected" if image_urls else "image alt text detected"),
        }

    def _build_progress_samples(self, posts: list[dict[str, Any]], *, offset: int = 0) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        base_ordinal = max(1, len(posts) - 2 + offset)
        for ordinal, post in enumerate(posts[-3:], start=base_ordinal):
            content = re.sub(r"\s+", " ", str(post.get("content") or "")).strip()
            samples.append(
                {
                    "ordinal": ordinal,
                    "post_id": str(post.get("post_id") or ""),
                    "source_url": post.get("source_url"),
                    "source_group_id": post.get("source_group_id"),
                    "record_type": post.get("record_type", "POST"),
                    "content_preview": content[:180],
                    "has_image_context": bool(post.get("image_urls") or post.get("image_alt_text") or post.get("image_summary")),
                }
            )
        return samples

    def _count_visual_candidates(self, posts: list[dict[str, Any]]) -> int:
        return sum(
            1
            for post in posts
            if post.get("image_urls") or post.get("image_alt_text") or post.get("image_summary")
        )

    def _post_id_from_url(self, url: str) -> str:
        match = re.search(r"/posts/(\d+)", url)
        if match:
            return f"fb-post-{match.group(1)}"
        match = re.search(r"/permalink/(\d+)", url)
        if match:
            return f"fb-post-{match.group(1)}"
        match = re.search(r"multi_permalinks=(\d+)", url)
        if match:
            return f"fb-post-{match.group(1)}"
        match = re.search(r"story_fbid=(\d+)", url)
        if match:
            return f"fb-post-{match.group(1)}"
        normalized = url.split("?", 1)[0].strip().lower()
        if normalized:
            return f"fb-post-{self._hash_stable_value(normalized)}"
        return f"fb-post-{self._hash_stable_value(url)}"

    def _post_id_from_context(
        self,
        *,
        post_url: str | None,
        content: str,
        fallback_seed: str,
    ) -> str:
        if post_url:
            return self._post_id_from_url(post_url)
        normalized = re.sub(r"\s+", " ", content).strip().lower()[:160]
        return f"fb-post-{self._hash_stable_value(f'{fallback_seed}|{normalized}')}"

    def _comment_id_from_context(
        self,
        *,
        parent_post_id: str,
        comment_url: str | None,
        comment_text: str,
        ordinal: int,
    ) -> str:
        if comment_url:
            return f"fb-comment-{self._hash_stable_value(comment_url.lower())}"
        normalized = re.sub(r"\s+", " ", comment_text).strip().lower()[:120]
        return f"fb-comment-{self._hash_stable_value(f'{parent_post_id}|{ordinal}|{normalized}')}"

    async def _emit_progress(
        self,
        progress_callback: ProgressCallback | None,
        payload: dict[str, Any],
    ) -> None:
        if progress_callback is None:
            return
        maybe_coro = progress_callback(payload)
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro

    def _build_mock_search_posts(self, query: str, target_count: int) -> dict[str, Any]:
        groups = [
            {
                "group_id": "group-taichinh-vn",
                "name": "Tai Chinh Viet Nam",
                "privacy": "PUBLIC",
                "status": "approved",
                "can_access": True,
            },
            {
                "group_id": "group-the-tindung",
                "name": "Hoi The Tin Dung",
                "privacy": "PUBLIC",
                "status": "approved",
                "can_access": True,
            },
            {
                "group_id": "group-review-bank",
                "name": "Review Ngan Hang VN",
                "privacy": "PRIVATE",
                "status": "not_joined",
                "can_access": False,
            },
        ]
        samples = [
            (f"Minh dang dung {query}, phi thuong nien kha cao nhung cashback tot.", groups[0]),
            (f"Co ai biet {query} co mien phi nam dau khong?", groups[1]),
            (f"So voi the khac thi {query} uu dai hon nhieu, dac biet cashback online.", groups[0]),
            (f"Dich vu ho tro {query} hoi cham, goi 3 lan moi duoc.", groups[2]),
            (f"Moi nguoi cho minh hoi {query} rut tien mat co phi khong?", groups[1]),
            (f"Minh thay {query} giao dien app dep, de dung.", None),
            (f"Canh bao: {query} tu dong gia han phi bao hiem!", groups[0]),
            (f"Da dung {query} 2 nam, rat hai long voi uu dai di cho.", groups[2]),
            (f"Ban nao muon lam {query} thi ib minh nhe, minh gioi thieu.", groups[1]),
            (f"Han muc {query} cho sinh vien chi 10 trieu, it qua.", None),
        ]
        posts = []
        for index, (text, group) in enumerate(samples[:target_count], start=1):
            group_id = group["group_id"] if group else None
            post_url = (
                f"https://www.facebook.com/groups/{group_id}/posts/100000000000{index}"
                if group_id
                else f"https://www.facebook.com/post/100000000000{index}"
            )
            post_id = self._post_id_from_url(post_url)
            posts.append({
                "post_id": post_id,
                "post_url": post_url,
                "source_group_id": group_id,
                "source_group_name": group["name"] if group else None,
                "source_group_privacy": group["privacy"] if group else "UNKNOWN",
                "source_group_status": group["status"] if group else "unknown",
                "source_group_can_access": group["can_access"] if group else False,
                "content": self._pii_masker.mask(text),
                "posted_at": f"2026-03-28T{10 + index}:00:00+07:00",
                "reaction_count": 3 + index * 2,
                "comment_count": 1 + index,
            })
        discovered = [g for g in groups if any(p["source_group_id"] == g["group_id"] for p in posts)]
        return {"posts": posts, "discovered_groups": discovered}

    def _build_mock_comments(
        self,
        post_url: str,
        target_count: int,
        *,
        source_group_id: str | None = None,
    ) -> list[RawPost]:
        parent_id = self._post_id_from_url(post_url)
        group_hash = self._resolve_group_hash(source_group_id, fallback_seed=parent_id)
        samples = [
            {"text": "Minh cung gap tinh trang nay, phi cao qua.", "parent_key": "post"},
            {"text": "Minh cung bi sau khi gia han thang truoc.", "parent_key": "c1"},
            {"text": "Ban thu goi hotline 1800 xxxx, ho tro nhanh lam.", "parent_key": "post"},
            {"text": "Dung roi, cashback thang nay bi tinh sai.", "parent_key": "post"},
            {"text": "Cam on ban da chia se, minh se thu.", "parent_key": "c4"},
            {"text": "Minh thay ok ma, co le do khu vuc.", "parent_key": "post"},
            {"text": "Co ai duoc mien phi nam dau khong vay?", "parent_key": "post"},
            {"text": "Ban dung the bao lau roi?", "parent_key": "c7"},
        ]
        comments: list[RawPost] = []
        comment_refs: dict[str, dict[str, str]] = {
            "post": {"post_id": parent_id, "source_url": post_url},
        }
        for index, sample in enumerate(samples[:target_count], start=1):
            text = str(sample["text"])
            parent_key = str(sample["parent_key"])
            parent_ref = comment_refs.get(parent_key, comment_refs["post"])
            comment_url = f"{post_url}?comment_id=200000000000{index}"
            comment_id = self._comment_id_from_context(
                parent_post_id=parent_ref["post_id"],
                comment_url=comment_url,
                comment_text=text,
                ordinal=index,
            )
            comments.append(
                RawPost(
                    post_id=comment_id,
                    group_id_hash=group_hash,
                    content=self._pii_masker.mask(text),
                    record_type="COMMENT",
                    source_url=comment_url,
                    parent_post_id=parent_ref["post_id"],
                    parent_post_url=parent_ref["source_url"],
                    posted_at=f"2026-03-28T12:{index:02d}:00+07:00",
                    reaction_count=index,
                    comment_count=0,
                )
            )
            comment_refs[f"c{index}"] = {"post_id": comment_id, "source_url": comment_url}
        return comments

    def _build_mock_in_group_posts(self, group_id: str, query: str, target_count: int) -> list[RawPost]:
        group_hash = self.hash_group_id(group_id)
        samples = [
            f"Trong nhom nay co ai dung {query} khong? Cho minh xin review.",
            f"Moi cap nhat: {query} vua thay doi chinh sach phi.",
            f"So sanh {query} voi cac the khac trong cung phan khuc.",
            f"Kinh nghiem dung {query} khi di nuoc ngoai.",
            f"Moi nguoi cho minh hoi {query} co the lien ket vi dien tu khong?",
            f"Review {query} sau 6 thang su dung thuc te.",
        ]
        posts: list[RawPost] = []
        for index, text in enumerate(samples[:target_count], start=1):
            post_url = f"https://www.facebook.com/groups/{group_id}/posts/300000000000{index}"
            posts.append(
                RawPost(
                    post_id=self._post_id_from_url(post_url),
                    group_id_hash=group_hash,
                    content=self._pii_masker.mask(text),
                    record_type="POST",
                    source_url=post_url,
                    parent_post_id=None,
                    parent_post_url=None,
                    posted_at=f"2026-03-28T14:{index:02d}:00+07:00",
                    reaction_count=2 + index,
                    comment_count=1 + (index % 3),
                )
            )
        return posts

    def _build_mock_posts(self, group_id: str) -> list[RawPost]:
        group_hash = self.hash_group_id(group_id)
        samples = [
            "Phi duy tri TPBank EVO cao qua, moi thang mat kha nhieu tien.",
            "Minh thay app dung on, nhan vien ho tro rat nhanh va lich su.",
            "Moi nguoi co ai biet TPBank EVO co mien phi rut tien khong?",
            "So voi the khac thi TPBank EVO uu dai on hon khong?",
            "Sale soc hom nay, ib ngay 0912345678 de nhan uu dai.",
            "Email minh la shopper@example.com, ai review giup voi.",
            "Dich vu hoi cham luc can khoa the gap.",
            "Minh thich giao dien app, de dung va thong bao ro rang.",
            "Ai da dung the nay de mua online chua, fee co cao khong?",
            "Ban gap ban gap ban gap, ship toan quoc, lien he 0987654321.",
            "Tot hon bank cu cua minh o phan cashback.",
            "Hoi ve han muc va cach nang han muc the cho sinh vien.",
        ]
        posts: list[RawPost] = []
        for index, sample in enumerate(samples, start=1):
            post_url = f"https://www.facebook.com/groups/{group_id}/posts/400000000000{index}"
            posts.append(
                RawPost(
                    post_id=self._post_id_from_url(post_url),
                    group_id_hash=group_hash,
                    content=self._pii_masker.mask(sample),
                    record_type="POST",
                    source_url=post_url,
                    parent_post_id=None,
                    parent_post_url=None,
                    posted_at=f"2026-03-28T10:{index:02d}:00+07:00",
                    reaction_count=5 + index,
                    comment_count=1 + (index % 4),
                )
            )
        return posts
