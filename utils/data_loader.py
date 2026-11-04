"""Load, clean and merge the movie data.

Main source : TMDB 5000 (Kaggle)  ->  data/movies_clean.csv  (built by scripts/prepare_data.py)
Extra source: your own hand-made list -> data/movie_data.csv  (kept as "Custom" movies)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .compat import cache_data

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_CSV = DATA_DIR / "movies_clean.csv"
CUSTOM_CSV = DATA_DIR / "movie_data.csv"

LANGUAGE_NAMES = {
    "en": "English", "fr": "French", "es": "Spanish", "zh": "Chinese", "de": "German",
    "hi": "Hindi", "ja": "Japanese", "it": "Italian", "cn": "Cantonese", "ko": "Korean",
    "ru": "Russian", "pt": "Portuguese", "ta": "Tamil", "te": "Telugu", "ml": "Malayalam",
    "bn": "Bengali", "sv": "Swedish", "da": "Danish", "nl": "Dutch", "pl": "Polish",
    "th": "Thai", "he": "Hebrew", "ar": "Arabic", "fa": "Persian", "tr": "Turkish",
    "cs": "Czech", "id": "Indonesian", "hu": "Hungarian", "el": "Greek", "no": "Norwegian",
    "fi": "Finnish", "ro": "Romanian", "is": "Icelandic", "xx": "No language",
}

CLEAN_COLUMNS = [
    "id", "title", "year", "release_date", "genres", "keywords", "cast", "director",
    "overview", "tagline", "original_language", "runtime", "budget", "revenue",
    "popularity", "vote_average", "vote_count",
]


# ----------------------------------------------------------------------------
# Small parsing helpers
# ----------------------------------------------------------------------------
def _clean_text(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _json_items(text) -> list:
    try:
        items = json.loads(text)
    except (TypeError, ValueError):
        return []
    return items if isinstance(items, list) else []


def _names(text, limit=None) -> list[str]:
    out = []
    for item in _json_items(text):
        if isinstance(item, dict) and item.get("name"):
            name = _clean_text(item["name"])
            if name and name not in out:
                out.append(name)
    return out[:limit] if limit else out


def _directors(text) -> list[str]:
    out = []
    for item in _json_items(text):
        if isinstance(item, dict) and item.get("job") == "Director" and item.get("name"):
            name = _clean_text(item["name"])
            if name and name not in out:
                out.append(name)
    return out


def _pipe_to_list(value) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    return [p.strip() for p in value.split("|") if p.strip()]


# ----------------------------------------------------------------------------
# 1) Clean the raw TMDB files (used by scripts/prepare_data.py)
# ----------------------------------------------------------------------------
def build_clean_dataset(movies: pd.DataFrame, credits: pd.DataFrame) -> pd.DataFrame:
    """Merge movies + credits and return one tidy table (one row per movie)."""
    credits = credits.rename(columns={"movie_id": "id"})[["id", "cast", "crew"]]
    df = movies.merge(credits, on="id", how="left")
    df = df.drop_duplicates(subset="id")

    df["title"] = df["title"].map(_clean_text)
    df = df[df["title"] != ""]

    # Only released movies have real ratings (drops "Rumored" / "Post Production")
    df = df[df["status"] == "Released"].copy()

    release = pd.to_datetime(df["release_date"], errors="coerce")
    df["release_date"] = release.dt.strftime("%Y-%m-%d")
    df["year"] = release.dt.year.astype("Int64")

    # 0 in these columns means "unknown", NOT a real zero -> make them blank
    for col in ["budget", "revenue", "runtime"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").replace(0, np.nan)

    df["vote_count"] = pd.to_numeric(df["vote_count"], errors="coerce").fillna(0).astype(int)
    df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce")
    df.loc[(df["vote_count"] == 0) | (df["vote_average"] == 0), "vote_average"] = np.nan
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce")

    df["genres"] = df["genres"].map(lambda s: "|".join(_names(s)))
    df["keywords"] = df["keywords"].map(lambda s: "|".join(_names(s)))
    df["cast"] = df["cast"].map(lambda s: "|".join(_names(s, limit=5)))
    df["director"] = df["crew"].map(lambda s: "|".join(_directors(s)))
    df["overview"] = df["overview"].map(_clean_text)
    df["tagline"] = df["tagline"].map(_clean_text)

    # Same title + same year = same movie -> keep the one with more votes
    df["_key"] = df["title"].str.lower()
    df = df.sort_values("vote_count", ascending=False)
    df = df.drop_duplicates(subset=["_key", "year"]).drop(columns="_key")

    return df[CLEAN_COLUMNS].sort_values("id").reset_index(drop=True)


# ----------------------------------------------------------------------------
# 2) Custom (hand-made) movies
# ----------------------------------------------------------------------------
def resolve_local_poster(relative_path) -> str:
    """Find a poster in posters/ ignoring upper/lower case (Windows vs Linux safe)."""
    if not isinstance(relative_path, str) or not relative_path.strip():
        return ""
    path = ROOT / relative_path.strip()
    if path.exists():
        return str(path)
    if path.parent.exists():
        for f in path.parent.iterdir():
            if f.name.lower() == path.name.lower():
                return str(f)
    return ""


def _nice_title(text: str) -> str:
    text = _clean_text(text).replace("_", " ")
    return " ".join(w[:1].upper() + w[1:] for w in text.split(" "))


def load_custom_movies(exclude_titles: set[str] | None = None) -> pd.DataFrame:
    """Read data/movie_data.csv (your own list) and convert it to the same columns."""
    exclude_titles = exclude_titles or set()
    if not CUSTOM_CSV.exists():
        return pd.DataFrame()
    raw = pd.read_csv(CUSTOM_CSV, encoding="utf-8-sig")
    raw.columns = [c.strip() for c in raw.columns]
    if "MovieName" not in raw.columns:
        return pd.DataFrame()

    box = (raw.get("BoxOffice", pd.Series(dtype=str)).astype(str)
           .str.replace("Cr", "", regex=False).str.replace("₹", "", regex=False)
           .str.replace(",", "", regex=False))

    out = pd.DataFrame({
        "title": raw["MovieName"].map(_nice_title),
        "year": pd.to_numeric(raw.get("Year"), errors="coerce").astype("Int64"),
        "genres": raw.get("Genre", pd.Series([""] * len(raw))).map(
            lambda g: "|".join(dict.fromkeys(
                x.strip()[:1].upper() + x.strip()[1:] for x in str(g).split("/")
                if x.strip() and str(g) != "nan"))),
        "vote_average": pd.to_numeric(raw.get("Rating"), errors="coerce"),
        "vote_count": pd.to_numeric(raw.get("Votes"), errors="coerce").fillna(0).astype(int),
        "box_office_cr": pd.to_numeric(box, errors="coerce"),
        "poster_local": raw.get("PosterPath", pd.Series([""] * len(raw))).map(resolve_local_poster),
    })
    out = out[out["title"] != ""]
    # If TMDB already has this movie, trust TMDB (real data) and skip the hand-made row
    out = out[~out["title"].str.lower().isin(exclude_titles)].reset_index(drop=True)
    out.insert(0, "id", [-(i + 1) for i in range(len(out))])  # negative ids = custom movies
    return out


# ----------------------------------------------------------------------------
# 3) Final table used by every page
# ----------------------------------------------------------------------------
def add_weighted_rating(df: pd.DataFrame, quantile: float = 0.80) -> pd.DataFrame:
    """IMDB-style weighted rating: movies with very few votes are pulled toward the
    average, so a 10.0 from 1 voter cannot beat an 8.5 from 10,000 voters."""
    rated = df[df["vote_count"] > 0]
    c = rated["vote_average"].mean()
    m = rated["vote_count"].quantile(quantile)
    v, r = df["vote_count"], df["vote_average"]
    wr = (v / (v + m)) * r + (m / (v + m)) * c
    df["weighted_rating"] = wr.where(v > 0)
    return df


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["keywords", "cast", "director", "overview", "tagline", "original_language",
                "genres", "poster_local"]:
        if col not in df:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    for col in ["runtime", "budget", "revenue", "popularity", "box_office_cr"]:
        if col not in df:
            df[col] = np.nan
    if "source" not in df:
        df["source"] = "TMDB"

    df["genre_list"] = df["genres"].map(_pipe_to_list)
    df["keyword_list"] = df["keywords"].map(_pipe_to_list)
    df["cast_list"] = df["cast"].map(_pipe_to_list)
    df["director_list"] = df["director"].map(_pipe_to_list)
    df["title_key"] = df["title"].str.lower().str.strip()
    df["language"] = (df["original_language"].map(lambda c: LANGUAGE_NAMES.get(c, c.upper() if c else "Unknown"))
                      .replace("", "Unknown"))
    df["display_title"] = [f"{t} ({int(y)})" if pd.notna(y) else t
                           for t, y in zip(df["title"], df["year"])]
    return df


@cache_data(show_spinner="Loading movie data...")
def load_movies(include_custom: bool = True) -> pd.DataFrame:
    """Return the full movie table. Row order is stable (used by the recommender)."""
    if CLEAN_CSV.exists():
        tmdb = pd.read_csv(CLEAN_CSV)
    else:
        movies_f, credits_f = RAW_DIR / "tmdb_5000_movies.csv", RAW_DIR / "tmdb_5000_credits.csv"
        if not (movies_f.exists() and credits_f.exists()):
            raise FileNotFoundError(
                "data/movies_clean.csv not found. Put tmdb_5000_movies.csv and "
                "tmdb_5000_credits.csv in data/raw/ and run:  python scripts/prepare_data.py")
        tmdb = build_clean_dataset(pd.read_csv(movies_f), pd.read_csv(credits_f))

    tmdb["year"] = tmdb["year"].astype("Int64")
    tmdb["source"] = "TMDB"
    frames = [tmdb]

    if include_custom:
        custom = load_custom_movies(exclude_titles=set(tmdb["title"].str.lower().str.strip()))
        if not custom.empty:
            custom["source"] = "Custom"
            frames.append(custom)

    df = pd.concat(frames, ignore_index=True)
    df = _finalize(df)
    df = add_weighted_rating(df)
    return df.reset_index(drop=True)


def explode_list(df: pd.DataFrame, column: str, new_name: str) -> pd.DataFrame:
    """One row per (movie, item) – used for genre / actor / director charts."""
    out = df.assign(**{new_name: df[column]}).explode(new_name)
    return out[out[new_name].notna() & (out[new_name] != "")]
