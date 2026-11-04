import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from utils import ui
from utils.auth import current_user
from utils.posters import get_posters
from utils.ratings import load_ratings, save_rating
from utils.recommender import get_recommender, search_movies, user_based_recommendations

st.set_page_config(page_title="Movie Recommendations", page_icon="⭐", layout="wide")
ui.inject_css()
st.title("⭐ Movie Recommendation System")

try:
    recommender = get_recommender(True)
except FileNotFoundError as exc:
    st.error(f"❌ {exc}")
    st.stop()
movies = recommender.movies  # same row order as the recommender matrix


# ----------------------------------------------------------------------
# Reusable pieces
# ----------------------------------------------------------------------
def movie_details(row: pd.Series) -> None:
    """Poster on the left, details on the right."""
    left, right = st.columns([1, 3])
    with left:
        ui.show_image(get_posters([row])[0])
    with right:
        year = f" ({int(row['year'])})" if pd.notna(row["year"]) else ""
        st.markdown(f'<p class="movie-title">{ui.esc(row["title"])}<span class="muted">{year}</span></p>',
                    unsafe_allow_html=True)
        st.markdown(ui.chips(row["genre_list"]) or '<span class="muted">Genre not available</span>',
                    unsafe_allow_html=True)

        facts = []
        if row["vote_count"] > 0 and pd.notna(row["vote_average"]):
            facts.append(f"⭐ {row['vote_average']:.1f} ({int(row['vote_count']):,} votes)")
        if pd.notna(row["runtime"]):
            facts.append(f"⏱ {int(row['runtime'])} min")
        if row["language"] != "Unknown":
            facts.append(f"🌍 {row['language']}")
        if pd.notna(row["revenue"]):
            facts.append(f"🏆 {ui.fmt_money(row['revenue'])} revenue")
        if pd.notna(row["box_office_cr"]):
            facts.append(f"💰 ₹{row['box_office_cr']:,.0f} Cr (your data)")
        if facts:
            st.write("  |  ".join(facts))

        if row["tagline"]:
            st.markdown(f"*{ui.md_escape(row['tagline'])}*")
        st.write(row["overview"] or "No description available for this movie.")
        if row["director"]:
            st.write(f"🎬 **Director:** {row['director'].replace('|', ', ')}")
        if row["cast"]:
            st.write(f"🎭 **Cast:** {row['cast'].replace('|', ', ')}")
        if row["source"] == "Custom":
            st.caption("This movie comes from your own list (data/movie_data.csv). It only has genre "
                       "information, so its recommendations are based on genre.")


def movie_grid(frame: pd.DataFrame, per_row: int = 5, show_score: bool = True, key_prefix: str = "rec") -> None:
    """Grid of poster cards with interactive click-to-recommend support."""
    rows = [r for _, r in frame.iterrows()]
    images = get_posters(rows)
    for start in range(0, len(rows), per_row):
        cols = st.columns(per_row)
        for col, row, img in zip(cols, rows[start:start + per_row], images[start:start + per_row]):
            with col:
                ui.show_image(img)
                year = f" ({int(row['year'])})" if pd.notna(row["year"]) else ""
                st.markdown(f"**{ui.md_escape(row['title'])}**{year}")
                st.caption(row["genres"].replace("|", ", ") or "—")
                line = []
                if row["vote_count"] > 0 and pd.notna(row["vote_average"]):
                    line.append(f"⭐ {row['vote_average']:.1f}")
                if show_score and "similarity" in row and pd.notna(row.get("similarity")):
                    line.append(f"🎯 {row['similarity']:.0f}/100 similar")
                if line:
                    st.write("  ·  ".join(line))
                if show_score and row.get("why"):
                    st.markdown(f'<div class="why">{ui.esc(row["why"])}</div>', unsafe_allow_html=True)

                # Interactive button to select this movie directly
                btn_key = f"{key_prefix}_{row['id']}_{row.name}"
                if st.button("🔍 View Similar", key=btn_key):
                    st.session_state["selected_idx"] = int(row.name)
                    st.rerun()
        st.write("")
# ----------------------------------------------------------------------
# 🔍 Search & select
# ----------------------------------------------------------------------
search = st.text_input("🔍 Search movie", placeholder="Type a movie name, e.g. dark knight")
matches = search_movies(movies, search)
if not matches:
    st.warning("No movie found. Check the spelling or try a shorter name.")
    st.stop()
if search:
    st.caption(f"{len(matches)} movie(s) found – pick one below.")

# 💡 FIX: Keep session state in sync with selectbox
if "selected_idx" not in st.session_state or st.session_state["selected_idx"] not in matches:
    st.session_state["selected_idx"] = matches[0]

def on_change_select():
    st.session_state["selected_idx"] = st.session_state["movie_dropdown_key"]

selected_idx = st.selectbox(
    "🎬 Select a movie",
    matches,
    index=matches.index(st.session_state["selected_idx"]),
    format_func=lambda i: movies.at[i, "display_title"],
    key="movie_dropdown_key",
    on_change=on_change_select
)

selected = movies.loc[st.session_state["selected_idx"]]

st.subheader("🎬 Selected Movie")
movie_details(selected)
st.divider()

# ----------------------------------------------------------------------
# 🎯 Content-based recommendations
# ----------------------------------------------------------------------
st.subheader("🎯 Similar Movies")
s1, s2, s3 = st.columns([1, 1, 2])
n_recs = s1.slider("How many?", 5, 20, 10)
min_votes = s2.slider("Minimum votes", 0, 2000, 0, step=50,
                      help="Raise this to hide obscure movies with very few votes.")
mode_label = s3.radio("Genre rule", ["Share at least one genre", "Contain ALL genres of this movie"],
                      horizontal=True)
genre_mode = "all" if mode_label.startswith("Contain") else "any"

recs = recommender.similar_to(int(selected_idx), n=n_recs, genre_mode=genre_mode, min_votes=min_votes)
if recs.empty:
    st.info("No similar movies found with these settings. Try 'Share at least one genre' "
            "or lower the minimum votes.")
else:
    movie_grid(recs, key_prefix="content_rec")

with st.expander("ℹ️ How are these movies chosen? (Tamil/Tanglish: epdi recommend panrom?)"):
    st.markdown("""
**Step by step**
1. Every movie is described by 4 things: **genres**, **keywords**, **people** (director + top 5 cast) and **story** (overview + tagline).

2. Each part is converted to numbers using **TF-IDF** – rare shared things (a director, a special keyword) count more than common ones (like "Drama").
3. The selected movie is compared with every other movie using **cosine similarity** (0 = nothing in common, 1 = identical).
4. Final score = genres 30% + keywords 25% + story 25% + people 20%.
5. A movie must **share a genre** with your selection, so an action movie gets action movies.
6. The selected movie itself and duplicate entries are removed. Best match is shown first.

**Ratings and box office are not used to decide similarity.** They only break exact ties.
Missing description / keywords / cast simply count as "no match" for that part – the app never crashes on them.

*Tamil: Genre, keywords, nadigar/director, kathai ellam compare panni, romba othu pora padangala mela kaattum. Rating vachu mattum choose panna maatom.*
""")

st.divider()

# ----------------------------------------------------------------------
# 👤 User-based recommendations (needs login)
# ----------------------------------------------------------------------
st.subheader("👤 User-Based Recommendations")
username = current_user()

if username is None:
    st.info("🔒 Login required for personalized recommendations (open the main page and log in).")
else:
    st.write(f"Rate **{selected['title']}** (1–5):")
    rating_input = st.slider("Your rating", 1, 5, 3)

    if st.button("Submit Rating"):
        try:
            save_rating(movies, username, int(selected["id"]), selected["title"], rating_input)
            st.success("Rating saved!")
        except OSError as exc:
            st.error(f"Could not save the rating: {exc}")

    ratings = load_ratings(movies)
    mine = ratings[ratings["UserID"] == username]
    if not mine.empty:
        with st.expander(f"Your ratings ({len(mine)})"):
            ui.show_df(mine[["MovieName", "Rating"]].rename(columns={"MovieName": "Movie"}))

    if st.button("🎯 Recommend Based on Users"):
        if mine.empty:
            st.warning("Rate at least one movie first 😶")
        else:
            scores = user_based_recommendations(ratings, username, n=10)
            if not scores.empty:
                st.subheader("🎬 Recommended Movies (users with similar taste)")
                found = movies[movies["id"].isin(scores.index)].copy()
                found["order"] = found["id"].map(scores)
                movie_grid(found.sort_values("order", ascending=False), show_score=False, key_prefix="user_rec")
            else:
                # Not enough other users yet -> fall back to content-based using your favourite movie
                st.info("No other user has rated the same movies yet, so here are movies similar to the "
                        "one you rated highest.")
                best = mine.dropna(subset=["MovieID"]).sort_values("Rating", ascending=False)
                fav = movies.index[movies["id"] == best.iloc[0]["MovieID"]] if not best.empty else []
                if len(fav):
                    st.write(f"Because you rated **{movies.at[fav[0], 'title']}** {int(best.iloc[0]['Rating'])}/5:")
                    movie_grid(recommender.similar_to(int(fav[0]), n=10), key_prefix="user_fav_rec")
                else:
                    st.warning("Not enough ratings to recommend 😶")