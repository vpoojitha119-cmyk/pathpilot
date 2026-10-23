
# PathPilot – Student Skill-to-Opportunity Intelligence

PathPilot is a web-based student opportunity platform designed to help students manage their skills and discover suitable internships and career opportunities. It provides a centralized dashboard for students to explore opportunities and track their applications.

## Live Demo

https://pathpilot-15.onrender.com/

## Project Objectives

- Help students manage their skills.
- Display internship and career opportunities.
- Help students track their applications.
- Provide a dashboard for student activities.
- Provide administrative features to manage opportunities and applications.

## Technologies Used

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask

### Database
- MySQL

### Development Tools
- Visual Studio Code
- Git and GitHub
- Render for deployment

## Key Features

- Student registration and login
- Student dashboard
- Skills management
- Internship and opportunity listings
- Opportunity recommendations
- Application tracking
- Student profile management
- Notifications
- Admin login and administration panel
- Database integration using MySQL

## Database

PathPilot uses MySQL to store and manage application data.

Main database tables include:
- students
- skills
- student_skills
- opportunities
- opportunity_skills
- applications

## Project Structure

PathPilot/
├── app.py
├── pathpilot.sql
├── templates/
├── static/
├── .gitignore
└── README.md

## How to Run Locally

1. Clone the repository:

   git clone https://github.com/vpoojitha119-cmyk/pathpilot.git

2. Open the project folder:

   cd pathpilot

3. Create and activate a Python virtual environment.

4. Install the required packages:

   pip install Flask mysql-connector-python

5. Create the MySQL database and configure your database connection using your local environment variables.

6. Start the Flask application:

   python app.py

7. Open the local address shown in the terminal.

## Project Outcome

PathPilot brings student skills, internships, and application tracking together in one platform. It aims to make opportunity discovery and career preparation easier for students.

## Author

Poojitha

## License

Created for educational and academic project purposes.
