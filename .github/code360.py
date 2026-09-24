import html
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROFILE_URL = "https://www.naukri.com/code360/profile/vaibhendra"
START = "<!-- CODE360:START -->"
END = "<!-- CODE360:END -->"
SVG_PATH = Path("assets/code360-stats.svg")

def fetch_reader():
    reader_url = "https://r.jina.ai/" + PROFILE_URL
    req = urllib.request.Request(
        reader_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/plain",
            "X-Engine": "browser",
            "X-Respond-With": "text",
            "X-Timeout": "30",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"Jina Reader returned HTTP {response.status}")
        return response.read().decode("utf-8", errors="replace")

def extract(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except (ValueError, IndexError):
                pass
    return None

text = fetch_reader()

stats = {
    "submissions": extract(text, [
        r"(\d[\d,]*)\s+Problem submissions",
        r"Problem submissions\s*[:\-]?\s*(\d[\d,]*)",
    ]),
    "coding": extract(text, [
        r"Coding\s*\((\d[\d,]*)\)",
        r"Coding\s*[:\-]?\s*(\d[\d,]*)",
    ]),
    "mcq": extract(text, [
        r"MCQ\s*\((\d[\d,]*)\)",
        r"MCQ\s*[:\-]?\s*(\d[\d,]*)",
    ]),
    "current_streak": extract(text, [
        r"Current streak\s*:\s*(\d[\d,]*)\s*days?",
        r"Current streak\s*[:\-]?\s*(\d[\d,]*)",
    ]),
    "longest_streak": extract(text, [
        r"Longest streak\s*:\s*(\d[\d,]*)\s*days?",
        r"Longest streak\s*[:\-]?\s*(\d[\d,]*)",
    ]),
}

print("Code360 Reader response length:", len(text))
print("Code360 stats:", stats)

if all(value is None for value in stats.values()):
    print("Reader response preview:")
    print(text[:5000])
    raise RuntimeError("Code360 statistics were not found in Reader output.")

for key, value in stats.items():
    if value is None:
        stats[key] = "—"

updated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

def esc(value):
    return html.escape(str(value), quote=True)

SVG_PATH.parent.mkdir(parents=True, exist_ok=True)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="920" height="230" viewBox="0 0 920 230">
  <rect width="920" height="230" rx="18" fill="#0d1117" stroke="#30363d"/>
  <text x="40" y="48" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="28" font-weight="700">Code360</text>
  <text x="40" y="76" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="14">Live coding activity</text>

  <text x="55" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(stats["submissions"])}</text>
  <text x="55" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Submissions</text>

  <text x="255" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(stats["coding"])}</text>
  <text x="255" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Coding</text>

  <text x="415" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(stats["mcq"])}</text>
  <text x="415" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">MCQ</text>

  <text x="555" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(stats["current_streak"])}</text>
  <text x="555" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Current streak</text>

  <text x="745" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(stats["longest_streak"])}</text>
  <text x="745" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Longest streak</text>

  <text x="40" y="198" fill="#6e7681" font-family="Arial,Helvetica,sans-serif" font-size="11">Last synced: {esc(updated)}</text>
</svg>'''

SVG_PATH.write_text(svg, encoding="utf-8")

readme_path = Path("README.md")
readme = readme_path.read_text(encoding="utf-8")
pattern = re.escape(START) + r".*?" + re.escape(END)

section = f'''## Code360

{START}

<p align="center">
  <img src="https://raw.githubusercontent.com/vaibhvendra2singh/vaibhvendra2singh/main/{SVG_PATH}" alt="Code360 live statistics" />
</p>

<p align="center">
  <a href="{PROFILE_URL}">View Code360 Profile →</a>
</p>

{END}'''

if not re.search(pattern, readme, re.DOTALL):
    raise RuntimeError("Code360 markers were not found in README.md")

readme = re.sub(pattern, section.strip(), readme, count=1, flags=re.DOTALL)
readme_path.write_text(readme, encoding="utf-8")

print("Code360 README updated successfully.")
