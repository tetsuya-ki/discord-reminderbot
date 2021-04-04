# file name is keep_alive.py
from flask import Flask
from threading import Thread
import logging
# ロガーの取得
werkzeug_logger = logging.getLogger("werkzeug")
# レベルの変更
werkzeug_logger.setLevel(logging.ERROR)

app = Flask('')
@app.route('/')
def main():
    return "Your bot is alive!"
def run():
    app.run(host="0.0.0.0", port=8080)
def keep_alive():
    server = Thread(target=run)
    server.start()