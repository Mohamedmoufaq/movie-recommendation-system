# 🎬 Movie Recommendation & Analytics System

Streamlit app with login, a searchable movie table, an interactive Plotly analytics dashboard and
content-based movie recommendations with posters. Data: **TMDB 5000 Movies** (Kaggle) + your own custom movies.

## Project structure
```
streamlit_app.py            Login / Register + home page
pages/1_Movie_Data.py       Search, filter, sort, download the movie table
pages/2_Analytics.py        Plotly dashboard (KPI cards, filters, 15+ charts)
pages/3_Recommendations.py  Similar movies (content-based) + user-based recommendations
utils/                      Reusable code: data_loader, recommender, posters, ratings, ui, auth
scripts/                    prepare_data.py, fetch_poster_paths.py, check_recommendations.py
data/movies_clean.csv       Cleaned TMDB data (created by scripts/prepare_data.py)
data/movie_data.csv         YOUR hand-made movies (kept as "Custom" movies)
data/user_movie_ratings.csv Ratings given by users
posters/                    Local posters of your custom movies
```

## Run
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Posters (one-time setup)
The Kaggle dataset has **no poster column**, so posters come from the official TMDB API using each movie's
exact TMDB `id` (so a poster can never belong to a different movie).
1. Free key: themoviedb.org -> Settings -> API.
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste the key. (Never commit this file.)
3. Optional but recommended – download all poster paths once (about 5 minutes):
   `python scripts/fetch_poster_paths.py`  (creates `data/poster_paths.csv`, commit that file).
Without a key the app still works; movies without a poster show a clean "No poster available" card.

## Rebuild the clean data (only if needed)
Put `tmdb_5000_movies.csv` and `tmdb_5000_credits.csv` into `data/raw/`, then `python scripts/prepare_data.py`.

## Check the recommender from the terminal
`python scripts/check_recommendations.py "The Dark Knight" "Toy Story"`

## How recommendations work
Each movie = genres (30%) + keywords (25%) + story (25%) + director/cast (20%). TF-IDF turns each part into
numbers, cosine similarity compares movies. A recommendation must share a genre with the selected movie; the
selected movie and duplicates are removed. Ratings/votes never decide similarity (they only break exact ties).

## Security
API keys live only in `.streamlit/secrets.toml` or environment variables. `users.db` and secrets are git-ignored.
