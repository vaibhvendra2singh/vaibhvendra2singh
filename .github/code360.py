import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_URL = "https://www.naukri.com/code360/profile/vaibhendra"
START = "<!-- CODE360:START -->"
END = "<!-- CODE360:END -->"
SVG_PATH = Path("assets/code360-stats.svg")

API_RESPONSES = []

def to_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        m = re.search(r"\b(\d[\d,]*)\b", value.replace(",", ""))
        return int(m.group(1).replace(",", "")) if m else None
    return None

def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)

def first_number(obj, keys):
    for key, value in walk(obj):
        lk = key.lower()
        if any(token in lk for token in keys):
            n = to_int(value)
            if n is not None:
                return n
    return None

def regex_number(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except (ValueError, IndexError):
                pass
    return None

def get_stats_from_json(data):
    # Code360 profile payload
    stats_block = (
        data.get("data", {})
        if isinstance(data, dict)
        else {}
    )

    solved = None
    easy = None
    medium = None
    hard = None

    # Search all nested objects for problem-count fields.
    for key, value in walk(stats_block):
        if key == "problem_count_data" and isinstance(value, dict):
            solved = solved or to_int(value.get("total_count"))
            easy = easy or to_int(value.get("easy_count"))
            medium = medium or to_int(value.get("medium_count"))
            hard = hard or to_int(value.get("hard_count"))

    solved = solved or first_number(
        data,
        ["total_count", "problems_solved", "totalproblemsolved", "solved_count"],
    )

    submissions = first_number(
        data,
        ["submission_count", "submissions", "total_submission", "total_submissions"],
    )
    coding = first_number(
        data,
        ["coding_count", "coding_problems", "coding"],
    )
    mcq = first_number(
        data,
        ["mcq_count", "mcq_problems", "mcq"],
    )
    current = first_number(
        data,
        ["current_streak", "currentstreak", "curr_streak"],
    )
    longest = first_number(
        data,
        ["longest_streak", "longeststreak", "long_streak"],
    )

    # Avoid interpreting generic "coding" fields such as coding score.
    if coding is not None and coding > 20000:
        coding = None

    return {
        "solved": solved,
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "submissions": submissions,
        "coding": coding,
        "mcq": mcq,
        "current_streak": current,
        "longest_streak": longest,
    }

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1440, "height": 1800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
        locale="en-US",
    )
    page = context.new_page()

    def capture(response):
        url = response.url
        if "naukri.com" not in url.lower():
            return
        if "/api/" not in url.lower():
            return
        try:
            ct = response.headers.get("content-type", "")
            if "json" not in ct.lower():
                return
            raw = response.text()
            if raw and len(raw) < 5_000_000:
                API_RESPONSES.append((url, raw))
        except Exception:
            pass

    page.on("response", capture)

    page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(7000)

    # Trigger lazy-loaded profile sections.
    for _ in range(5):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(1200)

    body_text = page.locator("body").inner_text()
    html_source = page.content()
    final_url = page.url
    title = page.title()

    browser.close()

stats = {
    "solved": None,
    "easy": None,
    "medium": None,
    "hard": None,
    "submissions": None,
    "coding": None,
    "mcq": None,
    "current_streak": None,
    "longest_streak": None,
}

for url, raw in API_RESPONSES:
    try:
        data = json.loads(raw)
    except Exception:
        continue

    found = get_stats_from_json(data)
    for key, value in found.items():
        if stats[key] is None and value is not None:
            stats[key] = value

# Rendered page fallback.
if stats["submissions"] is None:
    stats["submissions"] = regex_number(
        body_text,
        [r"(\d[\d,]*)\s+Problem submissions"],
    )

if stats["coding"] is None:
    stats["coding"] = regex_number(
        body_text,
        [r"Coding\s*\((\d+)\)"],
    )

if stats["mcq"] is None:
    stats["mcq"] = regex_number(
        body_text,
        [r"MCQ\s*\((\d+)\)"],
    )

if stats["current_streak"] is None:
    stats["current_streak"] = regex_number(
        body_text,
        [r"Current streak:\s*(\d+)\s*days?"],
    )

if stats["longest_streak"] is None:
    stats["longest_streak"] = regex_number(
        body_text,
        [r"Longest streak:\s*(\d+)\s*days?"],
    )

if stats["solved"] is None:
    stats["solved"] = regex_number(
        html_source,
        [
            r'"total_count"\s*:\s*(\d+)',
            r'"totalCount"\s*:\s*(\d+)',
        ],
    )

print(f"Final URL: {final_url}")
print(f"Title: {title}")
print(f"Captured API responses: {len(API_RESPONSES)}")
print(f"Code360 stats: {stats}")

if all(
    stats[k] is None
    for k in ("submissions", "coding", "mcq", "current_streak", "longest_streak", "solved")
):
    print("Relevant API URLs captured:")
    for url, _ in API_RESPONSES[-30:]:
        print(url)
    raise RuntimeError("Could not extract Code360 statistics.")

updated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

def val(key):
    return stats[key] if stats[key] is not None else "—"

SVG_PATH.parent.mkdir(parents=True, exist_ok=True)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="920" height="230" viewBox="0 0 920 230">
  <rect width="920" height="230" rx="18" fill="#0d1117" stroke="#30363d"/>
  <text x="40" y="48" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="28" font-weight="700">Code360</text>
  <text x="40" y="76" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="14">Live coding activity</text>

  <text x="55" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{html.escape(str(val("submissions")))}</text>
  <text x="55" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Submissions</text>

  <text x="255" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{html.escape(str(val("coding")))}</text>
  <text x="255" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Coding</text>

  <text x="415" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{html.escape(str(val("mcq")))}</text>
  <text x="415" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">MCQ</text>

  <text x="555" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{html.escape(str(val("current_streak")))}</text>
  <text x="555" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Current streak</text>

  <text x="745" y="124" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{html.escape(str(val("longest_streak")))}</text>
  <text x="745" y="150" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Longest streak</text>

  <text x="40" y="198" fill="#6e7681" font-family="Arial,Helvetica,sans-serif" font-size="11">Last synced: {html.escape(updated)}</text>
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

print(f"Successfully synced Code360 stats at {updated}.")
