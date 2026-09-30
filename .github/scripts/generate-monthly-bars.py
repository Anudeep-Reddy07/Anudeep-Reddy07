#!/usr/bin/env python3
"""Generate a monthly contribution bar-chart SVG from real GitHub data.

Fetches the authenticated user's contribution calendar via the GitHub
GraphQL API, aggregates contributions per month (last 12 months), and
renders a dark-themed bar chart SVG.

Usage:
    METRICS_TOKEN=<pat> python3 generate-monthly-bars.py [output.svg]

The token needs no special scopes for public data; a classic PAT also
picks up private contributions, matching what the metrics action sees.
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

LOGIN = "Anudeep-Reddy07"
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "monthly-bars.svg"

# --- colors / layout (matches the approved sample) ---
DARK = "#0d1117"
FG = "#e6edf3"
MUTED = "#8b949e"
W, H = 920, 320
PL, PR, PT, PB = 50, 24, 40, 44


def fetch_calendar(token: str):
    """Return list of (date, contribution_count) for roughly the last year."""
    to = datetime.now(timezone.utc)
    frm = to - timedelta(days=365)
    query = """
    query($login: String!, $from: DateTime, $to: DateTime) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    payload = json.dumps({
        "query": query,
        "variables": {
            "login": LOGIN,
            "from": frm.isoformat(),
            "to": to.isoformat(),
        },
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "monthly-bars-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    weeks = body["data"]["user"]["contributionsCollection"][
        "contributionCalendar"]["weeks"]
    days = []
    for week in weeks:
        for d in week["contributionDays"]:
            days.append((date.fromisoformat(d["date"]), d["contributionCount"]))
    return days


def render(days):
    bym = defaultdict(int)
    for d, c in days:
        bym[(d.year, d.month)] += c
    keys = sorted(bym)[-12:]  # last 12 months; drops any leading partial month
    vals = [bym[k] for k in keys]
    mx = max(vals) if vals else 0

    iw, ih = W - PL - PR, H - PT - PB
    bw = iw / len(keys)
    parts = []
    for i, (k, v) in enumerate(zip(keys, vals)):
        h = (v / mx) * ih if mx else 0
        x = PL + i * bw + bw * 0.22
        w = bw * 0.56
        y = PT + ih - h
        cx = x + w / 2
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{max(h, 2):.1f}" rx="6" fill="url(#mg)"/>')
        parts.append(
            f'<text x="{cx:.1f}" y="{y - 8:.1f}" font-size="12" fill="{FG}" '
            f'text-anchor="middle" font-family="sans-serif">{v}</text>')
        parts.append(
            f'<text x="{cx:.1f}" y="{H - 18}" font-size="12" fill="{MUTED}" '
            f'text-anchor="middle" font-family="sans-serif">'
            f'{date(k[0], k[1], 1).strftime("%b")}</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><linearGradient id="mg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#39d353"/><stop offset="1" stop-color="#0e4429"/></linearGradient></defs>
<rect width="{W}" height="{H}" fill="{DARK}" rx="8"/>
<text x="{PL}" y="26" font-size="14" fill="{FG}" font-family="sans-serif">Contributions per month</text>
{''.join(parts)}</svg>'''


def main():
    token = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Set METRICS_TOKEN (or GITHUB_TOKEN) in the environment.")
    days = fetch_calendar(token)
    svg = render(days)
    with open(OUTPUT, "w") as f:
        f.write(svg)
    total = sum(c for _, c in days)
    print(f"Wrote {OUTPUT}: {len(days)} days, {total} contributions")


if __name__ == "__main__":
    main()
