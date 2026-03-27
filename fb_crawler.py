"""
Facebook Group Crawler — Crawls target Facebook groups and saves posts.

Uses the saved session from fb_login.py to browse Facebook groups,
extract posts with comments and reactions, and save structured data
as JSON files for analysis by the social-listening skill.

Usage:
    python3 fb_crawler.py                    # Crawl all configured groups
    python3 fb_crawler.py --group GROUP_ID   # Crawl a specific group
    python3 fb_crawler.py --days 3           # Posts from last 3 days (default: 1)
"""

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ============================================================
# CONFIGURATION — Edit these to match your target groups
# ============================================================

TARGET_GROUPS = [
    # Format: {"id": "group_id_or_url_slug", "name": "Friendly name"}
    # Find the group ID from the group URL: facebook.com/groups/<GROUP_ID>
    #
    # Examples (replace with your actual groups):
    # {"id": "hoivaytieudung", "name": "Hội Vay Tiêu Dùng"},
    # {"id": "reviewthetindung", "name": "Review Thẻ Tín Dụng"},
    # {"id": "taborovietnam", "name": "Tài Chính Cá Nhân Vietnam"},
]

SESSION_DIR = os.path.join(os.path.dirname(__file__), "fb-session")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "crawled-data")

# Scroll settings — controls how much content to load
MAX_SCROLLS = 15  # Number of times to scroll down in a group
SCROLL_PAUSE = 2.5  # Seconds between scrolls (be human-like)
PAGE_LOAD_WAIT = 3  # Seconds to wait for page load


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_posts(page) -> list[dict]:
    """Extract post data from the currently loaded Facebook group page."""
    posts = []

    # Wait for posts to load
    page.wait_for_timeout(PAGE_LOAD_WAIT * 1000)

    # Scroll to load more posts
    for i in range(MAX_SCROLLS):
        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        page.wait_for_timeout(int(SCROLL_PAUSE * 1000))
        print(f"  Scroll {i + 1}/{MAX_SCROLLS}...")

    # Get page content
    content = page.content()
    soup = BeautifulSoup(content, "html.parser")

    # Facebook's DOM changes frequently. We look for common post containers.
    # These selectors may need updating if Facebook changes their markup.
    post_elements = soup.find_all("div", {"role": "article"})

    for idx, post_el in enumerate(post_elements):
        try:
            post_data = parse_post_element(post_el, idx)
            if post_data and post_data.get("text"):
                posts.append(post_data)
        except Exception as e:
            print(f"  Warning: Failed to parse post {idx}: {e}")
            continue

    return posts


def parse_post_element(el, idx: int) -> dict | None:
    """Parse a single post element into structured data."""

    # Extract text content
    text_parts = []
    for text_el in el.find_all(["span", "p"], recursive=True):
        text = text_el.get_text(strip=True)
        if text and len(text) > 10:  # Filter out UI labels
            text_parts.append(text)

    # Deduplicate while preserving order
    seen = set()
    unique_texts = []
    for t in text_parts:
        if t not in seen:
            seen.add(t)
            unique_texts.append(t)

    full_text = "\n".join(unique_texts)

    if not full_text or len(full_text) < 20:
        return None

    # Try to extract author name (usually the first link in a post)
    author = ""
    author_links = el.find_all("a", {"role": "link"})
    for link in author_links[:3]:
        link_text = link.get_text(strip=True)
        if link_text and 5 < len(link_text) < 50:
            author = link_text
            break

    # Try to extract reaction counts from aria-labels
    reactions = ""
    for aria_el in el.find_all(attrs={"aria-label": True}):
        label = aria_el.get("aria-label", "")
        if any(word in label.lower() for word in ["like", "love", "haha", "thích", "reaction"]):
            reactions = label
            break

    # Try to extract comment count
    comments_count = ""
    for span in el.find_all("span"):
        text = span.get_text(strip=True)
        if re.match(r"^\d+\s*(comments?|bình luận)", text, re.IGNORECASE):
            comments_count = text
            break

    return {
        "index": idx,
        "author": author,
        "text": full_text[:3000],  # Cap text length
        "reactions": reactions,
        "comments_count": comments_count,
        "crawled_at": datetime.now().isoformat(),
    }


def crawl_group(context, group: dict, days_back: int = 1) -> list[dict]:
    """Crawl a single Facebook group and return posts."""
    group_id = group["id"]
    group_name = group["name"]

    print(f"\nCrawling group: {group_name} ({group_id})")
    print("-" * 50)

    page = context.new_page()

    try:
        # Navigate to the group
        url = f"https://www.facebook.com/groups/{group_id}"

        # Try "New posts" sort for recent content
        page.goto(url + "?sorting_setting=CHRONOLOGICAL", wait_until="domcontentloaded")
        page.wait_for_timeout(PAGE_LOAD_WAIT * 1000)

        # Check if we're still logged in
        if "login" in page.url.lower():
            print("  ERROR: Session expired. Please run fb_login.py again.")
            return []

        # Check if we have access to the group
        page_text = page.text_content("body") or ""
        if "join group" in page_text.lower()[:500]:
            print(f"  WARNING: Not a member of group '{group_name}'. Skipping.")
            return []

        print("  Page loaded. Extracting posts...")
        posts = extract_posts(page)

        # Tag each post with group info
        for post in posts:
            post["group_id"] = group_id
            post["group_name"] = group_name

        print(f"  Found {len(posts)} posts")
        return posts

    except Exception as e:
        print(f"  ERROR crawling group {group_name}: {e}")
        return []

    finally:
        page.close()


def save_results(all_posts: list[dict], date_str: str):
    """Save crawled posts to a JSON file."""
    ensure_output_dir()

    filename = f"fb-crawl-{date_str}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    output = {
        "crawl_date": date_str,
        "crawled_at": datetime.now().isoformat(),
        "total_posts": len(all_posts),
        "groups_crawled": list({p["group_name"] for p in all_posts}),
        "posts": all_posts,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(all_posts)} posts to {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Crawl Facebook groups for social listening")
    parser.add_argument("--group", help="Crawl a specific group ID only")
    parser.add_argument("--days", type=int, default=1, help="Days of posts to look back (default: 1)")
    args = parser.parse_args()

    if not TARGET_GROUPS:
        print("=" * 60)
        print("NO GROUPS CONFIGURED")
        print("=" * 60)
        print()
        print("Edit fb_crawler.py and add your target groups to TARGET_GROUPS.")
        print()
        print("Example:")
        print('  {"id": "hoivaytieudung", "name": "Hội Vay Tiêu Dùng"},')
        print()
        print("Find the group ID from the URL: facebook.com/groups/<GROUP_ID>")
        return

    # Check session exists
    if not os.path.exists(SESSION_DIR) or not os.listdir(SESSION_DIR):
        print("No Facebook session found. Run fb_login.py first.")
        return

    groups_to_crawl = TARGET_GROUPS
    if args.group:
        groups_to_crawl = [g for g in TARGET_GROUPS if g["id"] == args.group]
        if not groups_to_crawl:
            print(f"Group '{args.group}' not found in TARGET_GROUPS config.")
            return

    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"Facebook Social Listening Crawl — {date_str}")
    print(f"Groups to crawl: {len(groups_to_crawl)}")
    print(f"Looking back: {args.days} day(s)")

    all_posts = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,  # Run in background (no browser window)
            viewport={"width": 1280, "height": 900},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        for group in groups_to_crawl:
            posts = crawl_group(context, group, args.days)
            all_posts.extend(posts)

            # Pause between groups to be human-like
            if group != groups_to_crawl[-1]:
                pause = 5
                print(f"  Pausing {pause}s before next group...")
                time.sleep(pause)

        context.close()

    if all_posts:
        filepath = save_results(all_posts, date_str)
        print(f"\nDone! {len(all_posts)} posts from {len(groups_to_crawl)} groups.")
        print(f"Run the analysis skill on: {filepath}")
    else:
        print("\nNo posts found. Check group access and session.")


if __name__ == "__main__":
    main()
