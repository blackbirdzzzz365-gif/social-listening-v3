"""
Facebook Login — One-time manual login to save session.

This script opens a real browser window. You log in manually,
join groups if needed, then close the browser. The session is
saved locally so the crawler can reuse it without logging in again.

Usage:
    python3 fb_login.py
"""

import os
from playwright.sync_api import sync_playwright

SESSION_DIR = os.path.join(os.path.dirname(__file__), "fb-session")


def main():
    print("=" * 60)
    print("FACEBOOK SESSION SETUP")
    print("=" * 60)
    print()
    print("A browser window will open. Please:")
    print("  1. Log in to your research Facebook account")
    print("  2. Complete any 2FA verification if prompted")
    print("  3. (Optional) Join target groups if you haven't yet")
    print("  4. When done, come back here and press Enter")
    print()
    print(f"Session will be saved to: {SESSION_DIR}")
    print()

    with sync_playwright() as p:
        # Persistent context saves cookies, localStorage, etc.
        context = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            # Mimic a real browser
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.facebook.com/")

        print("Browser is open. Log in to Facebook now.")
        print()
        input(">>> Press Enter here AFTER you've logged in successfully... ")

        # Verify login succeeded
        cookies = context.cookies()
        fb_cookies = [c for c in cookies if "facebook.com" in c.get("domain", "")]

        if fb_cookies:
            print()
            print(f"Session saved successfully! ({len(fb_cookies)} cookies stored)")
            print("You can now close this and run the crawler.")
        else:
            print()
            print("WARNING: No Facebook cookies found. Login may have failed.")
            print("Try running this script again.")

        context.close()


if __name__ == "__main__":
    main()
