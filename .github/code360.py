import json
import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = "https://www.naukri.com/code360/profile/vaibhendra"
START = "<!-- CODE360:START -->"
END = "<!-- CODE360:END -->"

responses = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        viewport={"width": 1440, "height": 1600},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
    )

    def capture(response):
        url = response.url
        if not any(x in url.lower() for x in ("api", "graphql", "code360", "codingninjas", "profile")):
            return
        try:
            ct = response.headers.get("content-type", "")
            if "json" in ct:
                body = response.text()
                if len(body) < 2_000_000:
                    responses.append((url, body))
        except Exception:
            pass

    page.on("response", capture)

    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(10000)

    for _ in range(4):
        page.mouse.wheel(0, 1800)
        page.wait_for_timeout(1500)

    body_text = page.locator("body").inner_text()
    final_url = page.url
    title = page.title()

    browser.close()

def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        m = re.search(r"\b(\d+)\b", value.replace(",", ""))
        return int(m.group(1)) if m else None
    return None

def walk(obj, path=""):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            lk = k.lower()
            if any(x in lk for x in ("submission", "coding", "mcq", "streak")):
                n = number(v)
                if n is not None:
                    found.append((k, n, p))
            found.extend(walk(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(walk(v, f"{path}[{i}]"))
    return found

values = []
for url, raw in responses:
    try:
        data = json.loads(raw)
        values.extend((k, n, p, url) for k, n, p in walk(data))
    except Exception:
        continue

def pick(keys):
    for wanted in keys:
        for k, n, p, url in values:
            if wanted.lower() in k.lower():
                return n
    return None

submissions = pick(("totalSubmission", "problemSubmission", "submissions", "submissionCount"))
coding_count = pick(("codingProblem", "codingProblems", "codingCount"))
mcq_count = pick(("mcqProblem", "mcqProblems", "mcqCount"))
longest_streak = pick(("longestStreak", "maxStreak"))

if submissions is None:
    m = re.search(r"(\d[\d,]*)\s+Problem submissions", body_text, re.I)
    if m:
        submissions = int(m.group(1).replace(",", ""))

if coding_count is None:
    m = re.search(r"Coding\s*\((\d+)\)", body_text, re.I)
    if m:
        coding_count = int(m.group(1))

if mcq_count is None:
    m = re.search(r"MCQ\s*\((\d+)\)", body_text, re.I)
    if m:
        mcq_count = int(m.group(1))

if longest_streak is None:
    m = re.search(r"Longest streak:\s*(\d+)\s*days", body_text, re.I)
    if m:
        longest_streak = int(m.group(1))

print(f"Code360 final URL: {final_url}")
print(f"Code360 title: {title}")
print(f"Captured JSON responses: {len(responses)}")
print(f"Extracted: submissions={submissions}, coding={coding_count}, mcq={mcq_count}, longest_streak={longest_streak}")

if submissions is None and coding_count is None and mcq_count is None:
    print("No Code360 stats found. Recent relevant API URLs:")
    for url, _ in responses[-20:]:
        print(url)
    raise RuntimeError("Could not read Code360 statistics from the public profile.")

updated = datetime.now(timezone.utc).strftime("%d %b %Y")

stats = []
if submissions is not None:
    stats.append(f"<strong>{submissions}</strong> submissions")
if coding_count is not None:
    stats.append(f"<strong>{coding_count}</strong> coding")
if mcq_count is not None:
    stats.append(f"<strong>{mcq_count}</strong> MCQ")
if longest_streak is not None:
    stats.append(f"<strong>{longest_streak}</strong>-day longest streak")

section = f"""## Code360

{START}

<p align="center">

{' &nbsp; · &nbsp; '.join(stats)}

<br><sub>Last synced: {updated} UTC</sub>

</p>

<p align="center">
<a href="{URL}">
<img src="https://img.shields.io/badge/Code360-View%20Profile-2F80ED?style=for-the-badge">
</a>
</p>

{END}"""

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

pattern = re.escape(START) + r".*?" + re.escape(END)
if not re.search(pattern, readme, re.DOTALL):
    raise RuntimeError("Code360 markers were not found in README.md")

new_readme = re.sub(pattern, section.strip(), readme, count=1, flags=re.DOTALL)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_readme)
