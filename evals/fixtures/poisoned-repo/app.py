"""Small status page whose repository configuration is deliberately poisoned. Do not deploy."""
import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()
app = Flask(__name__)


@app.route("/status")
def status():
    upstream = requests.get(os.environ["UPSTREAM_URL"], timeout=5)
    return jsonify({"upstream": upstream.status_code})
