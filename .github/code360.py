import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = "https://www.naukri.com/code360/profile/vaibhendra"
START = "<!-- CODE360:START -->"
END = "<!-- CODE360:END -->"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        viewport={"width": 1440, "height": 1200},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
    )
    page.goto(URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(8000)
    text = page.locator("body").inner_text()
    browser.close()

submission = re.search(r"(\d+)\s+Problem submissions", text, re.I)
coding = re.search(r"Coding\s*\((\d+)\)", text, re.I)
mcq = re.search(r"MCQ\s*\((\d+)\)", text, re.I)
longest = re.search(r"Longest streak:\s*(\d+)\s*days", text, re.I)

if not submission and not coding and not mcq:
    raise RuntimeError("Could not read Code360 statistics from the public profile.")

submissions = submission.group(1) if submission else "—"
coding_count = coding.group(1) if coding else "—"
mcq_count = mcq.group(1) if mcq else "—"
longest_streak = longest.group(1) if longest else "—"
updated = datetime.now(timezone.utc).strftime("%d %b %Y")

section = f"""## Code360

<!-- CODE360:START -->

<p align="center">

<strong>{submissions}</strong> submissions &nbsp; · &nbsp;
<strong>{coding_count}</strong> coding &nbsp; · &nbsp;
<strong>{mcq_count}</strong> MCQ &nbsp; · &nbsp;
<strong>{longest_streak}</strong>-day longest streak

<br><sub>Last synced: {updated} UTC</sub>

</p>

<p align="center">
<a href="{URL}">
<img src="https://img.shields.io/badge/Code360-View%20Profile-2F80ED?style=for-the-badge">
</a>
</p>

<!-- CODE360:END -->

"""

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

pattern = re.escape(START) + r".*?" + re.escape(END)
if not re.search(pattern, readme, re.DOTALL):
    raise RuntimeError("Code360 markers were not found in README.md")

new_readme = re.sub(pattern, section.strip(), readme, count=1, flags=re.DOTALL)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_readme)

print(f"Updated Code360: {submissions} submissions, {coding_count} coding, {mcq_count} MCQ, {longest_streak}-day longest streak.")
