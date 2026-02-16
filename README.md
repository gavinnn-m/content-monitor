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

Configured in `content-sources.json`. The included config has a few example feeds to get started. Add your own RSS/Atom feeds organized by category.

To keep your real feed list private, copy to `content-sources.local.json` (gitignored) and point the script there with `--sources`.

### Supported source types
- RSS/Atom feeds (any standard feed URL)
- Reddit subreddits (via `.rss` suffix)
- YouTube channels (via `/feeds/videos.xml?channel_id=...`)
- Any service that outputs RSS (RSS-Bridge, etc.)

## Authors

- Matt Gavin ([@gavinnn-m](https://github.com/gavinnn-m))
- Scout (AI Lab Ranger 🔭)
