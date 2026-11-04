import random
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from pathlib import Path

import streamlit as st
from werkzeug.security import check_password_hash, generate_password_hash

# ===============================
# 📌 PAGE CONFIG
# ===============================
st.set_page_config(page_title="🎬 Movie Dashboard", page_icon="🎬", layout="wide")

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "users.db"


# ===============================
# 📌 DATABASE CONNECTION & INIT
# ===============================
def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create users table with email column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
        )
    """)

    # Safely migration check: add email column if database existed previously without it
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "email" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

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
# 📌 AUTH HELPER FUNCTIONS
# ===============================
def login_user(username, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    conn.close()
    return check_password_hash(row[0], password) if row else False


def register_user(username, email, password):
    """Returns (ok, message)."""
    username = username.strip()
    email = email.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if "@" not in email or "." not in email:
        return False, "Please enter a valid Email address."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users(username, email, password) VALUES(?,?,?)",
            (username, email, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()
        return True, "Account created! Please login."
    except sqlite3.IntegrityError:
        return False, "Username already exists!"
    except sqlite3.Error:
        return False, "Database error. Please try again."


def verify_user_email(username, email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return False
    return row[0].strip().lower() == email.strip().lower()


def update_password(username, new_password):
    if len(new_password) < 4:
        return False
    hashed = generate_password_hash(new_password)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, username.strip()))
    conn.commit()
    conn.close()
    return True


def send_otp_email(receiver_email, otp_code):
    sender_email = st.secrets.get("EMAIL_SENDER")
    sender_password = st.secrets.get("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        st.error("❌ Email credentials missing in .streamlit/secrets.toml!")
        return False

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Movie Dashboard - Password Reset OTP"

    body = f"""Hello!

Your One-Time Password (OTP) code to reset your Movie Dashboard account password is:

🔑 OTP Code: {otp_code}

This code is valid for this session only. Do not share it with anyone.

Best regards,
Movie Dashboard Team
"""
    message.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(message)
        server.quit()
        return True
    except Exception as exc:
        st.error(f"❌ Failed to send email: {exc}")
        return False


# ===============================
# 📌 LOGIN / REGISTER / FORGOT UI
# ===============================
if not st.session_state.logged_in:

    st.title("🔐 Account Access")

    action = st.radio("Select Action", ["Login", "Register", "Forgot Password"], horizontal=True)

    if action == "Login":
        username = st.text_input("Username").strip()
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login Successful! 🎉")
                st.rerun()
            else:
                st.error("Invalid username or password")

    elif action == "Register":
        reg_username = st.text_input("Username").strip()
        reg_email = st.text_input("Email (for password recovery)").strip()
        reg_password = st.text_input("Password", type="password")
        if st.button("Create Account"):
            ok, message = register_user(reg_username, reg_email, reg_password)
            (st.success if ok else st.error)(message)

    elif action == "Forgot Password":
        st.subheader("🔑 Reset Password via Email OTP")

        if "otp_sent" not in st.session_state:
            st.session_state["otp_sent"] = False
        if "generated_otp" not in st.session_state:
            st.session_state["generated_otp"] = None
        if "reset_username" not in st.session_state:
            st.session_state["reset_username"] = None

        if not st.session_state["otp_sent"]:
            f_user = st.text_input("Enter Username").strip()
            f_email = st.text_input("Enter Registered Email").strip()
            if st.button("Send OTP"):
                if verify_user_email(f_user, f_email):
                    otp = str(random.randint(100000, 999999))
                    if send_otp_email(f_email, otp):
                        st.session_state["otp_sent"] = True
                        st.session_state["generated_otp"] = otp
                        st.session_state["reset_username"] = f_user
                        st.success(f"✅ OTP sent to {f_email}! Check your inbox.")
                        st.rerun()
                else:
                    st.error("❌ Username and Email combination not found.")
        else:
            st.info(f"OTP sent to email for user **{st.session_state['reset_username']}**")
            user_otp = st.text_input("Enter 6-Digit OTP").strip()
            new_pass = st.text_input("Enter New Password", type="password")

            c_btn1, c_btn2 = st.columns([1, 1])
            if c_btn1.button("Reset Password"):
                if user_otp == st.session_state["generated_otp"]:
                    if update_password(st.session_state["reset_username"], new_pass):
                        st.success("🎉 Password reset successfully! You can now Login.")
                        st.session_state["otp_sent"] = False
                        st.session_state["generated_otp"] = None
                        st.session_state["reset_username"] = None
                    else:
                        st.error("Password must be at least 4 characters.")
                else:
                    st.error("❌ Invalid OTP Code. Please try again.")

            if c_btn2.button("Cancel"):
                st.session_state["otp_sent"] = False
                st.session_state["generated_otp"] = None
                st.session_state["reset_username"] = None
                st.rerun()

    st.stop()

# ===============================
# 📌 LOGOUT
# ===============================
with st.sidebar:
    st.info(f"Logged in as: {st.session_state.username}")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

# ===============================
# 📌 HOME PAGE CONTENT
# ===============================
st.title("🎥 Welcome to the Movie Dashboard")
st.success("Use the left menu to navigate 🚀")

try:
    from utils.data_loader import load_movies

    movies = load_movies(include_custom=False)
    c1, c2, c3 = st.columns(3)
    c1.metric("🎬 Movies in dataset", f"{len(movies):,}")
    c2.metric("📅 Release years", f"{int(movies['year'].min())} – {int(movies['year'].max())}")
    c3.metric("⭐ Average rating", f"{movies['vote_average'].mean():.2f}")
except Exception as exc:
    st.warning(f"Movie data could not be loaded yet: {exc}")

st.write("""
### What you can do here:
- 📄 **Movie Data** – search, filter and sort the full movie dataset
- 📊 **Analytics** – interactive dashboard of ratings, genres, years, popularity and box office
- ⭐ **Recommendations** – pick a movie and get genuinely similar movies (with posters)
- 🔍 Rate movies after login to get recommendations from users with a similar taste
""")