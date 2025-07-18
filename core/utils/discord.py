import os
import requests
import argparse
from dotenv import load_dotenv

load_dotenv()

def split_message(message, max_length=1800):
    lines = message.split('\n')
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > max_length:
            chunks.append(current)
            current = line
        else:
            current += '\n' + line if current else line

    if current:
        chunks.append(current)

    return chunks

def ping_discord(message, message_info, webhook_url=None) :
    if webhook_url == "login":
        webhook_url = os.getenv("WEBHOOK_URL_LOGIN")
    else:
        webhook_url = os.getenv("WEBHOOK_URL")
    user_ids = os.getenv("USER_IDS", "").split(",")

    if not webhook_url or not user_ids:
        print(" Missing WEBHOOK_URL or USER_IDS in .env")
        return

    mentions = " ".join(f"\n<@{uid.strip()}>" for uid in user_ids)
    header = f" Info: {message_info}\n {mentions}"

    full_message = f"{header}\n\n{message}"
    
    if len(full_message) > 1800:
        print(" Message too long. Splitting and sending in parts...")

        parts = split_message(full_message)

        for idx, part in enumerate(parts):
            content = f"{part}\n\n Part {idx + 1} of {len(parts)}"
            send_to_webhook(webhook_url, content, idx + 1)
    else:
        send_to_webhook(webhook_url, full_message)

def send_to_webhook(webhook_url, content, part_num=None):
    payload = { "content": content }
    response = requests.post(webhook_url, json=payload)

    if response.status_code == 204:
        print(f" Message{' part ' + str(part_num) if part_num else ''} sent.")
    else:
        print(f"Failed to send message. Status {response.status_code}: {response.text}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a Discord ping with context")
    parser.add_argument("message", help="The message content to send")
    parser.add_argument("message_info", help="Info about where this message came from in your code")

    args = parser.parse_args()

    ping_discord(args.message, args.message_info)
