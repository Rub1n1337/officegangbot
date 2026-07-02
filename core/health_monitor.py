# core/health_monitor.py

"""
This module provides a Health Monitor for the bot.
-------------------------------------------------------------
What it does:
- It runs in a separate, non-blocking thread.
- It periodically checks key metrics of the bot and the system it's running on.
- The checks include:
  - Bot readiness (is it connected to Discord?).
  - Latency (ping to Discord's API).
  - Guild count (how many servers is it in?).
  - Memory usage of the bot process.
- It logs this information, which is very useful for diagnosing problems
  like memory leaks or connection issues over time.
"""

import time
import threading
import psutil  # A library to check system resource usage (pip install psutil)
from core.logger import logger
from core.observability import alerts

class HealthMonitor:
    """
    Monitors bot health (readiness, latency, guild count, memory usage) in a background thread.
    Logs warnings for high resource usage and provides thread-safe start/stop methods.
    """
    def __init__(self, bot, check_interval_seconds: int = 300) -> None:
        """
        Args:
            bot: The bot instance to monitor.
            check_interval_seconds: How often (in seconds) to perform health checks. Default is 5 minutes.
        """
        self.bot = bot
        self.check_interval = check_interval_seconds
        self.running: bool = False
        self._thread: threading.Thread | None = None
        # Consecutive not-ready checks; alerts fire from the 2nd one so a normal
        # deploy/reconnect blip doesn't page anyone.
        self._not_ready_streak: int = 0

    def _alert(self, key: str, title: str, description: str, level: str = "warning") -> None:
        """Sends an alert from this (non-async) thread via the bot's loop."""
        loop = getattr(self.bot, "loop", None)
        if loop is None or not alerts.enabled:
            return
        alerts.alert_threadsafe(loop, key, title, description, level)

    def start(self) -> None:
        """Starts the health monitoring process in a background thread."""
        if self.running:
            logger.info("Health monitor is already running.")
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops the health monitoring process and waits for the thread to finish."""
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        time.sleep(10)  # Wait for bot to fully start up
        while self.running:
            try:
                if not getattr(self.bot, 'is_ready', lambda: True)():
                    logger.warning("Health Check: Bot is NOT ready or is disconnected.")
                    self._not_ready_streak += 1
                    if self._not_ready_streak >= 2:
                        self._alert(
                            "bot_not_ready", "🔴 Bot disconnected",
                            f"The bot has not been ready for {self._not_ready_streak} consecutive "
                            f"health checks (~{self._not_ready_streak * self.check_interval // 60} min).",
                            "error",
                        )
                else:
                    self._not_ready_streak = 0
                    latency_ms = getattr(self.bot, 'latency', 0) * 1000
                    guild_count = len(getattr(self.bot, 'guilds', []))
                    try:
                        import psutil
                        import os
                        mem_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
                    except Exception as psu:
                        logger.warning(f"psutil error in health monitor: {psu}", exc_info=True)
                        mem_mb = 0.0
                    log_message = f"Health: latency={latency_ms:.0f}ms guilds={guild_count} mem={mem_mb:.1f}MB"
                    if latency_ms > 3000:
                        logger.warning(f"HIGH LATENCY DETECTED. {log_message}")
                        self._alert("high_latency", "🟠 High Discord latency", log_message)
                    elif mem_mb > 350:
                        logger.warning(f"HIGH MEMORY USAGE DETECTED. {log_message}")
                        self._alert("high_memory", "🟠 High memory usage", log_message)
                    else:
                        logger.info(log_message)
            except Exception as e:
                logger.error(f"Health monitor error: {e}", exc_info=True)
            time.sleep(self.check_interval)

        logger.info("Health monitor loop has finished.")

    def get_status(self):
        """
        Returns a dictionary with the current health status metrics of the bot.
        This can be used by other parts of the bot, like the webserver.
        """
        if not self.bot.is_ready() or not self.running:
            return {
                "bot_ready": False,
                "latency_ms": -1,
                "guilds_count": 0,
                "memory_mb": 0,
            }

        process = psutil.Process()
        return {
            "bot_ready": self.bot.is_ready(),
            "latency_ms": round(self.bot.latency * 1000),
            "guilds_count": len(self.bot.guilds),
            "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
        }
