"""
Agentic login workflow for PESU Academy portal.

Usage:
    1. pip install playwright
    2. playwright install chromium
    3. Set credentials as environment variables (recommended) instead of
       hardcoding them:
           export PESU_USERNAME="your_prn_here"
           export PESU_PASSWORD="your_password_here"
    4. python pesu_login.py

This opens a NEW, visible browser window, navigates to the PESU Academy
login page, fills in the credentials, submits the form, and waits for
you to land on the post-login dashboard.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

LOGIN_URL = "https://www.pesuacademy.com/Academy/"

# Prefer environment variables over hardcoding secrets in source code.
USERNAME = os.environ.get("PESU_USERNAME", "your_prn_here")
PASSWORD = os.environ.get("PESU_PASSWORD", "your_password_here")


def login_to_pesu_academy():
    with sync_playwright() as p:
        # Launch a NEW browser window (not headless, so you can see it).
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        print(f"[*] Navigating to {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        try:
            # PESU Academy's login form field names/ids can change over time.
            # Common selectors used by this portal historically:
            username_selector = "input[name='j_username'], #j_username, input[type='text']"
            password_selector = "input[name='j_password'], #j_password, input[type='password']"
            submit_selector = "button[type='submit'], input[type='submit']"

            print("[*] Waiting for login form...")
            page.wait_for_selector(username_selector, timeout=15000)

            print("[*] Filling credentials...")
            page.fill(username_selector, USERNAME)
            page.fill(password_selector, PASSWORD)

            print("[*] Submitting login form...")
            page.click(submit_selector)

            # Wait for navigation / dashboard element to confirm login succeeded.
            page.wait_for_load_state("networkidle", timeout=20000)
            print("[+] Login submitted. Current URL:", page.url)

        except PlaywrightTimeoutError:
            print("[!] Timed out waiting for an expected element.")
            print("    The site's login form structure may have changed.")
            print("    Inspect the page manually (it will stay open) and")
            print("    update the selectors in this script accordingly.")

        # Keep the window open so you can inspect the result.
        print("[*] Browser window will remain open. Press Ctrl+C in this")
        print("    terminal to close it when you're done.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Closing browser.")
            browser.close()


if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        print("Set PESU_USERNAME and PESU_PASSWORD environment variables.")
        sys.exit(1)
    login_to_pesu_academy()