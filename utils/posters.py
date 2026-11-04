"""Poster lookup – always the poster of the SAME movie.

Order used for every movie:
  1. local file in posters/            (your custom movies)
  2. data/poster_paths.csv             (movie id -> TMDB poster_path, built by scripts/fetch_poster_paths.py)
  3. live TMDB API lookup by movie id  (only if TMDB_API_KEY is set; result is remembered)
  4. generated "No Poster" image       (never a random or wrong poster)

The image is downloaded by the server and checked, so a broken URL can never show a broken icon.
"""
from __future__ import annotations

import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont

from .compat import get_secret
from .data_loader import DATA_DIR

IMG_BASE = "https://image.tmdb.org/t/p/w342"
POSTER_PATHS_CSV = DATA_DIR / "poster_paths.csv"
LEARNED_JSON = DATA_DIR / "poster_cache.json"   # paths learned while the app runs

_lock = threading.Lock()
_path_map: dict[int, str] | None = None
_img_cache: dict[str, bytes | None] = {}
_fallback_cache: dict[str, bytes] = {}


def _load_path_map() -> dict[int, str]:
    global _path_map
    if _path_map is None:
        m: dict[int, str] = {}
        if POSTER_PATHS_CSV.exists():
            df = pd.read_csv(POSTER_PATHS_CSV).dropna(subset=["poster_path"])
            m.update({int(i): str(p) for i, p in zip(df["id"], df["poster_path"]) if str(p).startswith("/")})
        if LEARNED_JSON.exists():
            try:
                m.update({int(k): v for k, v in json.loads(LEARNED_JSON.read_text()).items() if v})
            except (ValueError, OSError):
                pass
        _path_map = m
    return _path_map


def _api_key() -> str | None:
    return get_secret("TMDB_API_KEY")


def _tmdb_lookup(movie_id: int, key: str) -> str | None:
    """Ask TMDB for the poster path of exactly this movie id."""
    headers, params = {}, {}
    if key.startswith("eyJ"):                      # v4 "read access token"
        headers["Authorization"] = f"Bearer {key}"
    else:                                          # v3 API key
        params["api_key"] = key
    try:
        resp = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}",
                            headers=headers, params=params, timeout=6)
        if resp.status_code != 200:
            return None
        path = resp.json().get("poster_path")
    except (requests.RequestException, ValueError):
        return None
    if path:
        with _lock:
            _load_path_map()[movie_id] = path
            try:
                LEARNED_JSON.write_text(json.dumps(_load_path_map()))
            except OSError:
                pass
    return path


def poster_url(movie_id: int, key: str | None) -> str | None:
    if movie_id is None or movie_id <= 0:           # custom movies have no TMDB id
        return None
    path = _load_path_map().get(int(movie_id))
    if not path and key:
        path = _tmdb_lookup(int(movie_id), key)
    return f"{IMG_BASE}{path}" if path else None


def _download(url: str) -> bytes | None:
    """Download and VALIDATE an image. Returns None for anything broken."""
    if url in _img_cache:
        return _img_cache[url]
    data = None
    try:
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            Image.open(io.BytesIO(resp.content)).verify()
            data = resp.content
    except (requests.RequestException, OSError, ValueError):
        data = None
    if data is not None:                            # only remember successes (retry failures later)
        if len(_img_cache) > 1500:
            _img_cache.pop(next(iter(_img_cache)))
        _img_cache[url] = data
    return data


def fallback_poster(title: str) -> bytes:
    """A neat 'No Poster' card generated locally (no internet needed)."""
    if title in _fallback_cache:
        return _fallback_cache[title]
    w, h = 300, 450
    img = Image.new("RGB", (w, h), "#1C222B")
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, w - 11, h - 11], outline="#3A4250", width=2)
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:                               # very old Pillow
        font = ImageFont.load_default()
    lines, line = [], ""
    for word in str(title).split():
        trial = f"{line} {word}".strip()
        if d.textlength(trial, font=font) > w - 50 and line:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    y = h // 2 - 12 * len(lines) - 20
    for ln in lines[:5]:
        d.text(((w - d.textlength(ln, font=font)) / 2, y), ln, fill="#E6E8EB", font=font)
        y += 28
    note = "No poster available"
    d.text(((w - d.textlength(note, font=font)) / 2, y + 16), note, fill="#8B94A3", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    _fallback_cache[title] = buf.getvalue()
    return _fallback_cache[title]


def get_poster(row, key: str | None = None):
    """Image for one movie row: a file path (str) or image bytes."""
    local = row.get("poster_local", "")
    if isinstance(local, str) and local and Path(local).exists():
        return local
    url = poster_url(row.get("id"), key if key is not None else _api_key())
    data = _download(url) if url else None
    return data if data else fallback_poster(row.get("title", "Unknown"))


def get_posters(rows: list) -> list:
    """Posters for many movies at once (downloaded in parallel, so pages stay fast)."""
    key = _api_key()                                # read secrets on the main thread
    _load_path_map()                                # load the id->path table once, before threads start
    if len(rows) <= 1:
        return [get_poster(r, key) for r in rows]
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda r: get_poster(r, key), rows))
