
import os
import re
from flask import (
    Flask, render_template, jsonify, request,
    redirect, url_for, flash, session
)
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import (
    check_password_hash, generate_password_hash
)
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is missing from your .env file")


# --------------------------------------------------
# FLASK-LOGIN CONFIGURATION (ADMIN)
# --------------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"


class AdminUser(UserMixin):
    def __init__(self, username):
        self.id = username


@login_manager.user_loader
def load_user(user_id):
    admin_username = os.getenv("ADMIN_USERNAME")

    if user_id == admin_username:
        return AdminUser(user_id)

    return None


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Admin login required"}), 401

    return redirect(url_for("admin_login"))


# --------------------------------------------------
# MYSQL CONNECTION
# --------------------------------------------------

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="pathpilot"
    )


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# STUDENT REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        branch = request.form.get("branch", "").strip()
        year = request.form.get("year", "")

        if not all([name, email, password, branch, year]):
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "error"
            )
            return redirect(url_for("register"))

        try:
            year_value = int(year)

            if year_value < 1 or year_value > 8:
                raise ValueError

        except ValueError:
            flash("Please enter a valid academic year.", "error")
            return redirect(url_for("register"))

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO students
                    (name, email, password_hash, branch, year, role)
                VALUES (%s, %s, %s, %s, %s, 'student')
                """,
                (
                    name,
                    email,
                    generate_password_hash(password),
                    branch,
                    year_value
                )
            )

            conn.commit()

            flash(
                "Registration successful! Please log in.",
                "success"
            )
            return redirect(url_for("login"))

        except mysql.connector.IntegrityError:
            flash("This email is already registered.", "error")
            return redirect(url_for("register"))

        except mysql.connector.Error:
            app.logger.exception("Student registration failed")
            flash("Registration failed. Please try again.", "error")
            return redirect(url_for("register"))

        finally:
            if cursor is not None:
                cursor.close()

            if conn is not None and conn.is_connected():
                conn.close()

    return render_template("register.html")


# --------------------------------------------------
# STUDENT LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT student_id, password_hash, role
                FROM students
                WHERE email = %s
                """,
                (email,)
            )

            student = cursor.fetchone()

            if (
                student
                and student[2] == "student"
                and check_password_hash(student[1], password)
            ):
                session.clear()
                session["student_id"] = student[0]
                session["student_email"] = email

                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        except mysql.connector.Error:
            app.logger.exception("Student login failed")
            flash("Unable to log in. Please try again.", "error")
            return redirect(url_for("login"))

        finally:
            if cursor is not None:
                cursor.close()

            if conn is not None and conn.is_connected():
                conn.close()

    return render_template("login.html")


# --------------------------------------------------
# STUDENT DASHBOARD WITH SAVED SKILLS
# --------------------------------------------------

@app.route("/dashboard")
def dashboard():
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get student details
        cursor.execute(
            """
            SELECT name, email, branch, year
            FROM students
            WHERE student_id = %s
            """,
            (session["student_id"],)
        )

        student = cursor.fetchone()

        if student is None:
            session.clear()
            return redirect(url_for("login"))

        # Get this student's saved skills and proficiency
        cursor.execute(
            """
            SELECT s.skill_name, ss.proficiency
            FROM student_skills ss
            JOIN skills s ON s.skill_id = ss.skill_id
            WHERE ss.student_id = %s
            ORDER BY s.skill_name
            """,
            (session["student_id"],)
        )

        skills = cursor.fetchall()

        # Count saved skills
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM student_skills
            WHERE student_id = %s
            """,
            (session["student_id"],)
        )
        skills_count = cursor.fetchone()["total"]

        # Count applications
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM applications
            WHERE student_id = %s
            """,
            (session["student_id"],)
        )
        applications_count = cursor.fetchone()["total"]

        # Count opportunities matching saved skills
        cursor.execute(
            """
            SELECT COUNT(DISTINCT os.opportunity_id) AS total
            FROM opportunity_skills os
            JOIN student_skills ss
                ON os.skill_id = ss.skill_id
            WHERE ss.student_id = %s
            """,
            (session["student_id"],)
        )
        recommendations_count = cursor.fetchone()["total"]

        return render_template(
            "dashboard.html",
            student=student,
            skills=skills,
            skills_count=skills_count,
            applications_count=applications_count,
            recommendations_count=recommendations_count
        )
        
     


    except mysql.connector.Error:
        app.logger.exception("Could not load student dashboard")
        return "Unable to load dashboard. Please try again.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


# --------------------------------------------------
# STUDENT PROFILE
# --------------------------------------------------

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    conn = None
    cursor = None
    student_id = session["student_id"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            branch = request.form.get("branch", "").strip()
            year = request.form.get("year", "").strip()

            if not all([name, email, branch, year]):
                flash("Please fill in all fields.", "error")
                return redirect(url_for("profile"))

            if len(name) > 100 or len(branch) > 50:
                flash("Name or branch is too long.", "error")
                return redirect(url_for("profile"))

            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                flash("Please enter a valid email address.", "error")
                return redirect(url_for("profile"))

            try:
                year_value = int(year)
                if year_value < 1 or year_value > 8:
                    raise ValueError
            except ValueError:
                flash("Please enter a valid academic year.", "error")
                return redirect(url_for("profile"))

            cursor.execute(
                """
                UPDATE students
                SET name = %s, email = %s, branch = %s, year = %s
                WHERE student_id = %s AND role = 'student'
                """,
                (name, email, branch, year_value, student_id)
            )

            conn.commit()
            session["student_email"] = email
            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile"))

        cursor.execute(
            """
            SELECT student_id, name, email, branch, year, created_at
            FROM students
            WHERE student_id = %s AND role = 'student'
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        if student is None:
            session.clear()
            flash("Please log in again.", "error")
            return redirect(url_for("login"))

        return render_template("profile.html", student=student)

    except mysql.connector.IntegrityError:
        if conn is not None and conn.is_connected():
            conn.rollback()

        flash("That email address is already registered.", "error")
        return redirect(url_for("profile"))

    except mysql.connector.Error:
        if conn is not None and conn.is_connected():
            conn.rollback()

        app.logger.exception("Could not update student profile")
        return "Unable to update your profile. Please try again.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()

# --------------------------------------------------
# STUDENT LOGOUT
# --------------------------------------------------

@app.route("/logout")
def student_logout():
    session.pop("student_id", None)
    session.pop("student_email", None)

    flash("You have logged out successfully.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------
# OPPORTUNITIES PAGE
# --------------------------------------------------

@app.route("/opportunities")
def opportunities():
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    return render_template("opportunities.html")


# --------------------------------------------------
# SMART INTERNSHIP RECOMMENDATIONS
# --------------------------------------------------

import re

@app.route("/recommendations")
def recommendations():
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        student_id = session["student_id"]

        # Get the student's saved skills
        cursor.execute(
            """
            SELECT skill_id, proficiency
            FROM student_skills
            WHERE student_id = %s
            """,
            (student_id,)
        )
        student_skills = cursor.fetchall()

        # Get all internships and their required skills
        cursor.execute(
            """
            SELECT
                o.opportunity_id,
                o.title,
                o.company,
                o.description,
                o.stipend,
                o.application_url,
                s.skill_id,
                s.skill_name
            FROM opportunities o
            LEFT JOIN opportunity_skills os
                ON o.opportunity_id = os.opportunity_id
            LEFT JOIN skills s
                ON os.skill_id = s.skill_id
            ORDER BY o.opportunity_id
            """
        )
        rows = cursor.fetchall()

        # Count the student's skills
        student_skill_ids = {
            skill["skill_id"] for skill in student_skills
        }

        # Group required skills under each internship
        internships = {}

        for row in rows:
            opportunity_id = row["opportunity_id"]

            if opportunity_id not in internships:
                internships[opportunity_id] = {
                    "opportunity_id": opportunity_id,
                    "title": row["title"],
                    "company": row["company"],
                    "description": row["description"],
                    "stipend": row["stipend"],
                    "application_url": row["application_url"],
                    "required_skills": [],
                    "matched_skills": []
                }

            if row["skill_id"] is not None:
                internships[opportunity_id]["required_skills"].append(
                    {
                        "skill_id": row["skill_id"],
                        "skill_name": row["skill_name"]
                    }
                )

        # Compare skill IDs rather than description text
        results = []

        for internship in internships.values():
            required = internship["required_skills"]

       
        # Skills the student already has
  
            matched = [
    skill["skill_name"]
    for skill in required
    if skill["skill_id"] in student_skill_ids
]
            # Skills the student still needs to learn
            missing = [
    skill["skill_name"]
    for skill in required
    if skill["skill_id"] not in student_skill_ids
]
            internship["matched_skills"] = matched
            internship["missing_skills"] = missing

            if required:
                internship["match_percent"] = round(
                    len(matched) / len(required) * 100
                )
            else:
                internship["match_percent"] = 0

            if matched:
                results.append(internship)

        results.sort(
            key=lambda item: item["match_percent"],
            reverse=True
        )

        return render_template(
            "recommendations.html",
            recommendations=results,
            has_skills=bool(student_skills)
        )

    except mysql.connector.Error:
        app.logger.exception("Could not load internship recommendations")
        return "Unable to load recommendations. Please try again.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()



# --------------------------------------------------
# SKILLS PAGE
# --------------------------------------------------

@app.route("/skills")
def skills():
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    return render_template("skills.html")


# --------------------------------------------------
# SAVE AND LOAD STUDENT SKILLS
# --------------------------------------------------

@app.route("/api/student-skills", methods=["GET", "POST"])
def student_skills_api():
    if "student_id" not in session:
        return jsonify({"error": "Please log in first."}), 401

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        student_id = session["student_id"]

        # Load saved skills
        if request.method == "GET":
            cursor.execute(
                """
                SELECT s.skill_name, ss.proficiency
                FROM student_skills ss
                JOIN skills s ON s.skill_id = ss.skill_id
                WHERE ss.student_id = %s
                ORDER BY s.skill_name
                """,
                (student_id,)
            )

            return jsonify(cursor.fetchall())

        # Read selected skills from the page
        data = request.get_json(silent=True) or {}
        selected_skills = data.get("skills", [])

        if not isinstance(selected_skills, list):
            return jsonify({"error": "Invalid skills data."}), 400

        # Validate the submitted skills
        for item in selected_skills:
            if not isinstance(item, dict):
                return jsonify({"error": "Invalid skill entry."}), 400

            name = item.get("name")
            level = item.get("proficiency")

            if (
                not isinstance(name, str)
                or not name.strip()
                or level not in [
                    "Beginner", "Intermediate", "Advanced"
                ]
            ):
                return jsonify({
                    "error": "Invalid skill or proficiency level."
                }), 400

        # Save all selections as one transaction
        conn.start_transaction()

        cursor.execute(
            "DELETE FROM student_skills WHERE student_id = %s",
            (student_id,)
        )

        for item in selected_skills:
            name = item["name"].strip()
            level = item["proficiency"]

            cursor.execute(
                "INSERT IGNORE INTO skills (skill_name) VALUES (%s)",
                (name,)
            )

            cursor.execute(
                "SELECT skill_id FROM skills WHERE skill_name = %s",
                (name,)
            )

            result = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO student_skills
                    (student_id, skill_id, proficiency)
                VALUES (%s, %s, %s)
                """,
                (student_id, result["skill_id"], level)
            )

        conn.commit()

        return jsonify({
            "message": "Your skills have been saved!"
        })

    except mysql.connector.Error:
        if conn is not None and conn.is_connected():
            conn.rollback()

        app.logger.exception("Saving student skills failed")

        return jsonify({
            "error": "Could not save skills. Please try again."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


# --------------------------------------------------
# DISPLAY INTERNSHIPS (PUBLIC GET API)
# --------------------------------------------------

@app.route("/api/opportunities", methods=["GET"])
def api_opportunities():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT opportunity_id, title, company, description,
                   stipend, application_url
            FROM opportunities
            ORDER BY opportunity_id DESC
            """
        )

        return jsonify(cursor.fetchall())

    except mysql.connector.Error:
        app.logger.exception("Could not load opportunities")
        return jsonify({"error": "Could not load opportunities."}), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# --------------------------------------------------
# ADMIN LOGIN
# --------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin_username = os.getenv("ADMIN_USERNAME")
        password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")

        if (
            username == admin_username
            and password_hash
            and check_password_hash(password_hash, password)
        ):
            session.clear()
            login_user(AdminUser(username))
            return redirect(url_for("admin"))

        flash("Invalid username or password.", "error")

    return render_template("admin_login.html")


# --------------------------------------------------
# ADMIN LOGOUT
# --------------------------------------------------

@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("admin_login"))


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------


@app.route("/admin")
@login_required
def admin():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM students WHERE role = 'student'"
        )
        total_students = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM opportunities")
        total_opportunities = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM applications")
        total_applications = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM notifications")
        total_notifications = cursor.fetchone()[0]

        return render_template(
            "admin.html",
            total_students=total_students,
            total_opportunities=total_opportunities,
            total_applications=total_applications,
            total_notifications=total_notifications
        )

    except mysql.connector.Error:
        app.logger.exception("Could not load admin dashboard statistics")
        return "Unable to load admin dashboard. Check the database connection.", 500

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


# --------------------------------------------------
# VIEW ALL STUDENT APPLICATIONS (ADMIN ONLY)
# --------------------------------------------------

@app.route("/admin/applications")
@login_required
def admin_applications():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                a.application_id,
                a.status,
                a.applied_date,
                s.name AS student_name,
                s.email AS student_email,
                o.title AS internship_title,
                o.company
            FROM applications a
            JOIN students s
                ON a.student_id = s.student_id
            JOIN opportunities o
                ON a.opportunity_id = o.opportunity_id
            ORDER BY a.applied_date DESC
        """)

        applications = cursor.fetchall()

        return render_template(
            "admin_applications.html",
            applications=applications
        )

    except mysql.connector.Error:
        app.logger.exception("Could not load admin applications")
        return "Unable to load applications.", 500

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


# --------------------------------------------------
# UPDATE APPLICATION STATUS (ADMIN ONLY)
# --------------------------------------------------


@app.route(
    "/admin/applications/<int:application_id>/status",
    methods=["POST"]
)

@login_required
def update_application_status(application_id):
    new_status = request.form.get("status", "").strip()

    allowed_statuses = ["Applied", "Shortlisted", "Rejected"]

    if new_status not in allowed_statuses:
        flash("Invalid application status.", "error")
        return redirect(url_for("admin_applications"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get the student who submitted the application
        cursor.execute(
            """
            SELECT student_id
            FROM applications
            WHERE application_id = %s
            """,
            (application_id,)
        )

        application = cursor.fetchone()

        if application is None:
            flash("Application not found.", "error")
            return redirect(url_for("admin_applications"))

        student_id = application["student_id"]

        # Update the application status
        cursor.execute(
            """
            UPDATE applications
            SET status = %s
            WHERE application_id = %s
            """,
            (new_status, application_id)
        )

        # Save a notification for the student
        message = (
            f"Your application status has been updated to: {new_status}."
        )

        cursor.execute(
            """
            INSERT INTO notifications (student_id, message)
            VALUES (%s, %s)
            """,
            (student_id, message)
        )

        conn.commit()

        flash(
            "Application status updated and student notified!",
            "success"
        )

        return redirect(url_for("admin_applications"))

    except mysql.connector.Error:
        if conn is not None and conn.is_connected():
            conn.rollback()

        app.logger.exception("Could not update application status")
        flash("Could not update the status. Please try again.", "error")
        return redirect(url_for("admin_applications"))

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()



# --------------------------------------------------
# ADD INTERNSHIP (ADMIN ONLY)
# --------------------------------------------------

@app.route("/api/opportunities", methods=["POST"])
@login_required
def add_opportunity():
    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    company = data.get("company", "")
    description = data.get("description", "")
    stipend = data.get("stipend", "")
    application_url = data.get("application_url", "")

    if not all(
        isinstance(value, str) and value.strip()
        for value in [
            title, company, description, stipend, application_url
        ]
    ):
        return jsonify({
            "error": "Please fill in all fields."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO opportunities
                (title, company, description, stipend, application_url)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                title.strip(),
                company.strip(),
                description.strip(),
                stipend.strip(),
                application_url.strip()
            )
        )

        connection.commit()

        return jsonify({
            "message": "Internship added successfully."
        }), 201

    except mysql.connector.Error:
        if connection is not None and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not save internship")

        return jsonify({
            "error": "Could not save internship."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/opportunities/<int:opportunity_id>", methods=["PUT"])
@login_required
def edit_opportunity(opportunity_id):
    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    company = data.get("company", "")
    description = data.get("description", "")
    stipend = data.get("stipend", "")
    application_url = data.get("application_url", "")

    if not all(
        isinstance(value, str) and value.strip()
        for value in [
            title, company, description, stipend, application_url
        ]
    ):
        return jsonify({
            "error": "Please fill in all fields."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE opportunities
            SET title = %s,
                company = %s,
                description = %s,
                stipend = %s,
                application_url = %s
            WHERE opportunity_id = %s
            """,
            (
                title.strip(),
                company.strip(),
                description.strip(),
                stipend.strip(),
                application_url.strip(),
                opportunity_id
            )
        )

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT opportunity_id FROM opportunities WHERE opportunity_id = %s",
                (opportunity_id,)
            )

            if cursor.fetchone() is None:
                connection.rollback()
                return jsonify({
                    "error": "Internship not found."
                }), 404

        connection.commit()

        return jsonify({
            "message": "Internship updated successfully."
        }), 200

    except mysql.connector.Error:
        if connection is not None and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not update internship")

        return jsonify({
            "error": "Could not update internship."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

# --------------------------------------------------
# DELETE INTERNSHIP (ADMIN ONLY)
# --------------------------------------------------

@app.route(
    "/api/opportunities/<int:opportunity_id>",
    methods=["DELETE"]
)
@login_required
def delete_opportunity(opportunity_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM opportunities WHERE opportunity_id = %s",
            (opportunity_id,)
        )

        if cursor.rowcount == 0:
            connection.rollback()

            return jsonify({
                "error": "Internship not found."
            }), 404

        connection.commit()

        return jsonify({
            "message": "Internship deleted successfully."
        })

    except mysql.connector.Error:
        if connection is not None and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not delete internship")

        return jsonify({
            "error": "Could not delete internship."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# --------------------------------------------------
# RUN THE APPLICATION
# --------------------------------------------------

@app.route("/apply/<int:opportunity_id>", methods=["POST"])
def apply_for_internship(opportunity_id):
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check whether the internship exists
        cursor.execute(
            "SELECT opportunity_id FROM opportunities WHERE opportunity_id = %s",
            (opportunity_id,)
        )
        opportunity = cursor.fetchone()

        if not opportunity:
            flash("Internship not found.", "error")
            return redirect(url_for("opportunities"))

        # Prevent duplicate applications
        cursor.execute(
            """
            SELECT application_id
            FROM applications
            WHERE student_id = %s AND opportunity_id = %s
            """,
            (session["student_id"], opportunity_id)
        )

        existing = cursor.fetchone()

        if existing:
            flash("You have already applied for this internship.", "error")
        else:
            cursor.execute(
                """
                INSERT INTO applications
                    (student_id, opportunity_id, status)
                VALUES (%s, %s, %s)
                """,
                (session["student_id"], opportunity_id, "Applied")
            )

            conn.commit()
            flash("Application saved successfully!", "success")

        return redirect(url_for("my_applications"))

    except mysql.connector.Error:
        if conn is not None and conn.is_connected():
            conn.rollback()

        app.logger.exception("Could not save internship application")
        flash("Could not save your application. Please try again.", "error")
        return redirect(url_for("opportunities"))

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


@app.route("/my-applications")
def my_applications():
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                a.application_id,
                a.status,
                a.applied_date,
                o.title,
                o.company,
                o.stipend
            FROM applications a
            JOIN opportunities o
                ON a.opportunity_id = o.opportunity_id
            WHERE a.student_id = %s
            ORDER BY a.applied_date DESC
            """,
            (session["student_id"],)
        )

        applications = cursor.fetchall()

        return render_template(
            "my_applications.html",
            applications=applications
        )

    except mysql.connector.Error:
        app.logger.exception("Could not load student applications")
        return "Unable to load applications. Please try again.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()
 
 
# --------------------------------------------------
# STUDENT NOTIFICATIONS
# --------------------------------------------------

@app.route("/notifications")
def notifications():
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT notification_id, message, is_read, created_at
            FROM notifications
            WHERE student_id = %s
            ORDER BY created_at DESC
            """,
            (session["student_id"],)
        )

        student_notifications = cursor.fetchall()

        return render_template(
            "notifications.html",
            notifications=student_notifications
        )

    except mysql.connector.Error:
        app.logger.exception("Could not load notifications")
        return "Unable to load notifications.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()


@app.route(
    "/notifications/read/<int:notification_id>",
    methods=["POST"]
)
def mark_notification_read(notification_id):
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE notifications
            SET is_read = TRUE
            WHERE notification_id = %s
              AND student_id = %s
            """,
            (notification_id, session["student_id"])
        )

        conn.commit()

        flash("Notification marked as read.", "success")

        return redirect(url_for("notifications"))

    except mysql.connector.Error:
        if conn is not None and conn.is_connected():
            conn.rollback()

        app.logger.exception("Could not mark notification as read")
        flash("Unable to update notification.", "error")
        return redirect(url_for("notifications"))

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None and conn.is_connected():
            conn.close()

 

if __name__ == "__main__":
    app.run(debug=True)

