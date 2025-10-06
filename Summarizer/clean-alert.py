from pathlib import Path
from bs4 import BeautifulSoup

SAMPLES_DIR = Path(__file__).parent / "Samples"
ALERT_HTML = SAMPLES_DIR / "google-alert-patient-reported-outcome-2025-10-06.html"

with open(ALERT_HTML, encoding="utf8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
for a in soup.select("a"):
    href = a.get("href")
    title = a.get_text().strip()
    if href and title:
        print(title, href)
