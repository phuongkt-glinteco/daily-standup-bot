# daily-standup-bot

## Overview
Simple Flask app that posts a daily stand-up summary into Slack. Team members trigger a modal via `/standup`, fill in their updates (including multi-project reporting), and the bot publishes a formatted summary to the configured channel.

## Prerequisites
- Python 3.9+
- A Slack workspace where you can create/manage apps
- (Optional) `pip install pre-commit` if you plan to run the formatting hooks locally

## Local Setup
1. Clone the repository and `cd` into it.
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` (create the file if it does not exist) and set:
   - `SLACK_BOT_TOKEN` – Bot User OAuth token from Slack
   - `SLACK_USER_ID` – Default Slack user ID to DM daily prompts
   - `CHANNEL_ID` – Channel to receive the posted stand-up summaries

## Running the App
Start the Flask server locally:
```bash
python3 app.py
```

The server listens on port `3000` by default. Use a tunneling tool such as `ngrok` to expose `http://localhost:3000` to Slack during development.

## Slack App Configuration
1. Create a new app from [https://api.slack.com/apps](https://api.slack.com/apps) using "From scratch".
2. Under **Basic Information → Add features and functionality**, enable:
   - **Slash Commands**: configure `/standup` pointing to `https://<your-domain>/standup` (POST).
   - **Interactivity & Shortcuts**: toggle on and set the Request URL to `https://<your-domain>/interactivity`.
3. Under **OAuth & Permissions**, add bot scopes:
   - `chat:write`
   - `commands`
   - `im:write`
4. Install the app to your workspace and grab the Bot User OAuth token for `SLACK_BOT_TOKEN`.
5. Invite the bot user to the channel that should receive the reports and copy the channel ID for `CHANNEL_ID`.
6. Determine each teammate’s Slack user ID for use as `SLACK_USER_ID` (or supply this via API payloads when triggering prompts).

## GitHub Actions Secrets
If you deploy or test via GitHub Actions, store sensitive values as repository secrets:
- Navigate to **Settings → Secrets and variables → Actions**.
- Add the following names and values:
  - `SLACK_BOT_TOKEN`
  - `SLACK_USER_ID`
  - `CHANNEL_ID`
- Reference the secrets in your workflow using `${{ secrets.NAME }}` and export them to the job environment before running the bot.

## Helpful Commands
- `pytest` – Run the test suite.
- `pre-commit run --all-files` – Apply formatting and linting.

## Deploying to Render
Render can read the `render.yaml` blueprint in this repository to provision a web service:

1. Commit your changes and push to GitHub (Render deploys straight from the repo).
2. In the Render dashboard, click **New → Blueprint** and point it at this repository.
3. Review the generated service named `daily-standup-bot` and click **Apply**.
4. After the service is created, open its **Environment** tab and add the required variables:
   - `SLACK_BOT_TOKEN`
   - `SLACK_USER_ID`
   - `CHANNEL_ID`
5. Trigger a manual deploy to install dependencies (via `pip install -r requirements.txt`) and start the app with `gunicorn app:app`.

Render automatically provides the `PORT` environment variable; the app binds to it when running in production. Update your Slack slash command and interactivity URLs to point at the Render service once the deploy is healthy.
