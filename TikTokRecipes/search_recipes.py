#!/usr/bin/env python3
"""Search the extracted TikTok recipes.

Usage:
    python3 TikTokRecipes/search_recipes.py chicken rice --flavor savory
    python3 TikTokRecipes/search_recipes.py --tag high-protein --tag air-fryer --category snack
    python3 TikTokRecipes/search_recipes.py cottage -dessert --max-ingredients 6
    python3 TikTokRecipes/search_recipes.py --show one-pot-tuscan-bacon-gnocchi-122528

Words match title, ingredients, tags, category, and creator. A word starting with "-" excludes.
Reads the newest runs/*/recipes.json, or the live site's copy if there is no local run.
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

SITE = "https://tt-recipes.pages.dev"


def load(path: Path | None) -> list[dict]:
    if path is None:
        runs = sorted(Path(__file__).resolve().parent.glob("runs/*/recipes.json"), key=lambda p: p.stat().st_mtime)
        path = runs[-1] if runs else None
    if path:
        return json.loads(path.read_text())
    # Cloudflare rejects Python's default user agent with 403.
    request = urllib.request.Request(f"{SITE}/recipes.json", headers={"User-Agent": "search_recipes"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def recipe_id(recipe: dict) -> str:
    return recipe["file"].removesuffix(".md")


def to_markdown(r: dict) -> str:
    lines = [f"# {r['title']}", "", f"{r['category']} · {r.get('flavor', '?')} · {', '.join(r['tags'])}"]
    lines += [x for x in (r["servings"] and f"Servings: {r['servings']}", r["nutrition"] and f"Nutrition: {r['nutrition']}") if x]
    lines += ["", "## Ingredients", ""]
    lines += [f"- {i['quantity'] + ' ' if i['quantity'] else ''}{i['item']}" for i in r["ingredients"]]
    lines += ["", "## Instructions", ""] + [f"{n}. {s}" for n, s in enumerate(r["steps"], 1)]
    if r["missing"]:
        lines += ["", "Not stated: " + "; ".join(r["missing"])]
    lines += ["", f"Video: {r['video']['url']} (@{r['video']['uploader']})"]
    lines += [f"Recipe page: {u}" for u in r["video"].get("links", [])]
    lines += [f"Site: {SITE}/#{recipe_id(r)}"]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("words", nargs="*", help="Search words; prefix with - to exclude")
    parser.add_argument("--category", help="breakfast, main, side, soup-salad, snack, dessert, drink, sauce-dip, other")
    parser.add_argument("--flavor", choices=["sweet", "savory"])
    parser.add_argument("--tag", action="append", default=[], help="Required tag; repeat for more")
    parser.add_argument("--max-ingredients", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--show", metavar="ID", help="Print one recipe in full as Markdown")
    parser.add_argument("--tags", action="store_true", help="List all tags with counts")
    parser.add_argument("--json", action="store_true", help="Print matches as JSON")
    parser.add_argument("--data", type=Path, help="recipes.json to read")
    # argparse reads "-dessert" as an unknown option, so collect those as excludes.
    args, extra = parser.parse_known_args()
    if any(x.startswith("--") or not x.startswith("-") for x in extra):
        parser.error(f"unrecognized arguments: {' '.join(extra)}")
    recipes = load(args.data)

    if args.show:
        match = next((r for r in recipes if recipe_id(r) == args.show), None)
        if not match:
            sys.exit(f"No recipe {args.show}")
        print(to_markdown(match))
        return
    if args.tags:
        counts = {}
        for r in recipes:
            for t in r["tags"]:
                counts[t] = counts.get(t, 0) + 1
        for t, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"{n:4} {t}")
        return

    include = [w.lower() for w in args.words if not w.startswith("-")]
    exclude = [w[1:].lower() for w in [*args.words, *extra] if w.startswith("-") and len(w) > 1]
    hits = []
    for r in recipes:
        title = r["title"].lower()
        hay = " ".join([title, r["category"], r.get("flavor", ""), *r["tags"], r["video"]["uploader"],
                        *(i["item"] for i in r["ingredients"])]).lower()
        if any(w not in hay for w in include) or any(w in hay for w in exclude):
            continue
        if args.category and r["category"] != args.category:
            continue
        if args.flavor and r.get("flavor") != args.flavor:
            continue
        if any(t not in r["tags"] for t in args.tag):
            continue
        if args.max_ingredients and len(r["ingredients"]) > args.max_ingredients:
            continue
        # Title matches first, then newest saved.
        hits.append((-sum(w in title for w in include), r["video"].get("added", 0), r))
    hits = [r for *_, r in sorted(hits, key=lambda h: h[:2])]

    if args.json:
        print(json.dumps(hits[:args.limit], indent=2, ensure_ascii=False))
        return
    print(f"{len(hits)} matches" + (f", showing {args.limit}" if len(hits) > args.limit else ""))
    for r in hits[:args.limit]:
        print(f"- {r['title']} [{r['category']}, {r.get('flavor', '?')}, {len(r['ingredients'])} ingredients] "
              f"{', '.join(r['tags'])}\n  id: {recipe_id(r)}  {SITE}/#{recipe_id(r)}")


if __name__ == "__main__":
    main()
