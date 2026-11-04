"""Read / write data/user_movie_ratings.csv.

Columns: UserID, MovieName, Rating, MovieID
Old rows that have no MovieID are matched to a movie by title (case-insensitive)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data_loader import DATA_DIR

RATINGS_CSV = DATA_DIR / "user_movie_ratings.csv"
COLUMNS = ["UserID", "MovieName", "Rating", "MovieID"]


def _title_to_id(movies: pd.DataFrame) -> pd.Series:
    best = movies.sort_values("vote_count", ascending=False).drop_duplicates("title_key")
    return pd.Series(best["id"].values, index=best["title_key"].values)


def load_ratings(movies: pd.DataFrame) -> pd.DataFrame:
    try:
        r = pd.read_csv(RATINGS_CSV)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        r = pd.DataFrame(columns=COLUMNS)
    for col in COLUMNS:
        if col not in r:
            r[col] = np.nan
    r = r[COLUMNS].copy()
    r["UserID"] = r["UserID"].fillna("").astype(str).str.strip()
    r["MovieName"] = r["MovieName"].fillna("").astype(str).str.strip()
    r["Rating"] = pd.to_numeric(r["Rating"], errors="coerce")
    r = r[(r["UserID"] != "") & r["Rating"].notna()].reset_index(drop=True)  # drops blank-user rows

    # Convert MovieID to nullable Int64 type before assignment to prevent LossySetitemError
    r["MovieID"] = pd.to_numeric(r["MovieID"], errors="coerce").astype("Int64")

    missing = r["MovieID"].isna()
    if missing.any():
        mapped_ids = r.loc[missing, "MovieName"].str.lower().map(_title_to_id(movies))
        r.loc[missing, "MovieID"] = pd.to_numeric(mapped_ids, errors="coerce").astype("Int64")

    return r


def save_rating(movies: pd.DataFrame, user_id: str, movie_id: int, title: str, rating: int) -> None:
    r = load_ratings(movies)
    same = (r["UserID"] == user_id) & (r["MovieID"] == movie_id)
    if same.any():
        r.loc[same, ["Rating", "MovieName"]] = [rating, title]
    else:
        r = pd.concat([r, pd.DataFrame([{"UserID": user_id, "MovieName": title,
                                         "Rating": rating, "MovieID": movie_id}])],
                      ignore_index=True)
    r["MovieID"] = pd.to_numeric(r["MovieID"], errors="coerce").astype("Int64")
    r.to_csv(RATINGS_CSV, index=False)