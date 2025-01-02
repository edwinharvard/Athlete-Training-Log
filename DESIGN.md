# Design Document for Harvard Nordic Ski Team Training Log

## Introduction

The Harvard Nordic Ski Team Training Log is a web application I built with Flask to track training logs for athletes. It allows coaches to log and manage workouts, while athletes can view and update their training logs. The system includes features like user authentication, workout tracking, and role-based access control, ensuring that only coaches can manage workouts and athletes can only view and add their own logs. This design document discusses the technical implementation and design decisions made during the development of the project.

## Architecture Overview

### Technology Stack

- **Backend**: The application uses **Flask**, a lightweight Python web framework, to handle routing, user authentication, and interaction with the database. Flask was chosen for its simplicity and flexibility, making it ideal for building a small web application like this.
- **Database**: The app uses **SQLite**, a serverless, self-contained SQL database engine. SQLite was chosen because it's lightweight, easy to set up, and integrates well with Flask via the **CS50** library. This choice simplifies the deployment process since it doesn't require setting up a separate database server.
- **Frontend**: The user interface is built with **Bootstrap 5** for responsive design, ensuring a consistent experience across different devices. Custom CSS is used to handle styling specific to the project.
- **User Authentication**: The application uses session-based authentication provided by Flask's built-in `session` object, where user credentials are checked on login. The app employs password hashing to store passwords securely in the database.

## Key Design Decisions

### User Roles and Access Control

The application supports two user roles: **Coach** and **Athlete**. This role-based access control ensures that the correct permissions are granted to each type of user.

- **Coach**: Can manage workouts (create, update, delete), assign workouts to athletes, and view athlete logs. This role requires more privileges, which is why coaches are identified in the database with a boolean field (`coach`) set to `1`.
- **Athlete**: Can only view and add their own workouts and see their progress. They can update their profile details but cannot modify the workouts of others.

The role-based access is implemented via a `coach_account_required` decorator, which ensures that only users with the `coach` field set to `1` can access coach-specific routes. The decorator is used in key parts of the application like adding or deleting workouts for athletes.

### Database Schema

The database schema was designed to be simple yet effective for tracking workouts and users. The main entities in the database are **Users** and **Workouts**.

- **Users** Table:
  - `id`: Unique identifier for each user.
  - `username`: The user's name or username. The username must be unique
  - `password`: Hashed password for secure authentication.
  - `coach`: A boolean field indicating whether the user is a coach or an athlete.
  - `training_hours`: Total number of hours spent training.
  - `graduation_year`: The athlete’s expected graduation year.

- **Workouts** Table:
  - `id`: Unique identifier for each workout.
  - `user_id`: Foreign key linking the workout to a user (athlete).
  - `title`: A brief title or description of the workout.
  - `workout_type`: The type of workout (e.g., endurance, strength, interval, skiing, running).
  - `distance`: The distance of the workout (if applicable)
  - `planned_hours`: Number of hours the athlete or coach planned for the workout.
  - `completed_hours`: Number of hours actually completed during the workout.
  - `comments`: Additional comments or notes related to the workout.
  - `date`: The date the workout was performed.

```bash
project/ $ sqlite3 training_log.db
```

```
-- Users Table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT,
    planned_hours INTEGER,
    graduation_year INTEGER,
    coach BOOLEAN
);

-- Workouts Table
CREATE TABLE workout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    completed_hours INTEGER,
    workout_type TEXT,
    distance REAL,
    comments TEXT,
    date DATE,
    planned_hours INTEGER,
    title TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

The relationships between the **Users** and **Workouts** tables are straightforward, with a one-to-many relationship between users (athletes and coaches) and workouts, where each user can have multiple workouts.

### Routing and Request Handling

Routes are defined for every significant action the user can perform:

- **Home Page**: Displays the logged-in user’s details, including a link to their relevant actions.
- **Login and Registration**: Manages user authentication, including password hashing using Flask's `werkzeug.security` module.
- **Workouts Management**: Coaches can add, update, or delete workouts through dedicated routes (`/add-workout`, `/update-workout`, `/delete-workout`). These routes are protected by role-based decorators to ensure that only users with the correct privileges (coaches or the workout owner) can access them.
- **Profile Management**: Users can update their username, password, and other profile information using the `/update-profile` route.

### Error Handling

Error handling is implemented via custom error pages, including the **Apology Page**. When an action cannot be completed (e.g., unauthorized access or invalid data input), the user is shown a detailed error message with a relevant HTTP status code. For instance, if an athlete attempts to modify another user's workout, the system will return a 401 Unauthorized error with an apology page displaying the message “You must have a coach’s account to perform this action.”

### Form Validation and Data Integrity

To ensure proper data integrity, form validation is handled both on the frontend (via HTML5 attributes such as `required`, `min`, and `max`) and on the backend (via custom Flask validation). For example:
- When adding or updating workouts, the form fields for planned and completed hours are validated to ensure they are positive integers.
- The password fields during user registration are also checked for validity, and users are prevented from entering mismatched passwords.


### JavaScript Functionality

The JavaScript in this template is responsible for adding a "Clear Selections" button below the athlete selection dropdown. When clicked, it clears all selected athletes in the dropdown. This makes it easier for coaches to reset their selection before submitting the form.

- The script listens for the document's `DOMContentLoaded` event to ensure the page is fully loaded before executing.
- It creates a button with the label "Clear Selections" and styles it with Bootstrap's classes.
- When the button is clicked, it loops through the `<select>` options and sets `selected` to `false` for each option, effectively clearing the selection.


### Security Considerations

The application includes basic security features:
- **Password Hashing**: Passwords are hashed using the `werkzeug.security` library’s `generate_password_hash` and `check_password_hash` functions to ensure passwords are securely stored and not kept in plain text.
- **Session Management**: User sessions are managed using Flask's `session` object, and users are automatically logged out when they close the browser or after a session timeout.

## Conclusion

The Harvard Nordic Ski Team Training Log is a web application that allows athletes and coaches to manage training logs and track progress. The decision to use Flask, SQLite, and Bootstrap enabled rapid development while maintaining flexibility and scalability. Role-based access control ensures secure and appropriate access to different features based on the user's role, while the application’s error handling and validation mechanisms provide a smooth and secure experience. This design document outlines the key design decisions and technical implementation choices made to ensure the application meets both functional and non-functional requirements.
