# r/Piracy Megathread Explorer

A searchable, auto-updating web app for the [r/Piracy wiki megathread](https://www.reddit.com/r/Piracy/wiki/megathread/).

**Live site:** `https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/`

## Features
- Search across all resources by name, description, or URL
- Filter by category (Privacy, Torrents, Ebooks, Games, Movies, Music, etc.)
- Auto-updates weekly via GitHub Actions — no manual work needed

## Files

| File | Purpose |
|------|---------|
| `index.html` | The web app — reads from `data.json` on load |
| `data.json` | Parsed megathread data — auto-updated by the Action |
| `parse_megathread.py` | Fetches Reddit wiki JSON and writes `data.json` |
| `.github/workflows/update.yml` | GitHub Action — runs every Monday at 6am UTC |

## Setup

### 1. Fork or clone this repo to your GitHub account

### 2. Enable GitHub Pages
- Go to **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main`, folder: `/ (root)`
- Click **Save**

Your site will be live at `https://USERNAME.github.io/REPO-NAME/` within ~1 minute.

### 3. The Action runs automatically
Every Monday at 6am UTC, the Action will:
1. Fetch `https://www.reddit.com/r/Piracy/wiki/megathread.json`
2. Parse all links and descriptions
3. Write updated `data.json`
4. Commit and push if anything changed

### 4. Trigger a manual update anytime
Go to **Actions → Update Megathread Data → Run workflow**

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
