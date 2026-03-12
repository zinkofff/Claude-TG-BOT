#!/usr/bin/env python3
"""Run the Telegram webhook handler locally for testing.

Starts a lightweight HTTP server that invokes the Lambda handler.
Use with ngrok to expose it to Telegram:

    1. python scripts/local_webhook.py
    2. ngrok http 8080
    3. python scripts/set_webhook.py --url https://xxxx.ngrok.io/webhook

Usage:
    python scripts/local_webhook.py [--port 8080]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(override=True)

from src.handlers.telegram_webhook import lambda_handler


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler that forwards POST requests to the Lambda handler."""

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        print(f"\n📨 Received webhook: {body[:200]}...")

        # Build a mock API Gateway event
        event = {
            "body": body,
            "headers": dict(self.headers),
            "requestContext": {
                "http": {
                    "method": "POST",
                    "path": "/webhook",
                }
            },
        }

        result = lambda_handler(event, None)

        status = result.get("statusCode", 200)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result.get("body", "ok")).encode())

    def do_GET(self) -> None:  # noqa: N802
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Claude TG Bot webhook is running")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local webhook server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), WebhookHandler)
    print(f"🚀 Webhook server listening on http://localhost:{args.port}")
    print(f"   POST /webhook — Telegram webhook endpoint")
    print(f"   GET  /        — Health check")
    print(f"\nUse ngrok to expose: ngrok http {args.port}")
    print("Then register: python scripts/set_webhook.py --url https://xxxx.ngrok.io/webhook\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        server.server_close()


if __name__ == "__main__":
    main()
