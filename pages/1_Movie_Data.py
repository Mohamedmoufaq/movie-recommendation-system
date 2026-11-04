import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from utils import ui
from utils.data_loader import explode_list, load_movies

st.set_page_config(page_title="Movie Data Explorer", page_icon="📄", layout="wide")
ui.inject_css()
st.title("📄 Movie Data Explorer")

SORT_OPTIONS = {
    "Rating": "vote_average",
    "Votes": "vote_count",
    "Weighted Rating": "weighted_rating",
    "Popularity": "popularity",
    "Release Year": "year",
    "Revenue (USD)": "revenue",
}

try:
    include_custom = st.sidebar.checkbox(
        "Include my custom movies", value=True,
        help="Your hand-made list from data/movie_data.csv (movies not in the TMDB dataset).")
    df = load_movies(include_custom)
except FileNotFoundError as exc:
    st.error(f"❌ {exc}")
    st.stop()

# ===============================
# 🔍 Search & Filter Section
# ===============================
st.subheader("🔎 Search & Filter Movies")

c1, c2 = st.columns([2, 3])
search_text = c1.text_input("Search movie by name")
all_genres = sorted(explode_list(df, "genre_list", "g")["g"].unique())
selected_genres = c2.multiselect("Filter by Genre (movie must have ALL selected)", all_genres)

c3, c4, c5 = st.columns([2, 2, 3])
sort_label = c3.selectbox("Sort movies by", list(SORT_OPTIONS))
sort_order = c4.radio("Sort order", ["Descending", "Ascending"], horizontal=True)
min_votes = c5.slider("Minimum votes", 0, 5000, 0, step=10)

# ===============================
# 🧠 Apply Filters
# ===============================
filtered = df[df["vote_count"] >= min_votes]

if search_text:
    filtered = filtered[filtered["title"].str.contains(search_text, case=False, na=False, regex=False)]

if selected_genres:
    wanted = set(selected_genres)
    filtered = filtered[filtered["genre_list"].map(lambda g: wanted.issubset(g))]

filtered = filtered.sort_values(SORT_OPTIONS[sort_label], ascending=(sort_order == "Ascending"),
                                na_position="last").reset_index(drop=True)

# ===============================
# 📊 Display Result
# ===============================
table = pd.DataFrame({
    "S.No": filtered.index + 1,
    "Movie": filtered["title"],
    "Year": filtered["year"],
    "Genres": filtered["genres"].str.replace("|", ", ", regex=False),
    "Rating": filtered["vote_average"].round(1),
    "Votes": filtered["vote_count"],
    "Weighted Rating": filtered["weighted_rating"].round(2),
    "Popularity": filtered["popularity"].round(1),
    "Runtime (min)": filtered["runtime"],
    "Budget (USD)": filtered["budget"],
    "Revenue (USD)": filtered["revenue"],
    "Box Office (₹ Cr, custom only)": filtered["box_office_cr"],
    "Director": filtered["director"].str.replace("|", ", ", regex=False),
    "Language": filtered["language"],
    "Source": filtered["source"],
})

st.subheader(f"🎬 Movies Found: {len(table):,}")
if table.empty:
    st.info("No movies match these filters. Try removing a genre or lowering the minimum votes.")
else:
    ui.show_df(table, column_config={
        "Year": st.column_config.NumberColumn(format="%d"),
        "Votes": st.column_config.NumberColumn(format="%d"),
        "Budget (USD)": st.column_config.NumberColumn(format="$%d"),
        "Revenue (USD)": st.column_config.NumberColumn(format="$%d"),
    })
    st.download_button("📥 Download this table (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name="movies_filtered.csv", mime="text/csv")

st.caption("Empty budget / revenue / runtime = unknown in the dataset (not zero). "
           "Rating = TMDB vote average. Weighted Rating gives more trust to movies with more votes.")
