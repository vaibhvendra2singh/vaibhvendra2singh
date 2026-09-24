import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

PROFILE = "vaibhendra"
PROFILE_URL = "https://www.naukri.com/code360/profile/vaibhendra"
API_BASE = "https://www.naukri.com/code360/api/v3/public_section"
START = "<!-- CODE360:START -->"
END = "<!-- CODE360:END -->"
SVG_PATH = "assets/code360-stats.svg"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": PROFILE_URL,
}

def get_json(path, params):
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{path}?{query}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Code360 API returned HTTP {response.status}: {url}")
        return json.loads(response.read().decode("utf-8"))

def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        m = re.search(r"\b(\d+)\b", value.replace(",", ""))
        return int(m.group(1)) if m else None
    return None

def find_number(obj, wanted_keys):
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_l = key.lower()
            if any(w in key_l for w in wanted_keys):
                n = number(value)
                if n is not None:
                    return n
            found = find_number(value, wanted_keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_number(value, wanted_keys)
            if found is not None:
                return found
    return None

profile_payload = get_json(
    "profile/user_details",
    {
        "uuid": PROFILE,
        "app_context": "publicsection",
        "naukri_request": "true",
        "request_differentiator": int(datetime.now().timestamp() * 1000),
    },
)

profile_data = profile_payload.get("data") or {}
uuid = profile_data.get("uuid")
if not uuid:
    raise RuntimeError("Code360 did not return a profile UUID.")

stats = profile_data.get("dsa_domain_data", {}).get("problem_count_data", {})
solved = number(stats.get("total_count"))
easy = number(stats.get("easy_count"))

streak_payload = get_json(
    "streaks/fetch_curr_and_long_streak",
    {
        "uuid": uuid,
        "app_context": "publicsection",
        "naukri_request": "true",
        "request_differentiator": int(datetime.now().timestamp() * 1000),
    },
)
streak_data = streak_payload.get("data") or {}

current_streak = find_number(
    streak_data,
    ["current_streak", "currentstreak", "curr_streak", "current"],
)
longest_streak = find_number(
    streak_data,
    ["longest_streak", "longeststreak", "long_streak", "longest"],
)

if solved is None:
    solved = find_number(profile_data, ["total_count", "problems_solved", "solved_count"])

if solved is None:
    raise RuntimeError("Code360 API returned profile data, but no solved-count field was found.")

current_streak = current_streak if current_streak is not None else 0
longest_streak = longest_streak if longest_streak is not None else 0
updated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

def esc(value):
    return html.escape(str(value), quote=True)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="920" height="210" viewBox="0 0 920 210">
  <rect width="920" height="210" rx="18" fill="#0d1117" stroke="#30363d"/>
  <text x="40" y="48" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="28" font-weight="700">Code360</text>
  <text x="40" y="78" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="14">Live coding profile • automatically synced</text>

  <text x="55" y="130" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(solved)}</text>
  <text x="55" y="156" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Problems solved</text>

  <text x="280" y="130" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(current_streak)}</text>
  <text x="280" y="156" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Current streak</text>

  <text x="505" y="130" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(longest_streak)}</text>
  <text x="505" y="156" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Longest streak</text>

  <text x="735" y="130" fill="#f0f6fc" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(easy if easy is not None else "—")}</text>
  <text x="735" y="156" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" font-size="13">Easy</text>

  <text x="40" y="190" fill="#6e7681" font-family="Arial,Helvetica,sans-serif" font-size="11">Last synced: {esc(updated)}</text>
</svg>
'''

with open(SVG_PATH, "w", encoding="utf-8") as f:
    f.write(svg)

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

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

new_readme = re.sub(pattern, section.strip(), readme, count=1, flags=re.DOTALL)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_readme)

print(
    f"Code360 synced: solved={solved}, current_streak={current_streak}, "
    f"longest_streak={longest_streak}, easy={easy}"
)
