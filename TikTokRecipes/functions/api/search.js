// Cloudflare Pages Function: GET /api/search. Deployed with the site by tiktok_recipes.py.
// Lets any AI or script search the recipes without running the site's JavaScript.

const CORS = { "Access-Control-Allow-Origin": "*" };

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const p = url.searchParams;
  const recipes = await (await env.ASSETS.fetch(new URL("/recipes.json", url))).json();

  const words = (p.get("q") || "").toLowerCase().split(/\s+/).filter(Boolean);
  const include = words.filter((w) => !w.startsWith("-"));
  const exclude = words.filter((w) => w.startsWith("-") && w.length > 1).map((w) => w.slice(1));
  const tags = (p.get("tags") || "").split(",").filter(Boolean);
  const cat = p.get("cat");
  const flavor = p.get("flavor");
  const maxIngredients = Number(p.get("max_ingredients")) || Infinity;
  const limit = Math.min(Number(p.get("limit")) || 25, 200);

  const hits = [];
  for (const r of recipes) {
    const title = r.title.toLowerCase();
    const hay = [title, r.category, r.flavor, ...r.tags, r.video.uploader, ...r.ingredients.map((i) => i.item)]
      .join(" ").toLowerCase();
    if (include.some((w) => !hay.includes(w)) || exclude.some((w) => hay.includes(w))) continue;
    if (cat && r.category !== cat) continue;
    if (flavor && r.flavor !== flavor) continue;
    if (tags.some((t) => !r.tags.includes(t))) continue;
    if (r.ingredients.length > maxIngredients) continue;
    hits.push({ r, score: include.filter((w) => title.includes(w)).length });
  }
  // Title matches first, then newest saved.
  hits.sort((a, b) => b.score - a.score || a.r.video.added - b.r.video.added);

  const results = hits.slice(0, limit).map(({ r }) => {
    const id = r.file.replace(/\.md$/, "");
    return {
      id, title: r.title, category: r.category, flavor: r.flavor, tags: r.tags,
      ingredients: r.ingredients.map((i) => (i.quantity ? `${i.quantity} ${i.item}` : i.item)),
      recipe: `${url.origin}/r/${id}.md`, page: `${url.origin}/#${id}`, video: r.video.url,
    };
  });

  if (p.get("format") === "md") {
    const lines = [`${hits.length} matches${hits.length > limit ? `, showing ${limit}` : ""}`, ""];
    for (const x of results) {
      lines.push(`- [${x.title}](${x.recipe}) — ${x.category}, ${x.flavor}; ${x.tags.join(", ")}`);
      lines.push(`  Ingredients: ${x.ingredients.join("; ") || "not listed"}. Video: ${x.video}`);
    }
    return new Response(lines.join("\n") + "\n", { headers: { ...CORS, "Content-Type": "text/markdown; charset=utf-8" } });
  }
  return Response.json({ total: hits.length, results }, { headers: CORS });
}
