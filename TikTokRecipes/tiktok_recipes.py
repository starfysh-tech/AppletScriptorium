#!/usr/bin/env python3
"""Extract and organize recipes from a TikTok collection.

Usage:
    python3 TikTokRecipes/tiktok_recipes.py 'https://www.tiktok.com/t/XXXX/'

Stage 1 (fetch) caches each video's metadata and captions via the yt-dlp CLI.
Stage 2 (extract) reads any recipe page linked in the description (schema.org
Recipe data), sends description + transcript + page to LM Studio, and writes
Markdown recipes, an index grouped by category, recipes.json, and a static site in site/.
Re-runs reuse both caches; pass --refresh to refetch or --reextract to redo LLM.
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FLAVORS = ["sweet", "savory"]
CATEGORIES = [
    "breakfast", "main", "side", "soup-salad", "snack",
    "dessert", "drink", "sauce-dip", "other",
]
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130 Safari/537.36"
)
LMSTUDIO_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234").rstrip("/")
LMSTUDIO_TIMEOUT = float(os.environ.get("LMSTUDIO_TIMEOUT", "300"))
PAGES_PROJECT = os.environ.get("PAGES_PROJECT", "tt-recipes")
SITE_URL = f"https://{PAGES_PROJECT}.pages.dev"

RECIPE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "recipes",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_recipe": {"type": "boolean"},
                "recipes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "category": {"type": "string", "enum": CATEGORIES},
                            "flavor": {"type": "string", "enum": FLAVORS},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "credit": {"type": ["string", "null"]},
                            "servings": {"type": ["string", "null"]},
                            "nutrition": {"type": ["string", "null"]},
                            "ingredients": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "item": {"type": "string"},
                                        "quantity": {"type": ["string", "null"]},
                                    },
                                    "required": ["item", "quantity"],
                                },
                            },
                            "steps": {"type": "array", "items": {"type": "string"}},
                            "missing": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": [
                            "title", "category", "flavor", "tags", "credit", "servings",
                            "nutrition", "ingredients", "steps", "missing",
                        ],
                    },
                },
            },
            "required": ["is_recipe", "recipes"],
        },
    },
}

PROMPT = """You extract recipes from a TikTok video's description and spoken transcript.

Rules:
- If the video is not about a dish or drink someone could make (vlog, science demo, product ad, restaurant visit), set is_recipe false and recipes [].
- If the video makes a dish but the text gives few details (no captions, short description), still return it: name the dish, list only ingredients the text names, keep steps to what the text says (can be empty), and put "full recipe is only shown in the video" in missing.
- Usually return one recipe: the dish the video is about. Its parts (sauce, frosting, topping, drizzle, a side made for it) go into that recipe's ingredients and steps.
- Return several recipes only when the video teaches separate dishes, each with its own ingredients (a compilation or "what I eat in a day"). Return each dish once.
- Never return something that is only mentioned, store-bought, or shown for comparison (a drink on the side, plain rice, a bought dip, "two boiled eggs").
- Variations of the same dish (a protein swap, a lighter or plain version) go in that recipe's steps, not in a separate recipe.
- Quantity priority: linked recipe page, then description, then transcript.
- Never invent a quantity. If no amount is stated, set quantity to null.
- Write steps as short imperative sentences in cooking order.
- credit: the original recipe author if the poster credits someone else (e.g. "@name"), else null.
- servings / nutrition: only if stated (e.g. "450 calories, 40g protein"), else null.
- category: one of {categories}.
- flavor: sweet if the dish is mainly sweet (desserts, sweet breakfasts, most drinks), else savory.
- tags: 0-5 short lowercase tags such as high-protein, air-fryer, meal-prep, vegetarian, gluten-free, one-pan, no-bake.
- missing: list what a cook would need but the video did not give (e.g. "bake time", "sauce quantities").

Poster: @{uploader}
Title: {title}

Description:
{description}

Transcript ({transcript_source}):
{transcript}

Linked recipe page:
{linked}
"""


def resolve_url(url: str) -> str:
    """Follow TikTok /t/ short links to the collection URL, without its query string.

    yt-dlp's short-link extractor drops the ID after a hyphen and times out,
    so resolve the first redirect ourselves.
    """
    if "/t/" not in url and "vm.tiktok.com" not in url and "vt.tiktok.com" not in url:
        return url.split("?")[0]

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    try:
        opener.open(request, timeout=30)
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
            return exc.headers["Location"].split("?")[0]
        raise SystemExit(f"Could not resolve {url}: HTTP {exc.code}")
    raise SystemExit(f"Could not resolve {url}: no redirect returned")


def yt_dlp(args: list[str], cookies: str | None) -> subprocess.CompletedProcess:
    cmd = ["yt-dlp", "--no-warnings", "--retries", "3", "--socket-timeout", "30"]
    if cookies:
        cmd += ["--cookies-from-browser", cookies]
    return subprocess.run(cmd + args, capture_output=True, text=True)


def list_videos(collection_url: str, cookies: str | None) -> dict:
    result = yt_dlp(["--flat-playlist", "-J", collection_url], cookies)
    if result.returncode != 0:
        raise SystemExit(f"Collection discovery failed:\n{result.stderr.strip()}")
    return json.loads(result.stdout)


def fetch_video(url: str, folder: Path, cookies: str | None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    result = yt_dlp([
        "--skip-download", "--write-info-json",
        "--write-subs", "--write-auto-subs", "--sub-langs", "all", "--sub-format", "vtt/srt/best",
        "-o", str(folder / "video.%(ext)s"), url,
    ], cookies)
    if not (folder / "video.info.json").exists():
        raise RuntimeError(result.stderr.strip() or "yt-dlp returned no metadata")


def log(message: str) -> None:
    print(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {message}", flush=True)


def git_version() -> str:
    result = subprocess.run(["git", "describe", "--always", "--dirty"], capture_output=True, text=True,
                            cwd=Path(__file__).parent)
    return result.stdout.strip() or "unknown"


def download(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            path.write_bytes(resp.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        log(f"  image download failed {url[:80]}: {exc}")


def fetch_thumbnail(info: dict, path: Path) -> None:
    # "cover" is the frame the creator picked; yt-dlp's default "thumbnail" is the first frame.
    # The URLs are signed and expire within days, so keep a local copy.
    covers = {t.get("id"): t.get("url") for t in info.get("thumbnails") or []}
    url = covers.get("cover") or info.get("thumbnail")
    if url:
        download(url, path)


def _recipe_image(recipe: dict) -> str | None:
    image = recipe.get("image")
    if isinstance(image, list):
        image = image[0] if image else None
    if isinstance(image, dict):
        image = image.get("url")
    return image if isinstance(image, str) and image.startswith("http") else None


def vtt_to_text(path: Path) -> str:
    lines, previous = [], None
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig", errors="replace")):
        parts = block.strip().splitlines()
        timing = next((i for i, line in enumerate(parts) if "-->" in line), None)
        if timing is None:
            continue
        cue = html.unescape(re.sub(r"<[^>]+>", "", " ".join(parts[timing + 1:]))).strip()
        if cue and cue != previous:
            lines.append(cue)
            previous = cue
    return "\n".join(lines)


def pick_transcript(folder: Path) -> tuple[str, str]:
    """Prefer English captions; fall back to any track."""
    tracks = sorted(folder.glob("video.*.vtt")) + sorted(folder.glob("video.*.srt"))
    tracks.sort(key=lambda p: not p.name.split(".")[1].startswith("en"))
    for track in tracks:
        text = vtt_to_text(track)
        if text:
            return text, f"captions {track.name.split('.')[1]}"
    return "", "none"


def _find_recipe(node):
    """Depth-first search of JSON-LD for a schema.org Recipe object."""
    if isinstance(node, list):
        return next((r for r in map(_find_recipe, node) if r), None)
    if not isinstance(node, dict):
        return None
    kind = node.get("@type")
    if kind == "Recipe" or (isinstance(kind, list) and "Recipe" in kind):
        return node
    return _find_recipe(list(node.values()))


def _instruction_lines(node) -> list[str]:
    if isinstance(node, str):
        return [html.unescape(re.sub(r"<[^>]+>", "", node)).strip()]
    if isinstance(node, list):
        return [line for item in node for line in _instruction_lines(item)]
    if isinstance(node, dict):
        return _instruction_lines(node.get("itemListElement") or node.get("text") or "")
    return []


def fetch_linked_recipe(url: str) -> dict:
    """Read the schema.org Recipe block from a linked recipe page, if it has one."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(request, timeout=30) as response:
            page = response.read().decode("utf-8", "replace")
    except Exception as exc:
        return {"url": url, "error": str(exc)}
    for block in re.findall(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", page, re.S):
        try:
            recipe = _find_recipe(json.loads(block))
        except json.JSONDecodeError:
            continue
        if recipe:
            parts = [f"Name: {recipe.get('name', '')}"]
            servings = recipe.get("recipeYield")
            if servings:
                parts.append(f"Yield: {servings[-1] if isinstance(servings, list) else servings}")
            calories = (recipe.get("nutrition") or {}).get("calories")
            if calories:
                parts.append(f"Calories: {calories}")
            parts.append("Ingredients:\n" + "\n".join(f"- {i}" for i in recipe.get("recipeIngredient") or []))
            steps = [s for s in _instruction_lines(recipe.get("recipeInstructions")) if s]
            parts.append("Instructions:\n" + "\n".join(f"{n}. {s}" for n, s in enumerate(steps, 1)))
            return {"url": url, "text": html.unescape("\n".join(parts)), "image": _recipe_image(recipe)}
    return {"url": url, "error": "no schema.org Recipe on page"}


def lmstudio_model(explicit: str | None) -> str:
    if explicit:
        return explicit
    with urllib.request.urlopen(f"{LMSTUDIO_BASE_URL}/v1/models", timeout=10) as response:
        models = [m["id"] for m in json.load(response)["data"]]
    llms = [m for m in models if "embed" not in m]
    if not llms:
        raise SystemExit(f"No LLM loaded in LM Studio at {LMSTUDIO_BASE_URL}")
    return llms[0]


def extract_recipes(info: dict, transcript: str, source: str, linked: list[dict], model: str) -> dict:
    prompt = PROMPT.format(
        linked="\n\n".join(f"({l['url']})\n{l['text']}" for l in linked if l.get("text")) or "(none)",
        categories=", ".join(CATEGORIES),
        uploader=info.get("uploader") or "unknown",
        title=info.get("title") or "",
        description=info.get("description") or "(none)",
        transcript=transcript or "(none)",
        transcript_source=source,
    )
    return lmstudio_json(prompt, RECIPE_SCHEMA, model, 8000)


def classify_flavors(recipes: list[dict], model: str) -> list[str]:
    """Label recipes extracted before the flavor field existed."""
    listing = "\n".join(f"{n}. {r['title']}: {', '.join(i['item'] for i in r['ingredients'])}"
                         for n, r in enumerate(recipes, 1))
    prompt = (f"For each recipe, answer sweet if the dish is mainly sweet (desserts, sweet breakfasts, "
              f"most drinks), else savory. Return one answer per recipe, in order.\n\n{listing}")
    schema = {"type": "json_schema", "json_schema": {"name": "flavors", "strict": True, "schema": {
        "type": "object", "required": ["flavors"],
        "properties": {"flavors": {"type": "array", "items": {"type": "string", "enum": FLAVORS}}}}}}
    flavors = lmstudio_json(prompt, schema, model, 200)["flavors"]
    if len(flavors) != len(recipes):
        raise ValueError(f"expected {len(recipes)} flavors, got {len(flavors)}")
    return flavors


def lmstudio_json(prompt: str, schema: dict, model: str, max_tokens: int) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": schema,
        # Thinking multiplies latency for little gain on structured extraction.
        "reasoning_effort": os.environ.get("LMSTUDIO_REASONING_EFFORT", "none"),
    }
    request = urllib.request.Request(
        f"{LMSTUDIO_BASE_URL}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=LMSTUDIO_TIMEOUT) as response:
        content = json.load(response)["choices"][0]["message"]["content"]
    return json.loads(content)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "recipe"


def render_recipe(recipe: dict, video: dict) -> str:
    lines = [f"# {recipe['title']}", ""]
    meta = [f"**Category:** {recipe['category']}"]
    if recipe["tags"]:
        meta.append("**Tags:** " + ", ".join(recipe["tags"]))
    if recipe["servings"]:
        meta.append(f"**Servings:** {recipe['servings']}")
    if recipe["nutrition"]:
        meta.append(f"**Nutrition:** {recipe['nutrition']}")
    source = f"**Source:** [@{video['uploader']}]({video['url']})"
    if recipe["credit"]:
        source += f" (recipe by {recipe['credit']})"
    meta.append(source)
    meta.append(f"**Transcript:** {video['transcript_source']}")
    for url in video.get("linked", []):
        meta.append(f"**Recipe page:** {url}")
    lines += [line + "  " for line in meta] + ["", "## Ingredients", ""]
    for ing in recipe["ingredients"]:
        lines.append(f"- {ing['quantity']} {ing['item']}" if ing["quantity"] else f"- {ing['item']}")
    lines += ["", "## Steps", ""]
    lines += [f"{i}. {step}" for i, step in enumerate(recipe["steps"], 1)]
    if recipe["missing"]:
        lines += ["", "## Not stated in the video", ""]
        lines += [f"- {gap}" for gap in recipe["missing"]]
    return "\n".join(lines) + "\n"


def render_index(title: str, recipes: list[dict], skipped: list[dict], failed: list[dict]) -> str:
    lines = [f"# {title}", "", f"{len(recipes)} recipes. "
             f"{len(skipped)} videos were not recipes. {len(failed)} failed.", ""]
    for category in CATEGORIES:
        group = sorted((r for r in recipes if r["category"] == category), key=lambda r: r["title"].lower())
        if not group:
            continue
        lines += [f"## {category} ({len(group)})", ""]
        for r in group:
            tags = f" — {', '.join(r['tags'])}" if r["tags"] else ""
            lines.append(f"- [{r['title']}](recipes/{r['file']}){tags}")
        lines.append("")
    if skipped:
        lines += ["## Not recipes", ""] + [f"- [{v['title'][:80]}]({v['url']})" for v in skipped] + [""]
    if failed:
        lines += ["## Failed", ""] + [f"- {v['url']}: {v['error'][:200]}" for v in failed] + [""]
    return "\n".join(lines)


def write_site(root: Path, recipes: list[dict], title: str = "TikTok Recipes") -> Path:
    site = root / "site"
    (site / "img").mkdir(parents=True, exist_ok=True)
    for recipe in recipes:
        folder = root / "cache" / recipe["video"]["id"]
        # A recipe page photo shows the finished dish; the TikTok cover often shows the creator.
        thumb = next((p for p in (folder / "food.jpg", folder / "thumb.jpg") if p.exists()), folder / "thumb.jpg")
        recipe["video"]["thumb"] = thumb.exists()
        out = site / "img" / f"{recipe['video']['id']}.jpg"
        if thumb.exists() and (not out.exists() or out.stat().st_mtime < thumb.stat().st_mtime):
            # Covers come at up to 2000px; 720px JPEG keeps the site fast. sips ships with macOS.
            subprocess.run(["sips", "-Z", "720", "-s", "format", "jpeg", str(thumb), "--out", str(out)],
                           capture_output=True)
    template = (Path(__file__).parent / "site_template.html").read_text()
    # "</" would end the <script> tag that holds the JSON.
    data = json.dumps(recipes, ensure_ascii=False).replace("</", "<\\/")
    write_ai_files(site, recipes, title)
    (site / "index.html").write_text(template.replace("__TITLE__", html.escape(title)).replace("__DATA__", data))
    return site / "index.html"


def recipe_id(recipe: dict) -> str:
    return recipe["file"].removesuffix(".md")


def render_recipe_page(r: dict, title: str) -> str:
    """Static recipe page so crawlers and AI tools that do not run JavaScript can read it."""
    rid, video = recipe_id(r), r["video"]
    ingredients = [f"{i['quantity']} {i['item']}" if i["quantity"] else i["item"] for i in r["ingredients"]]
    ld = {
        "@context": "https://schema.org", "@type": "Recipe", "name": r["title"],
        "url": f"{SITE_URL}/r/{rid}", "recipeCategory": r["category"], "keywords": ", ".join(r["tags"]),
        "author": {"@type": "Person", "name": r["credit"] or "@" + video["uploader"]},
        "isBasedOn": video["url"], "recipeIngredient": ingredients,
        "recipeInstructions": [{"@type": "HowToStep", "text": step} for step in r["steps"]],
    }
    if video.get("thumb"):
        ld["image"] = f"{SITE_URL}/img/{video['id']}.jpg"
    if r["servings"]:
        ld["recipeYield"] = r["servings"]
    e = html.escape
    links = [f'<a href="{e(video["url"])}">Video by @{e(video["uploader"])} on TikTok</a>']
    links += [f'<a href="{e(u)}">{e(u)}</a>' for u in video.get("links", [])]
    meta = " · ".join(x for x in (r["category"], r.get("flavor"), r["servings"] and f"serves {r['servings']}",
                                   r["nutrition"]) if x)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(r['title'])} · {e(title)}</title>
<meta name="description" content="{e(r['title'])}: {e(', '.join(ingredients)[:150])}">
<link rel="canonical" href="{SITE_URL}/r/{rid}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:720px;margin:0 auto;padding:16px;color:#01404e}}</style>
</head><body>
<p><a href="/#{rid}">Open in {e(title)}</a></p>
<h1>{e(r['title'])}</h1>
<p>{e(meta)}{' · ' + e(', '.join(r['tags'])) if r['tags'] else ''}</p>
<p>{' · '.join(links)}{' · recipe by ' + e(r['credit']) if r['credit'] else ''}</p>
<h2>Ingredients</h2>
<ul>{''.join(f'<li>{e(i)}</li>' for i in ingredients) or '<li>Not listed in the video text.</li>'}</ul>
<h2>Instructions</h2>
<ol>{''.join(f'<li>{e(s)}</li>' for s in r['steps']) or '<li>Not written out in the video text.</li>'}</ol>
{'<h2>Not stated in the video</h2><ul>' + ''.join(f'<li>{e(m)}</li>' for m in r['missing']) + '</ul>' if r['missing'] else ''}
</body></html>
"""


def write_ai_files(site: Path, recipes: list[dict], title: str) -> None:
    pages = site / "r"
    if pages.exists():
        shutil.rmtree(pages)
    pages.mkdir()
    for r in recipes:
        (pages / f"{recipe_id(r)}.html").write_text(render_recipe_page(r, title))
        (pages / f"{recipe_id(r)}.md").write_text(render_recipe(r, r["video"]))
    (site / "recipes.json").write_text(json.dumps(recipes, ensure_ascii=False))
    ordered = sorted(recipes, key=lambda r: (CATEGORIES.index(r["category"]), r["title"].lower()))
    index = [f"# {title}", "", f"> {len(recipes)} recipes extracted from saved TikTok videos: ingredients, "
             "quantities, steps, and a link to each original video. A missing quantity was not stated by the creator.",
             "", "## Search", "",
             f"- [Search API]({SITE_URL}/api/search?q=chicken+rice&flavor=savory): GET /api/search with "
             "q (words; prefix - to exclude), cat, flavor (sweet|savory), tags (comma list, all required), "
             "max_ingredients, limit. Returns JSON; add format=md for Markdown.",
             f"- [All recipes as JSON]({SITE_URL}/recipes.json)",
             f"- [All recipes as Markdown]({SITE_URL}/llms-full.txt)",
             "- Each recipe: /r/<id>.md (Markdown) or /r/<id> (HTML with schema.org Recipe data).", ""]
    for category in CATEGORIES:
        group = [r for r in ordered if r["category"] == category]
        if group:
            index += [f"## {category}", ""]
            index += [f"- [{r['title']}]({SITE_URL}/r/{recipe_id(r)}.md): {r.get('flavor', '')}"
                      + (f"; {', '.join(r['tags'])}" if r["tags"] else "") for r in group]
            index.append("")
    (site / "llms.txt").write_text("\n".join(index))
    (site / "llms-full.txt").write_text("\n\n---\n\n".join(render_recipe(r, r["video"]) for r in ordered))
    urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/r/{recipe_id(r)}" for r in recipes]
    (site / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{html.escape(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    (site / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")


def site_digest(site: Path) -> str:
    h = hashlib.sha256()
    files = sorted(site.rglob("*")) + sorted((Path(__file__).parent / "functions").rglob("*"))
    for f in files:
        if f.is_file():
            h.update(str(f).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def deploy_site(site: Path) -> bool:
    if not shutil.which("wrangler"):
        log("deploy skipped: wrangler not installed")
        return False
    result = subprocess.run(["wrangler", "pages", "deploy", str(site.resolve()), "--project-name", PAGES_PROJECT,
                             "--branch", "main", "--commit-dirty=true"], capture_output=True, text=True,
                            cwd=Path(__file__).parent)
    if result.returncode:
        log(f"DEPLOY FAILED:\n{result.stderr.strip() or result.stdout.strip()}")
        return False
    log(f"deployed {SITE_URL}/")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="TikTok collection link (short /t/ links are resolved)")
    parser.add_argument("--out", type=Path, help="Output folder (default: TikTokRecipes/runs/<collection>)")
    parser.add_argument("--limit", type=int, help="Only process the first N videos")
    parser.add_argument("--model", help="LM Studio model ID (default: first loaded LLM)")
    parser.add_argument("--cookies-from-browser", metavar="BROWSER", help="e.g. chrome, if TikTok needs your login")
    parser.add_argument("--refresh", action="store_true", help="Refetch metadata and captions")
    parser.add_argument("--reextract", action="store_true", help="Rerun the LLM on cached videos")
    parser.add_argument("--fetch-only", action="store_true", help="Stop after caching metadata and captions")
    parser.add_argument("--no-deploy", action="store_true", help="Build site/ but do not publish it")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log every video, not only ones with work")
    args = parser.parse_args()

    started = time.monotonic()
    collection_url = resolve_url(args.url)
    log(f"start {collection_url} (code {git_version()})")
    collection = list_videos(collection_url, args.cookies_from_browser)
    entries = [e for e in collection.get("entries") or [] if e and e.get("url")]
    if args.limit:
        entries = entries[:args.limit]

    root = args.out or Path(__file__).resolve().parent / "runs" / slugify(collection.get("title") or collection.get("id"))
    cache = root / "cache"
    (root / "recipes").mkdir(parents=True, exist_ok=True)
    # Looked up on first use, so a run with nothing new works while LM Studio is closed.
    model_cache = {}

    def model() -> str:
        if "id" not in model_cache:
            try:
                model_cache["id"] = lmstudio_model(args.model)
            except Exception as exc:
                raise RuntimeError(f"LM Studio not reachable at {LMSTUDIO_BASE_URL}: {exc}") from exc
        return model_cache["id"]

    # TikTok's collection listing varies between calls (59 to 448 entries seen), so keep every video seen before.
    if not args.limit:
        listed = {e.get("id") for e in entries}
        for info_path in sorted(cache.glob("*/video.info.json")):
            if info_path.parent.name not in listed:
                entries.append({"id": info_path.parent.name,
                                "url": json.loads(info_path.read_text())["webpage_url"]})

    # The collection lists newest-saved first. Listings are partial, so keep the order across runs:
    # ids never seen before go on top, in listing order.
    order_path = root / "order.json"
    order = json.loads(order_path.read_text()) if order_path.exists() else []
    seen = set(order)
    new_ids = list(dict.fromkeys(e["id"] for e in entries if e.get("id") and e["id"] not in seen))
    order = new_ids + order
    if not args.limit:
        order_path.write_text(json.dumps(order))
    added = {video_id: n for n, video_id in enumerate(order)}
    log(f"listed {len(listed) if not args.limit else len(entries)} videos from TikTok, "
        f"{len(entries)} total with cache, {len(new_ids)} new")

    recipes, skipped, failed = [], [], []
    for n, entry in enumerate(entries, 1):
        url = entry["url"]
        video_id = entry.get("id") or url.rstrip("/").split("/")[-1]
        folder = cache / video_id
        if args.verbose:
            log(f"[{n}/{len(entries)}] {url}")
        try:
            if args.refresh or not (folder / "video.info.json").exists():
                log(f"fetch {url}")
                fetch_video(url, folder, args.cookies_from_browser)
            info = json.loads((folder / "video.info.json").read_text())
            transcript, source = pick_transcript(folder)
            if args.refresh or not (folder / "thumb.jpg").exists():
                fetch_thumbnail(info, folder / "thumb.jpg")
            video = {
                "id": video_id, "url": url, "uploader": info.get("uploader") or "unknown",
                "title": info.get("title") or info.get("description") or video_id,
                "transcript_source": source, "added": added.get(video_id, len(added)),
            }
            if args.fetch_only:
                continue

            linked_path = folder / "linked.json"
            new_links = args.refresh or not linked_path.exists()
            if new_links:
                urls = re.findall(r"https?://[^\s<>\"]+", info.get("description") or "")
                linked_path.write_text(json.dumps([fetch_linked_recipe(u) for u in urls], indent=2))
            linked = json.loads(linked_path.read_text())
            video["linked"] = [l["url"] for l in linked if l.get("text")]
            video["links"] = [l["url"] for l in linked]
            image = next((l["image"] for l in linked if l.get("image")), None)
            if image and (new_links or not (folder / "food.jpg").exists()):
                download(image, folder / "food.jpg")

            extracted_path = folder / "extracted.json"
            # Videos extracted before linked pages existed get redone once a page is found.
            failed_path = folder / "extract_failed.txt"
            # A video the LLM cannot handle would otherwise cost a full timeout every hour.
            if failed_path.exists() and not args.reextract:
                raise RuntimeError(f"extraction failed before, skipped (--reextract retries): {failed_path.read_text().strip()}")
            if args.reextract or not extracted_path.exists() or (new_links and video["linked"]):
                t0 = time.monotonic()
                try:
                    extracted = extract_recipes(info, transcript, source, linked, model())
                except Exception as exc:
                    failed_path.write_text(str(exc))
                    raise
                failed_path.unlink(missing_ok=True)
                extracted_path.write_text(json.dumps(extracted, indent=2, ensure_ascii=False))
                titles = ", ".join(r["title"] for r in extracted["recipes"]) or "not a recipe"
                log(f"extract {url} ({time.monotonic() - t0:.0f}s, captions: {source}): {titles}")
            extracted = json.loads(extracted_path.read_text())
            if any("flavor" not in r for r in extracted["recipes"]):
                for recipe, flavor in zip(extracted["recipes"], classify_flavors(extracted["recipes"], model())):
                    recipe["flavor"] = flavor
                extracted_path.write_text(json.dumps(extracted, indent=2, ensure_ascii=False))

            if not extracted["is_recipe"] or not extracted["recipes"]:
                skipped.append(video)
                continue
            # The LLM sometimes returns the same dish twice for one video.
            unique, seen = [], set()
            for recipe in extracted["recipes"]:
                keys = {slugify(recipe["title"]), frozenset(i["item"].lower() for i in recipe["ingredients"])}
                if not keys & seen:
                    unique.append(recipe)
                seen |= keys
            # In a multi-dish video, 1-2 ingredient entries are mentions ("two boiled eggs"), not recipes.
            if len(unique) > 1:
                unique = [r for r in unique if len(r["ingredients"]) >= 3] or unique[:1]
            for i, recipe in enumerate(unique):
                # The id is the shared link, so it depends on the title only, not on list position.
                base = f"{slugify(recipe['title'])}-{video_id[-6:]}"
                taken = sum(1 for u in unique[:i] if slugify(u["title"]) == slugify(recipe["title"]))
                recipe = {**recipe, "file": f"{base}{f'-{taken + 1}' if taken else ''}.md",
                          "video": video}
                (root / "recipes" / recipe["file"]).write_text(render_recipe(recipe, video))
                recipes.append(recipe)
        except Exception as exc:
            failed.append({"url": url, "error": str(exc)})
            log(f"FAILED {url}: {exc}")

    if args.fetch_only:
        no_captions = sum(1 for e in entries if pick_transcript(cache / (e.get("id") or ""))[1] == "none")
        log(f"fetched {len(entries) - len(failed)} videos, {no_captions} without captions, {len(failed)} failed")
        return

    keep = {r["file"] for r in recipes}
    for stale in (root / "recipes").glob("*.md"):
        if stale.name not in keep and not args.limit:
            stale.unlink()
    # TikTok's listing order varies between calls; a stable order keeps unchanged runs byte-identical.
    recipes.sort(key=lambda r: (r["video"]["added"], r["file"]))
    (root / "recipes.json").write_text(json.dumps(recipes, indent=2, ensure_ascii=False))
    (root / "index.md").write_text(render_index(collection.get("title") or "Recipes", recipes, skipped, failed))
    log(f"built {len(recipes)} recipes, {len(skipped)} not recipes, {len(failed)} failed "
        f"in {time.monotonic() - started:.0f}s")
    site = write_site(root, recipes)
    # A --limit run holds a partial collection and would replace the full live site.
    if args.no_deploy or args.limit:
        log("deploy skipped (--limit or --no-deploy)")
        return
    # Most hourly runs find nothing new; skip the upload when the built site is byte-identical.
    digest = site_digest(site.parent)
    stamp = root / "deployed.sha256"
    if stamp.exists() and stamp.read_text() == digest:
        log("site unchanged, deploy skipped")
    elif deploy_site(site.parent):
        stamp.write_text(digest)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        if isinstance(exc.code, str):
            log(f"ERROR {exc.code}")
            sys.exit(1)
        raise
    except Exception:
        log("ERROR run aborted:\n" + traceback.format_exc().rstrip())
        sys.exit(1)
