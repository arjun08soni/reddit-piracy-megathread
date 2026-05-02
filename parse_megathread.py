#!/usr/bin/env python3
"""
Fetches r/Piracy megathread wiki and parses it into data.json
for the GitHub Pages site.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

WIKI_URLS = [
    "https://www.reddit.com/r/Piracy/wiki/megathread.json",
    "https://old.reddit.com/r/Piracy/wiki/megathread.json",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}

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

def fetch_wiki():
    last_error = None
    for url in WIKI_URLS:
        for attempt in range(3):
            try:
                print(f"Trying {url} (attempt {attempt + 1})...")
                if attempt > 0:
                    time.sleep(3 * attempt)
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                    md = raw["data"]["content_md"]
                    print(f"Success! Got {len(md)} chars.")
                    return md
            except urllib.error.HTTPError as e:
                print(f"  HTTP {e.code}: {e.reason}", file=sys.stderr)
                last_error = e
                if e.code == 429:
                    print("  Rate limited, waiting 10s...", file=sys.stderr)
                    time.sleep(10)
            except Exception as e:
                print(f"  Error: {e}", file=sys.stderr)
                last_error = e

    print(f"\nAll fetch attempts failed. Last error: {last_error}", file=sys.stderr)
    print("Keeping existing data.json unchanged.", file=sys.stderr)
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
    print("Fetching megathread wiki...")
    md = fetch_wiki()

    if md is None:
        print("No new data fetched. Exiting without updating data.json.")
        sys.exit(0)

    sections = parse_markdown(md)
    total = sum(len(s["items"]) for s in sections)
    print(f"Parsed {len(sections)} sections, {total} items")

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "https://www.reddit.com/r/Piracy/wiki/megathread",
        "sections": sections
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Written to data.json")

if __name__ == "__main__":
    main()
