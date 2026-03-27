"""
Facebook Auto Join Groups — Search for and join relevant groups.

Searches Facebook for groups matching lending/credit/fintech keywords
and automatically requests to join them.

Joining criteria:
- Groups with >5,000 members
- Groups with daily posts >5
- Maximum 5 groups joined per keyword

Usage:
    python3 fb_join_groups.py
"""

import json
import os
import re
import time
from datetime import datetime
from urllib.parse import quote

from playwright.sync_api import sync_playwright

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fb-session")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawled-data")

# ============================================================
# JOINING CRITERIA
# ============================================================
MIN_MEMBERS = 5000
MIN_DAILY_POSTS = 5
MAX_GROUPS_PER_KEYWORD = 5

# Keywords to search for groups
SEARCH_KEYWORDS = [
    # Credit card related
    "thẻ tín dụng",
    "review thẻ tín dụng",
    "đáo hạn thẻ tín dụng",
    "hội thẻ tín dụng",
    # Lending / loans
    "vay tiêu dùng",
    "vay tiền online",
    "vay tín chấp",
    "hội vay tiêu dùng",
    "vay trả góp",
    # Personal finance
    "tài chính cá nhân",
    "quản lý tài chính",
    # Banks & FIs
    "TPBank",
    "Techcombank",
    "VPBank",
    "MB Bank",
    "Sacombank",
    # Consumer finance companies
    "FE Credit",
    "Home Credit Việt Nam",
    "HD Saison",
    "MCredit",
    "Shinhan Finance",
    # Fintech / e-wallets
    "MoMo tài chính",
    "ZaloPay",
    "Cake by VPBank",
    # BNPL / installment
    "trả góp",
    "mua trả góp",
    # General
    "kinh nghiệm vay vốn",
    "hỏi đáp tín dụng",
]

PAUSE_BETWEEN_CLICKS = 2.5
PAUSE_BETWEEN_SEARCHES = 5


def parse_member_count(text: str) -> int:
    """Parse Vietnamese/English member count strings into a number.

    Examples:
        '128,5K thành viên' -> 128500
        '1,2M members' -> 1200000
        '45.000 thành viên' -> 45000
        '12K members' -> 12000
        '5.234 thành viên' -> 5234
    """
    if not text:
        return 0

    text = text.strip().lower()

    # Try to find a number pattern with K/M suffix
    # Match: 128,5K / 1.2M / 12K / 1,2M etc.
    km_match = re.search(r"([\d.,]+)\s*([km])", text, re.IGNORECASE)
    if km_match:
        num_str = km_match.group(1).replace(",", ".")  # normalize comma to dot
        multiplier = km_match.group(2).upper()
        try:
            num = float(num_str)
            if multiplier == "K":
                return int(num * 1000)
            elif multiplier == "M":
                return int(num * 1000000)
        except ValueError:
            pass

    # Try plain number: 45.000 or 45,000 or 5234
    plain_match = re.search(r"([\d.]+)", text)
    if plain_match:
        num_str = plain_match.group(1)
        # Vietnamese uses dots as thousands separator: 45.000 = 45000
        # If pattern is like X.XXX or X.XXX.XXX, it's a thousands separator
        if re.match(r"^\d{1,3}(\.\d{3})+$", num_str):
            return int(num_str.replace(".", ""))
        try:
            return int(num_str.replace(".", ""))
        except ValueError:
            pass

    return 0


def parse_daily_posts(text: str) -> int:
    """Parse daily post activity strings into a number.

    Examples:
        '10+ bài viết mới mỗi ngày' -> 10
        '25 new posts a day' -> 25
        '5+ posts a day' -> 5
        '1 bài viết mới hôm nay' -> 1 (today only, not daily — treat as low)
    """
    if not text:
        return 0

    text = text.strip().lower()

    # Look for daily pattern: "X+ bài viết mới mỗi ngày" or "X+ posts a day" or "X+ new posts today"
    daily_match = re.search(r"(\d+)\+?\s*(bài viết|posts?|new posts?)", text)
    if daily_match:
        count = int(daily_match.group(1))
        # Check if it's "per day" / "mỗi ngày" (daily) vs "today" / "hôm nay" (just today)
        if "mỗi ngày" in text or "a day" in text or "per day" in text or "each day" in text:
            return count
        # "today" / "hôm nay" — still a signal, return as-is
        return count

    return 0


def collect_group_cards(page) -> list[dict]:
    """Scroll the search results and collect all group card data without clicking anything."""

    # Scroll to load results
    for i in range(5):
        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        page.wait_for_timeout(2500)

    # Extract all group cards with metadata
    cards = page.evaluate("""
    () => {
        const buttons = document.querySelectorAll('[role="button"]');
        const results = [];

        buttons.forEach((btn, btnIdx) => {
            const text = btn.innerText?.trim().toLowerCase();
            if (text !== 'tham gia' && text !== 'join' && text !== 'join group') return;

            // Walk up to find the group card container
            let card = btn.parentElement;
            for (let j = 0; j < 8; j++) {
                if (!card.parentElement) break;
                card = card.parentElement;
                if (card.querySelectorAll('a[href*="/groups/"]').length > 0) break;
            }

            let groupName = '';
            let groupLink = '';
            let membersText = '';
            let activityText = '';

            // Group link
            const links = card.querySelectorAll('a[href*="/groups/"]');
            for (const link of links) {
                const href = link.href || '';
                if (href.includes('/groups/') && !href.includes('/search/')) {
                    groupLink = href;
                    break;
                }
            }

            // Group name
            const nameEls = card.querySelectorAll('a span[dir="auto"], strong, a[role="presentation"]');
            for (const el of nameEls) {
                const name = el.innerText?.trim();
                if (name && name.length > 3 && name.length < 150 && name.toLowerCase() !== 'tham gia') {
                    groupName = name;
                    break;
                }
            }

            // Collect ALL text spans for members and activity
            const spans = card.querySelectorAll('span');
            for (const span of spans) {
                const t = span.innerText?.trim();
                if (!t) continue;
                // Member count: "128,5K thành viên" / "45.000 members"
                if (/thành viên|members?/i.test(t) && !membersText) {
                    membersText = t;
                }
                // Activity: "10+ bài viết mới mỗi ngày" / "5 posts a day"
                if (/bài viết|posts?\s*(a|per|each)?\s*day|mỗi ngày|hôm nay|today/i.test(t) && !activityText) {
                    activityText = t;
                }
            }

            if (groupName) {
                results.push({
                    btnIndex: btnIdx,
                    name: groupName,
                    link: groupLink,
                    membersText: membersText,
                    activityText: activityText,
                });
            }
        });

        return results;
    }
    """)

    return cards


def click_join_button_for_group(page, group_name: str) -> bool:
    """Find and click the join button associated with a specific group name."""
    clicked = page.evaluate("""
    (groupName) => {
        const buttons = document.querySelectorAll('[role="button"]');
        for (const btn of buttons) {
            const text = btn.innerText?.trim().toLowerCase();
            if (text !== 'tham gia' && text !== 'join' && text !== 'join group') continue;

            // Walk up to card
            let card = btn.parentElement;
            for (let j = 0; j < 8; j++) {
                if (!card.parentElement) break;
                card = card.parentElement;
                if (card.querySelectorAll('a[href*="/groups/"]').length > 0) break;
            }

            if (card.innerText?.includes(groupName)) {
                btn.click();
                return true;
            }
        }
        return false;
    }
    """, group_name)

    if clicked:
        # Dismiss any membership questions modal
        page.wait_for_timeout(1000)
        page.evaluate("""
        () => {
            const buttons = document.querySelectorAll('[role="button"], [aria-label="Close"], [aria-label="Đóng"]');
            for (const btn of buttons) {
                const text = (btn.innerText?.trim() || btn.getAttribute('aria-label') || '').toLowerCase();
                if (['cancel', 'hủy', 'skip', 'bỏ qua', 'close', 'đóng', 'not now', 'để sau'].includes(text)) {
                    btn.click();
                    return;
                }
            }
        }
        """)

    return clicked


def join_groups_on_page(page, already_joined: set) -> list[dict]:
    """Collect group cards, filter by criteria, and join qualifying groups."""
    joined = []

    cards = collect_group_cards(page)

    if not cards:
        return []

    print(f"    Found {len(cards)} groups. Filtering by criteria...")

    for card in cards:
        name = card.get("name", "Unknown")
        members_text = card.get("membersText", "")
        activity_text = card.get("activityText", "")
        member_count = parse_member_count(members_text)
        daily_posts = parse_daily_posts(activity_text)

        # Skip if already joined
        if name in already_joined:
            continue

        # Check: max groups per keyword
        if len(joined) >= MAX_GROUPS_PER_KEYWORD:
            print(f"    Reached max {MAX_GROUPS_PER_KEYWORD} groups for this keyword. Moving on.")
            break

        # Check: minimum members
        if member_count < MIN_MEMBERS:
            print(f"    SKIP (members: {member_count:,} < {MIN_MEMBERS:,}): {name} — {members_text}")
            continue

        # Check: minimum daily posts
        if daily_posts < MIN_DAILY_POSTS:
            print(f"    SKIP (posts/day: {daily_posts} < {MIN_DAILY_POSTS}): {name} — {activity_text or 'no activity info'}")
            continue

        # Passed all criteria — join!
        print(f"    JOINING: {name} ({members_text} | {activity_text})")
        clicked = click_join_button_for_group(page, name)

        if clicked:
            print(f"    OK: Joined {name}")
            already_joined.add(name)
            joined.append({
                "name": name,
                "link": card.get("link", ""),
                "members_text": members_text,
                "member_count": member_count,
                "activity_text": activity_text,
                "daily_posts": daily_posts,
                "keyword": "",  # will be set by caller
                "joined_at": datetime.now().isoformat(),
            })
            time.sleep(PAUSE_BETWEEN_CLICKS)
        else:
            print(f"    FAILED: Could not click join for {name}")

    return joined


def main():
    if not os.path.exists(SESSION_DIR) or len(os.listdir(SESSION_DIR)) < 2:
        print("No Facebook session found. Run fb_login.py first.")
        return

    print("=" * 60)
    print("FACEBOOK AUTO JOIN — Lending/Credit/Fintech Groups")
    print("=" * 60)
    print(f"  Keywords:           {len(SEARCH_KEYWORDS)}")
    print(f"  Min members:        {MIN_MEMBERS:,}")
    print(f"  Min daily posts:    {MIN_DAILY_POSTS}")
    print(f"  Max groups/keyword: {MAX_GROUPS_PER_KEYWORD}")
    print(f"  Date:               {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    all_joined = []
    already_joined = set()

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

        for i, keyword in enumerate(SEARCH_KEYWORDS):
            print(f"\n[{i + 1}/{len(SEARCH_KEYWORDS)}] Searching: \"{keyword}\"")

            encoded = quote(keyword)
            url = f"https://www.facebook.com/search/groups/?q={encoded}"

            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                if "login" in page.url.lower():
                    print("  ERROR: Session expired. Run fb_login.py again.")
                    break

                joined = join_groups_on_page(page, already_joined)
                for g in joined:
                    g["keyword"] = keyword
                all_joined.extend(joined)

                if not joined:
                    print("    No qualifying groups found.")

            except Exception as e:
                print(f"  ERROR: {e}")

            if i < len(SEARCH_KEYWORDS) - 1:
                time.sleep(PAUSE_BETWEEN_SEARCHES)

        context.close()

    # Save results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(OUTPUT_DIR, f"fb-joined-groups-{date_str}.json")

    output = {
        "date": date_str,
        "criteria": {
            "min_members": MIN_MEMBERS,
            "min_daily_posts": MIN_DAILY_POSTS,
            "max_groups_per_keyword": MAX_GROUPS_PER_KEYWORD,
        },
        "total_joined": len(all_joined),
        "keywords_searched": len(SEARCH_KEYWORDS),
        "groups": all_joined,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n")
    print("=" * 60)
    print(f"DONE! Requested to join {len(all_joined)} groups.")
    print("=" * 60)
    print(f"\nCriteria applied:")
    print(f"  Members >= {MIN_MEMBERS:,}")
    print(f"  Daily posts >= {MIN_DAILY_POSTS}")
    print(f"  Max {MAX_GROUPS_PER_KEYWORD} per keyword")
    print(f"\nSaved to: {filepath}")


if __name__ == "__main__":
    main()
