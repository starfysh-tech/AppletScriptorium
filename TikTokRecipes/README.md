# TikTokRecipes

Turns a TikTok collection into a recipe book, published at https://tt-recipes.pages.dev/ and updated hourly. Reads each video's description, captions, and any recipe page linked in the description. Does not download or process the video itself.

## Requirements

- `yt-dlp` CLI (`brew install yt-dlp`)
- `wrangler` CLI logged in to Cloudflare, for publishing
- LM Studio running at `http://localhost:1234` with an LLM loaded

No Python packages beyond stdlib.

## Run

```bash
python3 TikTokRecipes/tiktok_recipes.py 'https://www.tiktok.com/@user/collection/Name-1234567890'
```

Short `/t/` links work too. Options:

- `--out DIR` — output folder (default `TikTokRecipes/runs/<collection>`)
- `--limit N` — only the first N videos
- `--model ID` — LM Studio model (default: first loaded LLM)
- `--cookies-from-browser chrome` — if TikTok needs your login
- `--refresh` — refetch metadata and captions
- `--reextract` — rerun the LLM on cached videos, including ones that failed before
- `--fetch-only` — cache metadata and captions, skip the LLM
- `--no-deploy` — build `site/` but do not publish it

Env: `PAGES_PROJECT` (default `tt-recipes`), `LMSTUDIO_BASE_URL`, `LMSTUDIO_TIMEOUT` (default 300), `LMSTUDIO_REASONING_EFFORT` (default `none`).

## Output

```
runs/<collection>/
├── site/            # website: index.html, img/, r/<id>.html|.md, recipes.json, llms.txt, sitemap.xml
├── index.md         # recipes grouped by meal type, with tags
├── recipes.json     # all recipes as data
├── recipes/*.md     # one file per recipe
├── order.json       # video ids in the order they were saved, newest first
├── deployed.sha256  # fingerprint of the last uploaded site; unchanged sites are not uploaded
└── cache/<id>/      # video.info.json, captions, thumb.jpg, food.jpg, linked.json, extracted.json,
                     # extract_failed.txt (LLM error; skipped until --reextract)
```

`site/` is a static website. Open `site/index.html` or host the folder. It has search, meal type filters, a sweet / savory toggle, a multi-select tag filter (recipes must have every selected tag), sorting by newest added, oldest added, or A–Z, a random pick, and an ingredient checklist. Filters and sort are kept in the URL (`?q=&cat=&flavor=&tags=a,b&sort=oldest`), so a filtered view can be shared. Each recipe has its own page (`#<recipe>`) with the TikTok video embedded in a collapsed section (when a browser extension blocks TikTok's player, it shows a link to the video instead), a button that copies the recipe as Markdown, and links to the video and to any site linked in the description. Each card uses the photo from the linked recipe page when there is one, else the cover the creator picked on TikTok. Both are saved to the cache because TikTok's image links expire within days. When one video teaches several dishes, each of its recipe pages links to the others. A recipe's id is its title plus the last 6 digits of the video id, so links stay stable when the LLM re-runs. Edit `site_template.html` to change the design.

Meal types: breakfast, main, side, soup-salad, snack, dessert, drink, sauce-dip, other. Each recipe also gets 0–5 free tags.

`order.json` keeps the order videos were saved to the collection, newest first. TikTok lists the collection newest-saved first, and each run puts videos it has not seen before on top. Re-runs reuse the cache, so an interrupted run picks up where it stopped. TikTok returns a different number of collection entries from call to call, so every full run also includes all videos already in the cache. A video removed from the collection stays on the site until you delete its `cache/<id>/` folder. `runs/` is gitignored.

## Hosting

Each full run publishes `site/` to Cloudflare Pages at https://tt-recipes.pages.dev/ with `wrangler pages deploy`. The site is public. Runs with `--limit` or `--no-deploy` do not publish, so a partial run never replaces the live site. Needs `wrangler` logged in to the Cloudflare account that owns the project.

### Hourly updates

```bash
TikTokRecipes/install_hourly.sh 'https://www.tiktok.com/@user/collection/Name-123'
```

This installs a launchd agent (`com.starfysh.tiktokrecipes`) that runs now and every hour. Each run first does `git pull --ff-only origin main`, so changes merged to main go live within an hour. The pull fails without changing anything when the checkout has conflicting local edits or is not on main; the run then uses the local code. A run with no new videos and no code changes skips the upload. New videos are extracted and published. Cached videos cost no LLM calls. The Mac must be awake and LM Studio running. Output goes to `TikTokRecipes/runs/hourly.log`. Remove it with:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.starfysh.tiktokrecipes.plist
```

### Troubleshooting

```bash
tail -30 TikTokRecipes/runs/hourly.log
launchctl print gui/$(id -u)/com.starfysh.tiktokrecipes | grep -E 'state|last exit'
```

Each log line starts with a timestamp. A run with nothing new writes about 4 lines:

```
2026-10-11 20:02:27 start https://www.tiktok.com/@user/collection/... (code v4.2.0-37-g18eccd2)
2026-10-11 20:02:39 listed 448 videos from TikTok, 448 total with cache, 0 new
2026-10-11 20:02:40 built 415 recipes, 35 not recipes, 1 failed in 12s
2026-10-11 20:02:40 site unchanged, deploy skipped
```

- `code` is the git commit the run used. `-dirty` means local edits were included.
- `fetch` and `extract` lines appear only for new videos. `extract` shows the time, caption source, and recipe titles.
- `FAILED <url>: <reason>` is one video. Videos whose extraction failed before repeat this line each run until you rerun with `--reextract`.
- `ERROR` means the whole run stopped, for example when TikTok cannot be reached. `LM Studio not reachable` appears only when there are new videos to extract.
- `git pull failed, running local code` means main could not fast-forward, usually because of local edits.
- `DEPLOY FAILED` is followed by wrangler's output. A common cause is an expired login; run `wrangler login`.
- `-v` logs every video, for a manual run.

## AI access

Any AI or script can read the site without running its JavaScript:

- `/llms.txt`: index of every recipe with links, plus how to search
- `/api/search?q=chicken+-dairy&flavor=savory&tags=high-protein&format=md`: search (JSON by default). Served by `functions/api/search.js`, a Cloudflare Pages Function deployed with the site.
- `/r/<id>.md` and `/r/<id>`: one recipe as Markdown, or as HTML with schema.org Recipe data
- `/llms-full.txt`, `/recipes.json`: every recipe in one file
- `/sitemap.xml`, `/robots.txt`: allow all crawlers

## Local search

```bash
python3 TikTokRecipes/search_recipes.py chicken rice --flavor savory
python3 TikTokRecipes/search_recipes.py --tag high-protein --tag air-fryer --category snack
python3 TikTokRecipes/search_recipes.py cottage -dessert --max-ingredients 6
python3 TikTokRecipes/search_recipes.py --show <id>
```

Words match title, ingredients, tags, category, and creator. `-word` excludes. It reads the newest local `runs/*/recipes.json`, or the live site's `/recipes.json` when there is no local run. The site also serves `/llms.txt`, which describes the data for AI tools.

## What counts as a recipe

- A video about something other than making a dish or drink (a vlog, a science demo, a product ad) is listed under "Not recipes" in `index.md`.
- Usually one video gives one recipe. Its parts (sauce, frosting, topping, a side made for it) and its variations are folded into that recipe.
- A video gives several recipes only when it teaches separate dishes with their own ingredients, such as a "what I eat in a day". In those videos, entries with fewer than 3 ingredients are dropped as mentions.
- A cooking video with little text (no captions, short description) still becomes a recipe. It keeps the dish name and any ingredients the text names, and lists "full recipe is only shown in the video" as missing.

## How quantities are chosen

The LLM prefers the linked recipe page, then the description, then the captions. A quantity that no source states is left blank. Each recipe lists what is missing under "Not stated in the video".

## Limits

- "Link in bio" pages are not in TikTok's data, so they are not read.
- Videos without captions (often music-only) use the description alone.
- Some recipe sites block scripts (HTTP 403). Those pages are skipped.
- Comments are not read. yt-dlp returns none for TikTok.
