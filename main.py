import datetime
import os
import requests
import textwrap

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

if not WEBHOOK_URL:
    raise RuntimeError(
        "Set the WEBHOOK_URL environment variable before running the bot."
    )


def prompt_list(prompt_text):
    print(f"\n{prompt_text} (press Enter twice to finish):")
    items = []
    while True:
        line = input(" - ").strip()
        if not line:
            break
        items.append(line)
    return items or ["None"]


def get_project_input(project_num):
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    project_name = (
        input(f"\n{project_num}. Project name: ").strip() or f"Project {project_num}"
    )

    did = prompt_list(f"What did you do ({today})")
    plan = prompt_list(f"What do you plan to do ({tomorrow})")
    blockers = prompt_list("Blockers")
    hours = input("Working hours (e.g., 7.5 hrs): ").strip() or "N/A"

    # format Slack message section
    formatted = textwrap.dedent(
        f"""
    {project_num}. {project_name}
    a. What did you do ({today})
    {chr(10).join(f" - {task}" for task in did)}
    b. What do you plan to do ({tomorrow})
    {chr(10).join(f" - {task}" for task in plan)}
    c. Blockers:
    {chr(10).join(f" - {b}" for b in blockers)}
    d. Working hours: {hours}
    """
    ).strip()

    return formatted


def send_message(message):
    payload = {"text": message}
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Slack API error: {response.text}")


def main():
    print("👋 Let's prepare your daily stand-up report!")

    projects = []
    project_count = 1
    while True:
        projects.append(get_project_input(project_count))
        cont = input("\nAdd another project? (y/n): ").lower()
        if cont != "y":
            break
        project_count += 1

    final_message = "\n\n".join(projects)
    print("\n✅ Here's your final message:\n")
    print(final_message)
    confirm = input("\nSend to Slack? (y/n): ").lower()
    if confirm == "y":
        send_message(final_message)
        print("🎉 Message sent to Slack successfully!")
    else:
        print("❌ Message not sent.")


if __name__ == "__main__":
    main()
