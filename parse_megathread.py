#!/usr/bin/env python3
"""
Fetches r/Piracy megathread wiki via multiple strategies and parses into data.json.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from html import unescape

CATEGORY_MAP = {
    "privacy": {"badge": "privacy", "label": "Privacy & Security"},
    "torrent client": {"badge": "torrent", "label": "Torrent Clients"},
    "torrent indexer": {"badge": "torrent", "label": "Torrent Indexers"},
    "ebook": {"badge": "ebooks", "label": "Ebooks & Textbooks"},
    "textbook": {"badge": "ebooks", "label": "Ebooks & Textbooks"},
    "course": {"badge": "courses", "label": "Courses & Tutorials"},
    "tutorial": {"badge": "courses", "label": "Courses & Tutorials"},
    "game": {"badge": "games", "label": "Games"},
    "rom": {"badge": "games", "label": "Games"},
    "movie": {"badge": "movies", "label": "Movies & Series"},
    "series": {"badge": "movies", "label": "Movies & Series"},
    "stream": {"badge": "movies", "label": "Movies & Series"},
    "anime": {"badge": "anime", "label": "Anime"},
    "music": {"badge": "music", "label": "Music"},
    "android": {"badge": "android", "label": "Android"},
    "apk": {"badge": "android", "label": "Android"},
    "tool": {"badge": "tools", "label": "Tools & Activation"},
    "direct download": {"badge": "ddl", "label": "Direct Downloads"},
    "misc": {"badge": "misc", "label": "Miscellaneous"},
    "security": {"badge": "privacy", "label": "Privacy & Security"},
    "vpn": {"badge": "privacy", "label": "Privacy & Security"},
}

def detect_category(heading):
    h = heading.lower()
    for key, meta in CATEGORY_MAP.items():
        if key in h:
            return meta
    return {"badge": "misc", "label": heading.strip()}

def get(url, headers, timeout=20):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")

# ── Strategy 1: GitHub Gist mirror (most reliable, community-maintained) ──────
def fetch_from_gist():
    # Raw markdown from a known public gist mirror of the megathread
    url = "https://gist.githubusercontent.com/teraflik/f718fd2611cb1eb589a3e5e6599290f6/raw/Piracy.md"
    headers = {"User-Agent": "Mozilla/5.0"}
    print("Trying GitHub Gist mirror...")
    try:
        md = get(url, headers)
        if len(md) > 5000:
            print(f"  Gist: got {len(md)} chars")
            return md
    except Exception as e:
        print(f"  Gist failed: {e}", file=sys.stderr)
    return None

# ── Strategy 2: Reddit JSON with rotating user-agents ─────────────────────────
def fetch_from_reddit():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "curl/8.5.0",
    ]
    urls = [
        "https://www.reddit.com/r/Piracy/wiki/megathread.json",
        "https://old.reddit.com/r/Piracy/wiki/megathread.json",
    ]
    for url in urls:
        for agent in agents:
            try:
                print(f"Trying Reddit JSON ({agent[:30]}...)...")
                time.sleep(2)
                data = get(url, {
                    "User-Agent": agent,
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                })
                parsed = json.loads(data)
                md = parsed["data"]["content_md"]
                if len(md) > 5000:
                    print(f"  Reddit JSON: got {len(md)} chars")
                    return md
            except Exception as e:
                print(f"  Failed: {e}", file=sys.stderr)
    return None

# ── Strategy 3: Reddit HTML scrape ────────────────────────────────────────────
def fetch_from_reddit_html():
    url = "https://www.reddit.com/r/Piracy/wiki/megathread/"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.9",
    }
    print("Trying Reddit HTML scrape...")
    try:
        time.sleep(2)
        html = get(url, headers)
        # Extract links from HTML directly
        return extract_from_html(html)
    except Exception as e:
        print(f"  HTML scrape failed: {e}", file=sys.stderr)
    return None

def extract_from_html(html):
    """Parse sections and links directly from Reddit wiki HTML."""
    # Strip HTML tags helper
    def strip_tags(s):
        return re.sub(r'<[^>]+>', '', s).strip()

    sections = []
    current_section = None

    # Find all heading and list item elements in wiki content
    # Reddit wiki HTML uses h1/h2/h3 for sections and li > a for links
    content_match = re.search(r'<div class="[^"]*wiki[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
    if not content_match:
        # Try broader match
        content_match = re.search(r'<div[^>]+data-testid="wiki-content"[^>]*>(.*)', html, re.DOTALL)
    
    block = content_match.group(1) if content_match else html

    # Split by heading tags
    parts = re.split(r'(<h[1-4][^>]*>.*?</h[1-4]>)', block, flags=re.DOTALL)

    for part in parts:
        heading_m = re.match(r'<h[1-4][^>]*>(.*?)</h[1-4]>', part, re.DOTALL)
        if heading_m:
            heading_text = strip_tags(heading_m.group(1))
            heading_text = re.sub(r'[►▶]', '', heading_text).strip()
            if len(heading_text) < 3:
                continue
            meta = detect_category(heading_text)
            if sections and sections[-1]["cat"] == meta["label"]:
                current_section = sections[-1]["items"]
            else:
                items = []
                sections.append({"cat": meta["label"], "badge": meta["badge"], "items": items})
                current_section = items
        elif current_section is not None:
            # Extract links from this block
            for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', part, re.DOTALL):
                url = unescape(m.group(1))
                name = strip_tags(m.group(2))
                if not name or not url:
                    continue
                # Skip reddit internal links
                if "reddit.com" in url and "wiki" not in url and "comments" not in url:
                    continue
                # Get surrounding text as description
                surrounding = part[max(0, m.start()-200):m.end()+200]
                surrounding_text = strip_tags(surrounding)
                desc_match = re.search(re.escape(name) + r'\s*[-–—]\s*([^\.]{10,120})', surrounding_text)
                desc = desc_match.group(1).strip() if desc_match else ""
                current_section.append({"name": name, "url": url, "desc": desc})

    result = [s for s in sections if s["items"]]
    if result:
        print(f"  HTML scrape: got {len(result)} sections")
        return json.dumps({"_html_parsed": True, "sections": result})
    return None

def parse_markdown(md):
    sections = []
    current_section = None

    for line in md.splitlines():
        heading_match = re.match(r'^#{2,4}\s+(.+)', line)
        if heading_match:
            heading_text = re.sub(r'[*_`►]', '', heading_match.group(1)).strip()
            if len(heading_text) < 3:
                continue
            meta = detect_category(heading_text)
            if sections and sections[-1]["cat"] == meta["label"]:
                current_section = sections[-1]["items"]
            else:
                items = []
                sections.append({"cat": meta["label"], "badge": meta["badge"], "items": items})
                current_section = items
            continue

        if current_section is None:
            continue

        m = re.match(r'^\s*[\*\-\+]\s+\[([^\]]+)\]\((https?://[^\)]+)\)\s*[-–—]?\s*(.*)', line)
        if m:
            name = m.group(1).strip()
            url = m.group(2).strip()
            desc = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', m.group(3))
            desc = re.sub(r'[*_`]', '', desc).strip()
            if name and url:
                current_section.append({"name": name, "url": url, "desc": desc})
            continue

        m = re.match(r'^\s*[\*\-\+]\s+(https?://\S+)\s*[-–—]?\s*(.*)', line)
        if m:
            url = m.group(1).strip()
            desc = re.sub(r'[*_`]', '', m.group(2)).strip()
            name = url.replace("https://", "").replace("http://", "").split("/")[0]
            if url:
                current_section.append({"name": name, "url": url, "desc": desc})

    return [s for s in sections if s["items"]]

def main():
    # Try strategies in order
    raw = fetch_from_gist()

    if raw is None:
        raw = fetch_from_reddit()

    if raw is None:
        raw = fetch_from_reddit_html()

    if raw is None:
        print("\nAll strategies failed. Keeping existing data.json.", file=sys.stderr)
        sys.exit(0)

    # Check if HTML parser already returned structured sections
    try:
        maybe_json = json.loads(raw)
        if maybe_json.get("_html_parsed"):
            sections = maybe_json["sections"]
        else:
            sections = parse_markdown(raw)
    except (json.JSONDecodeError, AttributeError):
        sections = parse_markdown(raw)

    total = sum(len(s["items"]) for s in sections)
    print(f"Parsed {len(sections)} sections, {total} items")

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "https://www.reddit.com/r/Piracy/wiki/megathread",
        "sections": sections
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Written to data.json ✓")

if __name__ == "__main__":
    main()
