from pathlib import Path
from bs4 import BeautifulSoup

SAMPLES_DIR = Path(__file__).parent / "Samples"

with open(SAMPLES_DIR / "alert.html", encoding="utf8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
for a in soup.select("a"):
    href = a.get("href")
    title = a.get_text().strip()
    if href and title:
        print(title, href)
