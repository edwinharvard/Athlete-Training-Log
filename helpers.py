import requests
import sqlite3
from flask import redirect, render_template, session
from functools import wraps

sqliteConnection = sqlite3.connect('training_log.db')
cursor = sqliteConnection.cursor()

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
        coach_status = cursor.execute("SELECT coach FROM users WHERE id = ?", session.get("user_id"))
        if coach_status[0]['coach'] != 1:  # If the user is not a coach (coach value should be 1)
            return apology("must have a coach's account", 401)  # Show an apology with an error message
        return f(*args, **kwargs)

    return decorated_function

def refresh_access_token(client_id, client_secret, refresh_token):
    """
    Refresh an expired access token using Strava's OAuth API.

    Parameters:
        client_id (str): Your Strava API client ID.
        client_secret (str): Your Strava API client secret.
        refresh_token (str): The refresh token used to generate a new access token.

    Returns:
        dict: A dictionary containing the new access token, refresh token, and expiration time, or an error message.
    """
    url = "https://www.strava.com/api/v3/oauth/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the response JSON
        token_data = response.json()

        return {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": token_data.get("expires_at")
        }
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_athlete_data(access_token):
    """
    Fetch athlete data from the Strava API using an access token.

    Parameters:
        access_token (str): A valid access token for the Strava API.

    Returns:
        dict: The response from the API as a dictionary, or an error message.
    """
    url = "https://www.strava.com/api/v3/athlete"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Return the parsed JSON data
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
