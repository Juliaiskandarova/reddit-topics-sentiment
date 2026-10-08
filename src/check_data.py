import json, sys
from collections import Counter
from datetime import datetime, timezone

path = sys.argv[1]
n, years, keys = 0, Counter(), Counter()
first, last = None, None
with open(path, encoding="utf-8") as f:
    for line in f:
        post = json.loads(line)
        n += 1
        keys.update(post.keys())
        ts = int(post["created_utc"])
        first = ts if first is None else min(first, ts)
        last = ts if last is None else max(last, ts)
        years[datetime.fromtimestamp(ts, tz=timezone.utc).year] += 1

fmt = lambda t: datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
print("posts:", n)
print("period:", fmt(first), "->", fmt(last))
print("by year:", dict(sorted(years.items())))
print("fields:", len(keys))