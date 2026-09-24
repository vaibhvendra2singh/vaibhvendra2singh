#!/usr/bin/env python3
import json
import os
import urllib.request
from collections import Counter
from datetime import date, timedelta
from html import escape

LOGIN = "vaibhvendra2singh"
TOKEN = os.environ["GITHUB_TOKEN"]

def graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-analytics",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]

today = date.today()
start = today - timedelta(days=365)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        stargazerCount
        primaryLanguage { name }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""

data = graphql(
    query,
    {
        "login": LOGIN,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": f"{today.isoformat()}T23:59:59Z",
    },
)

user = data["user"]
days = [
    d
    for w in user["contributionsCollection"]["contributionCalendar"]["weeks"]
    for d in w["contributionDays"]
]
days.sort(key=lambda x: x["date"])

total = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]

current = 0
for d in reversed(days):
    if d["date"] > today.isoformat():
        continue
    if d["contributionCount"] > 0:
        current += 1
    else:
        break

longest = 0
run = 0
for d in days:
    if d["contributionCount"] > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0

repos = user["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
languages = Counter(
    r["primaryLanguage"]["name"]
    for r in repos
    if r.get("primaryLanguage")
)
top_languages = languages.most_common(4)

lang_text = " · ".join(f"{escape(k)} ({v})" for k, v in top_languages) or "No public language data"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="310" viewBox="0 0 900 310">
<rect width="900" height="310" rx="16" fill="#161b22"/>
<text x="40" y="48" fill="#58a6ff" font-family="Arial, sans-serif" font-size="24" font-weight="700">GitHub Analytics</text>
<text x="40" y="74" fill="#8b949e" font-family="Arial, sans-serif" font-size="13">Live data refreshed automatically by GitHub Actions</text>

<rect x="40" y="100" width="250" height="85" rx="12" fill="#0d1117" stroke="#30363d"/>
<text x="60" y="128" fill="#8b949e" font-family="Arial, sans-serif" font-size="13">Contributions · last 365 days</text>
<text x="60" y="162" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="30" font-weight="700">{total}</text>

<rect x="325" y="100" width="250" height="85" rx="12" fill="#0d1117" stroke="#30363d"/>
<text x="345" y="128" fill="#8b949e" font-family="Arial, sans-serif" font-size="13">Current streak</text>
<text x="345" y="162" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="30" font-weight="700">{current} days</text>

<rect x="610" y="100" width="250" height="85" rx="12" fill="#0d1117" stroke="#30363d"/>
<text x="630" y="128" fill="#8b949e" font-family="Arial, sans-serif" font-size="13">Longest streak</text>
<text x="630" y="162" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="30" font-weight="700">{longest} days</text>

<text x="40" y="220" fill="#8b949e" font-family="Arial, sans-serif" font-size="13">Public repositories</text>
<text x="40" y="250" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="24" font-weight="700">{len(repos)}</text>

<text x="220" y="220" fill="#8b949e" font-family="Arial, sans-serif" font-size="13">Total stars</text>
<text x="220" y="250" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="24" font-weight="700">{stars}</text>

<text x="400" y="220" fill="#8b949e" font-family="Arial, sans-serif" font-size="13">Top languages by repository</text>
<text x="400" y="250" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="15">{lang_text}</text>

<text x="40" y="286" fill="#6e7681" font-family="Arial, sans-serif" font-size="11">Updated: {today.isoformat()}</text>
</svg>
'''

with open("assets/github-analytics.svg", "w", encoding="utf-8") as f:
    f.write(svg)
