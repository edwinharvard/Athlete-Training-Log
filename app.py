import os
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session
import requests
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, coach_account_required, refresh_access_token, close_db, get_db, fetch_strava_activities, init_db

app = Flask(__name__)
app.secret_key = 'ryerson_project2'
app.config["DATABASE"] = "training_log.db"
app.config['DEBUG'] = True  # Add this line
app.config['ENV'] = 'development'  # Add this line

# Update your logging configuration
import logging
logging.basicConfig(level=logging.DEBUG)

app.teardown_appcontext(close_db)
with app.app_context():
    init_db()


@app.before_request
def log_request_info():
    app.logger.debug(f"Request URL: {request.url}")
    app.logger.debug(f"Request Headers: {request.headers}")
    app.logger.debug(f"Request Args: {request.args}")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        db = get_db()
        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        planned_hours = request.form.get("planned_hours")
        graduation_year = request.form.get("graduation_year")
        coach = request.form.get("coach")

        # Check if username is provided
        if not username:
            return apology("must provide username", 400)

        # Ensure passwords are submitted and match
        if not password or not confirmation:
            return apology("must provide two passwords", 400)
        if not password == confirmation:
            return apology("passwords must match", 400)

        # Hash the provided password for security
        password_hash = generate_password_hash(password, method="pbkdf2:sha256")

        # Handle coach field: convert to 1 if 'coach' is selected, otherwise 0
        if coach == "coach":
            coach = 1
        else:
            coach = 0

        # Validate the coach input to ensure it's either 0 or 1
        if coach != 0 and coach != 1:
            return apology("must provide input for coach 1", 400)

        # Try to insert the new user into the database
        try:
            db.execute("INSERT INTO users (username, password_hash, planned_hours, graduation_year, coach) VALUES (?, ?, ?, ?, ?)",
                       (username, password_hash, planned_hours, graduation_year, coach))
            db.commit()
        except:
            # Handle the case where the username already exists in the database
            return apology("username already exists", 400)

        # Retrieve the user details from the database to store in the session
        rows = db.execute("SELECT * FROM users WHERE username = ?", (username,))

        user = rows.fetchone()
        # Set the user session with the user's ID
        session["user_id"] = user["id"]

        # Redirect the user to the homepage after successful registration
        return redirect("/")

    # If the request method is GET, render the registration form
    else:
        return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        db = get_db()
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", (request.form.get("username"),)
        )

        user = rows.fetchone()
        
        if not user or not check_password_hash(
            user['password_hash'], request.form['password']
        ):
            return apology("invalid username and/or password", 403)
        session['user_id'] = user['id']

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/update-athlete-account", methods=["GET", "POST"])
@coach_account_required
def update_athlete_account():
    """Update account information for the logged-in user or an athlete"""

    if request.method == "POST":
        db = get_db()
        # Retrieve the form data submitted by the user
        athlete_id = request.form.getlist("athlete_id")
        username = request.form.get("username")  # New username input
        password = request.form.get("password")  # New password input (correct field name)
        confirmation = request.form.get("confirmation")  # Password confirmation input
        planned_hours = request.form.get("planned_hours") or 'N/A'  # Default to 'N/A' if not provided
        graduation_year = request.form.get("graduation_year") or 'N/A'  # Default to 'N/A' if not provided

        # Check if the username is provided
        if not username:
            return apology("must provide username", 400)

        # Validate if passwords are matching, if provided
        if password and confirmation:
            if password != confirmation:
                return apology("must provide matching password and confirmation", 400)

        # Hash the new password before storing it in the database
        if password:
            password_hash = generate_password_hash(password, method="pbkdf2:sha256")
        else:
            password_hash = None

        # Retrieve the current user's ID from the session
        current_user = session["user_id"]

        try:
            # Perform the update for the username, password, planned hours, and graduation year
            db.execute("""
                UPDATE users
                SET username = ?,
                    password_hash = ?,
                    planned_hours = ?,
                    graduation_year = ?
                WHERE id = ?
            """, (username, password_hash, planned_hours, graduation_year, athlete_id,))
            db.commit()
        except Exception as e:
            # Catch any database errors (e.g., if the username already exists) and show an error message
            return apology(f"Error: {e}", 400)

        # Redirect to the homepage after the update is successful
        return redirect("/")


    else:
        db = get_db()
        athlete_id = request.args.get("id")
        if not athlete_id:
            return "Error: athlete id is missing", 400
        # If the request method is GET, render the update account page
        # Retrieve all athletes that the current user (coach) can manage
        athlete = db.execute("SELECT * FROM users WHERE id = ?", (athlete_id,)).fetchone()
        return render_template("update_athlete_account.html", athlete=athlete)


@app.route("/update-coach-account", methods=["GET", "POST"])
@login_required  # or @coach_account_required if you want to double-check
def update_coach_account():
    db = get_db()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)

        # if password fields provided, ensure they match
        if password or confirmation:
            if password != confirmation:
                return apology("passwords must match", 400)
            pw_hash = generate_password_hash(password)
        else:
            pw_hash = None

        # build your UPDATE statement dynamically
        if pw_hash:
            db.execute(
                "UPDATE users SET username = ?, password_hash = ? WHERE id = ?",
                (username, pw_hash, session["user_id"])
            )
        else:
            db.execute(
                "UPDATE users SET username = ? WHERE id = ?",
                (username, session["user_id"])
            )
        db.commit()
        return redirect("/")

    else:
        user = db.execute("SELECT username FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        return render_template("update_coach_account.html", user=user)




@app.route("/add-workout", methods=["GET", "POST"])
@login_required
def add_workout():
    """Create a new workout entry"""

    if request.method == "POST":
        db = get_db()
        completed_hours = request.form.get("completed_hours")
        planned_hours = request.form.get("planned_hours")
        workout_type = request.form.get("workout_type")
        distance = request.form.get("distance")
        comments = request.form.get("comments")
        date = request.form.get("date")
        title = request.form.get("title")

        # Validate hours
        try:
            if not completed_hours or int(completed_hours) <= 0:
                return apology("Completed hours must be greater than zero", 400)

            if planned_hours:
                if int(planned_hours) < 0:
                    return apology("Planned hours must be a positive number", 400)
            else:
                planned_hours = 0

            completed_hours = int(completed_hours)
            planned_hours = int(planned_hours)

        except ValueError:
            return apology("Both completed and planned hours must be valid numbers", 400)

        # Validate required fields
        if not workout_type:
            return apology("You must provide the workout type", 400)
        if not date:
            return apology("You must provide the date", 400)

        current_user = session["user_id"]

        # Insert the workout into the database
        db.execute("INSERT INTO workout (user_id, completed_hours, workout_type, date, distance, comments, planned_hours, title) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (current_user, completed_hours, workout_type, date, distance, comments, planned_hours, title,))
        db.commit()
        return redirect("/")

    # GET request: render form
    else:
        return render_template("add_workout.html")



@app.route("/add-workout-coach", methods=["GET", "POST"])
@coach_account_required
def add_workout_coach():
    """create workout"""

    if request.method == "POST":
        db = get_db()
        completed_hours = request.form.get("completed_hours") or 'N/A'
        planned_hours = request.form.get("planned_hours") or 'N/A'
        workout_type = request.form.get("workout_type") or 'N/A'
        distance = request.form.get("distance") or 'N/A'
        comments = request.form.get("comments") or 'N/A'
        date = request.form.get("date")
        title = request.form.get("title") or 'N/A'

        athlete_ids = request.form.getlist("athlete_ids[]")
        # Convert to ints if you need:
        athlete_ids = [int(a) for a in athlete_ids]

        # Validate hours
        try:
            if not completed_hours or int(completed_hours) <= 0:
                return apology("Completed hours must be greater than zero", 400)

            if planned_hours:
                if int(planned_hours) < 0:
                    return apology("Planned hours must be a positive number", 400)
            else:
                planned_hours = 0

            completed_hours = int(completed_hours)
            planned_hours = int(planned_hours)

        except ValueError:
            return apology("Both completed and planned hours must be valid numbers", 400)

        if not (workout_type or title or comments):
            return apology("must provide more info (title, type, comments)", 400)
        if not date:
            return apology("must provide the date", 400)
        if not athlete_ids:
            return apology("must provide an athlete(s)", 400)

        for athlete_id in athlete_ids:
            db.execute("INSERT INTO workout (user_id, completed_hours, workout_type, distance, comments, date, planned_hours, title) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (int(athlete_id), completed_hours, workout_type, distance, comments, date, planned_hours, title,))
            db.commit()
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        db = get_db()
        athletes = db.execute("SELECT id, username FROM users WHERE coach = ?", (0,)).fetchall()
        return render_template("add_workout_coach.html", athletes=athletes)


@app.route("/update-workout", methods=["GET", "POST"])
@login_required  # Ensure the user is logged in
def update_workout():
    """Update workout information"""

    if request.method == "POST":
        db = get_db()
        # Retrieve form data
        workout_id = request.form.get("workout_id")
        completed_hours = request.form.get("completed_hours")
        planned_hours = request.form.get("planned_hours")
        workout_type = request.form.get("workout_type")
        distance = request.form.get("distance")
        comments = request.form.get("comments")
        date = request.form.get("date")
        title = request.form.get("title")

        # Ensure workout ID is provided
        if not workout_id:
            return apology("must provide a workout id", 400)

        # Validate hours
        try:
            if not completed_hours or int(completed_hours) <= 0:
                return apology("Completed hours must be greater than zero", 400)

            if planned_hours:
                if int(planned_hours) < 0:
                    return apology("Planned hours must be a positive number", 400)
            else:
                planned_hours = 0

            completed_hours = int(completed_hours)
            planned_hours = int(planned_hours)

        except ValueError:
            return apology("Both completed and planned hours must be valid numbers", 400)

        # Ensure at least one field (type, title, or comments) is provided
        if not (workout_type or title or comments):
            return apology("must provide more info (title, type, comments)", 400)

        # Ensure the date is provided
        if not date:
            return apology("must provide the date", 400)

        # Perform the update query in the database
        db.execute("UPDATE workout SET completed_hours = ?, planned_hours = ?, workout_type = ?, distance = ?, comments = ?, date = ?, title = ? WHERE id = ?", (
                   completed_hours, planned_hours, workout_type, distance, comments, date, title, workout_id,))
        db.commit()
        # Redirect to the homepage after successful update
        return redirect("/")

    else:
        db = get_db()
        # If the method is GET, retrieve workout ID from query parameters
        workout_id = request.args.get("id")  # Get workout_id from query params
        if not workout_id:
            return "Error: Workout ID is missing!", 400

        workout = db.execute(
                "SELECT * FROM workout WHERE id = ?", (workout_id,)).fetchone()
        # Render the update workout form, passing workout_id for context
        return render_template("update_workout.html", workout=workout)



@app.route("/update-workout-coach", methods=["GET", "POST"])
@coach_account_required
def update_workout_coach():
    """update workout coach"""
    if request.method == "POST":
        db = get_db()
        workout_id = request.form.get("workout_id")
        completed_hours = request.form.get("completed_hours")
        planned_hours = request.form.get("planned_hours")
        workout_type = request.form.get("workout_type")
        distance = request.form.get("distance")
        comments = request.form.get("comments")
        date = request.form.get("date")
        title = request.form.get("title")
        athlete_ids = request.form.getlist("athlete_ids[]")
        # Convert to ints if you need:
        athlete_ids = [int(a) for a in athlete_ids]

        # Validate hours
        try:
            if not completed_hours or int(completed_hours) <= 0:
                return apology("Completed hours must be greater than zero", 400)

            if planned_hours:
                if int(planned_hours) < 0:
                    return apology("Planned hours must be a positive number", 400)
            else:
                planned_hours = 0

            completed_hours = int(completed_hours)
            planned_hours = int(planned_hours)

        except ValueError:
            return apology("Both completed and planned hours must be valid numbers", 400)

        if not (workout_type or title or comments):
            return apology("must provide more info (title, type, comments)", 400)
        if not date:
            return apology("must provide the date", 400)
        if not athlete_ids:
            return apology("must provide an athlete(s)", 400)

        # Perform the update
        for athlete in athlete_ids:
            db.execute("UPDATE workout SET completed_hours = ?, planned_hours = ?, workout_type = ?, distance = ?, comments = ?, date = ?, title = ? WHERE id = ? AND athlete_id = ?",
                       (completed_hours, planned_hours, workout_type, distance, comments, date, title, workout_id, athlete,))
            db.commit()
        return redirect("/")

    else:
        db = get_db()
        # If the method is GET, retrieve workout ID from query parameters
        workout_id = request.args.get("id")  # Get workout_id from query params
        if not workout_id:
            return "Error: Workout ID is missing!", 400

        workout = db.execute(
                "SELECT * FROM workout WHERE id = ?", (workout_id,)).fetchone()
        # Render the update workout form, passing workout_id for context
        return render_template("update_workout_coach.html", workout=workout)
    

@app.route("/athlete")
@login_required  # Ensure the user is logged in
def index_athlete():
    """Show all athlete workouts"""

    if request.method == "GET":
        db = get_db()
        current_user = session["user_id"]

        # 1) fetch coach flag
        row = db.execute(
            "SELECT coach FROM users WHERE id = ?",
            (current_user,)
        ).fetchone()
        coach_flag = row["coach"] if row else 0

        # 2) decide whose log to show
        if coach_flag == 1:
            # coach: expect ?id=ATHLETE_ID
            athlete_id = request.args.get("id")
            if not athlete_id:
                return apology("must provide athlete id", 400)
            athlete_id = int(athlete_id)
        else:
            # non‐coach: only their own workouts
            athlete_id = current_user

        # 3) load workouts & user info
        workouts = db.execute(
            "SELECT * FROM workout WHERE user_id = ? ORDER BY date DESC",
            (athlete_id,)
        ).fetchall()
        user = db.execute(
            "SELECT username FROM users WHERE id = ?",
            (athlete_id,)
        ).fetchone()

        # 4) render template
        return render_template(
            "athlete.html",
            workouts=workouts,
            user=user,               # a Row with .username
            current_user=current_user  # if you need it in the template
        )




@app.route("/view-athletes")
@coach_account_required  # Ensure the user is a coach
def view_athletes():
    """Show all athletes"""

    if request.method == "GET":
        db = get_db()
        # Query all athletes (users who are not coaches) ordered by graduation year
        athletes = db.execute(
            "SELECT * FROM users WHERE coach = ? ORDER BY graduation_year DESC", (0,))

        # Render the athletes list in the template
        return render_template("view_athletes.html", athletes=athletes)


@app.route("/delete-workout", methods=["GET", "POST"])
@login_required  # Ensure the user is logged in
def delete_workout():
    """Delete workout"""

    if request.method == "POST":
        db = get_db()
        workout_id = request.form.get("workout_id")  # Get the workout ID from form data
        current_user = session["user_id"]  # Get the current user's ID

        if not workout_id:
            return apology("must provide the workout id", 400)

        # Delete the workout from the database if it belongs to the current user
        db.execute("DELETE FROM workout WHERE id = ? AND user_id = ?", (workout_id, current_user,))
        db.commit()
        return redirect("/")  # Redirect to the home page after deletion

    else:
        workout_id = request.args.get("id")  # Get workout_id from query params
        if not workout_id:
            return apology("Error: Workout ID is missing!", 400)

        # Render the delete workout confirmation page
        return render_template("delete_workout.html", workout_id=workout_id)



@app.route("/delete-workout-coach", methods=["GET", "POST"])
@coach_account_required  # Ensure the user is logged in
def delete_workout_coach():
    """delete workout from coach side"""
    if request.method == "POST":
        db = get_db()
        workout_id = request.form.get("workout_id")

        if not workout_id:
            return apology("must provide the workout id", 400)

        db.execute("DELETE FROM workout WHERE id = ?", workout_id)

        return redirect("/")

    else:
        db = get_db()
        workout_id = request.args.get("id")  # Get workout_id from query params
        if not workout_id:
            return apology("Error: Workout ID is missing!", 400)

        athletes = db.execute("SELECT id, username FROM users WHERE coach = ?", 0)
        return render_template("delete_workout_coach.html", athletes=athletes, workout_id=workout_id)


@app.route("/delete-account", methods=["GET", "POST"])
@coach_account_required  # Ensure the user is logged in and has coach privileges
def delete_account():
    """Delete account"""

    if request.method == "POST":
        db = get_db()
        athlete_id = request.form.get("athlete_ids")  # Get the selected athlete ID
        verification = request.form.get("verification")  # Verify the action before proceeding

        if not verification:
            return apology("must verify this action", 400)  # Ensure verification was provided

        if athlete_id:
            # If an athlete is selected, delete their related workouts and account
            db.execute("DELETE FROM workout WHERE user_id = ?", athlete_id)
            db.execute("DELETE FROM users WHERE id = ?", athlete_id)

        else:
            # If no athlete is selected, delete the coach's own account and log them out
            db.execute("DELETE FROM users WHERE id = ?", session["user_id"])
            logout()  # Log out the coach after deleting the account

        return redirect("/")  # Redirect to the home page after account deletion

    else:
        db = get_db()
        # If the request method is GET, fetch athletes' data and show the deletion form
        athletes = db.execute("SELECT id, username FROM users WHERE coach = ?", 0)
        return render_template("delete_account.html", athletes=athletes)



@app.route("/")
@login_required
def index():
    """Redirect to coach or athlete home based on role."""
    db = get_db()
    user = db.execute("SELECT coach FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if user["coach"] == 1:
        return redirect("/coach-home")
    else:
        return redirect("/athlete-home")


@app.route("/coach-home")
@login_required
@coach_account_required
def coach_home():
    """Render the coach’s dashboard page."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    return render_template("coach_home.html", user=user, coach=True)


from datetime import date, timedelta
import json

@app.route("/athlete-home")
@login_required
def athlete_home():
    """Render the athlete’s dashboard page with a 7-day calendar and pie‐chart data."""
    db = get_db()
    uid = session["user_id"]

    # 1) Build the 7-day window
    today = date.today()
    week_dates = [today - timedelta(days=i) for i in reversed(range(7))]

    start, end = week_dates[0].isoformat(), week_dates[-1].isoformat()

    # 2) Fetch and dedupe your workouts in that window
    rows = db.execute(
        "SELECT * FROM workout WHERE user_id = ? AND date BETWEEN ? AND ? ORDER BY date",
        (uid, start, end)
    ).fetchall()
    seen_ids = set()
    unique = []
    for w in rows:
        if w["id"] not in seen_ids:
            seen_ids.add(w["id"])
            unique.append(w)

    # 3) Group by date
    workouts_by_date = {d: [] for d in week_dates}
    for w in unique:
        d = w["date"] if isinstance(w["date"], date) else date.fromisoformat(w["date"])
        if d in workouts_by_date:
            workouts_by_date[d].append(w)


    today = date.today()

    # if we’re before May 1, then our current training year started last May 1…
    if today < date(today.year, 5, 1):
        start_year = date(today.year - 1, 5, 1)
        end_year   = date(today.year,     4, 15)
    else:
        # otherwise our current training year runs from this May 1 → next Apr 15
        start_year = date(today.year,     5, 1)
        end_year   = date(today.year + 1, 4, 15)

    # turn them into ISO strings for SQLite
    start_iso = start_year.isoformat()
    end_iso   = end_year.isoformat()

    # now your query will actually fall into the proper window
    total = db.execute(
        """
        SELECT SUM(completed_hours) AS total_hours
        FROM workout
        WHERE user_id = ?
        AND date BETWEEN ? AND ?
        """,
        (uid, start_iso, end_iso)
    ).fetchone()["total_hours"] or 0


    # 5) Aggregate by workout_type for the pie chart
    # Option A: do it in SQL
    agg = db.execute(
        """
        SELECT workout_type AS type,
               SUM(completed_hours) AS hours
        FROM workout
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY workout_type
        """,
        (uid, start_iso, end_iso,)
    ).fetchall()
    types = [row["type"] for row in agg]
    hours_by_type = [row["hours"] for row in agg]

    # Finally render, passing the two new lists into `workout`
    return render_template(
        "athlete_home.html",
        user=db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone(),
        coach=False,
        workout={
            "total_hours": total,
            "types": types,
            "hours_by_type": hours_by_type
        },
        week_dates=week_dates,
        workouts_by_date=workouts_by_date
    )


@app.route("/strava/auth")
@login_required
def strava_auth():
    if "user_id" not in session:
        return apology("You must log in to access this page", 403)

    # Load configuration from config.json
    with open("config.json") as config_file:
        config = json.load(config_file)

    client_id = config.get("client_id")
    # Use 127.0.0.1 instead of localhost
    redirect_uri = config.get("REDIRECT_URI", "http://127.0.0.1:5000/strava/callback")
    scope = "activity:read_all"

    print(f"Client ID: {client_id}, Redirect URI: {redirect_uri}")
    
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
    app.logger.debug("Strava OAuth URL → %s", auth_url)
    return redirect(auth_url)


@app.route("/strava/callback")
@login_required
def strava_callback():
    app.logger.debug("--------------------")
    app.logger.debug("Callback route triggered")
    code = request.args.get("code")
    scope = request.args.get("scope", "")
    
    if not code:
        app.logger.error("Authorization failed: No code received")
        return apology("Authorization failed", 400)

    app.logger.debug(f"Authorization code received: {code}")

    with open("config.json") as config_file:
        config = json.load(config_file)

    client_id = config.get("client_id")
    client_secret = config.get("client_secret")

    # Exchange the code for an access token
    response = requests.post(
        "https://www.strava.com/api/v3/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
    )

    if response.status_code != 200:
        app.logger.error(f"Failed to retrieve access token: {response.text}")
        return apology("Failed to retrieve access token", 400)

    token_data = response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_at = token_data["expires_at"]

    app.logger.debug(f"Access Token: {access_token}, Refresh Token: {refresh_token}, Expires At: {expires_at}")

    # Save tokens to the database with scope
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO refresh_tokens 
        (athlete_id, refresh_token_code, scope)
        VALUES (?, ?, ?)
    """, (session["user_id"], refresh_token, scope))
    
    db.execute("""
        INSERT OR REPLACE INTO short_lived_access_tokens 
        (athlete_id, access_token, expires_at)
        VALUES (?, ?, ?)
    """, (session["user_id"], access_token, expires_at))
    
    db.commit()

    return redirect("/athlete-home")


@app.route("/strava/sync")
@login_required
def strava_sync():
    activities = fetch_strava_activities(session["user_id"])
    db = get_db()

    for activity in activities:
        db.execute("""
            INSERT OR IGNORE INTO workout (user_id, completed_hours, workout_type, date, distance, title)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            activity["elapsed_time"] / 3600,  # Convert seconds to hours
            activity["type"],
            activity["start_date_local"].split("T")[0],
            activity.get("distance", 0) / 1000,  # Convert meters to kilometers
            activity["name"]
        ))
    db.commit()

    return redirect("/athlete-home")

@app.route("/debug-tokens")
@login_required
def debug_tokens():
    db = get_db()
    refresh_token = db.execute("SELECT * FROM refresh_tokens WHERE athlete_id = ?", (session["user_id"],)).fetchone()
    access_token = db.execute("SELECT * FROM short_lived_access_tokens WHERE athlete_id = ?", (session["user_id"],)).fetchone()
    return {
        "refresh_token": refresh_token,
        "access_token": access_token
    }

# *** finally, at the very bottom of the file: ***
if __name__ == "__main__":
    app.run(debug=True)
