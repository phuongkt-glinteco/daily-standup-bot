from flask import Flask, request, jsonify
import os
import datetime
import requests
from dotenv import load_dotenv


def _format_multiline_bullets(value):
    """Return stand-up bullet lines from multiline input."""
    if not value:
        return [" - None"]

    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return [" - None"]

    return [f" - {line}" for line in lines]


load_dotenv()

app = Flask(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_USER_ID = os.environ.get("SLACK_USER_ID")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
SLACK_API_URL = "https://slack.com/api/chat.postMessage"


def send_slack_message(channel, text, blocks=None):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }

    payload = {
        "channel": channel,
        "text": text,
        "mrkdwn": True,
    }

    if blocks:
        payload["blocks"] = blocks

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    if not data.get("ok"):
        print("❌ Slack API error:", data)
    else:
        print("✅ Message sent to Slack:", channel)


@app.route("/standup", methods=["POST"])
def standup_command():
    """Triggered via slash command like /standup"""
    user_id = request.form.get("user_id")
    send_standup_prompt(user_id)
    return jsonify(
        {
            "response_type": "ephemeral",
            "text": "Check your DM for today’s stand-up input!",
        }
    )


def send_standup_prompt(user_id):
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🗓️ Daily Stand-up for {today}",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "project",
            "element": {
                "type": "plain_text_input",
                "action_id": "project_input",
                "placeholder": {"type": "plain_text", "text": "Project or client name"},
            },
            "label": {"type": "plain_text", "text": "Project"},
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "did",
            "element": {
                "type": "plain_text_input",
                "action_id": "did_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "List what you worked on today...",
                },
            },
            "label": {"type": "plain_text", "text": f"What did you do ({today})?"},
        },
        {
            "type": "input",
            "block_id": "plan",
            "element": {
                "type": "plain_text_input",
                "action_id": "plan_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Tasks or goals for tomorrow...",
                },
            },
            "label": {
                "type": "plain_text",
                "text": f"What do you plan to do ({tomorrow})?",
            },
        },
        {
            "type": "input",
            "block_id": "blockers",
            "element": {
                "type": "plain_text_input",
                "action_id": "blockers_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Anything blocking your progress?",
                },
            },
            "label": {"type": "plain_text", "text": "Blockers"},
        },
        {
            "type": "input",
            "block_id": "hours",
            "element": {
                "type": "plain_text_input",
                "action_id": "hours_input",
                "placeholder": {"type": "plain_text", "text": "e.g. 7.5 hrs"},
            },
            "label": {"type": "plain_text", "text": "Working hours"},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Submit", "emoji": True},
                    "style": "primary",
                    "action_id": "submit_standup",
                }
            ],
        },
    ]

    # Open DM and send message
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    r = requests.post(
        "https://slack.com/api/conversations.open",
        headers=headers,
        json={"users": user_id},
    )
    dm_id = r.json()["channel"]["id"]
    send_slack_message(dm_id, "Please fill out your stand-up:", blocks=blocks)


def send_daily_standup_prompt():
    """Trigger the stand-up prompt for the configured default user."""
    if not SLACK_USER_ID:
        raise RuntimeError("Set SLACK_USER_ID to auto-DM the default recipient.")

    send_standup_prompt(SLACK_USER_ID)


@app.route("/interactivity", methods=["POST"])
@app.route("/interactivity", methods=["POST"])
def handle_interactivity():
    import json

    payload = json.loads(request.form["payload"])
    user = payload["user"]["id"]
    state = payload.get("state", {}).get("values", {})

    try:
        project = state["project"]["project_input"]["value"]
        did = state["did"]["did_input"]["value"]
        plan = state["plan"]["plan_input"]["value"]
        blockers = state["blockers"]["blockers_input"]["value"]
        hours = state["hours"]["hours_input"]["value"]
    except KeyError as e:
        print("❌ Parsing error:", e)
        return "", 200  # respond gracefully so Slack doesn't retry

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    summary_lines = [
        f"Stand-up summary from <@{user}>",
        f"Project: {project.strip() if project else 'N/A'}",
        f"a. What did you do ({today})",
        *_format_multiline_bullets(did),
        f"b. What do you plan to do ({tomorrow})",
        f" - {plan or 'None'}",
        "c. Blockers:",
        f" - {blockers or 'None'}",
        f"d. Working hours: {hours or 'N/A'}",
    ]

    summary = "```\n" + "\n".join(summary_lines) + "\n```"

    send_slack_message(CHANNEL_ID, summary)

    # Send confirmation back to user
    response_url = payload.get("response_url")
    if response_url:
        requests.post(
            response_url, json={"text": "✅ Your stand-up report has been sent!"}
        )

    return "", 200


if __name__ == "__main__":
    app.run(port=3000, debug=True)
