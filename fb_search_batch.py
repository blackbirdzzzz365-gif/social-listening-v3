"""
Facebook Batch Search — Search multiple keywords in a single browser session.

Searches Facebook for multiple keyword variations, deduplicates results,
and saves a consolidated JSON file for analysis.

Usage:
    python3 fb_search_batch.py --scrolls 15 --days 7
    python3 fb_search_batch.py --keywords "TPBank EVO" "thẻ EVO" --days 7
"""

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from fb_search import extract_posts_from_search, parse_relative_timestamp

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fb-session")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawled-data")

# Default keywords for TPBank EVO credit card
DEFAULT_KEYWORDS = [
    "TPBank EVO",
    "thẻ EVO",
    "thẻ EVO TPBank",
    "thẻ tín dụng TPBank",
    "TPBank EVO card",
    "tpb evo",
    "evo tpbank",
    "thẻ tpb evo",
]

DEFAULT_SCROLLS = 15
PAUSE_BETWEEN_SEARCHES = 5


def main():
    parser = argparse.ArgumentParser(description="Batch search Facebook for multiple keywords")
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=DEFAULT_KEYWORDS,
        help="Keywords to search (default: TPBank EVO variations)",
    )
    parser.add_argument(
        "--scrolls",
        type=int,
        default=DEFAULT_SCROLLS,
        help=f"Scrolls per keyword (default: {DEFAULT_SCROLLS})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help="Filter to posts from last N days (0 = no filter)",
    )
    parser.add_argument(
        "--output-name",
        default="",
        help="Custom output file name prefix (default: auto-generated from keywords)",
    )
    args = parser.parse_args()

    keywords = args.keywords

    if not os.path.exists(SESSION_DIR) or len(os.listdir(SESSION_DIR)) < 2:
        print("No Facebook session found. Run fb_login.py first.")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H%M")

    print("=" * 60)
    print("FACEBOOK BATCH SEARCH")
    print("=" * 60)
    print(f"  Keywords:    {len(keywords)}")
    for kw in keywords:
        print(f"               - {kw}")
    print(f"  Scrolls:     {args.scrolls} per keyword")
    print(f"  Days filter: {args.days if args.days > 0 else 'none'}")
    print(f"  Date:        {date_str}")
    print()

    all_posts = []
    seen_links = set()
    posts_per_keyword = {}

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
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

        for i, keyword in enumerate(keywords):
            print(f"\n[{i + 1}/{len(keywords)}] Searching: \"{keyword}\"")

            encoded = quote(keyword)
            search_url = f"https://www.facebook.com/search/posts/?q={encoded}"

            try:
                page.goto(search_url, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                if "login" in page.url.lower():
                    print("  ERROR: Session expired. Run fb_login.py again.")
                    break

                posts = extract_posts_from_search(page, args.scrolls)

                # Tag posts and deduplicate
                new_count = 0
                for post in posts:
                    post["search_keyword"] = keyword
                    post["search_filter"] = "posts"
                    post["crawled_at"] = datetime.now().isoformat()

                    # Parse timestamp
                    post_date = parse_relative_timestamp(post.get("timestamp", ""))
                    post["estimated_date"] = post_date.isoformat() if post_date else None

                    # Deduplicate by post_link (if available) or by text hash
                    dedup_key = post.get("post_link") or hash(post.get("text", "")[:200])
                    if dedup_key and dedup_key not in seen_links:
                        seen_links.add(dedup_key)
                        all_posts.append(post)
                        new_count += 1

                posts_per_keyword[keyword] = new_count
                print(f"  Found {len(posts)} posts, {new_count} new (after dedup)")

            except Exception as e:
                print(f"  ERROR: {e}")
                posts_per_keyword[keyword] = 0

            if i < len(keywords) - 1:
                time.sleep(PAUSE_BETWEEN_SEARCHES)

        context.close()

    if not all_posts:
        print("\nNo posts found across all keywords.")
        return

    # Apply date filter
    if args.days > 0:
        cutoff = datetime.now() - timedelta(days=args.days)
        filtered = []
        for post in all_posts:
            post_date = parse_relative_timestamp(post.get("timestamp", ""))
            if post_date and post_date >= cutoff:
                filtered.append(post)
            elif not post_date:
                filtered.append(post)
        print(f"\nDate filter: {len(filtered)}/{len(all_posts)} posts within last {args.days} days")
        all_posts = filtered

    # Save consolidated results
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.output_name:
        safe_name = re.sub(r"[^\w\s-]", "", args.output_name).strip().replace(" ", "-")[:50]
    else:
        safe_name = re.sub(r"[^\w\s-]", "", keywords[0]).strip().replace(" ", "-")[:30]

    filename = f"fb-search-{safe_name}-{date_str}-{time_str}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    output = {
        "search_keywords": keywords,
        "search_filter": "posts",
        "crawl_date": date_str,
        "crawled_at": datetime.now().isoformat(),
        "days_filter": args.days,
        "total_posts": len(all_posts),
        "posts_per_keyword": posts_per_keyword,
        "posts": all_posts,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"DONE! {len(all_posts)} total posts from {len(keywords)} keywords.")
    print(f"{'=' * 60}")
    print(f"\nPosts per keyword:")
    for kw, count in posts_per_keyword.items():
        print(f"  {kw}: {count}")
    print(f"\nSaved to: {filepath}")
    print(f"\nTo analyze, run:")
    print(f"  /facebook-social-listening analyze TPBank EVO from {filepath}")


if __name__ == "__main__":
    main()
