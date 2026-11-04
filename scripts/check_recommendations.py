"""Quick sanity test of the recommender (no Streamlit needed).
Run:  python scripts/check_recommendations.py "The Dark Knight" "Toy Story" "Avatar"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.data_loader import load_movies  # noqa: E402
from utils.recommender import MovieRecommender, search_movies  # noqa: E402

titles = sys.argv[1:] or ["The Dark Knight", "Toy Story", "The Conjuring", "Mad Max: Fury Road"]
rec = MovieRecommender(load_movies(True))
m = rec.movies

for t in titles:
    hits = search_movies(m, t, limit=1)
    if not hits:
        print(f"\n'{t}' not found")
        continue
    i = hits[0]
    out = rec.similar_to(i, n=8)
    assert m.at[i, "id"] not in out["id"].values, "selected movie must not recommend itself"
    assert out["display_title"].is_unique, "duplicates found"
    print(f"\n=== {m.at[i, 'display_title']}  [{m.at[i, 'genres']}]")
    for _, r in out.iterrows():
        print(f"  {r['similarity']:5.1f}  {r['display_title']:42s} {r['genres']}")
print("\nAll checks passed ✅")
