# core/webserver.py

"""
This module runs a simple web server using Flask.
-------------------------------------------------------------
Why is this needed?
- Many free hosting platforms (like Replit, Heroku's free tier, etc.) will put your
  application to "sleep" if it doesn't receive any web traffic (HTTP requests).
- This web server provides a simple webpage that can be "pinged" by an external
  service (like UptimeRobot) every few minutes.
- This "pinging" counts as web traffic and tricks the hosting platform into
  keeping your bot operational 24/7.

How it works:
- It uses the Flask library to create a lightweight web application.
- It runs this application in a separate, non-blocking background thread so it
  doesn't interfere with the main bot operations.

The web server provides two endpoints:
- `/`: A simple status page that shows the bot is alive.
- `/health`: A health check endpoint that provides detailed status information.
  This is useful for monitoring services like UptimeRobot.
"""

from flask import Flask, jsonify
from threading import Thread
import logging
import time
from core.logger import logger
from typing import Any, Optional
import psutil
import os

# --- Flask App Setup ---

# We want to use our custom logger, so we disable Flask's default noisy logging.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# --- Web Page Endpoints ---
# These are the different URLs that our web server will respond to.

@app.route('/')
def home() -> str:
    """The main page. It just shows a simple status message."""
    return "<h1>Discord Bot is Alive!</h1><p>This web server is running to keep the bot operational on hosting platforms.</p>"

@app.route('/health')
def health_check():
    """
    A health check endpoint that provides detailed status information.
    This is useful for monitoring services like UptimeRobot.
    It gets its data from the bot and health monitor instances.
    """
    # These globals will be set by the `keep_alive` function
    bot = app.config.get('BOT_INSTANCE')
    health_monitor = app.config.get('HEALTH_MONITOR_INSTANCE')
    start_time = app.config.get('START_TIME')

    if not bot or not health_monitor or not start_time:
        return jsonify({"status": "error", "message": "Bot not fully initialized"}), 500

    uptime_seconds = time.time() - start_time
    health_status = health_monitor.get_status()

    return jsonify({
        "status": "healthy" if health_status.get("bot_ready") else "unhealthy",
        "timestamp": time.time(),
        "uptime_seconds": round(uptime_seconds),
        "bot_metrics": health_status
    })

# --- Web Server Control ---

def run_flask_app():
    """
    Runs the Flask application. This function is the target for our background thread.
    """
    try:
        # `host='0.0.0.0'` makes the server accessible from outside its container.
        # `port=8080` is a common port for web applications.
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        logger.error(f"Flask webserver encountered an error: {e}", exc_info=True)

def keep_alive(bot_instance, health_monitor_instance):
    """
    Starts the Flask web server in a separate background thread.

    Args:
        bot_instance: The main bot object.
        health_monitor_instance: The health monitor object.
    """
    logger.info("Starting keep-alive webserver...")
    # We pass the bot and health monitor instances to the Flask app's config
    # so our '/health' endpoint can access them.
    app.config['BOT_INSTANCE'] = bot_instance
    app.config['HEALTH_MONITOR_INSTANCE'] = health_monitor_instance
    app.config['START_TIME'] = time.time()

    server_thread = Thread(target=run_flask_app, daemon=True, name="WebServerThread")
    server_thread.start()
    logger.info("Keep-alive webserver is running in the background.")
