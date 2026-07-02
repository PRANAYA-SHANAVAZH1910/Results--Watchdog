#!/usr/bin/env python3
"""
PESU Academy Portal Automation
Logs into https://www.pesuacademy.com/Academy/ and navigates to the
student profile/results page using Playwright.

Credentials are read from environment variables:
    PESU_USERNAME
    PESU_PASSWORD

Usage:
    export PESU_USERNAME="your_srn"
    export PESU_PASSWORD="your_password"
    python pesu_login.py
"""
import re
import os
import sys
#import urllib.parse
import requests
import logging
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Page,
    Browser,
)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

BASE_URL = "https://www.pesuacademy.com/Academy/"
RESULTS_URL = "https://www.pesuacademy.com/Academy/s/studentProfilePESU"
DEFAULT_TIMEOUT_MS = 30_000  # 30 seconds for most waits
HEADLESS = os.environ.get("PESU_HEADLESS", "false").lower() == "true"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pesu_automation.log"),
    ],
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------

def get_credentials() -> tuple[str, str]:
    """Fetch credentials from environment variables, failing fast if missing."""
    username = os.environ.get("PESU_USERNAME","PRN")
    password = os.environ.get("PESU_PASSWORD","Password")

    if not username or not password:
        logger.error(
            "Missing credentials. Please set PESU_USERNAME and PESU_PASSWORD "
            "environment variables before running this script."
        )
        raise EnvironmentError("PESU_USERNAME and/or PESU_PASSWORD not set")

    return username, password


def launch_browser(playwright, headless: bool = HEADLESS) -> Browser:
    """Launch a Chromium browser instance."""
    logger.info("Launching Chromium (headless=%s)...", headless)
    try:
        browser = playwright.chromium.launch(
            headless=headless,
            args=["--start-maximized"],
        )
        logger.info("Browser launched successfully.")
        return browser
    except Exception as exc:
        logger.exception("Failed to launch browser: %s", exc)
        raise


def open_login_page(page: Page, url: str = BASE_URL) -> None:
    """Navigate to the PESU Academy login page and wait for it to load."""
    logger.info("Navigating to %s", url)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
        # Wait for network to settle so dynamic content (JS-rendered form) loads
        page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT_MS)
        logger.info("Login page loaded successfully.")
    except PlaywrightTimeoutError:
        logger.exception("Timed out waiting for login page to load.")
        raise


def perform_login(page: Page, username: str, password: str) -> None:
    """Click 'Sign In' to open the login modal, then fill and submit the form."""
    logger.info("Opening the Sign In modal...")
    try:
        sign_in_button = page.get_by_role("button", name="Sign In", exact=True).first
        sign_in_button.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        sign_in_button.click()

        username_field = page.locator("#j_scriptusername")
        username_field.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        username_field.fill(username)
        logger.info("Username entered.")

        password_field = page.locator("#passwordField")
        password_field.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        password_field.fill(password)
        logger.info("Password entered.")

        # --- DIAGNOSTIC BLOCK ---
        page.screenshot(path="before_submit.png")
        logger.info("Saved screenshot: before_submit.png")

        all_buttons = page.query_selector_all("button")
        logger.info("Button states right before submit attempt:")
        for i, el in enumerate(all_buttons):
            try:
                logger.info(
                    "  [%d] text=%r type=%r visible=%s enabled=%s",
                    i, el.inner_text().strip(), el.get_attribute("type"),
                    el.is_visible(), el.is_enabled()
                )
            except Exception:
                pass
        # --- END DIAGNOSTIC BLOCK ---

        # Try pressing Enter in the password field as the primary submit method —
        # more reliable than guessing which button is the real submit trigger.
        password_field.press("Enter")
        logger.info("Pressed Enter on password field to submit.")

    except PlaywrightTimeoutError:
        logger.exception("Timed out locating or interacting with login form elements.")
        raise
    except Exception as exc:
        logger.exception("Unexpected error during login: %s", exc)
        raise


def wait_for_login_completion(page: Page) -> None:
    """Wait until the login modal closes and the page transitions post-login."""
    logger.info("Waiting for login to complete...")
    try:
        page.locator("#j_scriptusername").wait_for(state="hidden", timeout=DEFAULT_TIMEOUT_MS)
        page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT_MS)
        logger.info("Login completed successfully.")
    except PlaywrightTimeoutError:
        logger.error(
            "Could not confirm login completion within timeout. "
            "This may mean login failed (wrong credentials), a CAPTCHA appeared, "
            "or an error dialog is blocking the page."
        )
        page.screenshot(path="login_stuck.png")
        logger.info("Saved screenshot: login_stuck.png — check this to see what's on screen.")
        raise

def navigate_to_results(page: Page, results_url: str = RESULTS_URL) -> None:
    """Navigate to the Results page by clicking the sidebar link."""
    logger.info("Navigating to Results page via sidebar link...")
    try:
        results_link = page.get_by_text("Results", exact=True).first
        results_link.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        results_link.click()

        page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT_MS)

        page.locator("select").first.wait_for(state="attached", timeout=DEFAULT_TIMEOUT_MS)

        logger.info("Results page loaded successfully. Current URL: %s", page.url)
    except PlaywrightTimeoutError:
        logger.exception("Timed out waiting for Results page to load.")
        raise
def extract_subject_grades(page: Page, send_sms: bool = False) -> bool:
    """
    Extract subject/grade pairs and CGPA, then send an SMS depending on status:
      - If all grades are N/A -> "Results are not yet displayed"
      - If any real grade found -> "Congratulations! Your results are out" +
        subject/grade list + CGPA
    Returns True if results are out (at least one real grade found), else False.
    Nothing is printed to the terminal.
    """
    logger.info("Attempting to extract subject/grade data...")
    try:
        page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT_MS)

        full_text = page.inner_text("body")
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        subject_line_pattern = re.compile(r"^[A-Z0-9]+\s*-\s*(.+)$")

        results = []
        i = 0
        while i < len(lines):
            match = subject_line_pattern.match(lines[i])
            if match:
                subject_name = match.group(1).strip()
                grade = None
                for j in range(i + 1, min(i + 40, len(lines))):
                    if lines[j] == "ESA":
                        if j + 1 < len(lines):
                            candidate = lines[j + 1].strip()
                            if re.fullmatch(r"[A-Za-z][+-]?", candidate):
                                grade = candidate
                        break
                    if subject_line_pattern.match(lines[j]):
                        break
                results.append((subject_name, grade))
            i += 1

        if not results:
            logger.warning("No subject/grade pairs found. Saving screenshot for inspection.")
            page.screenshot(path="results_parse_failed.png")
            return False

        # --- Extract CGPA ---
        cgpa = None
        for idx, line in enumerate(lines):
            if line == "CGPA":
                if idx + 1 < len(lines):
                    candidate = lines[idx + 1].strip()
                    if re.fullmatch(r"\d+(\.\d+)?", candidate):
                        cgpa = candidate
                break
        logger.info("CGPA found on page: %r", cgpa)

        results_out = any(grade is not None for _, grade in results)

        if results_out:
            message_lines = ["Congratulations! Your results are out"]
            for subject_name, grade in results:
                if grade:
                    message_lines.append(f"{subject_name}: {grade}")
            if cgpa:
                message_lines.append(f"CGPA: {cgpa}")
            sms_body = "\n".join(message_lines)
            logger.info("Results are OUT. %d subject(s) graded.", sum(1 for _, g in results if g))
        else:
            sms_body = "Results are not yet displayed"
            logger.info("Results not yet displayed (all N/A).")

        if send_sms:
            send_sms_via_macrodroid(sms_body)

        return results_out

    except PlaywrightTimeoutError:
        logger.exception("Timed out while extracting grade data.")
        raise
    except Exception as exc:
        logger.exception("Unexpected error while extracting grades: %s", exc)
        raise

def select_semester(page: Page, semester_label: str = "Sem-2") -> None:
    """
    Select the semester using the underlying native <select> element
    (visually hidden but functionally the real dropdown).
    """
    logger.info("Attempting to select semester: %s", semester_label)
    try:
        page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT_MS)

        selects = page.locator("select")
        count = selects.count()
        logger.info("Found %d <select> element(s) on the page.", count)

        target_select = None
        for i in range(count):
            sel = selects.nth(i)
            try:
                options = sel.locator("option").all_inner_texts()
            except Exception:
                options = []
            logger.info("  [%d] options=%s", i, options)
            if any(opt.strip().startswith("Sem-") for opt in options):
                target_select = sel
                logger.info("  -> Using <select> #%d (contains semester options).", i)

        if target_select is None:
            logger.error("No <select> containing 'Sem-' options was found.")
            page.screenshot(path="semester_select_failed.png")
            raise RuntimeError("Semester <select> element not found.")

        before = target_select.input_value()
        logger.info("Current selected value/id: %r", before)

        target_select.select_option(label=semester_label)
        logger.info("Selected option with label %r", semester_label)

        # Let the AJAX-driven content update
        page.wait_for_timeout(1000)
        page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT_MS)

        after = target_select.input_value()
        logger.info("Value after selection: %r", after)

        page.screenshot(path="after_semester_change.png")
        logger.info("Saved screenshot: after_semester_change.png")

    except PlaywrightTimeoutError:
        logger.exception("Timed out while trying to select semester %s.", semester_label)
        page.screenshot(path="semester_select_failed.png")
        raise
    except Exception as exc:
        logger.exception("Unexpected error while selecting semester: %s", exc)
        raise

MACRODROID_WEBHOOK_URL = os.environ.get(
    "MACRODROID_WEBHOOK_URL",
    "your_macrodroid_webhook_url_here" 
)


def send_sms_via_macrodroid(message: str) -> None:
    """Trigger a MacroDroid webhook to send an SMS with the given message."""
    logger.info("Sending SMS via MacroDroid webhook...")
    try:
        params = {"message": message}
        response = requests.get(MACRODROID_WEBHOOK_URL, params=params, timeout=15)

        if response.status_code == 200:
            logger.info("MacroDroid webhook triggered successfully.")
        else:
            logger.error(
                "MacroDroid webhook returned unexpected status: %s", response.status_code
            )
    except requests.RequestException as exc:
        logger.exception("Failed to trigger MacroDroid webhook: %s", exc)
        raise

# --------------------------------------------------------------------------
# Main workflow
# --------------------------------------------------------------------------

RESULTS_READY_EXIT_CODE = 42  

def run() -> None:
    username, password = get_credentials()

    with sync_playwright() as playwright:
        browser = None
        try:
            browser = launch_browser(playwright)
            context = browser.new_context(no_viewport=True)
            page = context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT_MS)

            open_login_page(page)
            perform_login(page, username, password)
            wait_for_login_completion(page)
            navigate_to_results(page)

            # Sem-1 already has grades — check/print/SMS it, but don't let it trigger exit
            extract_subject_grades(page, send_sms=False)

            select_semester(page, "Sem-2")
            sem2_out = extract_subject_grades(page, send_sms=True)

            if sem2_out:
                logger.info("Sem-2 results detected as out. Terminating scheduled runs.")
                if browser:
                    browser.close()
                sys.exit(RESULTS_READY_EXIT_CODE)

            logger.info("Automation completed successfully. Sem-2 results still pending — will retry next cycle.")

        except SystemExit:
            raise  # let our intentional exit code pass through untouched
        except Exception as exc:
            logger.error("Automation failed: %s", exc)
            logger.info("Browser will stay open for inspection despite the error.")
            input("\n❌ Script failed. Press Enter here to close the browser...")

        finally:
            if browser:
                browser.close()
                logger.info("Browser closed.")

if __name__ == "__main__":
    run()