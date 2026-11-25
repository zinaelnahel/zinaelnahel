#!/usr/bin/env python3
"""Refresh the profile contribution SVGs from GitHub's public contribution calendar."""
from datetime import date, timedelta
from html.parser import HTMLParser
from math import ceil
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json
import os
import re

USER = "zinaelnahel"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PALETTE = ["#efede7", "#d6f3de", "#a8e9c2", "#62c98b", "#23864f"]


class ContributionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        if tag != "rect":
            return
        attrs = dict(attrs)
        day = attrs.get("data-date")
        count = attrs.get("data-count")
        if day and count is not None:
            try:
                self.days[day] = int(count)
            except ValueError:
                pass


def fetch_calendar(start, end):
    query = urlencode({"from": start.isoformat(), "to": end.isoformat()})
    req = Request(
        "https://github.com/users/{}/contributions?{}".format(USER, query),
        headers={"User-Agent": "profile-contribution-refresh", "Accept": "text/html"},
    )
    with urlopen(req, timeout=30) as response:
        html = response.read().decode("utf-8", "replace")
    parser = ContributionParser()
    parser.feed(html)
    if not parser.days:
        # Keep this fail-closed: never replace valid profile graphics with zeroes
        # if GitHub changes the page markup or blocks the request.
        raise RuntimeError("GitHub contribution calendar did not contain daily counts")
    return parser.days


def get_days():
    today = date.today()
    trailing_start = today - timedelta(days=364)
    year_start = date(today.year, 1, 1)
    days = fetch_calendar(min(trailing_start, year_start), today)
    if len(days) < 30:
        raise RuntimeError("GitHub returned an incomplete contribution calendar")
    return today, trailing_start, days


def svg_stats(today, start, days, public_repos, stars):
    last_year = sum(n for d, n in days.items() if start.isoformat() <= d <= today.isoformat())
    last30_start = today - timedelta(days=29)
    last30 = sum(days.get((last30_start + timedelta(days=i)).isoformat(), 0) for i in range(30))
    current_streak = 0
    cursor = today
    while days.get(cursor.isoformat(), 0) > 0:
        current_streak += 1
        cursor -= timedelta(days=1)
    best = run = 0
    cursor = start
    while cursor <= today:
        if days.get(cursor.isoformat(), 0) > 0:
            run += 1
            best = max(best, run)
        else:
            run = 0
        cursor += timedelta(days=1)
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="300" viewBox="0 0 1200 300" role="img" aria-labelledby="t d">
<title id="t">On GitHub</title><desc id="d">{last_year} contributions in the last year, {current_streak} day current streak, {best} day longest streak, {last30} contributions in the last 30 days, {public_repos} public repositories, and {stars} stars.</desc>
<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.4" fill="#26231f" opacity=".1"/></pattern></defs>
<rect x="3" y="3" width="1194" height="294" rx="27" fill="#fffaf0" stroke="#26231f" stroke-width="4"/><rect x="7" y="7" width="1186" height="286" rx="23" fill="url(#dots)"/>
<text x="34" y="43" font-family="Trebuchet MS,Arial,sans-serif" font-size="26" font-weight="900" fill="#26231f">On GitHub</text><text x="1164" y="41" text-anchor="end" font-family="monospace" font-size="13" fill="#625d55">PUBLIC CONTRIBUTIONS · {today:%d %b %Y}</text>
<g font-family="Trebuchet MS,Arial,sans-serif" fill="#26231f">
<g><rect x="27" y="60" width="268" height="132" rx="20" fill="#b9dcff" stroke="#26231f" stroke-width="3"/><text x="48" y="113" font-size="43" font-weight="900">{last_year}</text><text x="49" y="142" font-size="17">contributions in the last year</text><text x="49" y="169" font-family="monospace" font-size="12">{start:%d %b %Y} — {today:%d %b %Y}</text></g>
<g><rect x="318" y="60" width="268" height="132" rx="20" fill="#c8f0d7" stroke="#26231f" stroke-width="3"/><text x="341" y="113" font-size="43" font-weight="900">{current_streak} days</text><text x="342" y="142" font-size="17">current streak</text><text x="342" y="169" font-family="monospace" font-size="12">STILL SHOWING UP</text></g>
<g><rect x="609" y="60" width="268" height="132" rx="20" fill="#f9dfa8" stroke="#26231f" stroke-width="3"/><text x="632" y="113" font-size="43" font-weight="900">{best} days</text><text x="633" y="142" font-size="17">longest streak this year</text><text x="633" y="169" font-family="monospace" font-size="12">CONSECUTIVE DAYS</text></g>
<g><rect x="900" y="60" width="272" height="132" rx="20" fill="#e3d5ff" stroke="#26231f" stroke-width="3"/><text x="923" y="113" font-size="43" font-weight="900">{last30}</text><text x="924" y="142" font-size="17">contributions in 30 days</text><text x="924" y="169" font-family="monospace" font-size="12">{last30_start:%d %b} — {today:%d %b %Y}</text></g>
<g><rect x="27" y="211" width="554" height="57" rx="18" fill="#c8f0d7" stroke="#26231f" stroke-width="3"/><text x="49" y="248" font-size="25" font-weight="900">{public_repos}</text><text x="103" y="246" font-size="16">public repositories</text></g>
<g><rect x="599" y="211" width="573" height="57" rx="18" fill="#f7b8c8" stroke="#26231f" stroke-width="3"/><text x="622" y="248" font-size="25" font-weight="900">{stars}</text><text x="653" y="246" font-size="16">stars earned</text><text x="1144" y="245" text-anchor="end" font-family="monospace" font-size="12">UPDATED {today:%d %b %Y}</text></g>
</g></svg>""".format(last_year=last_year, current_streak=current_streak, best=best, last30=last30,
             public_repos=public_repos, stars=stars, today=today, start=start, last30_start=last30_start)


def svg_calendar(today, start, days):
    # Sunday-first weeks like GitHub's contribution calendar.
    offset = (start.weekday() + 1) % 7
    grid_start = start - timedelta(days=offset)
    ncols = ceil((offset + (today - start).days + 1) / 7)
    x0, y0, step = 70, 111, 21
    cells, month_labels = [], []
    previous_month = None
    for col in range(ncols):
        first = grid_start + timedelta(days=col * 7)
        if first.month != previous_month:
            month_labels.append('<text x="{}" y="101" font-family="monospace" font-size="12" fill="#555149">{}</text>'.format(x0 + col * step, first.strftime("%b")))
            previous_month = first.month
        for row in range(7):
            day = first + timedelta(days=row)
            if day < start or day > today:
                count, fill = 0, "#fff"
            else:
                count = days.get(day.isoformat(), 0)
                fill = PALETTE[0 if count == 0 else 1 if count < 3 else 2 if count < 6 else 3 if count < 10 else 4]
            x, y = x0 + col * step, y0 + row * 25
            cells.append('<rect x="{}" y="{}" width="18" height="21" rx="5" fill="{}"/><text x="{}" y="{}" text-anchor="middle" font-family="monospace" font-size="8.5" font-weight="700" fill="#26231f">{}</text>'.format(x, y, fill, x + 9, y + 14, count))
    total = sum(n for d, n in days.items() if start.isoformat() <= d <= today.isoformat())
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="328" viewBox="0 0 1200 328" role="img" aria-labelledby="t d">
<title id="t">Daily GitHub contributions</title><desc id="d">Daily contribution counts from {start:%B %d, %Y} to {today:%B %d, %Y}. Total {total}.</desc>
<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.4" fill="#26231f" opacity=".1"/></pattern></defs>
<rect x="3" y="3" width="1194" height="322" rx="27" fill="#fffaf0" stroke="#26231f" stroke-width="4"/><rect x="7" y="7" width="1186" height="314" rx="23" fill="url(#dots)"/>
<rect x="23" y="25" width="1154" height="276" rx="19" fill="#fff" stroke="#26231f" stroke-width="3"/>
<text x="43" y="60" font-family="Trebuchet MS,Arial,sans-serif" font-size="22" font-weight="900" fill="#26231f">Contribution calendar</text><text x="1152" y="59" text-anchor="end" font-family="monospace" font-size="12" fill="#625d55">DAILY COUNT · LAST 12 MONTHS</text>
{months}
<text x="28" y="150" font-family="monospace" font-size="11" fill="#555149">Sun</text><text x="28" y="200" font-family="monospace" font-size="11" fill="#555149">Tue</text><text x="28" y="250" font-family="monospace" font-size="11" fill="#555149">Thu</text>
{cells}
<text x="44" y="289" font-family="monospace" font-size="12" fill="#625d55">contributions per day · {total} total</text>
<g transform="translate(900 277)" font-family="monospace" font-size="11" fill="#625d55"><text x="0" y="11">Less</text><rect x="39" y="0" width="15" height="14" rx="4" fill="#efede7"/><rect x="59" y="0" width="15" height="14" rx="4" fill="#d6f3de"/><rect x="79" y="0" width="15" height="14" rx="4" fill="#a8e9c2"/><rect x="99" y="0" width="15" height="14" rx="4" fill="#62c98b"/><rect x="119" y="0" width="15" height="14" rx="4" fill="#23864f"/><text x="142" y="11">More</text></g></svg>""".format(start=start, today=today, total=total, months="".join(month_labels), cells="".join(cells))


def svg_chart(today, days):
    start = today - timedelta(days=29)
    values = [days.get((start + timedelta(days=i)).isoformat(), 0) for i in range(30)]
    total, maxval = sum(values), max(values + [1])
    ceiling = max(10, ceil(maxval / 10) * 10)
    left, right, top, bottom = 70, 1130, 108, 260
    points = []
    for i, value in enumerate(values):
        x = left + (right - left) * i / (len(values) - 1)
        y = bottom - (bottom - top) * value / ceiling
        points.append((x, y, value))
    path = " ".join(("M" if i == 0 else "L") + "{:.1f} {:.1f}".format(x, y) for i, (x, y, _) in enumerate(points))
    area = path + " L {:.1f} {} L {:.1f} {} Z".format(right, bottom, left, bottom)
    grid, dots = [], []
    for tick in range(0, ceiling + 1, max(1, ceiling // 3)):
        y = bottom - (bottom - top) * tick / ceiling
        grid.append('<line x1="70" y1="{:.1f}" x2="1130" y2="{:.1f}" stroke="#d8d4ca" stroke-width="1.5" stroke-dasharray="5 6"/><text x="53" y="{:.1f}" text-anchor="end" font-family="monospace" font-size="11" fill="#625d55">{}</text>'.format(y, y, y + 4, tick))
    for x, y, value in points:
        dots.append('<circle cx="{:.1f}" cy="{:.1f}" r="5.5" fill="#ff6247" stroke="#26231f" stroke-width="2"><title>{} contributions</title></circle>'.format(x, y, value))
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="330" viewBox="0 0 1200 330" role="img" aria-labelledby="t d">
<title id="t">{total} contributions in the last 30 days</title><desc id="d">A line chart of daily GitHub contributions from {start:%B %d} through {today:%B %d, %Y}. Total {total} contributions.</desc>
<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.4" fill="#26231f" opacity=".1"/></pattern></defs>
<rect x="3" y="3" width="1194" height="324" rx="27" fill="#fffaf0" stroke="#26231f" stroke-width="4"/><rect x="7" y="7" width="1186" height="316" rx="23" fill="url(#dots)"/>
<rect x="24" y="24" width="1152" height="278" rx="19" fill="#fff" stroke="#26231f" stroke-width="3"/>
<text x="44" y="59" font-family="Trebuchet MS,Arial,sans-serif" font-size="22" font-weight="900" fill="#26231f">{total} contributions in the last 30 days</text><text x="1150" y="58" text-anchor="end" font-family="monospace" font-size="12" fill="#625d55">{start:%d %b} — {today:%d %b %Y}</text>
{grid}<path d="{area}" fill="#f7b8c8" opacity=".42"/><path d="{path}" fill="none" stroke="#ff6247" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>{dots}
<text x="70" y="286" font-family="monospace" font-size="11" fill="#625d55">{start:%d %b}</text><text x="1130" y="286" text-anchor="end" font-family="monospace" font-size="11" fill="#625d55">{today:%d %b}</text></svg>""".format(total=total, start=start, today=today, grid="".join(grid), area=area, path=path, dots="".join(dots))


def repo_totals():
    repos, page, stars = 0, 1, 0
    while True:
        req = Request(
            "https://api.github.com/users/{}/repos?type=owner&per_page=100&page={}".format(USER, page),
            headers={"User-Agent": "profile-contribution-refresh", "Accept": "application/vnd.github+json"},
        )
        with urlopen(req, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise RuntimeError("GitHub repository API returned an unexpected response")
        repos += len(batch)
        stars += sum(int(repo.get("stargazers_count", 0)) for repo in batch)
        if len(batch) < 100:
            return repos, stars
        page += 1


def main():
    today, start, days = get_days()
    public_repos, stars = repo_totals()
    assets = {
        "contribution-stats.svg": svg_stats(today, start, days, public_repos, stars),
        "contribution-calendar.svg": svg_calendar(today, start, days),
        "contributions-30d.svg": svg_chart(today, days),
    }
    for name, content in assets.items():
        with open(os.path.join(ROOT, "assets", name), "w", encoding="utf-8") as handle:
            handle.write(content + "\n")
    readme_path = os.path.join(ROOT, "README.md")
    with open(readme_path, encoding="utf-8") as handle:
        readme = handle.read()
    today_total = sum(n for d, n in days.items() if d.startswith(str(today.year)))
    block = """<!-- contributions:start -->
<p align="center"><img src="assets/contribution-stats.svg" width="100%" alt="GitHub contribution statistics, refreshed automatically."></p>

<p align="center"><img src="assets/contribution-calendar.svg" width="100%" alt="Daily GitHub contribution counts for the last 12 months."></p>

<details>
  <summary><b>{year}: {total} contributions so far</b></summary>
  <br>
  This contribution dashboard refreshes daily and after profile repository pushes.
</details>

<p align="center"><img src="assets/contributions-30d.svg" width="100%" alt="Daily GitHub contributions over the last 30 days."></p>
<!-- contributions:end -->""".format(year=today.year, total=today_total)
    pattern = r"<!-- contributions:start -->.*?<!-- contributions:end -->"
    if re.search(pattern, readme, re.S):
        readme = re.sub(pattern, lambda _: block, readme, flags=re.S)
    else:
        old = r"<p align=\\"center\\"><img src=\\"assets/contribution-stats\\.svg\\".*?(?=### What I ship)"
        if not re.search(old, readme, re.S):
            raise RuntimeError("README contribution section not found")
        readme = re.sub(old, block + "\n\n", readme, count=1, flags=re.S)
    with open(readme_path, "w", encoding="utf-8") as handle:
        handle.write(readme)


if __name__ == "__main__":
    main()
