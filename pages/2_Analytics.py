import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils import ui
from utils.data_loader import explode_list, load_movies

st.set_page_config(page_title="Movie Analytics Dashboard", page_icon="📊", layout="wide")
ui.inject_css()
st.title("📊 Movie Analytics Dashboard")
st.caption("Source: TMDB 5000 Movies dataset (Kaggle). Every chart below uses real columns from that data.")

# ===============================
# 📂 Load data
# ===============================
try:
    include_custom = st.sidebar.checkbox(
        "Include my custom movies", value=False,
        help="Your hand-made list has no budget/revenue/cast info and its ratings were typed by hand, "
             "so it is OFF by default to keep the analytics clean.")
    movies = load_movies(include_custom)
except FileNotFoundError as exc:
    st.error(f"❌ {exc}")
    st.stop()

# ===============================
# 🎛️ Filters (sidebar)
# ===============================
st.sidebar.header("🎛️ Filters")
year_min, year_max = int(movies["year"].min()), int(movies["year"].max())
years = st.sidebar.slider("Release year", year_min, year_max, (year_min, year_max))

genre_counts = explode_list(movies, "genre_list", "genre")["genre"].value_counts()
genres_sel = st.sidebar.multiselect("Genre (any of)", genre_counts.index.tolist())

lang_counts = movies["language"].value_counts()
langs_sel = st.sidebar.multiselect("Language", lang_counts.index.tolist())

min_votes = st.sidebar.slider("Minimum votes", 0, 5000, 10, step=10,
                              help="Hides movies with too few votes, because their ratings are unreliable.")

df = movies[movies["year"].between(*years) & (movies["vote_count"] >= min_votes)]
if genres_sel:
    wanted = set(genres_sel)
    df = df[df["genre_list"].map(lambda g: bool(wanted & set(g)))]
if langs_sel:
    df = df[df["language"].isin(langs_sel)]

if df.empty:
    st.warning("No movies match these filters. Please widen the filters in the sidebar.")
    st.stop()

# ===============================
# 📌 KPI cards
# ===============================
known_budget, known_revenue = df["budget"].dropna(), df["revenue"].dropna()
ui.kpi_cards([
    ("🎬 Total Movies", f"{len(df):,}", f"of {len(movies):,} in dataset"),
    ("⭐ Average Rating", f"{df['vote_average'].mean():.2f}", "out of 10"),
    ("🗳 Total Votes", ui.fmt_int(df["vote_count"].sum()), "all selected movies"),
    ("⏱ Avg Runtime", f"{df['runtime'].mean():.0f} min" if df["runtime"].notna().any() else "—", "known runtimes only"),
    ("💰 Median Budget", ui.fmt_money(known_budget.median()), f"{len(known_budget):,} movies with known budget"),
    ("🏆 Median Revenue", ui.fmt_money(known_revenue.median()), f"{len(known_revenue):,} movies with known revenue"),
])
st.write("")

# helper tables
genre_df = explode_list(df, "genre_list", "genre")
has_decade = df.dropna(subset=["year"]).assign(decade=lambda d: (d["year"].astype(int) // 10) * 10)


def top_bar(data, x, title, label, hover, color_scale=None, x_title=None):
    """Horizontal bar chart used by the Top-N charts."""
    data = data.sort_values(x, ascending=True)
    fig = px.bar(data, x=x, y="display_title", orientation="h", title=title,
                 hover_data=hover, color=x, color_continuous_scale=color_scale or ui.RED_SCALE,
                 labels={"display_title": "", x: x_title or label})
    fig.update_layout(coloraxis_showscale=False)
    return ui.style_fig(fig, height=max(340, 34 * len(data) + 90))


def excel_bytes(frame: pd.DataFrame, sheet: str) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        frame.to_excel(writer, index=False, sheet_name=sheet)
    return out.getvalue()


tab_overview, tab_genre, tab_top, tab_money, tab_people = st.tabs(
    ["📈 Overview", "🎭 Genres & Ratings", "🏅 Top Movies", "💰 Budget & Revenue", "👥 People"])

# ======================================================================
# 📈 OVERVIEW
# ======================================================================
with tab_overview:
    c1, c2 = st.columns(2)

    top_genres = genre_df["genre"].value_counts().reset_index()
    top_genres.columns = ["Genre", "Movies"]
    fig = px.bar(top_genres.sort_values("Movies"), x="Movies", y="Genre", orientation="h",
                 title="🍿 Genre Distribution (movies per genre)", color="Movies",
                 color_continuous_scale=ui.RED_SCALE)
    fig.update_layout(coloraxis_showscale=False)
    with c1:
        ui.show_chart(ui.style_fig(fig, height=520))
        st.caption("A movie can have several genres, so it is counted once in each of its genres.")

    per_year = df.dropna(subset=["year"]).groupby("year").size().reset_index(name="Movies")
    per_year["year"] = per_year["year"].astype(int)
    fig = px.area(per_year, x="year", y="Movies", title="📅 Movies by Release Year",
                  labels={"year": "Release year"})
    fig.update_traces(line_color="#E50914", fillcolor="rgba(229,9,20,0.25)")
    with c2:
        ui.show_chart(ui.style_fig(fig, height=520))

    c3, c4 = st.columns(2)
    fig = px.histogram(df.dropna(subset=["vote_average"]), x="vote_average", nbins=30,
                       title="🎯 Rating Distribution", labels={"vote_average": "Rating (0–10)"})
    fig.update_traces(marker_line_color="#0E1117", marker_line_width=1)
    fig.update_layout(yaxis_title="Number of movies", bargap=0.05)
    with c3:
        ui.show_chart(ui.style_fig(fig))

    by_decade = has_decade.groupby("decade").agg(avg=("vote_average", "mean"), n=("id", "size")).reset_index()
    fig = px.line(by_decade, x="decade", y="avg", markers=True, hover_data={"n": True},
                  title="🕰 Average Rating by Decade", labels={"decade": "Decade", "avg": "Average rating", "n": "Movies"})
    fig.update_traces(line_color="#F5B301")
    fig.update_yaxes(range=[max(0, by_decade["avg"].min() - 0.5), 10])
    with c4:
        ui.show_chart(ui.style_fig(fig))

    non_en = df[df["language"] != "English"]["language"].value_counts().head(10).reset_index()
    non_en.columns = ["Language", "Movies"]
    en_share = (df["language"] == "English").mean() * 100
    if not non_en.empty:
        fig = px.bar(non_en.sort_values("Movies"), x="Movies", y="Language", orientation="h",
                     title="🌍 Top Non-English Languages", color_discrete_sequence=["#2EC4B6"])
        ui.show_chart(ui.style_fig(fig, height=360))
    st.caption(f"English-language movies make up {en_share:.0f}% of the selected data, "
               "so they are left out of the chart above to keep the other languages visible.")

# ======================================================================
# 🎭 GENRES & RATINGS
# ======================================================================
with tab_genre:
    g = genre_df.dropna(subset=["vote_average"])
    stats = g.groupby("genre").agg(avg=("vote_average", "mean"), n=("id", "size")).reset_index()
    stats = stats[stats["n"] >= 5]  # tiny genres give misleading averages
    fig = px.bar(stats.sort_values("avg"), x="avg", y="genre", orientation="h", color="n",
                 color_continuous_scale=ui.RED_SCALE, title="⭐ Average Rating by Genre",
                 labels={"avg": "Average rating", "genre": "", "n": "Movies"}, hover_data={"n": True})
    fig.update_xaxes(range=[max(0, stats["avg"].min() - 0.5), stats["avg"].max() + 0.3])
    ui.show_chart(ui.style_fig(fig, height=520))
    st.caption("Genres with fewer than 5 rated movies are hidden. Darker bars = fewer movies.")

    top10 = g["genre"].value_counts().head(10).index
    fig = px.box(g[g["genre"].isin(top10)], x="genre", y="vote_average", color="genre",
                 title="📦 Rating Spread in the 10 Biggest Genres",
                 labels={"genre": "", "vote_average": "Rating"})
    ui.show_chart(ui.style_fig(fig, height=430))
    st.caption("The box shows where the middle 50% of ratings fall; the line inside is the median.")

# ======================================================================
# 🏅 TOP MOVIES
# ======================================================================
with tab_top:
    top_n = st.slider("How many movies to show", 5, 20, 10)

    c1, c2 = st.columns(2)
    top_rated = df.dropna(subset=["weighted_rating"]).nlargest(top_n, "weighted_rating")
    with c1:
        ui.show_chart(top_bar(top_rated, "weighted_rating", "⭐ Top Rated (weighted by votes)", "Weighted rating",
                              {"vote_average": ":.1f", "vote_count": ":,"}))
    popular = df.dropna(subset=["popularity"]).nlargest(top_n, "popularity")
    with c2:
        ui.show_chart(top_bar(popular, "popularity", "🔥 Most Popular (TMDB popularity)", "Popularity",
                              {"vote_average": ":.1f", "vote_count": ":,"}, color_scale=["#1B2A2E", "#2EC4B6"]))
    st.caption("Weighted rating = IMDB-style formula: a movie with few votes is pulled toward the average, "
               "so one 10/10 vote cannot beat a movie loved by thousands.")

    top_box = df.dropna(subset=["revenue"]).nlargest(top_n, "revenue")
    ui.show_chart(top_bar(top_box, "revenue", "💰 Top Box Office (revenue, USD)", "Revenue",
                          {"vote_average": ":.1f", "budget": ":,.0f"}, color_scale=["#2B2410", "#F5B301"],
                          x_title="Revenue (USD)"))

    d1, d2 = st.columns(2)
    cols = ["display_title", "genres", "vote_average", "vote_count", "weighted_rating", "revenue"]
    d1.download_button("📥 Download Top Rated (Excel)",
                       excel_bytes(top_rated[cols].rename(columns={"display_title": "Movie"}), "TopRated"),
                       file_name="top_rated.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    d2.download_button("📥 Download Top Box Office (Excel)",
                       excel_bytes(top_box[cols].rename(columns={"display_title": "Movie"}), "TopBoxOffice"),
                       file_name="top_boxoffice.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ======================================================================
# 💰 BUDGET & REVENUE
# ======================================================================
with tab_money:
    both = df.dropna(subset=["budget", "revenue"])
    if both.empty:
        st.info("No movies with both budget and revenue in the current selection.")
    else:
        fig = px.scatter(both, x="budget", y="revenue", color="vote_average", log_x=True, log_y=True,
                         hover_name="display_title", color_continuous_scale="RdYlGn",
                         title=f"💵 Budget vs Revenue ({len(both):,} movies with both known)",
                         labels={"budget": "Budget (USD, log scale)", "revenue": "Revenue (USD, log scale)",
                                 "vote_average": "Rating"})
        fig.update_traces(marker=dict(size=6, opacity=0.75))
        lo, hi = both["budget"].min(), both["budget"].max()
        fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi, line=dict(color="#9AA4B2", dash="dot"))
        ui.show_chart(ui.style_fig(fig, height=500))
        st.caption("Dotted line = break-even (revenue equals budget). Points above it earned more than they cost "
                   "(this ignores marketing costs and cinema shares).")

        profit = both.assign(profit=both["revenue"] - both["budget"]).nlargest(10, "profit")
        ui.show_chart(top_bar(profit, "profit", "🏦 Biggest Earners (revenue − budget)", "Profit",
                              {"budget": ":,.0f", "revenue": ":,.0f"}, color_scale=["#1F2B18", "#9BD770"],
                              x_title="Revenue − budget (USD)"))

    runtime = df.dropna(subset=["runtime", "vote_average"])
    if not runtime.empty:
        fig = px.scatter(runtime, x="runtime", y="vote_average", hover_name="display_title", opacity=0.5,
                         title="⏱ Runtime vs Rating", labels={"runtime": "Runtime (minutes)", "vote_average": "Rating"},
                         color_discrete_sequence=["#7B8CDE"])
        ui.show_chart(ui.style_fig(fig, height=420))

# ======================================================================
# 👥 PEOPLE
# ======================================================================
with tab_people:
    directors = explode_list(df, "director_list", "director")
    actors = explode_list(df, "cast_list", "actor")
    c1, c2 = st.columns(2)

    if not directors.empty:
        d = directors.groupby("director").agg(Movies=("id", "size"), avg=("vote_average", "mean")).reset_index()
        d = d.nlargest(10, "Movies").sort_values("Movies")
        fig = px.bar(d, x="Movies", y="director", orientation="h", title="🎬 Directors with Most Movies",
                     hover_data={"avg": ":.2f"}, labels={"director": "", "avg": "Avg rating"},
                     color_discrete_sequence=["#E50914"])
        with c1:
            ui.show_chart(ui.style_fig(fig, height=430))

        best = directors.groupby("director").agg(n=("id", "size"), avg=("vote_average", "mean")).reset_index()
        best = best[best["n"] >= 3].nlargest(10, "avg").sort_values("avg")
        if not best.empty:
            fig = px.bar(best, x="avg", y="director", orientation="h", hover_data={"n": True},
                         title="🌟 Highest Rated Directors (3+ movies)",
                         labels={"avg": "Average rating", "director": "", "n": "Movies"},
                         color_discrete_sequence=["#F5B301"])
            fig.update_xaxes(range=[max(0, best["avg"].min() - 0.5), 10])
            with c2:
                ui.show_chart(ui.style_fig(fig, height=430))

    if not actors.empty:
        a = actors.groupby("actor").agg(Movies=("id", "size"), avg=("vote_average", "mean")).reset_index()
        a = a.nlargest(10, "Movies").sort_values("Movies")
        fig = px.bar(a, x="Movies", y="actor", orientation="h", title="🎭 Actors in Most Movies (top 5 billed cast)",
                     hover_data={"avg": ":.2f"}, labels={"actor": "", "avg": "Avg rating"},
                     color_discrete_sequence=["#2EC4B6"])
        ui.show_chart(ui.style_fig(fig, height=430))
    if directors.empty and actors.empty:
        st.info("Director / cast information is not available for the current selection "
                "(your custom movies do not have it).")
