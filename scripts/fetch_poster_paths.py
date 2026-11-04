"""One-time step (needs internet + a free TMDB API key):
   downloads the poster path of every movie id into data/poster_paths.csv

   1. Create a free account on themoviedb.org -> Settings -> API -> copy the key
   2. Put it in .streamlit/secrets.toml :  TMDB_API_KEY = "your_key"
      (or set an environment variable TMDB_API_KEY)
   3. Run:  python scripts/fetch_poster_paths.py
You can stop and run again – movies that are already done are skipped.
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.data_loader import CLEAN_CSV  # noqa: E402
from utils.posters import POSTER_PATHS_CSV  # noqa: E402


def read_key():
    key = os.environ.get("TMDB_API_KEY")
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if not key and secrets.exists():
        try:
            import tomllib
            key = tomllib.loads(secrets.read_text(encoding="utf-8")).get("TMDB_API_KEY")
        except Exception:
            for line in secrets.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("TMDB_API_KEY"):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
    return key


def fetch(movie_id, key):
    headers, params = {}, {}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    else:
        params["api_key"] = key
    for attempt in range(4):
        try:
            r = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}",
                             headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                return movie_id, r.json().get("poster_path") or ""
            if r.status_code == 404:
                return movie_id, ""
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 2)))
            elif r.status_code == 401:
                sys.exit("TMDB rejected the API key (401). Please check TMDB_API_KEY.")
        except requests.RequestException:
            time.sleep(1 + attempt)
    return movie_id, None            # failed -> will be retried next run


def main():
    key = read_key()
    if not key:
        sys.exit("TMDB_API_KEY not found. Add it to .streamlit/secrets.toml or set it as an environment variable.")
    ids = pd.read_csv(CLEAN_CSV)["id"].tolist()
    done = {}
    if POSTER_PATHS_CSV.exists():
        old = pd.read_csv(POSTER_PATHS_CSV)
        done = {int(i): ("" if pd.isna(p) else p) for i, p in zip(old["id"], old["poster_path"])}
    todo = [i for i in ids if i not in done]
    print(f"{len(done)} already done, {len(todo)} to fetch...")

    with ThreadPoolExecutor(max_workers=8) as pool:
        for n, (mid, path) in enumerate(pool.map(lambda i: fetch(i, key), todo), 1):
            if path is not None:
                done[mid] = path
            if n % 200 == 0 or n == len(todo):
                pd.DataFrame({"id": list(done), "poster_path": list(done.values())}).to_csv(
                    POSTER_PATHS_CSV, index=False)
                print(f"  {n}/{len(todo)}")
    found = sum(1 for p in done.values() if p)
    print(f"Done. Posters found for {found} of {len(done)} movies -> {POSTER_PATHS_CSV}")


if __name__ == "__main__":
    main()
