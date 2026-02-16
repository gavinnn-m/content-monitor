# Content Monitor

RSS/content monitoring pipeline for [mattgavin.dev](https://mattgavin.dev). Tracks 30+ feeds across telecom, AI/enterprise, thought leadership, Reddit, and aggregator sources to surface trending topics and blog post ideas.

## How it works

1. **Fetches** RSS feeds defined in `content-sources.json`
2. **Clusters** articles by keyword similarity
3. **Scores** clusters based on topic weights, source diversity, and volume
4. **Suggests** blog post angles connecting trends to telecom/vCon/voice-intelligence

## Usage

```bash
# Human-readable report (last 7 days)
python3 content-monitor.py

# JSON output
python3 content-monitor.py --json

# Custom lookback period
python3 content-monitor.py --days 3
```

## Dependencies

- Python 3.10+
- `feedparser`, `requests` (auto-installed on first run)

## Feed Sources

Configured in `content-sources.json`. Categories:
- **Telecom Industry** — Light Reading, Fierce Telecom, RCR Wireless, etc.
- **AI & Enterprise** — The Verge AI, Ars Technica, MIT Tech Review, etc.
- **Thought Leaders** — Simon Willison, Ben Thompson, Benedict Evans, etc.
- **Reddit** — r/VoIP, r/telecom, r/artificial, r/LocalLLaMA, etc.
- **Aggregators** — Hacker News, Techmeme

## Authors

- Matt Gavin ([@gavinnn-m](https://github.com/gavinnn-m))
- Scout (AI Lab Ranger 🔭)
