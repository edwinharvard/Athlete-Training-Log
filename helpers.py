import datetime
import requests
import sqlite3
from flask import g, redirect, render_template, session, current_app
from functools import wraps
import json

with open("config.json", "r") as config_file:
    config = json.load(config_file)

CLIENT_ID = config["client_id"]
CLIENT_SECRET = config["client_secret"]


def get_db():
    """Return a SQLite DB connection for this request, creating if needed."""
    if "db" not in g:
        # You can omit check_same_thread since each request is single-threaded here
        g.db = sqlite3.connect(
            current_app.config["DATABASE"], 
            # (optional) detect types, make rows dict-like:
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Close the DB at the end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Function to render an apology message with an optional error code
def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters for meme generation.
        This helps format error messages to be displayed properly on the page.
        """
        for old, new in [
            ("-", "--"),  # Double hyphen for special character escape
            (" ", "-"),   # Replace space with dash
            ("_", "__"),  # Double underscore for underscore escape
            ("?", "~q"),  # Replace question mark with a tilde and q
            ("%", "~p"),  # Replace percentage symbol with a tilde and p
            ("#", "~h"),  # Replace hash symbol with a tilde and h
            ("/", "~s"),  # Replace slash with a tilde and s
            ('"', "''"),   # Double single quote for double quotes escape
        ]:
            s = s.replace(old, new)
        return s

    # Return the apology message and the HTTP status code (default: 400)
    return render_template("apology.html",
                           message=message,
                           description=f"Error code: {code}"), code


# Decorator to require the user to be logged in
def login_required(f):
    """
    Decorate routes to require login.

    This ensures that only logged-in users can access certain pages.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:  # Check if user is logged in (session contains user_id)
            return redirect("/login")  # If not, redirect to the login page
        return f(*args, **kwargs)

    return decorated_function


# Decorator to require coach account for certain routes
def coach_account_required(f):
    @wraps(f)
    @login_required
    def wrapped(*args, **kwargs):
        db  = get_db()
        row = db.execute(
            "SELECT coach FROM users WHERE id = ?",
            (session['user_id'],)
        ).fetchone()
        if not row or row['coach'] != 1:
            return apology("must have a coach's account", 401)
        return f(*args, **kwargs)
    return wrapped

def refresh_access_token(athlete_id, authorization_code=None):
    db = get_db()

    # If an auth code was provided, do the initial exchange…
    if authorization_code:
        payload = {
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code":          authorization_code,
            "grant_type":    "authorization_code"
        }
    else:
        # …otherwise do a refresh
        row = db.execute(
            "SELECT refresh_token_code FROM refresh_tokens WHERE athlete_id = ?",
            (athlete_id,)
        ).fetchone()
        if not row:
            return {"error": "Athlete not found"}

        payload = {
            "client_id":      CLIENT_ID,
            "client_secret":  CLIENT_SECRET,
            "grant_type":     "refresh_token",
            "refresh_token":  row["refresh_token_code"]
        }

    resp = requests.post(
        "https://www.strava.com/api/v3/oauth/token",
        data=payload
    )
    if resp.status_code != 200:
        return {"error": resp.text}

    data = resp.json()

    # Persist both tokens + scope if available
    db.execute("""
        INSERT OR REPLACE INTO refresh_tokens
          (athlete_id, refresh_token_code, scope)
        VALUES (?, ?, ?)
    """, (
        athlete_id,
        data["refresh_token"],
        data.get("scope", "")
    ))
    db.execute("""
        INSERT OR REPLACE INTO short_lived_access_tokens
          (athlete_id, access_token, expires_at)
        VALUES (?, ?, ?)
    """, (
        athlete_id,
        data["access_token"],
        data["expires_at"]
    ))
    db.commit()

    return data


def get_valid_access_token(athlete_id):
    db = get_db()

    row = db.execute("""
        SELECT short_lived_access_token_code, expires_at
        FROM short_lived_access_tokens
        WHERE athlete_id = ?
    """, (athlete_id,)).fetchone()

    if not row:
        return {"error": "No token on file"}

    access_token, expires_at = row
    now_ts = int(datetime.datetime.now().timestamp())

    if now_ts >= expires_at:
        # Refresh the token if it has expired
        data = refresh_access_token(athlete_id)
        if "error" in data:
            return data
        return data["access_token"]

    return access_token


def strava_api_request(athlete_id, endpoint="athlete"):
    """
    endpoint should be something like 'athlete', 'activities', etc.
    """
    token = get_valid_access_token(athlete_id)
    if isinstance(token, dict) and token.get("error"):
        return token

    url = f"https://www.strava.com/api/v3/{endpoint}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()


def fetch_strava_activities(athlete_id):
    token = get_valid_access_token(athlete_id)
    if isinstance(token, dict) and token.get("error"):
        return []

    url = "https://www.strava.com/api/v3/activities"
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        return []

    return response.json()


def init_db():
    """Initialize the database with required tables."""
    db = get_db()
    
    # Drop existing tables if they exist
    db.execute('DROP TABLE IF EXISTS refresh_tokens')
    db.execute('DROP TABLE IF EXISTS short_lived_access_tokens')
    
    # Create tables for Strava OAuth tokens
    db.execute('''
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        athlete_id INTEGER PRIMARY KEY,
        refresh_token_code TEXT NOT NULL,
        scope TEXT NOT NULL
    )
    ''')
    
    db.execute('''
    CREATE TABLE IF NOT EXISTS short_lived_access_tokens (
        athlete_id INTEGER PRIMARY KEY,
        access_token TEXT NOT NULL,
        expires_at INTEGER NOT NULL
    )
    ''')
    
    db.commit()