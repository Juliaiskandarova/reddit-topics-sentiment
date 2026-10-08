import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
FIELDS = ("id,subreddit,created_utc,title,selftext,score,"
          "num_comments,author,link_flair_text")
OUT_DIR = Path("data/raw")


def iso(ts):
   
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def get(params):
    
    for attempt in range(6):
        r = requests.get(BASE, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()["data"]
        if r.status_code == 429:
            wait = int(float(r.headers.get("X-RateLimit-Reset", 5))) + 1
        else:
            wait = 2 ** attempt * 2
        print(f"  status {r.status_code}, wait {wait}s")
        time.sleep(wait)
    raise RuntimeError("Too many failed attempts")


def fetch_month(subreddit, year, month):
   
    after = f"{year}-{month:02d}-01"
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    before = f"{ny}-{nm:02d}-01"
    seen = set()
    while True:
        data = get({"subreddit": subreddit, "after": after, "before": before,
                    "limit": 100, "sort": "asc", "fields": FIELDS})
        new = [p for p in data if p["id"] not in seen]
        if not new:
            return
        for p in new:
            seen.add(p["id"])
            yield p
        if len(data) < 100:
            return
        after = iso(data[-1]["created_utc"])   
        time.sleep(0.5)                       


def months(start, end):
    
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    while (y, m) <= (ye, me):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--subreddit", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM")
    ap.add_argument("--end", required=True, help="YYYY-MM")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for y, m in months(args.start, args.end):
        path = OUT_DIR / f"{args.subreddit}_{y}-{m:02d}.jsonl"
        if path.exists():
            print("skip", path.name)
            continue
        tmp = path.with_suffix(".tmp")
        n = 0
        with open(tmp, "w", encoding="utf-8") as f:
            for post in fetch_month(args.subreddit, y, m):
                f.write(json.dumps(post, ensure_ascii=False) + "\n")
                n += 1
        tmp.rename(path)
        print(f"done {path.name}: {n} posts")