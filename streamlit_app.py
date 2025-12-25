import streamlit as st
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# ===============================
# 📌 PAGE CONFIG
# ===============================
st.set_page_config(page_title="🎬 Movie Dashboard", layout="wide")

# ===============================
# 📌 DATABASE CONNECTION
# ===============================
def get_db():
    return sqlite3.connect("data/users.db")

# ===============================
# 📌 DATABASE INITIALIZATION
# ===============================
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_likes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            movie TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ===============================
# 📌 SESSION STATE LOGIN STATUS
# ===============================
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("username", "")

# ===============================
# 📌 LOGIN FUNCTION
# ===============================
def login_user(username, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return check_password_hash(row[0], password) if row else False

# ===============================
# 📌 REGISTER FUNCTION
# ===============================
def register_user(username, password):
    try:
        conn = get_db()
        cursor = conn.cursor()
        hashed = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users(username, password) VALUES(?,?)",
            (username, hashed),
        )
        conn.commit()
        conn.close()
        return True
    except:
        return False

# ===============================
# 📌 LOGIN UI
# ===============================
if not st.session_state.logged_in:

    st.title("🔐 Login / Register")

    choice = st.radio("Select Action", ["Login", "Register"], horizontal=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if choice == "Login":
        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login Successful! 🎉")
                st.rerun()
            else:
                st.error("Invalid username or password")

    if choice == "Register":
        if st.button("Create Account"):
            if register_user(username, password):
                st.success("Account created! Please login.")
            else:
                st.error("Username already exists!")

    st.stop()

# ===============================
# 📌 LOGOUT
# ===============================
with st.sidebar:
    st.info(f"Logged in as: {st.session_state.username}")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# ===============================
# 📌 HOME PAGE CONTENT
# ===============================
st.title("🎥 Welcome to the Movie Dashboard")
st.success("Use the left menu to navigate 🚀")

st.write("""
### What you can do here:
- 📄 View full movie dataset  
- 📊 Analyze ratings, votes & box office  
- ⭐ Get AI-based movie recommendations  
- 🔍 Search, filter & discover movies  
""")







