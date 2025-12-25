import streamlit as st
import pandas as pd

st.title("📄 Movie Data Explorer")

try:
    # ===============================
    # 📂 Load Dataset
    # ===============================
    df = pd.read_csv("data/movie_data.csv")

    # ===============================
    # 🔍 Search & Filter Section
    # ===============================
    st.subheader("🔎 Search & Filter Movies")

    search_text = st.text_input("Search movie by name")

    genres = sorted(df["Genre"].dropna().unique())
    selected_genres = st.multiselect("Filter by Genre", genres)

    sort_column = st.selectbox(
        "Sort movies by",
        ["Rating", "Votes", "BoxOffice"]
    )

    sort_order = st.radio(
        "Sort order",
        ["Descending", "Ascending"],
        horizontal=True
    )

    # ===============================
    # 🧠 Apply Filters
    # ===============================
    filtered_df = df.copy()

    if search_text:
        filtered_df = filtered_df[
            filtered_df["MovieName"].str.contains(search_text, case=False, na=False)
        ]

    if selected_genres:
        filtered_df = filtered_df[
            filtered_df["Genre"].isin(selected_genres)
        ]

    filtered_df = filtered_df.sort_values(
        by=sort_column,
        ascending=(sort_order == "Ascending")
    ).reset_index(drop=True)

    # ===============================
    # 🔢 Add Serial Number
    # ===============================
    filtered_df.insert(0, "S.No", filtered_df.index + 1)

    # ===============================
    # 📊 Display Result
    # ===============================
    st.subheader(f"🎬 Movies Found: {len(filtered_df)}")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

except FileNotFoundError:
    st.error("❌ movie_data.csv not found inside /data folder!")






