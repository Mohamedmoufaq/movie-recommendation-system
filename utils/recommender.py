"""Content-based movie recommender (TF-IDF + cosine similarity).

How it works (short):
 1. For every movie we build 4 "text blocks": genres, keywords, people (director + top cast),
    and story (overview + tagline).
 2. Each block is turned into TF-IDF numbers (rare shared words/names count more).
 3. Blocks are weighted and joined into one vector per movie.
 4. Similarity = weighted sum of the cosine similarity of each block (0-100 score).
 5. Ratings / votes are NOT used for similarity – only to break exact ties.
"""
from __future__ import annotations

import re
from difflib import get_close_matches

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .compat import cache_resource
from .data_loader import load_movies

# How much each block matters (sum = 1.0)
WEIGHTS = {"genres": 0.30, "keywords": 0.25, "story": 0.25, "people": 0.20}


def _slug(text: str) -> str:
    """'Science Fiction' -> 'science_fiction' (one token, so phrases stay together)."""
    return re.sub(r"\W+", "_", text.lower()).strip("_")


def _person(text: str) -> str:
    """'Sam Worthington' -> 'samworthington' so first names alone never match."""
    return re.sub(r"\W+", "", text.lower())


def _block(texts, **kwargs):
    """TF-IDF for one block. Returns an all-zero matrix if the block is completely empty."""
    try:
        return TfidfVectorizer(**kwargs).fit_transform(texts)
    except ValueError:  # "empty vocabulary"
        from scipy.sparse import csr_matrix
        return csr_matrix((len(texts), 1))


class MovieRecommender:
    def __init__(self, movies: pd.DataFrame):
        self.movies = movies.reset_index(drop=True)
        m = self.movies

        genres_txt = m["genre_list"].map(lambda xs: " ".join(_slug(x) for x in xs))
        keywords_txt = m["keyword_list"].map(lambda xs: " ".join(_slug(x) for x in xs))
        people_txt = [
            " ".join([_person(d) for d in dirs] * 2 + [_person(c) for c in cast])
            for dirs, cast in zip(m["director_list"], m["cast_list"])
        ]
        story_txt = (m["overview"].fillna("") + " " + m["tagline"].fillna("")).str.strip()

        token = r"[^ ]+"
        blocks = {
            "genres": _block(genres_txt, token_pattern=token, lowercase=False),
            "keywords": _block(keywords_txt, token_pattern=token, lowercase=False, min_df=2),
            "people": _block(people_txt, token_pattern=token, lowercase=False, min_df=2),
            "story": _block(story_txt, stop_words="english", ngram_range=(1, 2), min_df=2,
                            max_df=0.5, sublinear_tf=True, max_features=50000),
        }
        # sqrt(weight) so that the final cosine = weighted sum of the block cosines
        # NOTE: we do NOT re-normalise rows. A movie with missing info (e.g. a custom movie that
        # only has genres) simply scores 0 for the missing blocks instead of being inflated.
        self.X = hstack([blocks[k] * np.sqrt(w) for k, w in WEIGHTS.items()]).tocsr()

        # Binary genre matrix – used for the "must share a genre" rule
        self.G = CountVectorizer(token_pattern=token, lowercase=False, binary=True).fit_transform(
            genres_txt) if genres_txt.str.len().sum() else None

        self.ids = m["id"].to_numpy()
        self.votes = m["vote_count"].fillna(0).to_numpy()
        self.wr = m["weighted_rating"].fillna(0).to_numpy()
        self.dup_key = (m["title_key"] + "|" + m["year"].astype("string").fillna("")).to_numpy()
        self.genre_sets = [set(x) for x in m["genre_list"]]
        self.keyword_sets = [set(x) for x in m["keyword_list"]]
        self.cast_sets = [set(x) for x in m["cast_list"]]
        self.director_sets = [set(x) for x in m["director_list"]]

    # ------------------------------------------------------------------
    def similar_to(self, idx: int, n: int = 10, genre_mode: str = "any",
                   min_votes: int = 0) -> pd.DataFrame:
        """Top-n movies most similar to row `idx`.

        genre_mode: "any" -> must share at least one genre with the selected movie
                    "all" -> must contain ALL genres of the selected movie
        """
        sims = (self.X @ self.X[idx].T).toarray().ravel()

        ok = np.ones(len(sims), dtype=bool)
        ok &= self.ids != self.ids[idx]                 # never recommend the movie itself
        ok &= self.dup_key != self.dup_key[idx]         # nor a duplicate entry of it
        ok &= self.votes >= min_votes
        ok &= sims > 0

        if self.genre_sets[idx] and self.G is not None:
            overlap = (self.G @ self.G[idx].T).toarray().ravel()
            need = len(self.genre_sets[idx]) if genre_mode == "all" else 1
            ok &= overlap >= need

        cand = np.flatnonzero(ok)
        if cand.size == 0:
            return self.movies.iloc[0:0].assign(similarity=[], why=[])

        # Best similarity first; exact ties (to 3 decimals) -> better weighted rating first
        order = cand[np.lexsort((-self.wr[cand], -np.round(sims[cand], 3)))]

        picked, seen = [], set()
        for j in order:
            if self.dup_key[j] in seen:
                continue
            seen.add(self.dup_key[j])
            picked.append(j)
            if len(picked) == n:
                break

        out = self.movies.iloc[picked].copy()
        out["similarity"] = np.round(sims[picked] * 100, 1)
        out["why"] = [self._why(idx, j) for j in picked]
        return out

    def _why(self, a: int, b: int) -> str:
        parts = []
        g = [x for x in self.movies.at[a, "genre_list"] if x in self.genre_sets[b]]
        if g:
            parts.append("genres: " + ", ".join(g))
        k = [x for x in self.movies.at[a, "keyword_list"] if x in self.keyword_sets[b]][:3]
        if k:
            parts.append("keywords: " + ", ".join(k))
        d = [x for x in self.movies.at[a, "director_list"] if x in self.director_sets[b]]
        if d:
            parts.append("director: " + ", ".join(d))
        c = [x for x in self.movies.at[a, "cast_list"] if x in self.cast_sets[b]][:2]
        if c:
            parts.append("cast: " + ", ".join(c))
        return "Shared " + " | ".join(parts) if parts else "Similar story / theme"


@cache_resource(show_spinner="Building recommendation engine...")
def get_recommender(include_custom: bool = True) -> MovieRecommender:
    return MovieRecommender(load_movies(include_custom))


# ----------------------------------------------------------------------
# Search
# ----------------------------------------------------------------------
def search_movies(movies: pd.DataFrame, query: str, limit: int | None = None) -> list[int]:
    """Return row positions of matching movies.
    Empty query -> everything, most popular first.
    Otherwise exact word/substring matches first, then spelling-tolerant matches."""
    pop = movies["popularity"].fillna(0)
    q = (query or "").strip().lower()
    if not q:
        idx = pop.sort_values(ascending=False).index.tolist()
        return idx[:limit] if limit else idx

    titles = movies["title_key"]
    contains = titles.str.contains(re.escape(q), regex=True)
    starts = titles.str.startswith(q)
    hits = movies[contains].assign(_s=starts[contains].astype(int), _p=pop[contains])
    hits = hits.sort_values(["_s", "_p"], ascending=False)
    result = hits.index.tolist()

    if not result:  # typo-tolerant fallback (e.g. "avtar" -> "Avatar")
        lookup = {}
        for i, t in titles.items():
            lookup.setdefault(t, []).append(i)
        for t in get_close_matches(q, list(lookup), n=15, cutoff=0.55):
            result.extend(lookup[t])
    return result[:limit] if limit else result


# ----------------------------------------------------------------------
# User-based recommendations (kept from the original project)
# ----------------------------------------------------------------------
def user_based_recommendations(ratings: pd.DataFrame, user_id: str, n: int = 10,
                               k_users: int = 5) -> pd.Series:
    """Movies liked by users whose ratings look like yours. Returns Series: MovieID -> score."""
    r = ratings.dropna(subset=["MovieID"]).copy()
    if r.empty or user_id not in set(r["UserID"]):
        return pd.Series(dtype=float)
    r["MovieID"] = r["MovieID"].astype(int)

    matrix = r.pivot_table(index="UserID", columns="MovieID", values="Rating", aggfunc="mean")
    sim = cosine_similarity(matrix.fillna(0))
    sim = pd.Series(sim[matrix.index.get_loc(user_id)], index=matrix.index).drop(user_id)
    sim = sim[sim > 0].nlargest(k_users)           # >0 means you share at least one movie
    if sim.empty:
        return pd.Series(dtype=float)

    mine = set(r.loc[r["UserID"] == user_id, "MovieID"])
    others = r[r["UserID"].isin(sim.index) & ~r["MovieID"].isin(mine)].copy()
    others["score"] = others["UserID"].map(sim) * others["Rating"]
    return others.groupby("MovieID")["score"].sum().sort_values(ascending=False).head(n)
