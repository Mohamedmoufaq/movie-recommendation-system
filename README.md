# 🎬 Movie Mind – Intelligent Analytics & Recommendation System

An end-to-end Machine Learning & Business Intelligence web application built with **Python**, **Streamlit**, and **Scikit-learn**. The system features a Content-Based Recommendation Engine trained on the TMDB 5000 dataset, an Interactive Analytics Dashboard, and a Secure User Authentication framework with Email OTP Password Recovery.

---

## 🌟 Key Features

- **🎬 Content-Based Recommendation Engine:** Uses TF-IDF Vectorization and Cosine Similarity to recommend similar movies based on genres, cast, crew, keywords, and storyline.
- **🖼️ Real-Time Poster Fetching:** Dynamically fetches high-resolution movie posters directly from the official TMDB API.
- **📊 Interactive Data Analytics:** Built with **Plotly** to explore ratings, box-office revenue trends, budget analysis, genres distribution, and release timeline metrics.
- **🔐 Secure Authentication System:** 
  - Password hashing via `Werkzeug` (scrypt).
  - SQLite database for persistent user accounts.
  - **Email OTP Password Reset:** Automated 6-digit OTP delivery using Python `smtplib` and Gmail SMTP integration.
- **📁 Custom Movie Support:** Seamlessly integrates local user-added movies alongside the global TMDB dataset.

---

## 🛠️ Tech Stack & Libraries

- **Language:** Python 3.11
- **Frontend / Framework:** Streamlit
- **Data Processing:** Pandas, NumPy
- **Machine Learning & NLP:** Scikit-learn (TF-IDF, Cosine Similarity)
- **Data Visualization:** Plotly
- **Database:** SQLite3
- **Security & Mail:** Werkzeug, smtplib, email.mime
- **API Integration:** TMDB API (The Movie Database)

---

## 📁 Project Structure

```text
mrs/
│── .streamlit/
│   ├── config.toml           # UI Theme Configurations
│   └── secrets.toml.example  # Template for Secrets & API Keys
│── data/
│   ├── movies_clean.csv      # Processed TMDB 5000 dataset
│   ├── movie_data.csv        # Custom handcrafted movies dataset
│   └── users.db              # SQLite Database (Git Ignored)
│── pages/
│   ├── 1_Movie_Data.py       # Dataset Explorer, Filters, and Table Download
│   ├── 2_Analytics.py        # Plotly Interactive BI Dashboard
│   └── 3_Recommendations.py  # Movie Recommendation Interface with Posters
│── scripts/                  # Data preparation & posters caching scripts
│── utils/
│   ├── auth.py               # User Login, Registration, and Email OTP Logic
│   ├── data_loader.py        # Optimized CSV Data Loading
│   ├── recommender.py       # Machine Learning Recommendation Engine
│   └── ui.py                 # Custom Styling & CSS Injections
│── requirements.txt          # Project Dependencies
│── streamlit_app.py          # Main Entrance & Auth Router
└── README.md                 # Project Documentation
