import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, coach_account_required

app = Flask(__name__)
app.secret_key = 'ryerson_project2'

if __name__ == '__main__':
    app.run(debug=True)

db = SQL("sqlite:///training_log.db")


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
        password_hash = generate_password_hash(password)

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
                       username, password_hash, planned_hours, graduation_year, coach)
        except:
            # Handle the case where the username already exists in the database
            return apology("username already exists", 400)

        # Retrieve the user details from the database to store in the session
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Set the user session with the user's ID
        session["user_id"] = rows[0]["id"]

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

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["password_hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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


@app.route("/update-account", methods=["GET", "POST"])
@coach_account_required
def update_account():
    """Update account information for the logged-in user or an athlete"""

    if request.method == "POST":
        # Retrieve the form data submitted by the user
        athlete_id = request.form.getlist("athlete_ids")  # List of selected athlete IDs
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
        password_hash = hash(password) if password else None

        # Retrieve the current user's ID from the session
        current_user = session["user_id"]

        # If an athlete is selected, handle updating their info
        if athlete_id:
            # Make sure we only have one athlete selected (otherwise return an error)
            if len(athlete_id) != 1:
                return apology("Please select only one athlete to update", 400)
            athlete_id = athlete_id[0]  # Extract the single athlete ID
            current_user = athlete_id  # Update the current user to the selected athlete
            try:
                # Perform the update for the username, password, planned hours, and graduation year
                db.execute("""
                    UPDATE users
                    SET username = ?,
                        password_hash = ?,
                        planned_hours = ?,
                        graduation_year = ?
                    WHERE id = ?
                """, username, password_hash, planned_hours, graduation_year, current_user)
            except Exception as e:
                # Catch any database errors (e.g., if the username already exists) and show an error message
                return apology(f"Error: {e}", 400)

        # Redirect to the homepage after the update is successful
        return redirect("/")


    else:
        # If the request method is GET, render the update account page
        # Retrieve all athletes that the current user (coach) can manage
        athletes = db.execute("SELECT id, username FROM users WHERE coach = ?", 0)
        return render_template("update_account.html", athletes=athletes)




@app.route("/add-workout", methods=["GET", "POST"])
@login_required
def add_workout():
    """Create a new workout entry"""

    if request.method == "POST":
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
                return apology("Completed hours must be a positive number", 400)

            if not planned_hours or int(planned_hours) <= 0:
                return apology("Planned hours must be a positive number", 400)

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
                   current_user, completed_hours, workout_type, date, distance, comments, planned_hours, title)

        return redirect("/")

    # GET request: render form
    else:
        return render_template("add_workout.html")



@app.route("/add-workout-coach", methods=["GET", "POST"])
@coach_account_required
def add_workout_coach():
    """create workout"""

    if request.method == "POST":
        completed_hours = request.form.get("completed_hours") or 'N/A'
        planned_hours = request.form.get("planned_hours") or 'N/A'
        workout_type = request.form.get("workout_type") or 'N/A'
        distance = request.form.get("distance") or 'N/A'
        comments = request.form.get("comments") or 'N/A'
        date = request.form.get("date")
        title = request.form.get("title") or 'N/A'
        athlete_ids = request.form.getlist("athlete_ids")

        # Validate that hours are provided and are positive numbers
        try:
            if not completed_hours or int(completed_hours) <= 0:
                return apology("Completed hours must be a positive number", 400)

            if not planned_hours or int(planned_hours) <= 0:
                return apology("Planned hours must be a positive number", 400)

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
                       int(athlete_id), completed_hours, workout_type, distance, comments, date, planned_hours, title)

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        athletes = db.execute("SELECT id, username FROM users WHERE coach = ?", 0)
        return render_template("add_workout_coach.html", athletes=athletes)


@app.route("/update-workout", methods=["GET", "POST"])
@login_required  # Ensure the user is logged in
def update_workout():
    """Update workout information"""

    if request.method == "POST":
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

        # Validate that hours are provided and are positive numbers
        try:
            if not completed_hours or int(completed_hours) <= 0:
                return apology("Completed hours must be a positive number", 400)

            if not planned_hours or int(planned_hours) <= 0:
                return apology("Planned hours must be a positive number", 400)

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
        db.execute("UPDATE workout SET completed_hours = ?, planned_hours = ?, workout_type = ?, distance = ?, comments = ?, date = ?, title = ? WHERE id = ?",
                   completed_hours, planned_hours, workout_type, distance, comments, date, title, workout_id)

        # Redirect to the homepage after successful update
        return redirect("/")

    else:
        # If the method is GET, retrieve workout ID from query parameters
        workout_id = request.args.get("id")  # Get workout_id from query params
        if not workout_id:
            return "Error: Workout ID is missing!", 400

        # Render the update workout form, passing workout_id for context
        return render_template("update_workout.html", workout_id=workout_id)



@app.route("/update-workout-coach", methods=["GET", "POST"])
@coach_account_required
def update_workout_coach():
    """update workout coach"""
    if request.method == "POST":
        workout_id = request.form.get("workout_id")
        completed_hours = request.form.get("completed_hours")
        planned_hours = request.form.get("planned_hours")
        workout_type = request.form.get("workout_type")
        distance = request.form.get("distance")
        comments = request.form.get("comments")
        date = request.form.get("date")
        title = request.form.get("title")
        athlete_ids = request.form.getlist("athlete_ids")

        # Validate that hours are provided and are positive numbers
        try:
            if not completed_hours or int(completed_hours) <= 0:
                return apology("Completed hours must be a positive number", 400)

            if not planned_hours or int(planned_hours) <= 0:
                return apology("Planned hours must be a positive number", 400)

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
                       completed_hours, planned_hours, workout_type, distance, comments, date, title, workout_id, athlete)

        return redirect("/")

    else:
        workout_id = request.args.get("id")  # Get workout_id from query params
        if not workout_id:
            return apology("Error: Workout ID is missing!", 400)

        return render_template("update_workout_coach.html", workout_id=workout_id)


@app.route("/athlete")
@login_required  # Ensure the user is logged in
def index_athlete():
    """Show all athlete workouts"""

    if request.method == "GET":
        current_user = session["user_id"]
        current_user = [session["user_id"]]  # Current logged-in user's ID

        # Check if the current user is a coach
        coach_status = db.execute("SELECT coach FROM users WHERE id = ?", session.get("user_id"))

        # If not a coach, show the logged-in athlete's workouts
        if coach_status[0]['coach'] != 1:
            workouts = db.execute(
                "SELECT * FROM workout WHERE user_id = ? ORDER BY date ASC", current_user[0])
            user = db.execute("SELECT username FROM users WHERE id = ?", current_user[0])
        else:
            # If a coach, get the athlete's ID from query params
            athlete_id = request.args.get("id")
            if not athlete_id:
                return apology("Error: Athlete ID is missing!", 400)
            workouts = db.execute(
                "SELECT * FROM workout WHERE user_id = ? ORDER BY date ASC", athlete_id)
            user = db.execute("SELECT username FROM users WHERE id = ?", athlete_id)
            current_user = db.execute("SELECT coach FROM users WHERE id = ?", current_user[0])

        # Render workouts for the athlete (or selected athlete)
        return render_template("athlete.html", workouts=workouts, user=user[0], current_user=current_user[0])



@app.route("/view-athletes")
@coach_account_required  # Ensure the user is a coach
def view_athletes():
    """Show all athletes"""

    if request.method == "GET":
        # Query all athletes (users who are not coaches) ordered by graduation year
        athletes = db.execute(
            "SELECT * FROM users WHERE coach = ? ORDER BY graduation_year DESC", 0)

        # Render the athletes list in the template
        return render_template("view_athletes.html", athletes=athletes)


@app.route("/delete-workout", methods=["GET", "POST"])
@login_required  # Ensure the user is logged in
def delete_workout():
    """Delete workout"""

    if request.method == "POST":
        workout_id = request.form.get("workout_id")  # Get the workout ID from form data
        current_user = session["user_id"]  # Get the current user's ID

        if not workout_id:
            return apology("must provide the workout id", 400)

        # Delete the workout from the database if it belongs to the current user
        db.execute("DELETE FROM workout WHERE id = ? AND user_id = ?", workout_id, current_user)

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
        workout_id = request.form.get("workout_id")

        if not workout_id:
            return apology("must provide the workout id", 400)

        db.execute("DELETE FROM workout WHERE id = ?", workout_id)

        return redirect("/")

    else:
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
        # If the request method is GET, fetch athletes' data and show the deletion form
        athletes = db.execute("SELECT id, username FROM users WHERE coach = ?", 0)
        return render_template("delete_account.html", athletes=athletes)



@app.route("/")
@login_required  # Ensure the user is logged in
def index():
    """Render homepage"""

    if request.method == "GET":
        current_user = session["user_id"]  # Get the ID of the logged-in user
        coach = False  # Default to not being a coach

        # Fetch the user's details from the database
        user = db.execute("SELECT * FROM users WHERE id = ?", current_user)

        # Check if the user is a coach
        if user[0]["coach"] == 1:
            coach = True  # Set coach to True if the user is a coach

        # Render the homepage template, passing user data and coach status
        return render_template("index.html", user=user[0], coach=coach)

