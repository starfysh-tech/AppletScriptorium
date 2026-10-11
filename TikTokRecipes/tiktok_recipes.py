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
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

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
                            "title", "category", "tags", "credit", "servings",
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
- If the video does not teach a dish someone could cook, set is_recipe false and recipes [].
- A video can hold more than one recipe; return each one.
- Quantity priority: linked recipe page, then description, then transcript.
- Never invent a quantity. If no amount is stated, set quantity to null.
- Write steps as short imperative sentences in cooking order.
- credit: the original recipe author if the poster credits someone else (e.g. "@name"), else null.
- servings / nutrition: only if stated (e.g. "450 calories, 40g protein"), else null.
- category: one of {categories}.
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


def fetch_thumbnail(info: dict, path: Path) -> None:
    # TikTok cover URLs are signed and expire within days, so keep a local copy.
    if not info.get("thumbnail"):
        return
    req = urllib.request.Request(info["thumbnail"], headers={"User-Agent": BROWSER_UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            path.write_bytes(resp.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  no thumbnail: {exc}", file=sys.stderr)


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
            return {"url": url, "text": html.unescape("\n".join(parts))}
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
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4000,
        "response_format": RECIPE_SCHEMA,
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
        thumb = root / "cache" / recipe["video"]["id"] / "thumb.jpg"
        recipe["video"]["thumb"] = thumb.exists()
        if thumb.exists():
            shutil.copyfile(thumb, site / "img" / f"{recipe['video']['id']}.jpg")
    template = (Path(__file__).parent / "site_template.html").read_text()
    # "</" would end the <script> tag that holds the JSON.
    data = json.dumps(recipes, ensure_ascii=False).replace("</", "<\\/")
    (site / "index.html").write_text(template.replace("__TITLE__", html.escape(title)).replace("__DATA__", data))
    return site / "index.html"


def deploy_site(site: Path) -> None:
    if not shutil.which("wrangler"):
        print("Deploy skipped: wrangler not installed.", file=sys.stderr)
        return
    result = subprocess.run(["wrangler", "pages", "deploy", str(site), "--project-name", PAGES_PROJECT,
                             "--branch", "main", "--commit-dirty=true"], capture_output=True, text=True)
    if result.returncode:
        print(f"Deploy failed:\n{result.stderr.strip() or result.stdout.strip()}", file=sys.stderr)
    else:
        print(f"Live:  https://{PAGES_PROJECT}.pages.dev/")


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
    args = parser.parse_args()

    collection_url = resolve_url(args.url)
    print(f"Collection: {collection_url}")
    collection = list_videos(collection_url, args.cookies_from_browser)
    entries = [e for e in collection.get("entries") or [] if e and e.get("url")]
    if args.limit:
        entries = entries[:args.limit]

    root = args.out or Path(__file__).resolve().parent / "runs" / slugify(collection.get("title") or collection.get("id"))
    cache = root / "cache"
    (root / "recipes").mkdir(parents=True, exist_ok=True)
    model = None if args.fetch_only else lmstudio_model(args.model)

    recipes, skipped, failed = [], [], []
    for n, entry in enumerate(entries, 1):
        url = entry["url"]
        video_id = entry.get("id") or url.rstrip("/").split("/")[-1]
        folder = cache / video_id
        print(f"[{n}/{len(entries)}] {url}", flush=True)
        try:
            if args.refresh or not (folder / "video.info.json").exists():
                fetch_video(url, folder, args.cookies_from_browser)
            info = json.loads((folder / "video.info.json").read_text())
            transcript, source = pick_transcript(folder)
            if args.refresh or not (folder / "thumb.jpg").exists():
                fetch_thumbnail(info, folder / "thumb.jpg")
            video = {
                "id": video_id, "url": url, "uploader": info.get("uploader") or "unknown",
                "title": info.get("title") or info.get("description") or video_id,
                "transcript_source": source,
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

            extracted_path = folder / "extracted.json"
            # Videos extracted before linked pages existed get redone once a page is found.
            if args.reextract or not extracted_path.exists() or (new_links and video["linked"]):
                extracted = extract_recipes(info, transcript, source, linked, model)
                extracted_path.write_text(json.dumps(extracted, indent=2, ensure_ascii=False))
            extracted = json.loads(extracted_path.read_text())

            if not extracted["is_recipe"] or not extracted["recipes"]:
                skipped.append(video)
                continue
            for i, recipe in enumerate(extracted["recipes"]):
                suffix = f"-{i + 1}" if len(extracted["recipes"]) > 1 else ""
                recipe = {**recipe, "file": f"{slugify(recipe['title'])}-{video_id[-6:]}{suffix}.md",
                          "video": video}
                (root / "recipes" / recipe["file"]).write_text(render_recipe(recipe, video))
                recipes.append(recipe)
        except Exception as exc:
            failed.append({"url": url, "error": str(exc)})
            print(f"  failed: {exc}", file=sys.stderr)

    if args.fetch_only:
        no_captions = sum(1 for e in entries if pick_transcript(cache / (e.get("id") or ""))[1] == "none")
        print(f"Fetched {len(entries) - len(failed)} videos, {no_captions} without captions, {len(failed)} failed.")
        return

    (root / "recipes.json").write_text(json.dumps(recipes, indent=2, ensure_ascii=False))
    (root / "index.md").write_text(render_index(collection.get("title") or "Recipes", recipes, skipped, failed))
    print(f"\n{len(recipes)} recipes, {len(skipped)} not recipes, {len(failed)} failed.")
    print(f"Index: {root / 'index.md'}")
    site = write_site(root, recipes)
    print(f"Site:  {site}")
    # A --limit run holds a partial collection and would replace the full live site.
    if args.no_deploy or args.limit:
        print("Deploy skipped.")
    else:
        deploy_site(site.parent)


if __name__ == "__main__":
    main()
