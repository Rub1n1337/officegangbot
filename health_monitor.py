
import requests
import time
import threading
import logging

logger = logging.getLogger('BrawlStarsBot')

class HealthMonitor:
    def __init__(self, bot, check_interval=300):  # 5 minutes
        self.bot = bot
        self.check_interval = check_interval
        self.last_heartbeat = time.time()
        self.is_running = True
        
    def start_monitoring(self):
        """Start the health monitoring in a separate thread"""
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        logger.info("Health monitoring started")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Update heartbeat
                self.last_heartbeat = time.time()
                
                # Check bot status
                if self.bot.is_ready():
                    logger.info(f"Bot health check: OK - {len(self.bot.guilds)} guilds connected")
                else:
                    logger.warning("Bot health check: Bot not ready")
                    
                # Check memory usage
                import psutil
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 80:
                    logger.warning(f"High memory usage: {memory_percent}%")
                    
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
                
    def get_status(self):
        """Get current health status"""
        return {
            "bot_ready": self.bot.is_ready(),
            "guilds_count": len(self.bot.guilds) if self.bot.is_ready() else 0,
            "last_heartbeat": self.last_heartbeat,
            "uptime": time.time() - self.last_heartbeat
        }
