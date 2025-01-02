# Harvard Nordic Ski Team Training Log

## Running the Application on CS50.dev

### Step-by-Step Instructions

To run this project without needing to install anything on your local machine, follow these instructions to use CS50.dev:

1. **Download the Project Folder**:
   - Download the project folder `project` to your local machine from the repository or project link.

2. **Go to CS50.dev**:
   - Open [CS50.dev](https://cs50.dev) in your browser. This is an online environment that allows you to run web projects without any setup.

3. **Upload the Project Folder**:
   - Upload the `project` folder that you downloaded in Step 1.

4. **Navigate to the Project Folder**:
   - After uploading the project, open the terminal in CS50.dev and **cd** into the project folder:
     ```bash
     cd project
     ```

5. **Run the Flask Application**:
   - Once you're inside the project folder, run the Flask application using the command:
     ```bash
     flask run
     ```

6. **Access the App**:
   - Once the server is running, you can access the application through CS50.dev’s provided web URL.

7. **Register and Log In**:
   - After opening the app in the browser, you can register as either a coach or an athlete.
   - Coaches can log workouts and assign them to athletes.
   - Athletes can view their assigned workouts and make updates.

### Expected Behavior

Once the app is running, the main functionalities should include:

- **Coach Dashboard**:
   - Coaches can log workout details, including planned hours, completed hours, and workout type.
   - Coaches can assign workouts to specific athletes and manage workouts via the coach dashboard.
   - Coaches can update or delete athlete accounts (can also delete their own account)
   - Coaches can also see a list of all athletes.

- **Athlete Dashboard**:
   - Athletes can see their workouts, including details like workout type and hours.
   - Athletes can update their workouts or remove them.

### Features for Coaches:
- Coaches have access to the following functionalities:
  - **Workout Creation/Update**: Coaches can log new workouts, set planned and completed hours, and provide descriptions and comments.
  - **Assign Athletes**: Coaches can assign logged workouts to specific athletes.
  - **Workout Deletion**: Coaches can delete workouts that may be outdated or incorrect.
  - **Account Management**: Coaches can update or delete their own account via the account settings.

### Features for Athletes:
- Athletes can:
  - View their workout history.
  - Update their current workouts
  - Delete workouts

## Technical Details

- **Framework**: The project uses Flask, a lightweight Python web framework.
- **Database**: SQLite is used to store user data and workout logs. The database is configured to automatically create tables when the application is first run.
- **Styling**: The app uses Bootstrap 5 for responsive and modern styling.
- **Authentication**: The app implements a login system with basic authentication (using Flask's session management). Passwords are securely hashed using the `werkzeug.security` module.

### Database Schema
The following tables are created in the database:
- **Users**: Stores user information including their role (coach or athlete).
- **Workouts**: Stores details of each workout logged, including time, type, distance, and assigned athlete(s).

## Troubleshooting

- **App Not Starting**: If the app is not starting, ensure that you’ve followed the setup instructions correctly, especially when installing dependencies and setting up the database.
- **Database Issues**: If the database is not found or data isn't appearing as expected, ensure you’ve run the appropriate commands to set up the SQLite database.
- **Logging In**: If you are unable to log in, make sure your credentials are correct and your account is registered as either a coach or athlete.


## Video Link: https://youtu.be/Xur6qTCSloQ
