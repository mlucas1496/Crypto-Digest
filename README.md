# Crypto Digest

A daily crypto news digest that scrapes multiple sources, filters with Claude AI, and serves a clean dashboard — automatically every morning at 7:30 AM.

## How it works

1. **Scrapes** news from: Google News, CoinDesk, CoinTelegraph, Decrypt, The Block, Bitcoin Magazine, GlobeNewswire, Milk Road, WSJ
2. **Filters & summarizes** articles using Claude (via Claude Code CLI — no API key needed)
3. **Serves** a web dashboard at `http://localhost:8080`

The digest runs automatically every day at **7:30 AM Eastern Time**.

## Prerequisites

- Python 3.11+
- [Claude Code CLI](https://claude.ai/code) installed and authenticated (`claude` must be in your PATH)

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/mlucas1496/Crypto-Digest.git
cd Crypto-Digest

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env if you need to change the schedule or sources

# 5. Run
python run.py
```

Open `http://localhost:8080` in your browser.

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `DIGEST_HOUR` | `7` | Hour to run digest (24h) |
| `DIGEST_MINUTE` | `30` | Minute to run digest |
| `DIGEST_TIMEZONE` | `America/New_York` | Timezone for schedule |
| `ENABLED_SOURCES` | all sources | Comma-separated list of scrapers to enable |
| `LOOKBACK_HOURS` | `24` | How far back to look for articles |
| `MAX_ARTICLES_PER_CATEGORY` | `5` | Max items per category in the digest |
| `FLASK_PORT` | `8080` | Web server port |
| `NODE_EXTRA_CA_CERTS` | _(unset)_ | Path to CA cert bundle (for corporate SSL proxies) |
| `REQUESTS_CA_BUNDLE` | _(unset)_ | Path to CA cert bundle for Python requests (for corporate SSL proxies) |

## Run a digest immediately

```bash
# One-shot run (no server)
python run.py --once

# Or via the API while server is running
curl -X POST "http://localhost:8080/api/run-now"

# Force re-run even if today's digest already completed
curl -X POST "http://localhost:8080/api/run-now?force=true"
```

## Corporate SSL proxies (e.g. Zscaler)

If your company inspects HTTPS traffic, set these in your `.env`:

```
NODE_EXTRA_CA_CERTS=/path/to/corporate-cert.pem
REQUESTS_CA_BUNDLE=/path/to/corporate-cert.pem
```

## Running as a background service (macOS)

To have the server start automatically at login, create a LaunchAgent plist pointing to `run.py`. See Apple's [launchd documentation](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) for details.
