"""
cloudflare_bypass.py

Opens a visible browser window so the user can solve the Cloudflare challenge
manually. After the challenge is passed, cookies are saved to a JSON file and
returned, ready to be reused in urllib requests.
"""

import json
import os
import time
import threading
from typing import Optional

_COOKIES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cf_cookies.json")


def _cookies_to_header(cookies: list) -> str:
    """Convert a list of Playwright cookie dicts into a Cookie header string."""
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


def load_saved_cookies(domain: str) -> Optional[list]:
    """Load previously saved cookies for a given domain, or None if not found."""
    if not os.path.exists(_COOKIES_PATH):
        return None
    try:
        with open(_COOKIES_PATH, "r", encoding="utf-8") as f:
            all_cookies = json.load(f)
        domain_cookies = all_cookies.get(domain, [])
        if domain_cookies:
            return domain_cookies
    except Exception:
        pass
    return None


def save_cookies(domain: str, cookies: list):
    """Persist cookies for a domain to disk."""
    all_cookies = {}
    if os.path.exists(_COOKIES_PATH):
        try:
            with open(_COOKIES_PATH, "r", encoding="utf-8") as f:
                all_cookies = json.load(f)
        except Exception:
            pass
    all_cookies[domain] = cookies
    with open(_COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(all_cookies, f, indent=2)


def get_cookie_header(domain: str) -> str:
    """Return a Cookie header string for the given domain, or empty string."""
    cookies = load_saved_cookies(domain)
    if cookies:
        return _cookies_to_header(cookies)
    return ""


def solve_cloudflare(url: str, on_success=None, on_error=None):
    """
    Opens a visible Playwright browser window for the user to pass the Cloudflare
    challenge on the given URL. Runs in a separate thread so it doesn't block the GUI.

    Args:
        url: The URL to visit (home page of the protected site).
        on_success: Optional callback(domain, cookies) called on success.
        on_error: Optional callback(error_message) called on failure.
    """

    def _run():
        try:
            from playwright.sync_api import sync_playwright
            import re

            # Extract domain from URL
            domain_match = re.search(r"https?://([^/]+)", url)
            domain = domain_match.group(1) if domain_match else url

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()

                print(f"[CloudflareBypass] Opening browser for {url}")
                page.goto(url)

                # Wait for Cloudflare challenge to clear.
                # We detect success when the page title is no longer "Just a moment..."
                max_wait = 120  # seconds
                elapsed = 0
                passed = False
                while elapsed < max_wait:
                    time.sleep(1)
                    elapsed += 1
                    try:
                        title = page.title()
                        # Cloudflare challenge page titles
                        if "just a moment" not in title.lower() and "verificando" not in title.lower():
                            passed = True
                            break
                    except Exception:
                        pass

                if passed:
                    cookies = context.cookies()
                    save_cookies(domain, cookies)
                    print(f"[CloudflareBypass] Cookies saved for {domain} ({len(cookies)} cookies)")
                    if on_success:
                        on_success(domain, cookies)
                else:
                    if on_error:
                        on_error("Tempo esgotado aguardando a verificação do Cloudflare.")

                browser.close()

        except Exception as e:
            print(f"[CloudflareBypass] Error: {e}")
            if on_error:
                on_error(str(e))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
