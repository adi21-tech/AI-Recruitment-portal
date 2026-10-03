import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import get_connection, init_db
from models.resume_ranker import compute_match_score, skill_gap_analysis

import PyPDF2
import docx2txt

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

app = Flask(__name__)
app.secret_key = "change-this-secret-key-for-production"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------- Helpers ----------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_resume(filepath):
    ext = filepath.rsplit(".", 1)[1].lower()
    text = ""
    if ext == "pdf":
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    elif ext == "docx":
        text = docx2txt.process(filepath)
    else:  # txt
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    return text


def login_required(role=None):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You don't have access to that page.")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


# ---------- Auth ----------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        role = request.form["role"]
        full_name = request.form.get("full_name", "").strip()

        conn = get_connection()
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("Username already taken.")
            conn.close()
            return redirect(url_for("register"))

        conn.execute(
            "INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), role, full_name),
        )
        conn.commit()
        conn.close()
        flash("Registered successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Dashboard (redirects by role) ----------

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] == "company":
        return redirect(url_for("company_dashboard"))
    return redirect(url_for("student_dashboard"))


# ---------- Company routes ----------

@app.route("/company/dashboard")
@login_required(role="company")
def company_dashboard():
    conn = get_connection()
    jobs = conn.execute(
        "SELECT * FROM jobs WHERE company_id = ? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("company_dashboard.html", jobs=jobs)


@app.route("/company/post_job", methods=["GET", "POST"])
@login_required(role="company")
def post_job():
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        required_skills = request.form.get("required_skills", "").strip()

        conn = get_connection()
        conn.execute(
            "INSERT INTO jobs (company_id, title, description, required_skills) VALUES (?, ?, ?, ?)",
            (session["user_id"], title, description, required_skills),
        )
        conn.commit()
        conn.close()
        flash("Job posted.")
        return redirect(url_for("company_dashboard"))

    return render_template("post_job.html")


@app.route("/company/job/<int:job_id>/applicants")
@login_required(role="company")
def view_applicants(job_id):
    conn = get_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ? AND company_id = ?",
                        (job_id, session["user_id"])).fetchone()
    if not job:
        conn.close()
        flash("Job not found.")
        return redirect(url_for("company_dashboard"))

    applicants = conn.execute("""
        SELECT applications.*, users.full_name, users.username
        FROM applications
        JOIN users ON applications.student_id = users.id
        WHERE applications.job_id = ?
        ORDER BY applications.match_score DESC
    """, (job_id,)).fetchall()
    conn.close()
    return render_template("view_applicants.html", job=job, applicants=applicants)


@app.route("/company/job/<int:job_id>/schedule", methods=["GET", "POST"])
@login_required(role="company")
def schedule_interview(job_id):
    conn = get_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ? AND company_id = ?",
                        (job_id, session["user_id"])).fetchone()
    if not job:
        conn.close()
        flash("Job not found.")
        return redirect(url_for("company_dashboard"))

    if request.method == "POST":
        slot_time = request.form["slot_time"]
        conn.execute(
            "INSERT INTO interview_slots (job_id, company_id, slot_time) VALUES (?, ?, ?)",
            (job_id, session["user_id"], slot_time),
        )
        conn.commit()
        flash("Interview slot added.")

    slots = conn.execute("""
        SELECT interview_slots.*, users.full_name AS student_name
        FROM interview_slots
        LEFT JOIN users ON interview_slots.booked_by = users.id
        WHERE interview_slots.job_id = ?
        ORDER BY slot_time
    """, (job_id,)).fetchall()
    conn.close()
    return render_template("schedule_interview.html", job=job, slots=slots)


# ---------- Student routes ----------

@app.route("/student/dashboard")
@login_required(role="student")
def student_dashboard():
    conn = get_connection()
    jobs = conn.execute("""
        SELECT jobs.*, users.full_name AS company_name
        FROM jobs
        JOIN users ON jobs.company_id = users.id
        ORDER BY jobs.created_at DESC
    """).fetchall()

    my_applications = conn.execute(
        "SELECT job_id FROM applications WHERE student_id = ?",
        (session["user_id"],),
    ).fetchall()
    applied_job_ids = {row["job_id"] for row in my_applications}
    conn.close()

    return render_template("student_dashboard.html", jobs=jobs, applied_job_ids=applied_job_ids)


@app.route("/student/job/<int:job_id>/apply", methods=["GET", "POST"])
@login_required(role="student")
def apply_job(job_id):
    conn = get_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        flash("Job not found.")
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        file = request.files.get("resume")
        if not file or file.filename == "":
            flash("Please choose a resume file.")
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash("Only PDF, DOCX, or TXT files are allowed.")
            return redirect(request.url)

        filename = secure_filename(f"{session['user_id']}{job_id}{file.filename}")
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        resume_text = extract_text_from_resume(filepath)
        job_text = job["description"] + " " + (job["required_skills"] or "")

        # Deep learning based similarity score
        score = compute_match_score(resume_text, job_text)
        matched, missing = skill_gap_analysis(resume_text, job_text)

        conn.execute("""
            INSERT INTO applications
                (job_id, student_id, resume_filename, resume_text, match_score, matched_skills, missing_skills)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (job_id, session["user_id"], filename, resume_text, score,
              ", ".join(matched), ", ".join(missing)))
        conn.commit()
        conn.close()

        flash(f"Application submitted! Match score: {score}%")
        return redirect(url_for("student_dashboard"))

    conn.close()
    return render_template("apply_job.html", job=job)


@app.route("/student/interviews")
@login_required(role="student")
def student_interviews():
    conn = get_connection()
    applied_jobs = conn.execute(
        "SELECT DISTINCT job_id FROM applications WHERE student_id = ?",
        (session["user_id"],),
    ).fetchall()
    job_ids = [row["job_id"] for row in applied_jobs]

    slots = []
    if job_ids:
        placeholders = ",".join("?" * len(job_ids))
        slots = conn.execute(f"""
            SELECT interview_slots.*, jobs.title AS job_title, users.full_name AS company_name
            FROM interview_slots
            JOIN jobs ON interview_slots.job_id = jobs.id
            JOIN users ON interview_slots.company_id = users.id
            WHERE interview_slots.job_id IN ({placeholders})
            ORDER BY slot_time
        """, job_ids).fetchall()
    conn.close()
    return render_template("student_interviews.html", slots=slots)


@app.route("/student/book_slot/<int:slot_id>")
@login_required(role="student")
def book_slot(slot_id):
    conn = get_connection()
    slot = conn.execute("SELECT * FROM interview_slots WHERE id = ?", (slot_id,)).fetchone()
    if slot and not slot["booked_by"]:
        conn.execute("UPDATE interview_slots SET booked_by = ? WHERE id = ?",
                     (session["user_id"], slot_id))
        conn.commit()
        flash("Interview slot booked!")
    else:
        flash("Slot unavailable.")
    conn.close()
    return redirect(url_for("student_interviews"))


@app.route("/uploads/<path:filename>")
def download_resume(filename):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] == "student" and not filename.startswith(f"{session['user_id']}_"):
        flash("You can't access that file.")
        return redirect(url_for("dashboard"))
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


if __name__ == "__main__":
    if not os.path.exists(os.path.join(BASE_DIR, "portal.db")):
        init_db()
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)