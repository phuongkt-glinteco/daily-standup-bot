import datetime
import os

import requests

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

if not WEBHOOK_URL:
    raise RuntimeError("Set the WEBHOOK_URL environment variable before running the bot.")

def send_message():
    today = datetime.datetime.now().strftime("%A, %B %d")
    message = f"Good morning team! 🌞\nToday is *{today}*. Let’s make it a great day!"
    payload = {"text": message}
    requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    send_message()
