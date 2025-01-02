import requests
from cs50 import SQL
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
    """
    db = SQL("sqlite:///training_log.db")  # Database connection

    @wraps(f)
    @login_required  # First check if the user is logged in
    def decorated_function(*args, **kwargs):
        # Query the database to check if the logged-in user is a coach
        coach_status = db.execute("SELECT coach FROM users WHERE id = ?", session.get("user_id"))
        if coach_status[0]['coach'] != 1:  # If the user is not a coach (coach value should be 1)
            return apology("must have a coach's account", 401)  # Show an apology with an error message
        return f(*args, **kwargs)

    return decorated_function
