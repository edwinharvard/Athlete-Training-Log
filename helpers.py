import datetime
import requests
import sqlite3
from flask import redirect, render_template, session
from functools import wraps

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
    """
    Decorate routes to require coach account.
    This ensures only users with a coach account can access certain pages.
    """  # Database connection

    @wraps(f)
    @login_required  # First check if the user is logged in
    def decorated_function(*args, **kwargs):
        # Query the database to check if the logged-in user is a coach
        sqliteConnection = sqlite3.connect('training_log.db')
        cursor = sqliteConnection.cursor()
        coach_status = cursor.execute("SELECT coach FROM users WHERE id = ?", session.get("user_id"))
        cursor.close()
        if coach_status[0]['coach'] != 1:  # If the user is not a coach (coach value should be 1)
            return apology("must have a coach's account", 401)  # Show an apology with an error message
        return f(*args, **kwargs)

    return decorated_function

def refresh_access_token(client_id, client_secret, athlete_id):
    """
    Refresh a short-lived access token for the specified athlete.

    Parameters:
        client_id (str): Your Strava API client ID.
        client_secret (str): Your Strava API client secret.
        athlete_id (int): The athlete's ID in the database.

    Returns:
        dict: A dictionary containing the new access token and expiration time, or an error message.
    """
    try:
        sqliteConnection = sqlite3.connect('training_log.db')
        cursor = sqliteConnection.cursor()

        # Retrieve the refresh token for the given athlete
        cursor.execute("""
            SELECT refresh_token_code FROM refresh_tokens WHERE athlete_id = ?
        """, (athlete_id,))
        row = cursor.fetchone()

        if not row:
            return {"error": "Athlete not found in refresh_tokens table"}
        
        refresh_token_code = row[0]

        # Use the refresh token to request a new access token from Strava
        url = "https://www.strava.com/api/v3/oauth/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token_code
        }

        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()

        # Extract the new access token and expiration time
        new_access_token = token_data.get("access_token")
        expires_at = token_data.get("expires_at")

        # Update the short-lived access tokens table
        cursor.execute("""
            INSERT OR REPLACE INTO short_lived_access_tokens (athlete_id, scope, short_lived_access_token_code, expires_at)
            VALUES (?, ?, ?, ?)
        """, (athlete_id, True, new_access_token, expires_at))
        sqliteConnection.commit()
        cursor.close()
        sqliteConnection.close()

        return {
            "access_token": new_access_token,
            "expires_at": expires_at
        }

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    except sqlite3.Error as db_error:
        return {"error": f"Database error: {db_error}"}



def get_valid_access_token(client_id, client_secret, athlete_id):
    """
    Retrieve a valid short-lived access token, refreshing it if expired.

    Parameters:
        client_id (str): Strava API client ID.
        client_secret (str): Strava API client secret.
        athlete_id (int): Athlete ID in the database.

    Returns:
        str: A valid access token or an error message.
    """
    try:
        sqliteConnection = sqlite3.connect('training_log.db')
        cursor = sqliteConnection.cursor()

        # Get the current access token and expiration time
        cursor.execute("""
            SELECT short_lived_access_token_code, expires_at
            FROM short_lived_access_tokens
            WHERE athlete_id = ?
        """, (athlete_id,))
        row = cursor.fetchone()

        if not row:
            return {"error": "Athlete not found in short_lived_access_tokens table"}

        access_token, expires_at = row
        current_time = int(datetime.now().timestamp())

        # Check if the token is expired
        if current_time >= expires_at:
            # Refresh the token
            refreshed_token_data = refresh_access_token(client_id, client_secret, athlete_id)
            if "error" in refreshed_token_data:
                return {"error": refreshed_token_data["error"]}
            return refreshed_token_data["access_token"]

        return access_token

    except sqlite3.Error as db_error:
        return {"error": f"Database error: {db_error}"}


def strava_api_request(endpoint, client_id, client_secret, athlete_id):
    """
    Make a Strava API request using a valid access token.

    Parameters:
        endpoint (str): The API endpoint to query.
        client_id (str): Strava API client ID.
        client_secret (str): Strava API client secret.
        athlete_id (int): Athlete ID in the database.

    Returns:
        dict: The API response or an error message.
    """
    access_token = get_valid_access_token(client_id, client_secret, athlete_id)
    if "error" in access_token:
        return {"error": access_token["error"]}

    url = f"https://www.strava.com/api/v3/{endpoint}"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
