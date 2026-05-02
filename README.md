# r/Piracy Megathread Explorer

A searchable, auto-updating web app for the [r/Piracy wiki megathread](https://www.reddit.com/r/Piracy/wiki/megathread/).

**Live site:** `https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/`

## Features
- Search across all resources by name, description, or URL
- Filter by category (Privacy, Torrents, Ebooks, Games, Movies, Music, etc.)
- Auto-updates weekly via GitHub Actions — no manual work needed

## Local development

```bash
# Serve locally (required — file:// won't load data.json due to CORS)
python3 -m http.server 8080
# then open http://localhost:8080
```

To manually refresh data:
```bash
python3 parse_megathread.py
```
