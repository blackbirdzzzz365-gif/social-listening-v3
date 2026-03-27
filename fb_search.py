"""
Facebook Search Crawler — Search Facebook for a keyword and extract results.

Uses the saved session from fb_login.py to search Facebook,
extract posts from search results, and save structured data.

Usage:
    python3 fb_search.py "đáo hạn thẻ tín dụng"
    python3 fb_search.py "vay tiêu dùng" --scrolls 20
    python3 fb_search.py "FE Credit review" --filter posts
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote

from playwright.sync_api import sync_playwright

SESSION_DIR = os.path.join(os.path.dirname(__file__), "fb-session")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "crawled-data")

# Tune these for speed vs. volume
DEFAULT_SCROLLS = 15
SCROLL_PAUSE = 3.0  # seconds — keep it human-like
PAGE_LOAD_WAIT = 4


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_relative_timestamp(relative_text: str, reference_time: datetime = None) -> datetime | None:
    """Convert Facebook relative time ('2 giờ', '3 ngày', '1 tuần') to a datetime."""
    if not relative_text:
        return None
    ref = reference_time or datetime.now()
    text = relative_text.lower().strip()

    patterns = [
        (r"(\d+)\s*(phút|m\b)", "minutes"),
        (r"(\d+)\s*(giờ|h\b)", "hours"),
        (r"(\d+)\s*(ngày|d\b)", "days"),
        (r"(\d+)\s*(tuần|w\b)", "weeks"),
        (r"(\d+)\s*(tháng)", "months"),
        (r"(\d+)\s*(năm|y\b)", "years"),
    ]
    for pattern, unit in patterns:
        match = re.search(pattern, text)
        if match:
            value = int(match.group(1))
            if unit == "minutes":
                return ref - timedelta(minutes=value)
            if unit == "hours":
                return ref - timedelta(hours=value)
            if unit == "days":
                return ref - timedelta(days=value)
            if unit == "weeks":
                return ref - timedelta(weeks=value)
            if unit == "months":
                return ref - timedelta(days=value * 30)
            if unit == "years":
                return ref - timedelta(days=value * 365)

    if "hôm qua" in text or "yesterday" in text:
        return ref - timedelta(days=1)

    return None


def extract_posts_from_search(page, max_scrolls: int) -> list[dict]:
    """Scroll through search results and extract post data."""

    # Wait for initial results
    page.wait_for_timeout(PAGE_LOAD_WAIT * 1000)

    # Scroll to load more results
    for i in range(max_scrolls):
        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        page.wait_for_timeout(int(SCROLL_PAUSE * 1000))
        print(f"  Scroll {i + 1}/{max_scrolls}...")

    # Extract posts — Facebook search uses data-pagelet="message" containers
    # (not role="article" like group feeds). We try both selectors.
    posts_data = page.evaluate("""
    () => {
        // Try multiple selectors: search results use data-pagelet, feeds use role="article"
        let containers = Array.from(document.querySelectorAll('[data-pagelet="message"]'));
        if (containers.length === 0) {
            containers = Array.from(document.querySelectorAll('[role="article"]'));
        }
        // Fallback: look for the feed and split by top-level children
        if (containers.length === 0) {
            const feed = document.querySelector('[role="feed"]');
            if (feed) {
                containers = Array.from(feed.children);
            }
        }

        const results = [];
        const seenTexts = new Set();

        containers.forEach((container, idx) => {
            // Get all text content from div[dir="auto"] elements
            const textParts = [];
            const divs = container.querySelectorAll('div[dir="auto"]');
            divs.forEach(div => {
                const text = div.innerText?.trim();
                if (text && text.length > 15) {
                    textParts.push(text);
                }
            });

            // Deduplicate text parts
            const seen = new Set();
            const uniqueTexts = [];
            textParts.forEach(t => {
                if (!seen.has(t)) {
                    seen.add(t);
                    uniqueTexts.push(t);
                }
            });

            const fullText = uniqueTexts.join('\\n');
            if (!fullText || fullText.length < 30) return;

            // Skip if we've already seen this exact text (cross-container dedup)
            const textKey = fullText.substring(0, 200);
            if (seenTexts.has(textKey)) return;
            seenTexts.add(textKey);

            // Author — strong tag or heading link
            let author = '';
            const authorEl = container.querySelector('strong') || container.querySelector('h3 a, h4 a');
            if (authorEl) {
                author = authorEl.innerText?.trim() || '';
            }

            // Group name
            let groupName = '';
            const groupLinks = container.querySelectorAll('a[href*="/groups/"]');
            groupLinks.forEach(link => {
                const linkText = link.innerText?.trim();
                if (linkText && linkText.length > 3 && linkText.length < 100) {
                    groupName = linkText;
                }
            });

            // Reactions
            let reactions = '';
            const reactionEls = container.querySelectorAll('[aria-label]');
            reactionEls.forEach(el => {
                const label = el.getAttribute('aria-label') || '';
                if (/like|love|haha|thích|reaction|cảm xúc/i.test(label) && label.length > 3) {
                    reactions = label;
                }
            });

            // Comment count & share count
            let commentsCount = '';
            let sharesCount = '';
            const allSpans = container.querySelectorAll('span');
            allSpans.forEach(span => {
                const text = span.innerText?.trim();
                if (/^\\d+\\s*(comments?|bình luận)/i.test(text)) {
                    commentsCount = text;
                }
                if (/^\\d+\\s*(shares?|lượt chia sẻ)/i.test(text)) {
                    sharesCount = text;
                }
            });

            // Post link and timestamp
            let postLink = '';
            let timestamp = '';
            const timeLinks = container.querySelectorAll('a[href*="/posts/"], a[href*="/permalink/"], a[href*="story_fbid"], a[href*="pfbid"]');
            if (timeLinks.length > 0) {
                postLink = timeLinks[0].href || '';
            }

            // Timestamp from permalink anchors
            timeLinks.forEach(a => {
                if (timestamp) return;
                const spans = a.querySelectorAll('span');
                spans.forEach(span => {
                    const t = span.innerText?.trim();
                    if (t && !timestamp && t.length < 30 &&
                        /^(\\d+\\s*(giờ|phút|ngày|tuần|tháng|năm|[hmdwy])\\s*(trước)?|Hôm qua|Yesterday)/i.test(t)) {
                        timestamp = t;
                    }
                });
                if (!timestamp) {
                    const aText = a.innerText?.trim();
                    if (aText && aText.length < 30 && /\\d+\\s*(giờ|phút|ngày|tuần|[hmdwy])/i.test(aText)) {
                        timestamp = aText;
                    }
                }
            });

            // Fallback: any span with time-like text
            if (!timestamp) {
                allSpans.forEach(span => {
                    if (timestamp) return;
                    const t = span.innerText?.trim();
                    if (t && t.length < 25 && /^\\d+\\s*(giờ|phút|ngày|tuần|tháng|[hmdwy])/.test(t)) {
                        timestamp = t;
                    }
                });
            }

            results.push({
                index: idx,
                author: author.substring(0, 100),
                group_name: groupName.substring(0, 200),
                text: fullText.substring(0, 5000),
                reactions: reactions,
                comments_count: commentsCount,
                shares_count: sharesCount,
                post_link: postLink,
                timestamp: timestamp,
            });
        });

        return results;
    }
    """)

    return posts_data


def search_facebook(keyword: str, max_scrolls: int, search_filter: str, days_filter: int = 0):
    """Search Facebook for a keyword and extract results."""

    # Check session exists
    if not os.path.exists(SESSION_DIR) or len(os.listdir(SESSION_DIR)) < 2:
        print("=" * 60)
        print("NO FACEBOOK SESSION FOUND")
        print("=" * 60)
        print()
        print("Run fb_login.py first to log in and save your session:")
        print("  python3 fb_login.py")
        return

    encoded_keyword = quote(keyword)

    # Facebook search URL with filter
    filter_map = {
        "posts": "/posts",
        "people": "/people",
        "photos": "/photos",
        "videos": "/videos",
        "groups": "/groups",
        "pages": "/pages",
    }
    filter_path = filter_map.get(search_filter, "/posts")
    search_url = f"https://www.facebook.com/search{filter_path}/?q={encoded_keyword}"

    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H%M")

    print("=" * 60)
    print(f"FACEBOOK SEARCH CRAWL")
    print("=" * 60)
    print(f"  Keyword:  {keyword}")
    print(f"  Filter:   {search_filter}")
    print(f"  Scrolls:  {max_scrolls}")
    print(f"  Date:     {date_str}")
    print()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,  # Visible browser so you can monitor
            viewport={"width": 1280, "height": 900},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        page = context.pages[0] if context.pages else context.new_page()

        print(f"Navigating to search: {keyword}")
        page.goto(search_url, wait_until="domcontentloaded")
        page.wait_for_timeout(PAGE_LOAD_WAIT * 1000)

        # Check if redirected to login
        if "login" in page.url.lower():
            print()
            print("ERROR: Session expired! Please run fb_login.py again.")
            context.close()
            return

        print("Search results loaded. Extracting posts...\n")
        posts = extract_posts_from_search(page, max_scrolls)

        # Tag posts with search metadata and parse timestamps
        for post in posts:
            post["search_keyword"] = keyword
            post["search_filter"] = search_filter
            post["crawled_at"] = datetime.now().isoformat()
            post_date = parse_relative_timestamp(post.get("timestamp", ""))
            post["estimated_date"] = post_date.isoformat() if post_date else None

        context.close()

    if not posts:
        print("No posts found. The search may have returned no results,")
        print("or Facebook's layout may have changed.")
        return

    # Apply date filter if requested
    if days_filter > 0:
        cutoff = datetime.now() - timedelta(days=days_filter)
        filtered = []
        for post in posts:
            post_date = parse_relative_timestamp(post.get("timestamp", ""))
            if post_date and post_date >= cutoff:
                filtered.append(post)
            elif not post_date:
                # Keep posts without parseable timestamps (better to include than miss)
                filtered.append(post)
        print(f"Date filter: {len(filtered)}/{len(posts)} posts within last {days_filter} days")
        posts = filtered

    # Save results
    ensure_output_dir()
    safe_keyword = re.sub(r"[^\w\s-]", "", keyword).strip().replace(" ", "-")[:50]
    filename = f"fb-search-{safe_keyword}-{date_str}-{time_str}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    output = {
        "search_keyword": keyword,
        "search_filter": search_filter,
        "crawl_date": date_str,
        "crawled_at": datetime.now().isoformat(),
        "total_posts": len(posts),
        "posts": posts,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Found {len(posts)} posts.")
    print(f"Saved to: {filepath}")
    print()
    print("To analyze this data, use the social listening skill:")
    print(f'  /facebook-social-listening analyze crawled data for "{keyword}"')

    return filepath


def main():
    parser = argparse.ArgumentParser(description="Search Facebook and extract posts")
    parser.add_argument("keyword", help="Search keyword (Vietnamese or English)")
    parser.add_argument(
        "--scrolls",
        type=int,
        default=DEFAULT_SCROLLS,
        help=f"Number of scrolls to load more results (default: {DEFAULT_SCROLLS})",
    )
    parser.add_argument(
        "--filter",
        choices=["posts", "groups", "pages", "photos", "videos"],
        default="posts",
        help="Facebook search filter (default: posts)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help="Filter to posts from last N days (0 = no filter)",
    )
    args = parser.parse_args()

    search_facebook(args.keyword, args.scrolls, args.filter, args.days)


if __name__ == "__main__":
    main()
