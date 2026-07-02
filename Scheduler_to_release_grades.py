import subprocess
import sys
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
SCRIPT_PATH = "Navigation_to_resultspage.py"  # adjust if your filename differs
INTERVAL_HOURS = 2
RESULTS_READY_EXIT_CODE = 42

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scheduler.log"),
    ],
)
logger = logging.getLogger(__name__)


def run_main_script() -> bool:
    """Execute the main script. Returns True if results were found (stop scheduling)."""
    logger.info("Triggering main script: %s", SCRIPT_PATH)
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT_PATH],
            capture_output=True,
            text=True,
        )
        logger.info("Script finished with exit code %s.\nSTDOUT:\n%s", result.returncode, result.stdout[-2000:])

        if result.returncode == RESULTS_READY_EXIT_CODE:
            logger.info("Results are out! Stopping scheduler.")
            return True
        if result.returncode != 0:
            logger.error("Script exited with error.\nSTDERR:\n%s", result.stderr[-2000:])
        return False

    except Exception as exc:
        logger.exception("Unexpected error running script: %s", exc)
        return False


def main() -> None:
    logger.info("Starting scheduler — will check every %d hour(s) until results are out.", INTERVAL_HOURS)

    try:
        run_count = 0
        while True:
            run_count += 1
            now = datetime.now(IST)
            logger.info("Run #%d starting at %s IST", run_count, now.strftime("%Y-%m-%d %H:%M"))

            results_ready = run_main_script()
            if results_ready:
                logger.info("Results found on run #%d — exiting scheduler.", run_count)
                break

            logger.info("Results not yet out. Sleeping %d hour(s) until next check...", INTERVAL_HOURS)
            remaining = INTERVAL_HOURS * 3600
            while remaining > 0:
                chunk = min(remaining, 60)
                time.sleep(chunk)
                remaining -= chunk

    except KeyboardInterrupt:
        logger.warning("Scheduler interrupted by user (Ctrl+C). Exiting gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    main()