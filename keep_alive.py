from flask import Flask
from threading import Thread
import os


app = Flask(__name__)


@app.route("/")
def home():

    return "Discord Gemini AI Bot is online."


@app.route("/health")
def health():

    return {
        "status": "online"
    }


def run():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )


def keep_alive():

    thread = Thread(
        target=run
    )

    thread.daemon = True

    thread.start()
