
from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "Bot is running", "code": 200})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "code": 200})

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server = Thread(target=run)
    server.daemon = True
    server.start()
