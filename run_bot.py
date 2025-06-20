
#!/usr/bin/env python3
import subprocess
import time
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BotRunner')

def run_bot():
    """Run the bot with restart logic"""
    restart_count = 0
    max_restarts = 10
    
    while restart_count < max_restarts:
        try:
            logger.info(f"Starting bot (attempt {restart_count + 1})")
            process = subprocess.Popen([sys.executable, 'main.py'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            
            # Wait for process to complete
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Bot crashed with return code {process.returncode}")
                logger.error(f"STDERR: {stderr.decode()}")
                restart_count += 1
                
                # Exponential backoff
                wait_time = min(300, 10 * (2 ** restart_count))
                logger.info(f"Waiting {wait_time} seconds before restart...")
                time.sleep(wait_time)
            else:
                logger.info("Bot exited normally")
                break
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            if process:
                process.terminate()
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            restart_count += 1
            time.sleep(60)
    
    logger.error(f"Max restarts ({max_restarts}) reached. Stopping.")

if __name__ == "__main__":
    run_bot()
