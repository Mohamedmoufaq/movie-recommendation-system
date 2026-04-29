import streamlit as st
import pandas as pd
import requests
import os
from fuzzywuzzy import process
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

API_KEY = os.getenv("omdb_api")


@st.cache_data
def get_movie_poster(movie_name):
    movie_name = str(movie_name).strip()
    if movie_name == "":
        return None

    url = f"https://www.omdbapi.com/?t={movie_name}&apikey={API_KEY}&type=movie"

    try:
        data = requests.get(url, timeout=5).json()

        if not isinstance(data, dict):
            return None

        if data.get("Response") == "False":
            return None

        poster = data.get("Poster")
        if poster and poster != "N/A":
            return poster

    except:
        return None

    return None


st.title("⭐ Movie Recommendation System")

df = pd.read_csv("data/movie_data.csv")
df.reset_index(drop=True, inplace=True)

df["BoxOffice"] = (
    df["BoxOffice"]
    .astype(str)
    .str.replace("Cr", "", regex=False)
    .str.replace("₹", "", regex=False)
    .str.replace(",", "", regex=False)
)

df["BoxOffice"] = pd.to_numeric(df["BoxOffice"], errors="coerce").fillna(0)


def show_movie_card(row):
    col1, col2 = st.columns([1, 3])

    with col1:
        poster_path = row.get("PosterPath", "")
        poster_url_csv = row.get("PosterURL", "")

        if isinstance(poster_path, str) and os.path.exists(poster_path):
            st.image(poster_path, width=180)

        else:
            if isinstance(poster_url_csv, str) and poster_url_csv != "":
                st.markdown(f"[Poster URL]({poster_url_csv})")

            poster = get_movie_poster(row["MovieName"])
            if poster:
                st.image(poster, width=180)
            else:
                st.image("https://via.placeholder.com/300x450?text=No+Poster", width=180)

    with col2:
        st.markdown(f"### 🎬 {row['MovieName']}")
        st.write(f"⭐ Rating: {row['Rating']}")
        st.write(f"🗳 Votes: {row['Votes']}")
        st.write(f"💰 Box Office: {row['BoxOffice']} Cr")
        st.write(f"🎭 Genre: {row['Genre']}")

    st.write("---")


search = st.text_input("🔍 Search Movie")
movie_list = df["MovieName"].tolist()

if search:
    matches = process.extract(search, movie_list, limit=15)
    movie_list = [m[0] for m in matches if m[1] >= 60]

selected_movie = st.selectbox("🎬 Select a Movie", movie_list)

selected_row = df[df["MovieName"] == selected_movie].iloc[0]
st.subheader("🎬 Selected Movie")
show_movie_card(selected_row)

# ===============================
# USER BASED RECOMMENDATION
# ==============================
st.subheader("👤 User-Based Recommendations")

username = st.session_state.get("username", None)

if username is None:

    st.info("🔒 Login required for personalized recommendations")

else:
    ratings_file = "data/user_movie_ratings.csv"

    try:
        ratings = pd.read_csv(ratings_file)
    except:
        ratings = pd.DataFrame(columns=["UserID", "MovieName", "Rating"])
        ratings.to_csv(ratings_file, index=False)

    user_id = str(username)

    st.write("Rate selected movie (1-5)")
    rating_input = st.slider("Rating", 1, 5, 3)

    if st.button("Submit Rating"):

        duplicate = ((ratings.UserID == user_id) & (ratings.MovieName == selected_movie))

        if duplicate.any():
            ratings.loc[duplicate, "Rating"] = rating_input
        else:
            new_row = pd.DataFrame({"UserID": [user_id], "MovieName": [selected_movie], "Rating": [rating_input]})
            ratings = pd.concat([ratings, new_row], ignore_index=True)

        ratings.to_csv(ratings_file, index=False)
        st.success("Rating saved!")

    if st.button("🎯 Recommend Based on Users"):

        if ratings.empty or user_id not in ratings.UserID.astype(str).values:
            st.warning("Not enough ratings to recommend 😶")

        else:
            rating_matrix = ratings.pivot_table(index="UserID", columns="MovieName", values="Rating")
            rating_matrix.index = rating_matrix.index.astype(str)

            user_similarity = cosine_similarity(rating_matrix.fillna(0))
            sim_df = pd.DataFrame(user_similarity, index=rating_matrix.index, columns=rating_matrix.index)


            def similar_users(u_id, n=5):
                if u_id not in sim_df.columns:
                    return pd.Series(dtype=float)
                return sim_df[u_id].sort_values(ascending=False)[1:n + 1]


            def recommend_movies(u_id):

                users = similar_users(u_id)

                if users.empty:
                    return pd.Series(dtype=str)

                watched = ratings[ratings.UserID.astype(str) == u_id]["MovieName"]

                similar_user_movies = ratings[ratings.UserID.astype(str).isin(users.index)]
                final = similar_user_movies[~similar_user_movies["MovieName"].isin(watched)]
                final = final[final["MovieName"].isin(df["MovieName"].values)]
                return final["MovieName"].value_counts().head(10)


            recs = recommend_movies(user_id)

            if recs.empty:
                st.info("No new recommendations 😶")

            else:
                st.subheader("🎬 Recommended Movies (User-Based)")
                for m in recs.index:
                    show_movie_card(df[df["MovieName"] == m].iloc[0])

# ==================================================
# GENRE BASED RECOMMENDATION
# ==================================================
if st.button("🎯 Recommend Same Genre"):

    selected_genre = df[df["MovieName"] == selected_movie]["Genre"].values[0]

    features = df[["Rating", "Votes", "BoxOffice"]].copy()

    scaler = MinMaxScaler()
    features_scaled = scaler.fit_transform(features)

    similarity = cosine_similarity(features_scaled)

    index = df[df["MovieName"] == selected_movie].index[0]

    scores = list(enumerate(similarity[index]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)

    recommendations = []

    for i, score in scores:
        if selected_genre in df.iloc[i]["Genre"] and df.iloc[i]["MovieName"] != selected_movie:
            recommendations.append(i)
        if len(recommendations) == 5:
            break

    st.subheader(f"🎭 Same Genre Recommendations → {selected_genre}")

    if recommendations:
        for i in recommendations:
            show_movie_card(df.iloc[i])
    else:
        st.error("No similar genre movies found!")























