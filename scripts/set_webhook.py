#!/usr/bin/env python3
"""Register the Telegram webhook URL.

Usage:
    python scripts/set_webhook.py --url https://xxxx.execute-api.region.amazonaws.com/webhook

Or to delete the webhook:
    python scripts/set_webhook.py --delete
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from src.telegram.bot import TelegramBot


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Telegram bot webhook")
    parser.add_argument("--url", help="Webhook URL to register")
    parser.add_argument(
        "--delete", action="store_true", help="Delete the current webhook"
    )
    parser.add_argument(
        "--info", action="store_true", help="Show current bot info"
    )
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set in environment")
        sys.exit(1)

    bot = TelegramBot(token)

    if args.info:
        result = bot.get_me()
        print(json.dumps(result, indent=2))

    elif args.delete:
        result = bot.delete_webhook()
        print(f"Webhook deleted: {json.dumps(result, indent=2)}")

    elif args.url:
        result = bot.set_webhook(args.url)
        print(f"Webhook set to {args.url}")
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
