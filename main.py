#!/usr/bin/env python3
# main.py
# This is the primary startup script for the bot.

import subprocess
import time
import sys
from core.logger import logger

def run_bot_process():
    """
    Runs and monitors the bot process (`bot.py`), handling restarts.
    """
    max_restarts = 10
    initial_wait_time = 10
    restart_attempts = 0
    backoff = 3

    logger.info("Bot Runner Script has started. Preparing to launch the bot.")

    while restart_attempts < max_restarts:
        logger.info(f"Attempting to start bot... [Attempt {restart_attempts + 1} of {max_restarts}]")
        process = None

        try:
            process = subprocess.Popen(
                [sys.executable, 'bot.py'],
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            return_code = process.wait()

            if return_code == 0:
                logger.info("Bot process exited gracefully (Code 0). Shutting down runner.")
                break
            else:
                logger.error(f"Bot process crashed with exit code {return_code}. It will be restarted.")
                restart_attempts += 1
                if restart_attempts >= max_restarts:
                    logger.critical(f"Maximum restart limit ({max_restarts}) reached. The bot will not be restarted again.")
                    break
                wait_time = min(300, initial_wait_time * (2 ** (restart_attempts - 1)))
                logger.info(f"Waiting {wait_time} seconds before the next restart attempt.")
                time.sleep(wait_time)
        except KeyboardInterrupt:
            logger.info("Shutdown signal (Ctrl+C) received. Terminating bot process.")
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Bot process did not terminate gracefully. Forcing shutdown.")
                    process.kill()
            break
        except Exception as e:
            logger.critical(f"An unexpected error occurred in the runner script: {e}", exc_info=True)
            restart_attempts += 1
            time.sleep(60)

    logger.info("Bot Runner Script has finished.")

if __name__ == "__main__":
    run_bot_process()
