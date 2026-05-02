#!/usr/bin/env python3
"""
Fetches r/Piracy megathread wiki and parses it into data.json
for the GitHub Pages site.
"""

import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

WIKI_URL = "https://www.reddit.com/r/Piracy/wiki/megathread.json"
HEADERS = {
    "User-Agent": "piracy-megathread-updater/1.0 (GitHub Actions bot)"
}

# Map section headings to category metadata
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
    req = urllib.request.Request(WIKI_URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            return raw["data"]["content_md"]
    except urllib.error.HTTPError as e:
        print(f"HTTP error fetching wiki: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching wiki: {e}", file=sys.stderr)
        sys.exit(1)

def parse_markdown(md):
    sections = []
    current_section = None
    current_label = None
    current_badge = None

    lines = md.splitlines()

    for line in lines:
        # Detect section headings (## or ####)
        heading_match = re.match(r'^#{2,4}\s+(.+)', line)
        if heading_match:
            heading_text = re.sub(r'[*_`►]', '', heading_match.group(1)).strip()
            # Skip table of contents / intro lines
            if len(heading_text) < 3:
                continue
            meta = detect_category(heading_text)
            # Merge into existing section of same label if contiguous
            if sections and sections[-1]["cat"] == meta["label"]:
                current_section = sections[-1]["items"]
            else:
                items = []
                sections.append({
                    "cat": meta["label"],
                    "badge": meta["badge"],
                    "items": items
                })
                current_section = items
            current_label = meta["label"]
            current_badge = meta["badge"]
            continue

        if current_section is None:
            continue

        # Match markdown list items with links: * [Name](url) - description
        link_match = re.match(
            r'^\s*[\*\-\+]\s+\[([^\]]+)\]\((https?://[^\)]+)\)\s*[-–—]?\s*(.*)',
            line
        )
        if link_match:
            name = link_match.group(1).strip()
            url = link_match.group(2).strip()
            desc = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', link_match.group(3)).strip()
            desc = re.sub(r'[*_`]', '', desc).strip()
            if name and url:
                current_section.append({
                    "name": name,
                    "url": url,
                    "desc": desc or ""
                })
            continue

        # Match plain list items with inline URLs: * https://example.com - desc
        plain_url_match = re.match(
            r'^\s*[\*\-\+]\s+(https?://\S+)\s*[-–—]?\s*(.*)',
            line
        )
        if plain_url_match:
            url = plain_url_match.group(1).strip()
            desc = plain_url_match.group(2).strip()
            name = url.replace("https://", "").replace("http://", "").split("/")[0]
            if url:
                current_section.append({
                    "name": name,
                    "url": url,
                    "desc": re.sub(r'[*_`]', '', desc).strip()
                })

    # Remove empty sections
    sections = [s for s in sections if s["items"]]

    return sections

def main():
    print("Fetching megathread wiki...")
    md = fetch_wiki()
    print(f"Fetched {len(md)} chars of markdown")

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
