"""Fail if anything confidential is tracked or staged: the data pack, derived outputs, secrets, raw tables.

    python scripts/check_repo_safety.py            # check all tracked files (CI)
    python scripts/check_repo_safety.py --staged   # check staged files (pre-commit hook)
"""
from __future__ import annotations

import re
import subprocess
import sys

BLOCKED_PATHS = re.compile(r"^(data/|outputs/|\.env$|\.streamlit/secrets\.toml$|.*\.(csv|parquet|xlsx|xls|zip|pkl|pickle)$)")
ALLOWED = {".streamlit/secrets.toml.example"}
SECRET = re.compile(r"(APP_PASSWORD\s*=\s*['\"](?!choose-a-strong-password)[^'\"]{4,}|GEMINI_API_KEY\s*=\s*\S{10,}|"
                    r"GROQ_API_KEY\s*=\s*\S{10,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})")
MAX_BYTES = 2_000_000
# showcase/ = aggregates-only results export (pressure/showcase.py). Its parquet tables are allowed, but only after a
# content check: no ball/delivery identifier columns and no table large enough to be row-level data.
SHOWCASE_OK = re.compile(r"^showcase/[^/]+\.parquet$")
SHOWCASE_BANNED = {"innings_ball_num", "over_ball_num", "overid", "delivery_ist_time", "striker_id", "non_striker_id",
                   "bowler_id", "bowl_speed", "stroke", "delivery_style", "dismissed_player_id", "wp_before", "wp_after",
                   "match_id"}
SHOWCASE_MAX_ROWS = 50_000


def showcase_problem(f: str, blob: bytes) -> str | None:
    import io
    try:
        import pandas as pd
    except ImportError:
        return f"{f}: cannot vet showcase tables without pandas - run pip install -r requirements.txt first"
    try:
        d = pd.read_parquet(io.BytesIO(blob))
    except Exception:  # noqa: BLE001
        return f"{f}: unreadable parquet in showcase/"
    if set(d.columns) & SHOWCASE_BANNED:
        return f"{f}: row-level columns {sorted(set(d.columns) & SHOWCASE_BANNED)}"
    if len(d) > SHOWCASE_MAX_ROWS:
        return f"{f}: {len(d):,} rows - too many for an aggregates-only export"
    return None


def files(staged: bool) -> list[str]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged else ["git", "ls-files"]
    return [f for f in subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines() if f]


def main() -> int:
    staged = "--staged" in sys.argv
    bad = []
    for f in files(staged):
        if f in ALLOWED:
            continue
        showcase = bool(SHOWCASE_OK.match(f))
        if BLOCKED_PATHS.match(f) and not showcase:
            bad.append(f"{f}: confidential path or raw table type")
            continue
        try:
            if staged:
                blob = subprocess.run(["git", "show", f":{f}"], capture_output=True, check=True).stdout
            else:
                with open(f, "rb") as fh:          # plain Python read: works on Windows, macOS and Linux
                    blob = fh.read()
        except (subprocess.CalledProcessError, OSError):
            continue
        if len(blob) > MAX_BYTES:
            bad.append(f"{f}: larger than 2 MB (data?)")
        elif showcase and (why := showcase_problem(f, blob)):
            bad.append(why)
        elif SECRET.search(blob.decode("utf-8", "ignore")):
            bad.append(f"{f}: looks like it contains a secret")
    if bad:
        print("BLOCKED - confidential content would be committed:\n  " + "\n  ".join(bad))
        return 1
    print(f"ok - {'staged' if staged else 'tracked'} files are clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
