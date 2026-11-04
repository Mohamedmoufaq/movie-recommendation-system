"""Login helpers shared by all pages."""
import sqlite3
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import streamlit as st
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "users.db"


def current_user() -> str | None:
    """Username if someone is really logged in, otherwise None."""
    if st.session_state.get("logged_in") and str(st.session_state.get("username", "")).strip():
        return str(st.session_state["username"]).strip()
    return None


def get_db():
    DB_FILE.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    email = email.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if "@" not in email or "." not in email:
        return False, "Please enter a valid email address."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    hashed = generate_password_hash(password)
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                         (username, email, hashed))
            conn.commit()
        return True, "Account created! You can now log in."
    except sqlite3.IntegrityError:
        return False, "Username already exists. Pick another."


def verify_user(username: str, password: str) -> bool:
    username = username.strip()
    with get_db() as conn:
        row = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        return False
    return check_password_hash(row[0], password)


def verify_user_email(username: str, email: str) -> bool:
    username = username.strip()
    email = email.strip()
    with get_db() as conn:
        row = conn.execute("SELECT email FROM users WHERE username = ?", (username,)).fetchone()
    if not row or not row[0]:
        return False
    return row[0].strip().lower() == email.lower()


def update_password(username: str, new_password: str) -> bool:
    if len(new_password) < 4:
        return False
    hashed = generate_password_hash(new_password)
    with get_db() as conn:
        conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, username.strip()))
        conn.commit()
    return True


def send_otp_email(receiver_email: str, otp_code: str) -> bool:
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