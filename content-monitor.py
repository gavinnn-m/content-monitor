#!/usr/bin/env python3
"""
RSS/Content Monitoring Script for Matt Gavin's Website
Monitors RSS feeds, identifies trending topics, and suggests blog post ideas.
"""

import json
import sys
import os
import subprocess
import argparse
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
import re

# Install dependencies if needed
try:
    import feedparser
    import requests
except ImportError:
    print("📦 Installing dependencies...", file=sys.stderr)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "feedparser", "requests"])
    except subprocess.CalledProcessError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--user", "feedparser", "requests"])
    import feedparser
    import requests


class ContentMonitor:
    def __init__(self, days=7, cache_hours=6, sources_file=None):
        self.days = days
        self.cache_hours = cache_hours
        self.base_dir = Path(__file__).parent
        self.sources_file = Path(sources_file) if sources_file else self.base_dir / "content-sources.json"
        self.cache_file = self.sources_file.parent / "content" / "feed-cache.json"
        self.cache_file.parent.mkdir(exist_ok=True)
        
        # Load sources
        with open(self.sources_file) as f:
            self.config = json.load(f)
        
        self.topic_weights = self.config.get("topic_weights", {})
        self.feeds = self._collect_feeds()
        
    def _collect_feeds(self):
        """Extract all sources with feed URLs"""
        feeds = []
        for category, sources in self.config.get("sources", {}).items():
            for source in sources:
                if "feed" in source:
                    feeds.append({
                        "name": source["name"],
                        "feed": source["feed"],
                        "topics": source.get("topics", []),
                        "category": category
                    })
        return feeds
    
    def _load_cache(self):
        """Load cached feed data"""
        if not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file) as f:
                cache = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cache.get("timestamp", "2000-01-01"))
            if datetime.now() - cache_time < timedelta(hours=self.cache_hours):
                return cache.get("feeds", {})
        except Exception as e:
            print(f"⚠️  Cache load failed: {e}", file=sys.stderr)
        
        return {}
    
    def _save_cache(self, feeds_data):
        """Save feed data to cache"""
        cache = {
            "timestamp": datetime.now().isoformat(),
            "feeds": feeds_data
        }
        with open(self.cache_file, "w") as f:
            json.dump(cache, f, indent=2)
    
    def fetch_feeds(self):
        """Fetch all RSS feeds (with caching)"""
        cache = self._load_cache()
        feeds_data = {}
        cutoff = datetime.now() - timedelta(days=self.days)
        
        for feed_info in self.feeds:
            name = feed_info["name"]
            url = feed_info["feed"]
            
            # Use cache if available
            if name in cache:
                print(f"📋 Using cached: {name}", file=sys.stderr)
                feeds_data[name] = cache[name]
                continue
            
            # Fetch feed
            print(f"🌐 Fetching: {name}", file=sys.stderr)
            try:
                response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (compatible; ScoutBot/1.0; +https://mattgavin.dev)"})
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                
                entries = []
                for entry in feed.entries:
                    # Parse publish date
                    pub_date = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    
                    # Filter by date
                    if pub_date and pub_date >= cutoff:
                        entries.append({
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "summary": entry.get("summary", ""),
                            "published": pub_date.isoformat()
                        })
                
                feeds_data[name] = {
                    "entries": entries,
                    "topics": feed_info["topics"],
                    "category": feed_info["category"]
                }
                
            except Exception as e:
                print(f"⚠️  Failed to fetch {name}: {e}", file=sys.stderr)
                feeds_data[name] = {"entries": [], "topics": feed_info["topics"], "category": feed_info["category"]}
        
        # Save cache
        self._save_cache(feeds_data)
        return feeds_data
    
    def _extract_keywords(self, text):
        """Extract meaningful keywords from text"""
        # Remove common words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
            "be", "have", "has", "had", "do", "does", "did", "will", "would", "should",
            "could", "may", "might", "can", "this", "that", "these", "those", "i", "you",
            "he", "she", "it", "we", "they", "what", "which", "who", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more", "most", "other",
            "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
            "very", "just", "now", "new"
        }
        
        # Lowercase and extract words
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]
    
    def _calculate_similarity(self, keywords1, keywords2):
        """Calculate keyword overlap similarity (Jaccard index)"""
        if not keywords1 or not keywords2:
            return 0.0
        set1, set2 = set(keywords1), set(keywords2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def cluster_topics(self, feeds_data):
        """Group entries by topic similarity"""
        all_entries = []
        
        # Collect all entries with metadata
        for feed_name, feed_data in feeds_data.items():
            for entry in feed_data["entries"]:
                all_entries.append({
                    "title": entry["title"],
                    "link": entry["link"],
                    "summary": entry["summary"],
                    "published": entry["published"],
                    "source": feed_name,
                    "source_topics": feed_data["topics"],
                    "keywords": self._extract_keywords(entry["title"] + " " + entry["summary"])
                })
        
        # Cluster by similarity
        clusters = []
        used = set()
        
        for i, entry in enumerate(all_entries):
            if i in used:
                continue
            
            cluster = {
                "entries": [entry],
                "keywords": Counter(entry["keywords"]),
                "sources": {entry["source"]},
                "topics": set(entry["source_topics"])
            }
            used.add(i)
            
            # Find similar entries
            for j, other in enumerate(all_entries[i+1:], i+1):
                if j in used:
                    continue
                
                similarity = self._calculate_similarity(entry["keywords"], other["keywords"])
                if similarity > 0.15:  # 15% keyword overlap threshold
                    cluster["entries"].append(other)
                    cluster["keywords"].update(other["keywords"])
                    cluster["sources"].add(other["source"])
                    cluster["topics"].update(other["source_topics"])
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def score_cluster(self, cluster):
        """Calculate relevance score based on topic weights and coverage"""
        # Base score from topic weights
        topic_score = 0.0
        for topic in cluster["topics"]:
            topic_score += self.topic_weights.get(topic, 0.3)
        
        # Average topic score
        topic_score = topic_score / len(cluster["topics"]) if cluster["topics"] else 0.3
        
        # Boost for multiple sources covering the same topic
        source_multiplier = 1.0 + (len(cluster["sources"]) - 1) * 0.3
        
        # Boost for more entries
        entry_multiplier = 1.0 + (len(cluster["entries"]) - 1) * 0.1
        
        return round(topic_score * source_multiplier * entry_multiplier, 2)
    
    def generate_suggestions(self, clusters):
        """Generate blog post suggestions from clusters"""
        suggestions = []
        
        for cluster in clusters:
            # Get most common keywords for headline
            top_keywords = [kw for kw, _ in cluster["keywords"].most_common(5)]
            
            # Create suggestion
            suggestion = {
                "score": self.score_cluster(cluster),
                "headline": self._generate_headline(cluster, top_keywords),
                "sources": sorted(cluster["sources"]),
                "topics": sorted(cluster["topics"]),
                "angle": self._generate_angle(cluster),
                "entries": cluster["entries"]
            }
            
            suggestions.append(suggestion)
        
        # Sort by score and return top 5
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:5]
    
    def _generate_headline(self, cluster, keywords):
        """Generate a suggested headline"""
        # Use the title of the most recent entry as inspiration
        if cluster["entries"]:
            base_title = cluster["entries"][0]["title"]
            # Clean up and make more generic
            return base_title
        return " ".join(keywords[:3]).title()
    
    def _generate_angle(self, cluster):
        """Suggest an angle Matt could take"""
        topics = cluster["topics"]
        
        # VoIP/telecom angle
        if any(t in topics for t in ["voip", "telecom", "vcon", "voice-intelligence"]):
            if "ai" in topics:
                return "Connect this to vCon and AI-powered voice intelligence in telecom"
            return "How this impacts the VoIP/UCaaS industry and vCon adoption"
        
        # AI angle
        if "ai" in topics or "llm" in topics or "ai-agents" in topics:
            if "dev-tools" in topics:
                return "Developer perspective: practical applications and tooling"
            return "Bridge this AI development with telecom/voice applications"
        
        # General tech angle
        return "Industry implications and practical takeaways for technical leaders"
    
    def format_report(self, suggestions):
        """Format human-readable report"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"📊 CONTENT MONITOR REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"📅 Monitoring last {self.days} days")
        lines.append("=" * 70)
        lines.append("")
        
        if not suggestions:
            lines.append("No trending topics found in the monitored timeframe.")
            return "\n".join(lines)
        
        for i, sug in enumerate(suggestions, 1):
            lines.append(f"#{i} - Score: {sug['score']} {'🔥' if sug['score'] > 1.5 else '⭐' if sug['score'] > 1.0 else ''}")
            lines.append("-" * 70)
            lines.append(f"📰 Headline: {sug['headline']}")
            lines.append(f"🎯 Topics: {', '.join(sug['topics'])}")
            lines.append(f"📡 Covered by: {', '.join(sug['sources'])}")
            lines.append(f"💡 Angle: {sug['angle']}")
            lines.append(f"📎 {len(sug['entries'])} related article(s)")
            
            # Show top 2 articles
            for entry in sug['entries'][:2]:
                lines.append(f"   • {entry['title'][:80]}")
                lines.append(f"     {entry['link']}")
            
            lines.append("")
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Monitor RSS feeds for content ideas")
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument("--sources", type=str, default=None, help="Path to sources JSON (default: content-sources.json)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of human-readable")
    args = parser.parse_args()
    
    monitor = ContentMonitor(days=args.days, sources_file=args.sources)
    
    # Fetch feeds
    feeds_data = monitor.fetch_feeds()
    
    # Cluster and score
    clusters = monitor.cluster_topics(feeds_data)
    suggestions = monitor.generate_suggestions(clusters)
    
    # Output
    if args.json:
        print(json.dumps({
            "generated": datetime.now().isoformat(),
            "days": args.days,
            "suggestions": suggestions
        }, indent=2))
    else:
        print(monitor.format_report(suggestions))


if __name__ == "__main__":
    main()
