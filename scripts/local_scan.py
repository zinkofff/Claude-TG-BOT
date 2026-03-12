#!/usr/bin/env python3
"""Run the news scanner locally for testing.

Simulates the EventBridge trigger by calling the Lambda handler
with a mock event. Requires real API keys in .env file.

Usage:
    python scripts/local_scan.py
"""

from __future__ import annotations

import json
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from src.handlers.news_scanner import lambda_handler


def main() -> None:
    # Simulate EventBridge scheduled event
    event = {
        "source": "local.test",
        "detail-type": "Scheduled Event",
        "detail": {},
    }

    print("🔍 Starting local news scan...")
    print("=" * 50)

    result = lambda_handler(event, None)

    print("=" * 50)
    print(f"\n📊 Result:\n{json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
