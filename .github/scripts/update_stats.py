#!/usr/bin/env python3
"""Refresh the coding statistics table in README.md from GitHub contributions."""

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = os.environ.get("GITHUB_USERNAME", "DhruvDoshi")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = "README.md"
FIRST_YEAR = 2018


def graphql(query):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def year_query(year):
    start = f"{year}-01-01T00:00:00Z"
    end = f"{year + 1}-01-01T00:00:00Z"
    return f"""
      y{year}: contributionsCollection(from: "{start}", to: "{end}") {{
        contributionCalendar {{
          totalContributions
          weeks {{ contributionDays {{ date contributionCount }} }}
        }}
      }}
    """


def load_contributions():
    now = datetime.now(timezone.utc)
    fields = "\n".join(year_query(year) for year in range(FIRST_YEAR, now.year + 1))
    data = graphql(f"query {{ user(login: \"{USERNAME}\") {{ {fields} }} }}")
    days = {}
    overall = 0
    for year in range(FIRST_YEAR, now.year + 1):
        calendar = data["user"][f"y{year}"]["contributionCalendar"]
        overall += calendar["totalContributions"]
        if year == now.year:
            for week in calendar["weeks"]:
                for day in week["contributionDays"]:
                    days[day["date"]] = day["contributionCount"]
    return now, days, overall


def period_totals(now, days):
    today = now.date()
    week_start = today - timedelta(days=(today.weekday() + 1) % 7)

    def total(predicate):
        return sum(count for date, count in days.items() if predicate(datetime.strptime(date, "%Y-%m-%d").date()))

    return {
        "Today": total(lambda day: day == today),
        "This week": total(lambda day: week_start <= day <= today),
        "This month": total(lambda day: day.year == today.year and day.month == today.month and day <= today),
        "This year": total(lambda day: day.year == today.year and day <= today),
    }


def render_table(periods, overall, now):
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    rows = "\n".join(f"| {label} | {count:,} |" for label, count in periods.items())
    return (
        "## Coding statistics\n\n"
        "| Period | Contributions |\n"
        "| --- | ---: |\n"
        f"{rows}\n"
        f"| Overall | {overall:,} |\n\n"
        f"*GitHub contributions, including private activity. Updated {stamp}.*\n"
    )


def current_overall(content):
    match = re.search(r"\| Overall \| ([0-9,]+) \|", content)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def update_readme(table, overall):
    with open(README, encoding="utf-8") as handle:
        content = handle.read()
    existing = current_overall(content)
    if existing and overall < existing * 0.8:
        raise RuntimeError(
            "New total is much smaller than the README. "
            "Use a personal access token that can read private contributions."
        )
    pattern = r"## Coding statistics\n.*?(?=\n<!-- stats:end -->)"
    if not re.search(pattern, content, flags=re.DOTALL):
        raise RuntimeError("Could not find the coding statistics section")
    updated = re.sub(pattern, table.rstrip() + "\n\n", content, count=1, flags=re.DOTALL)
    with open(README, "w", encoding="utf-8") as handle:
        handle.write(updated)


def main():
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is required")
    now, days, overall = load_contributions()
    update_readme(render_table(period_totals(now, days), overall, now), overall)
    print("Updated coding statistics")


if __name__ == "__main__":
    main()
