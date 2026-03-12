# Claude-TG-BOT

Telegram bot that scans RSS feeds daily for tech, crypto, macro-economic, and digital asset news — then uses Claude AI to generate Twitter/X and LinkedIn post drafts with interactive Telegram controls.

## Features

- **RSS feed scanning** across 10 curated sources (CoinDesk, TechCrunch, CNBC, etc.)
- **Claude AI drafts** — generates both Twitter (280 char) and LinkedIn (150-300 word) posts
- **Interactive Telegram controls** — view, approve, edit with feedback, or skip each draft
- **Smart deduplication** — URL and title-based dedup to avoid repeated suggestions
- **Article ranking** — scores by recency, topic relevance, and source priority
- **Serverless** — AWS Lambda + EventBridge + DynamoDB, deployed via SAM

## Quick Start

### Prerequisites

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/)
- [Telegram Bot token](https://core.telegram.org/bots#botfather) (create via BotFather)
- AWS account (for deployment)

### Local Development

```bash
# Clone and install
git clone https://github.com/zinkofff/Claude-TG-BOT.git
cd Claude-TG-BOT
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run tests
pytest tests/ -v

# Run a local scan (sends to your Telegram)
python scripts/local_scan.py

# Run the webhook locally (use with ngrok)
python scripts/local_webhook.py
```

### AWS Deployment

```bash
# Set secrets in SSM Parameter Store
aws ssm put-parameter --name /claude-tg-bot/anthropic-api-key --value "sk-ant-..." --type SecureString
aws ssm put-parameter --name /claude-tg-bot/telegram-bot-token --value "123:ABC..." --type SecureString
aws ssm put-parameter --name /claude-tg-bot/telegram-chat-id --value "your-chat-id" --type String

# Build and deploy
sam build
sam deploy --guided

# Register the webhook URL (shown in deploy outputs)
python scripts/set_webhook.py --url https://xxxx.execute-api.region.amazonaws.com/webhook
```

## Architecture

```
EventBridge (daily 08:00 UTC)
        |
        v
Lambda: news_scanner ──> DynamoDB (articles + drafts)
  - Fetch 10 RSS feeds              ^
  - Deduplicate                      |
  - Rank top 5               Lambda: telegram_webhook
  - Claude AI → drafts          - Approve / Edit / Skip
  - Send Telegram digest         - Claude re-drafts on feedback
                                     ^
                                     |
                                 API Gateway ← Telegram Webhook
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and instructions |
| `/help`  | Show available commands |
| `/scan`  | Trigger an on-demand news scan |

## Configuration

All configuration via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | — | Your Telegram chat ID |
| `CLAUDE_MODEL` | `claude-haiku-4-5` | Claude model to use |
| `DIGEST_ARTICLE_COUNT` | `5` | Articles per daily digest |

## RSS Sources

| Category | Sources |
|----------|---------|
| Crypto | CoinDesk, CoinTelegraph, Decrypt, The Block, Bitcoin Magazine |
| Digital Assets | Blockworks, The Defiant |
| Tech | TechCrunch |
| Macro | CNBC, Investing.com |

Edit `src/config/feeds.py` to add or remove feeds.
