import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Movie Analytics Dashboard", layout="wide")
st.title("📊 Movie Analytics Dashboard")

try:
    df = pd.read_csv("data/movie_data.csv")

    min_rating = st.slider(
        "🎯 Minimum Rating",
        min_value=0.0,
        max_value=10.0,
        value=7.0,
        step=0.1
    )

    filtered_df = df[df["Rating"] >= min_rating]

    # 📌 KPI SECTION
    st.subheader("📌 Key Insights")
    col1, col2, col3 = st.columns(3)
    col1.metric("🎬 Total Movies", len(filtered_df))
    col2.metric("⭐ Average Rating", round(filtered_df["Rating"].mean(), 2))
    col3.metric("💰 Avg Box Office", round(filtered_df["BoxOffice"].mean(), 2))
    st.markdown("---")

    # 🎬 Average Rating by Genre
    st.subheader("🎬 Average Rating by Genre")
    genre_rating = (
        filtered_df.groupby("Genre")["Rating"]
        .mean()
        .sort_values(ascending=False)
    )
    fig1, ax1 = plt.subplots()
    ax1.bar(genre_rating.index, genre_rating.values)
    plt.xticks(rotation=60, ha="right")
    st.pyplot(fig1)

    # 🍿 Genre Distribution
    st.subheader("🍿 Genre Distribution")
    genre_counts = filtered_df["Genre"].value_counts()
    colors = plt.cm.tab20(np.linspace(0, 1, len(genre_counts)))
    fig2, ax2 = plt.subplots(figsize=(6, 6))
    ax2.pie(
        genre_counts.values,
        labels=genre_counts.index,
        autopct="%1.1f%%",
        colors=colors,
        startangle=80
    )
    ax2.axis("equal")
    st.pyplot(fig2)

    # 🎯 Rating Distribution
    st.subheader("🎯 Rating Distribution")
    fig3, ax3 = plt.subplots()
    ax3.hist(filtered_df["Rating"], bins=10, edgecolor='black')
    ax3.set_xlabel("Rating")
    ax3.set_ylabel("Number of Movies")
    st.pyplot(fig3)
    st.markdown("---")

    # ⭐ Top 10 Highest Rated Movies
    st.subheader("⭐ Top 10 Highest Rated Movies")
    top_10_rating = df.sort_values("Rating", ascending=False).head(10).reset_index(drop=True)
    top_10_rating["Rank"] = top_10_rating.index + 1

    st.dataframe(
        top_10_rating[["Rank", "MovieName", "Genre", "Rating", "Votes", "BoxOffice"]],
        use_container_width=True,
        hide_index=True
    )

    rating_output = BytesIO()
    with pd.ExcelWriter(rating_output, engine='xlsxwriter') as writer:
        top_10_rating.to_excel(writer, index=False, sheet_name='Top10Rating')
    st.download_button(
        label="📥 Download Top 10 Rating (Excel)",
        data=rating_output.getvalue(),
        file_name="top10_rating.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # 💰 Top 10 Box Office Movies
    st.subheader("💰 Top 10 Box Office Movies")
    top_10_box = filtered_df.sort_values("BoxOffice", ascending=False).head(10).reset_index(drop=True)
    top_10_box["Rank"] = top_10_box.index + 1

    st.dataframe(
        top_10_box[["Rank","MovieName", "Genre", "Rating", "Votes", "BoxOffice"]],
        use_container_width=True,
        hide_index=True
    )

    box_output = BytesIO()
    with pd.ExcelWriter(box_output, engine='xlsxwriter') as writer:
        top_10_box.to_excel(writer, index=False, sheet_name='Top10BoxOffice')
    st.download_button(
        label="📥 Download Top 10 Box Office (Excel)",
        data=box_output.getvalue(),
        file_name="top10_boxoffice.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

except FileNotFoundError:
    st.error("❌ movie_data.csv not found! Please keep it in the main folder.")




