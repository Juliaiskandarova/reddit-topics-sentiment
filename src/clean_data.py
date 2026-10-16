import hashlib
import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/processed")
SAMPLE = Path("data/sample")
OUT.mkdir(parents=True, exist_ok=True)

KEEP = ["id", "subreddit", "created_utc", "title", "selftext", "score",
        "num_comments", "link_flair_text", "author", "removed_by_category"]


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            rows.append({k: p.get(k) for k in KEEP})
    return pd.DataFrame(rows)


def short_hash(name):
    if not isinstance(name, str):
        return None
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]


log = []  # шаг

frames = []
for path in sorted(RAW.glob("*.jsonl")):
    print("reading", path.name)
    frames.append(load(path))
df = pd.concat(frames, ignore_index=True)
log.append(("raw", len(df)))

df = df.drop_duplicates("id")
log.append(("drop duplicates", len(df)))

df["title"] = df["title"].fillna("").str.strip()
df["selftext"] = df["selftext"].fillna("")
df = df[df["title"] != ""]
log.append(("drop empty title", len(df)))

df = df[~df["selftext"].isin(["[removed]", "[deleted]"])]
df = df[df["removed_by_category"].isna()]
log.append(("drop removed/deleted", len(df)))

df = df[df["author"] != "AutoModerator"]
log.append(("drop AutoModerator", len(df)))

# новые колонки
df["created_utc"] = pd.to_numeric(df["created_utc"], errors="coerce")
df = df.dropna(subset=["created_utc"])
df["created"] = pd.to_datetime(df["created_utc"].astype("int64"), unit="s", utc=True)
df["year"] = df["created"].dt.year
df["month"] = df["created"].dt.strftime("%Y-%m")
df["text"] = (df["title"] + "\n\n" + df["selftext"]).str.strip()
df["n_words"] = df["text"].str.split().str.len()
df["has_body"] = df["selftext"].str.strip() != ""


df["author_id"] = df["author"].map(short_hash)

final_cols = ["id", "subreddit", "created", "year", "month", "title",
              "selftext", "text", "n_words", "has_body", "score",
              "num_comments", "link_flair_text", "author_id"]
df = df[final_cols].reset_index(drop=True)

df.to_parquet(OUT / "posts_clean.parquet", index=False)
df.sample(min(200, len(df)), random_state=42).to_csv(
    SAMPLE / "posts_clean_sample.csv", index=False)
pd.DataFrame(log, columns=["step", "rows"]).to_csv(
    OUT / "cleaning_log.csv", index=False)

print("\n=== Cleaning log ===")
for step, n in log:
    print(f"{step:25s} {n:>9,}")
print("\n=== Posts by subreddit and year ===")
print(df.groupby(["subreddit", "year"]).size().unstack(fill_value=0))
print("\n=== Median words per post ===")
print(df.groupby("subreddit")["n_words"].median())