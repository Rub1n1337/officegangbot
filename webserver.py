
from flask import Flask, jsonify
from threading import Thread
import logging
import time

# Suppress Flask's default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
start_time = time.time()

@app.route('/')
def home():
    return jsonify({
        "status": "Bot is running", 
        "timestamp": time.time(),
        "uptime": time.time() - start_time,
        "code": 200
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "timestamp": time.time(),
        "uptime": time.time() - start_time,
        "code": 200
    })

@app.route('/ping')
def ping():
    return jsonify({"status": "pong", "timestamp": time.time()})

def run():
    """Run Flask server"""
    try:
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Flask server error: {e}")

def keep_alive():
    """Start the keep-alive webserver"""
    print("Starting keep-alive webserver on port 8080...")
    server = Thread(target=run, daemon=True)
    server.start()
    print("Keep-alive webserver started successfully!")
    return server
