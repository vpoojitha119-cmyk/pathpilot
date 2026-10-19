
import os

from flask import (
    Flask, render_template, jsonify, request,
    redirect, url_for, flash
)
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is missing from your .env file")


# Flask-Login configuration
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


# MySQL connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="pathpilot"
    )


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Student pages (existing)
@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/opportunities")
def opportunities():
    return render_template("opportunities.html")


@app.route("/skills")
def skills():
    return render_template("skills.html")


# Public API: display internships
@app.route("/api/opportunities", methods=["GET"])
def api_opportunities():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM opportunities")
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        connection.close()


# Admin login
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
            login_user(AdminUser(username))
            return redirect(url_for("admin"))

        flash("Invalid username or password.", "error")

    return render_template("admin_login.html")


# Admin logout
@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("admin_login"))


# Protected admin dashboard
@app.route("/admin")
@login_required
def admin():
    return render_template("admin.html")


# Protected API: add an internship
@app.route("/api/opportunities", methods=["POST"])
@login_required
def add_opportunity():
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    company = data.get("company", "").strip()
    description = data.get("description", "").strip()
    stipend = data.get("stipend", "").strip()
    application_url = data.get("application_url", "").strip()

    if not all([
        title, company, description, stipend, application_url
    ]):
        return jsonify({
            "error": "Please fill in all fields"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        sql = """
            INSERT INTO opportunities
            (title, company, description, stipend, application_url)
            VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(sql, (
            title, company, description, stipend, application_url
        ))

        connection.commit()

        return jsonify({
            "message": "Internship added successfully"
        }), 201

    except Exception:
        connection.rollback()
        app.logger.exception("Could not save internship")

        return jsonify({
            "error": "Could not save internship"
        }), 500

    finally:
        cursor.close()
        connection.close()


# Protected API: delete an internship
@app.route(
    "/api/opportunities/<int:opportunity_id>",
    methods=["DELETE"]
)
@login_required
def delete_opportunity(opportunity_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM opportunities WHERE opportunity_id = %s",
            (opportunity_id,)
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return jsonify({
                "error": "Internship not found"
            }), 404

        connection.commit()

        return jsonify({
            "message": "Internship deleted successfully"
        })

    except Exception:
        connection.rollback()
        app.logger.exception("Could not delete internship")

        return jsonify({
            "error": "Could not delete internship"
        }), 500

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    app.run(debug=True)
