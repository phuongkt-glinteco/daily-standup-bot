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


def _collect_project_reports(state):
    """Return ordered project payloads parsed from a Slack view state."""

    relevant_keys = {"project", "did", "plan", "blockers", "hours"}
    grouped = {}

    def _extract_base(block_id):
        if block_id in relevant_keys:
            return block_id, ""

        for delimiter in ("_", "-"):
            for key in relevant_keys:
                prefix = f"{key}{delimiter}"
                if block_id.startswith(prefix):
                    return key, block_id[len(prefix) :]
        return None, None

    for block_id, action_payloads in state.items():
        base, suffix = _extract_base(block_id)

        if base not in relevant_keys:
            continue

        # Each block contains a single action payload keyed by action_id
        payload = next(iter(action_payloads.values()), {})
        value = payload.get("value")

        group = grouped.setdefault(suffix, {})
        group[base] = value

    def sort_key(item):
        suffix, _ = item
        if not suffix:
            return (0, 0)

        try:
            return (1, int(suffix))
        except ValueError:
            return (1, suffix)

    project_reports = []
    for _, fields in sorted(grouped.items(), key=sort_key):
        project_reports.append(  # preserve order for consistent summaries
            {
                "project": (fields.get("project") or "").strip(),
                "did": fields.get("did") or "",
                "plan": fields.get("plan") or "",
                "blockers": fields.get("blockers") or "",
                "hours": (fields.get("hours") or "").strip(),
            }
        )

    return project_reports


def _build_project_summary_lines(project_reports, today, tomorrow):
    """Compose markdown summary lines for one or more project reports."""

    lines = []
    multi_project = len(project_reports) > 1

    for index, report in enumerate(project_reports, start=1):
        if index > 1:
            lines.append("")  # blank line between project summaries

        project_name = report.get("project") or "N/A"
        header = (
            f"Project {index}: {project_name}"
            if multi_project
            else f"Project: {project_name}"
        )
        lines.append(header)

        lines.append(f"a. What did you do ({today})")
        lines.extend(_format_multiline_bullets(report.get("did")))

        lines.append(f"b. What do you plan to do ({tomorrow})")
        lines.extend(_format_multiline_bullets(report.get("plan")))

        lines.append("c. Blockers:")
        lines.extend(_format_multiline_bullets(report.get("blockers")))

        hours = report.get("hours") or "N/A"
        lines.append(f"d. Working hours: {hours}")

    return lines


def _build_standup_blocks(today, tomorrow, num_projects=1):
    """Return the block kit payload for the stand-up collection form."""

    project_count = max(1, min(num_projects, 5))  # enforce a reasonable upper bound

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🗓️ Daily Stand-up for {today}",
                "emoji": True,
            },
        }
    ]

    for index in range(1, project_count + 1):
        suffix = "" if index == 1 else f"_{index}"

        if project_count > 1:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Project {index}*",
                    },
                }
            )

        blocks.extend(
            [
                {
                    "type": "input",
                    "block_id": f"project{suffix}",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "project_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Project or client name",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Project"},
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": f"did{suffix}",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "did_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "List what you worked on today...",
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": f"What did you do ({today})?",
                    },
                },
                {
                    "type": "input",
                    "block_id": f"plan{suffix}",
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
                    "block_id": f"blockers{suffix}",
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
                    "block_id": f"hours{suffix}",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "hours_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g. 7.5 hrs",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Working hours"},
                },
                {"type": "divider"},
            ]
        )

    blocks.append(
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
        }
    )

    return blocks


load_dotenv()

app = Flask(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_USER_ID = os.environ.get("SLACK_USER_ID")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
SLACK_API_URL = "https://slack.com/api/chat.postMessage"


def _parse_project_count(command_text):
    """Return the requested number of projects parsed from slash command text."""

    if not command_text:
        return 1

    token = command_text.split()[0]
    try:
        return int(token)
    except ValueError:
        return 1


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
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    request_text = (request.form.get("text") or "").strip()
    requested_projects = max(1, _parse_project_count(request_text))

    blocks = _build_standup_blocks(today, tomorrow, requested_projects)

    return jsonify(
        {
            "response_type": "ephemeral",
            "text": "Please fill out your stand-up report:",
            "blocks": blocks,
        }
    )


def send_standup_prompt(user_id, num_projects=1):
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    blocks = _build_standup_blocks(today, tomorrow, num_projects)

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

    project_reports = _collect_project_reports(state)
    if not project_reports:
        try:
            project_reports = [
                {
                    "project": (
                        state["project"]["project_input"]["value"] or ""
                    ).strip(),
                    "did": state["did"]["did_input"]["value"] or "",
                    "plan": state["plan"]["plan_input"]["value"] or "",
                    "blockers": state["blockers"]["blockers_input"]["value"] or "",
                    "hours": (state["hours"]["hours_input"]["value"] or "").strip(),
                }
            ]
        except KeyError as e:
            print("❌ Parsing error:", e)
            return "", 200  # respond gracefully so Slack doesn't retry

    if not project_reports:
        print("❌ No project data found in Slack payload.")
        return "", 200

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    summary_lines = [f"Stand-up summary from <@{user}>"]
    summary_lines.extend(_build_project_summary_lines(project_reports, today, tomorrow))

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
