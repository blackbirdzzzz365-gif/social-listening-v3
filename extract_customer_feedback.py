"""
Extract and classify customer feedback from crawled Facebook data.
Filters out sales agents, spam, and irrelevant posts.
Outputs a structured CSV with theme, emotion, timestamp, link, and customer name.
"""

import csv
import json
import os
import re

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "crawled-data", "fb-search-TPBank-EVO-2026-03-25-1410.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "crawled-data", "tpbank-evo-customer-feedback.csv")

# ============================================================
# AGENT / SPAM DETECTION
# ============================================================

# Known agent/spam group names or author patterns
AGENT_AUTHORS = [
    "Hỗ Trợ Vay Vốn",
    "Vay Vốn Ngân hàng",
    "Nhóm Vay Vốn",
    "Thông Tin Và Hỗ Trợ Vay Vốn",
    "Vay Thế Chấp",
]

AGENT_TEXT_SIGNALS = [
    r"(?i)zalo\s*:\s*\d",
    r"(?i)call/zalo",
    r"(?i)ib\s+mình\s+hỗ\s+trợ",
    r"(?i)liên\s+hệ\s+(inbox|fb|zalo)",
    r"(?i)kết\s+bạn\s*\+\s*ib",
    r"(?i)hỗ\s+trợ\s+mở\s+thẻ\s+tín\s+dụng",
    r"(?i)v@y\s+tín\s+chấp",
    r"(?i)đ\.á\.o",
    r"(?i)r\.ú\.t",
    r"(?i)da0\s+han",
    r"\d{4}[\.\s]?\d{3}[\.\s]?\d{3}",  # phone numbers
    r"(?i)𝐌Ở\s*𝐓𝐇Ẻ\s*𝐓Í𝐍\s*𝐃Ụ𝐍𝐆",
    r"(?i)MỞ THẺ TÍN DỤNG.*KHOẢN V",
    r"(?i)hỗ trợ nợ xấu",
    r"(?i)quẹt the td",
]

# Known brand/official pages
BRAND_AUTHORS = [
    "GOEVO",
    "TPBank",
    "Hoàng Hà Mobile",
    "Hoàng Hà ",
    "Hoanghamobile",
    "Thế giới di động",
    "TopZone",
    "Hiền Topzone",
    "Phong Vũ",
    "Taiphanmemmienphi",
    "Nhat Phan",  # Blogger/content writer
]

# Non-Vietnamese / irrelevant content
IRRELEVANT_SIGNALS = [
    r"(?i)bonjour",
    r"(?i)hello\s+(la|les|petite)",
    r"(?i)salut\s+a\s+tous",
    r"(?i)simagic",
    r"(?i)assetto\s+corsa",
    r"(?i)motorfest",
    r"(?i)#foryouシ",
    r"(?i)galaxy\s+(watch|s25|a36|a56)",
    r"(?i)apple\s+watch\s+series",
    r"(?i)HAPPY WOMEN.S DAY",
    r"(?i)FLAGSHIP SAMSUNG",
]


def is_agent_or_spam(post):
    """Check if a post is from a sales agent or is spam."""
    author = post.get("author", "")
    text = post.get("text", "")
    group = post.get("group_name", "")

    # Check author names
    for pattern in AGENT_AUTHORS:
        if pattern.lower() in author.lower():
            return True
        if pattern.lower() in group.lower():
            # Group is an agent group but the poster might be a customer
            # Check if the poster name differs from the group
            pass

    # Check text signals
    for pattern in AGENT_TEXT_SIGNALS:
        if re.search(pattern, text):
            return True

    return False


def is_brand_or_official(post):
    """Check if post is from official brand page."""
    author = post.get("author", "")
    for brand in BRAND_AUTHORS:
        if brand.lower() in author.lower():
            return True
    return False


def is_irrelevant(post):
    """Check if post is irrelevant (non-Vietnamese, unrelated products)."""
    text = post.get("text", "")
    for pattern in IRRELEVANT_SIGNALS:
        if re.search(pattern, text):
            return True
    return False


def is_about_tpbank_evo(post):
    """Check if post actually mentions TPBank EVO or related terms."""
    text = post.get("text", "").lower()
    keywords = ["evo", "tpbank", "tp bank", "tp bạnk", "tpb", "bank tím"]
    return any(kw in text for kw in keywords)


# ============================================================
# THEME CLASSIFICATION
# ============================================================

THEME_RULES = [
    ("Cashback / Hoàn tiền", [
        r"(?i)hoàn\s+tiền", r"(?i)cashback", r"(?i)cash\s+back",
        r"(?i)hoàn\s+\d+k", r"(?i)hoàn\s+500k", r"(?i)tiền\s+hoàn",
        r"(?i)T\+2", r"(?i)chuyển\s+lúa",
    ]),
    ("Phí / Phạt", [
        r"(?i)phạt\s+3%", r"(?i)cảnh\s+(báo|cáo)", r"(?i)phí\s+thường\s+niên",
        r"(?i)phí\s+phát\s+hành", r"(?i)phí\s+quản\s+lý", r"(?i)phí\s+220k",
        r"(?i)bị\s+phạt",
    ]),
    ("Đáo hạn / Rút tiền", [
        r"(?i)đáo\s+hạn", r"(?i)đáo\s+tiếp", r"(?i)rút\s+thẻ",
        r"(?i)rút\s+tiền", r"(?i)bị\s+khoá",
    ]),
    ("Ưu đãi / Khuyến mãi", [
        r"(?i)ưu\s+đãi", r"(?i)khuyến\s+mãi", r"(?i)cắt\s+ưu\s+đãi",
        r"(?i)âm\s+thầm", r"(?i)giảm\s+mức", r"(?i)chương\s+trình",
    ]),
    ("Trả góp / Installment", [
        r"(?i)trả\s+góp", r"(?i)quy\s+đổi.*góp", r"(?i)kỳ\s+hạn",
        r"(?i)góp\s+linh\s+hoạt", r"(?i)0%\s+lãi",
    ]),
    ("Hạn mức / Credit limit", [
        r"(?i)hạn\s+mức", r"(?i)check\s+hạn\s+mức", r"(?i)cấp\s+hạn\s+mức",
        r"(?i)hm\s+nhỏ", r"(?i)75\s*tr",
    ]),
    ("Mở thẻ / Đăng ký", [
        r"(?i)mở\s+thẻ", r"(?i)đăng\s+ký", r"(?i)duyệt\s+online",
        r"(?i)CCCD", r"(?i)chứng\s+minh\s+thu\s+nhập",
    ]),
    ("Trải nghiệm sử dụng", [
        r"(?i)trải\s+nghiệm", r"(?i)chia\s+sẻ", r"(?i)review",
        r"(?i)dùng\s+có\s+tốt", r"(?i)có\s+nên\s+dùng",
    ]),
    ("So sánh thẻ / Competitor", [
        r"(?i)VIB", r"(?i)VPBank", r"(?i)MSB", r"(?i)Techcombank",
        r"(?i)KBank", r"(?i)MBBank", r"(?i)sang\s+ngang",
    ]),
    ("Hạng thẻ / Card tier", [
        r"(?i)hạng\s+vàng", r"(?i)hạng\s+chuẩn", r"(?i)gold",
        r"(?i)nâng\s+hạng",
    ]),
]


def classify_theme(text):
    """Classify the primary theme of a post."""
    themes = []
    for theme_name, patterns in THEME_RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                themes.append(theme_name)
                break
    return themes[0] if themes else "Khác"


def classify_all_themes(text):
    """Return all matching themes."""
    themes = []
    for theme_name, patterns in THEME_RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                themes.append(theme_name)
                break
    return themes if themes else ["Khác"]


# ============================================================
# EMOTION CLASSIFICATION
# ============================================================

NEGATIVE_SIGNALS = [
    r"(?i)buồn", r"(?i)quá\s+buồn", r"(?i)phạt", r"(?i)cảnh\s+báo",
    r"(?i)bị\s+khoá", r"(?i)âm\s+thầm\s+cắt", r"(?i)mất\s+công",
    r"(?i)ko\s+thấy\s+tiền\s+hoàn", r"(?i)không\s+được\s+hoàn",
    r"(?i)bị\s+buộc", r"(?i)giảm\s+mức\s+hoàn", r"(?i)khó\s+chệu",
    r"(?i)bị\s+cảnh", r"(?i)hết\s+chương\s+trình",
    r"(?i)k\s+thấy\s+tiền", r"(?i)vài\s+chục\s+nghìn",
    r"(?i)cất\s+tạm.*đi",
]

POSITIVE_SIGNALS = [
    r"(?i)mở\s+thẻ\s+liền", r"(?i)nhanh", r"(?i)dễ\s+dàng",
    r"(?i)tốt", r"(?i)hí\s+hửng", r"(?i)đã\s+chuyển\s+lúa",
    r"(?i)hoàn\s+tiền.*đều", r"(?i)ưu\s+đãi\s+ngập",
]

QUESTION_SIGNALS = [
    r"(?i)cho\s+em\s+hỏi", r"(?i)cho\s+hỏi", r"(?i)có\s+ai",
    r"(?i)mọi\s+người\s+ơi", r"(?i)các\s+ct", r"(?i)\?\s*$",
    r"(?i)mn\s+ơi", r"(?i)có\s+nên", r"(?i)có\s+cách\s+nào",
    r"(?i)phải\s+không\s+ạ",
]


def classify_emotion(text):
    """Classify emotion: Positive, Negative, or Neutral."""
    neg_score = sum(1 for p in NEGATIVE_SIGNALS if re.search(p, text))
    pos_score = sum(1 for p in POSITIVE_SIGNALS if re.search(p, text))
    q_score = sum(1 for p in QUESTION_SIGNALS if re.search(p, text))

    if neg_score > pos_score and neg_score > 0:
        return "Negative"
    elif pos_score > neg_score and pos_score > 0:
        return "Positive"
    elif q_score > 0:
        return "Neutral (Question)"
    else:
        return "Neutral"


# ============================================================
# CUSTOMER NAME EXTRACTION
# ============================================================

def extract_customer_name(post):
    """Extract the actual customer name from the post."""
    author = post.get("author", "")
    group = post.get("group_name", "")

    # In Facebook search results, the group_name field often contains
    # the actual poster name when the author field shows the group name
    if group and group != author:
        # If author looks like a group name and group looks like a person name
        group_indicators = ["Review thẻ", "Hội", "Cộng Đồng", "mở thẻ", "RCGV",
                           "Mua Bán", "Chợ", "Cuồng"]
        if any(g.lower() in author.lower() for g in group_indicators):
            return group  # The "group" field is actually the poster
        if any(g.lower() in group.lower() for g in group_indicators):
            return author  # The "author" field is the poster

    # Default: use whichever looks more like a person name
    return group if group and len(group) < 30 else author


# ============================================================
# MAIN
# ============================================================

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data["posts"]
    customer_feedback = []

    for post in posts:
        # Skip agents, brands, and irrelevant content
        if is_agent_or_spam(post):
            continue
        if is_brand_or_official(post):
            continue
        if is_irrelevant(post):
            continue
        if not is_about_tpbank_evo(post):
            continue

        text = post.get("text", "")
        customer_name = extract_customer_name(post)
        themes = classify_all_themes(text)
        emotion = classify_emotion(text)

        customer_feedback.append({
            "customer_name": customer_name,
            "feedback": text[:500].replace("\n", " ").strip(),
            "theme": " | ".join(themes),
            "emotion": emotion,
            "timestamp": post.get("estimated_date") or post.get("crawled_at", ""),
            "post_link": post.get("post_link", ""),
            "group_name": post.get("group_name", ""),
            "search_keyword": post.get("search_keyword", ""),
            "comments_count": post.get("comments_count", ""),
            "reactions": post.get("reactions", ""),
        })

    # Sort by emotion (negative first) then by comments
    def sort_key(fb):
        emotion_order = {"Negative": 0, "Neutral (Question)": 1, "Neutral": 2, "Positive": 3}
        comments = fb.get("comments_count", "")
        num = int(re.search(r"\d+", comments).group()) if re.search(r"\d+", comments) else 0
        return (emotion_order.get(fb["emotion"], 2), -num)

    customer_feedback.sort(key=sort_key)

    # Write CSV
    fieldnames = [
        "customer_name", "theme", "emotion", "feedback",
        "timestamp", "post_link", "group_name",
        "comments_count", "reactions", "search_keyword",
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(customer_feedback)

    # Print summary
    print(f"=" * 60)
    print(f"CUSTOMER FEEDBACK EXTRACTION")
    print(f"=" * 60)
    print(f"  Total posts:              {len(posts)}")
    print(f"  Customer feedback:        {len(customer_feedback)}")
    print(f"  Filtered out (agents/spam/irrelevant): {len(posts) - len(customer_feedback)}")
    print()

    # Theme breakdown
    theme_counts = {}
    for fb in customer_feedback:
        for t in fb["theme"].split(" | "):
            theme_counts[t] = theme_counts.get(t, 0) + 1
    print("  Themes:")
    for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
        print(f"    {theme}: {count}")

    # Emotion breakdown
    emotion_counts = {}
    for fb in customer_feedback:
        emotion_counts[fb["emotion"]] = emotion_counts.get(fb["emotion"], 0) + 1
    print()
    print("  Emotions:")
    for emotion, count in sorted(emotion_counts.items(), key=lambda x: -x[1]):
        print(f"    {emotion}: {count}")

    print(f"\n  Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
