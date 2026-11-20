
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "college_job_portal_secret"

# Database connection
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# Create database tables
def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            salary TEXT,
            description TEXT,
            category TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            job_id INTEGER,
            phone TEXT,
            education TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            message TEXT
        )
    """)

    # Sample jobs
    count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    if count == 0:
        sample_jobs = [
            ("Python Developer", "ABC Technologies",
             "Ahmedabad", "15000-25000",
             "Python and Flask knowledge required.", "Job"),

            ("Web Developer", "XYZ Solutions",
             "Rajkot", "12000-20000",
             "HTML, CSS and JavaScript required.", "Job"),

            ("Digital Marketing Intern", "Qtonz",
             "Remote", "5000-8000",
             "Basic SEO and marketing knowledge.", "Internship"),

            ("Software Developer Intern", "Tech Company",
             "Surat", "6000-10000",
             "Basic programming knowledge required.", "Internship")
        ]

        conn.executemany("""
            INSERT INTO jobs
            (title, company, location, salary, description, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_jobs)

    conn.commit()
    conn.close()


# Home Page
@app.route("/")
def home():
    conn = get_db()
    jobs = conn.execute(
        "SELECT * FROM jobs ORDER BY id DESC LIMIT 3"
    ).fetchall()
    conn.close()
    return render_template("index.html", jobs=jobs)


# About Page
@app.route("/about")
def about():
    return render_template("about.html")


# Student Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name, email, password)
            )
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered.")

        finally:
            conn.close()

    return render_template("register.html")


# Student Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# Jobs Page
@app.route("/jobs")
def jobs():
    conn = get_db()
    job_list = conn.execute(
        "SELECT * FROM jobs WHERE category='Job'"
    ).fetchall()
    conn.close()
    return render_template("jobs.html", jobs=job_list)


# Internship Page
@app.route("/internship")
def internship():
    conn = get_db()
    internship_list = conn.execute(
        "SELECT * FROM jobs WHERE category='Internship'"
    ).fetchall()
    conn.close()
    return render_template(
        "internship.html", jobs=internship_list
    )


# Apply Job
@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply(job_id):
    if "user_id" not in session:
        flash("Please login before applying.")
        return redirect(url_for("login"))

    conn = get_db()
    job = conn.execute(
        "SELECT * FROM jobs WHERE id=?", (job_id,)
    ).fetchone()

    if not job:
        conn.close()
        return "Job not found", 404

    if request.method == "POST":
        phone = request.form["phone"]
        education = request.form["education"]

        conn.execute("""
            INSERT INTO applications(user_id,job_id,phone,education)
            VALUES(?,?,?,?)
        """, (session["user_id"], job_id, phone, education))

        conn.commit()
        conn.close()

        flash("Your application submitted successfully!")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("apply.html", job=job)


# Student Dashboard
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    applications = conn.execute("""
        SELECT jobs.title, jobs.company, applications.phone
        FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        WHERE applications.user_id=?
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "dashboard.html", applications=applications
    )


# Contact Page
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        conn = get_db()
        conn.execute("""
            INSERT INTO messages(name,email,message)
            VALUES(?,?,?)
        """, (name, email, message))
        conn.commit()
        conn.close()

        flash("Message sent successfully!")

    return render_template("contact.html")


# Admin Login and Dashboard
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect(url_for("admin"))

        flash("Invalid admin details.")

    if not session.get("admin"):
        return render_template("admin.html", logged_in=False)

    conn = get_db()
    jobs = conn.execute("SELECT * FROM jobs").fetchall()
    applications = conn.execute("""
        SELECT users.name, users.email, jobs.title
        FROM applications
        JOIN users ON applications.user_id=users.id
        JOIN jobs ON applications.job_id=jobs.id
    """).fetchall()
    conn.close()

    return render_template(
        "admin.html",
        logged_in=True,
        jobs=jobs,
        applications=applications
    )


# Admin Add Job
@app.route("/add_job", methods=["POST"])
def add_job():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    conn = get_db()
    conn.execute("""
        INSERT INTO jobs(title,company,location,salary,description,category)
        VALUES(?,?,?,?,?,?)
    """, (
        request.form["title"],
        request.form["company"],
        request.form["location"],
        request.form["salary"],
        request.form["description"],
        request.form["category"]
    ))
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# Admin Delete Job
@app.route("/delete_job/<int:job_id>")
def delete_job(job_id):
    if not session.get("admin"):
        return redirect(url_for("admin"))

    conn = get_db()
    conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.route("/admin_logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
