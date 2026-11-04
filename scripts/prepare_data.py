"""One-time step: clean the Kaggle TMDB files and save data/movies_clean.csv

Run from the project folder:   python scripts/prepare_data.py
Put tmdb_5000_movies.csv and tmdb_5000_credits.csv in data/raw/ first.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.data_loader import CLEAN_CSV, RAW_DIR, build_clean_dataset  # noqa: E402


def main():
    movies_f = RAW_DIR / "tmdb_5000_movies.csv"
    credits_f = RAW_DIR / "tmdb_5000_credits.csv"
    for f in (movies_f, credits_f):
        if not f.exists():
            sys.exit(f"Missing file: {f}\nCopy the two Kaggle CSV files into data/raw/ and try again.")

    movies, credits = pd.read_csv(movies_f), pd.read_csv(credits_f)
    clean = build_clean_dataset(movies, credits)
    clean.to_csv(CLEAN_CSV, index=False)

    print(f"Raw movies            : {len(movies)}")
    print(f"Clean movies saved    : {len(clean)}  ->  {CLEAN_CSV}")
    print(f"Removed (not released): {(movies['status'] != 'Released').sum()}")
    print(f"Missing genres        : {(clean['genres'] == '').sum()}")
    print(f"Missing keywords      : {(clean['keywords'] == '').sum()}")
    print(f"Missing overview      : {(clean['overview'] == '').sum()}")
    print(f"Missing director      : {(clean['director'] == '').sum()}")
    print(f"Unknown budget/revenue: {clean['budget'].isna().sum()} / {clean['revenue'].isna().sum()}")


if __name__ == "__main__":
    main()
