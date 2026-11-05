"""
app.py — Learnlytics: E-Learning Course Analytics System
Full-stack Flask application with secure MySQL connectivity, Pandas/NumPy analytics,
Chart.js visualizations, CRUD operations, CSV exports, and graceful error handling.
"""

import csv
import io
import os
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, Response
)
from dotenv import load_dotenv

import config
from config import fetch_all, fetch_one, execute_query, check_db_status
import analytics

# Load environment configuration
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "learnlytics_secret_key_2026")


# ─────────────────────────────────────────────────────────────
#  CONTEXT PROCESSOR: Global DB Status for all templates
# ─────────────────────────────────────────────────────────────
@app.context_processor
def inject_db_status():
    """Inject database connection status and masked credentials into all templates."""
    db_info = check_db_status()
    return {"db_status": db_info}


# ─────────────────────────────────────────────────────────────
#  1. DASHBOARD
# ─────────────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    db_info = check_db_status()
    
    if not db_info["connected"] or not db_info["db_exists"]:
        # Render graceful empty state without crashing
        stats = {
            "total_courses": 0,
            "total_learners": 0,
            "total_enrollments": 0,
            "completed": 0,
            "active": 0,
            "dropped": 0,
            "completion_rate": 0.0,
        }
        return render_template(
            "dashboard.html",
            stats=stats,
            recent_enrollments=[],
            course_comp={"labels": [], "enrolled": [], "completed": []},
            weekly={"weeks": [], "counts": []},
            status_dist={"labels": ["Completed", "Active", "Dropped"], "counts": [0, 0, 0]},
        )

    try:
        stats = analytics.get_dashboard_summary()
        course_comp = analytics.course_wise_enrollment_comparison()
        weekly = analytics.weekly_activity_trends(weeks=8)
        status_dist = analytics.enrollment_status_distribution()

        recent_enrollments = fetch_all("""
            SELECT
                e.enrollment_id,
                l.learner_name,
                l.roll_no,
                c.course_name,
                e.enrolled_at,
                e.status
            FROM enrollments e
            JOIN learners l ON l.learner_id = e.learner_id
            JOIN courses  c ON c.course_id  = e.course_id
            ORDER BY e.enrolled_at DESC, e.enrollment_id DESC
            LIMIT 6
        """)
    except Exception as exc:
        flash(f"Data retrieval notice: {exc}", "error")
        stats = analytics.get_dashboard_summary()
        recent_enrollments = []
        course_comp = {"labels": [], "enrolled": [], "completed": []}
        weekly = {"weeks": [], "counts": []}
        status_dist = {"labels": ["Completed", "Active", "Dropped"], "counts": [0, 0, 0]}

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_enrollments=recent_enrollments,
        course_comp=course_comp,
        weekly=weekly,
        status_dist=status_dist,
    )


@app.route("/api/dashboard-data")
def api_dashboard_data():
    """API endpoint providing live JSON statistics and chart feeds."""
    db_info = check_db_status()
    if not db_info["connected"]:
        return jsonify({"connected": False, "error": db_info["error"]}), 503

    return jsonify({
        "connected": True,
        "summary": analytics.get_dashboard_summary(),
        "courses": analytics.course_wise_enrollment_comparison(),
        "weekly": analytics.weekly_activity_trends(),
        "status_distribution": analytics.enrollment_status_distribution(),
    })


# ─────────────────────────────────────────────────────────────
#  2. COURSES MANAGEMENT
# ─────────────────────────────────────────────────────────────
@app.route("/courses")
def courses():
    db_info = check_db_status()
    courses_list = []
    if db_info["connected"] and db_info["db_exists"]:
        try:
            courses_list = fetch_all("""
                SELECT
                    c.course_id,
                    c.course_name,
                    c.category,
                    COUNT(e.enrollment_id) AS enrolled_count,
                    SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END) AS completed_count
                FROM courses c
                LEFT JOIN enrollments e ON e.course_id = c.course_id
                GROUP BY c.course_id, c.course_name, c.category
                ORDER BY c.course_name ASC
            """)
        except Exception as exc:
            flash(f"Error fetching courses: {exc}", "error")

    return render_template("courses.html", courses=courses_list)


@app.route("/courses/add", methods=["POST"])
def add_course():
    name = request.form.get("course_name", "").strip()
    category = request.form.get("category", "").strip()

    if not name or not category:
        flash("Course name and category are required fields.", "error")
        return redirect(url_for("courses"))

    try:
        existing = fetch_one("SELECT course_id FROM courses WHERE LOWER(course_name) = LOWER(%s)", (name,))
        if existing:
            flash(f'A course with the name "{name}" already exists.', "error")
            return redirect(url_for("courses"))

        execute_query("INSERT INTO courses (course_name, category) VALUES (%s, %s)", (name, category))
        flash(f'Course "{name}" created successfully.', "success")
    except Exception as exc:
        flash(f"Failed to create course: {exc}", "error")

    return redirect(url_for("courses"))


@app.route("/courses/edit/<int:course_id>", methods=["POST"])
def edit_course(course_id):
    name = request.form.get("course_name", "").strip()
    category = request.form.get("category", "").strip()

    if not name or not category:
        flash("Course name and category cannot be empty.", "error")
        return redirect(url_for("courses"))

    try:
        existing = fetch_one(
            "SELECT course_id FROM courses WHERE LOWER(course_name) = LOWER(%s) AND course_id != %s",
            (name, course_id)
        )
        if existing:
            flash(f'Another course with the name "{name}" already exists.', "error")
            return redirect(url_for("courses"))

        execute_query(
            "UPDATE courses SET course_name = %s, category = %s WHERE course_id = %s",
            (name, category, course_id)
        )
        flash("Course details updated successfully.", "success")
    except Exception as exc:
        flash(f"Failed to update course: {exc}", "error")

    return redirect(url_for("courses"))


@app.route("/courses/delete/<int:course_id>", methods=["POST"])
def delete_course(course_id):
    try:
        # Cascade manually for databases without foreign key CASCADE configured
        execute_query("""
            DELETE a FROM activities a
            JOIN enrollments e ON e.enrollment_id = a.enrollment_id
            WHERE e.course_id = %s
        """, (course_id,))
        execute_query("DELETE FROM enrollments WHERE course_id = %s", (course_id,))
        execute_query("DELETE FROM courses WHERE course_id = %s", (course_id,))
        flash("Course and associated enrolments removed successfully.", "success")
    except Exception as exc:
        flash(f"Failed to delete course: {exc}", "error")

    return redirect(url_for("courses"))


# ─────────────────────────────────────────────────────────────
#  3. LEARNERS MANAGEMENT
# ─────────────────────────────────────────────────────────────
@app.route("/learners")
def learners():
    db_info = check_db_status()
    learners_list = []
    if db_info["connected"] and db_info["db_exists"]:
        try:
            learners_list = fetch_all("""
                SELECT
                    l.learner_id,
                    l.roll_no,
                    l.learner_name,
                    l.email,
                    COUNT(e.enrollment_id) AS course_count,
                    SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END) AS completed_count
                FROM learners l
                LEFT JOIN enrollments e ON e.learner_id = l.learner_id
                GROUP BY l.learner_id, l.roll_no, l.learner_name, l.email
                ORDER BY l.learner_name ASC
            """)
        except Exception as exc:
            flash(f"Error fetching learners: {exc}", "error")

    return render_template("learners.html", learners=learners_list)


@app.route("/learners/add", methods=["POST"])
def add_learner():
    roll_no = request.form.get("roll_no", "").strip().upper()
    name = request.form.get("learner_name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not roll_no or not name or not email:
        flash("Roll number, name, and email are required.", "error")
        return redirect(url_for("learners"))

    try:
        existing = fetch_one("SELECT learner_id FROM learners WHERE roll_no = %s", (roll_no,))
        if existing:
            flash(f'Roll number "{roll_no}" is already registered.', "error")
            return redirect(url_for("learners"))

        execute_query(
            "INSERT INTO learners (roll_no, learner_name, email) VALUES (%s, %s, %s)",
            (roll_no, name, email)
        )
        flash(f'Learner "{name}" registered successfully.', "success")
    except Exception as exc:
        flash(f"Failed to register learner: {exc}", "error")

    return redirect(url_for("learners"))


@app.route("/learners/edit/<int:learner_id>", methods=["POST"])
def edit_learner(learner_id):
    roll_no = request.form.get("roll_no", "").strip().upper()
    name = request.form.get("learner_name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not roll_no or not name or not email:
        flash("All fields are required.", "error")
        return redirect(url_for("learners"))

    try:
        duplicate = fetch_one(
            "SELECT learner_id FROM learners WHERE roll_no = %s AND learner_id != %s",
            (roll_no, learner_id)
        )
        if duplicate:
            flash(f'Roll number "{roll_no}" is already used by another learner.', "error")
            return redirect(url_for("learners"))

        execute_query(
            "UPDATE learners SET roll_no = %s, learner_name = %s, email = %s WHERE learner_id = %s",
            (roll_no, name, email, learner_id)
        )
        flash("Learner details updated successfully.", "success")
    except Exception as exc:
        flash(f"Failed to update learner: {exc}", "error")

    return redirect(url_for("learners"))


@app.route("/learners/delete/<int:learner_id>", methods=["POST"])
def delete_learner(learner_id):
    try:
        execute_query("""
            DELETE a FROM activities a
            JOIN enrollments e ON e.enrollment_id = a.enrollment_id
            WHERE e.learner_id = %s
        """, (learner_id,))
        execute_query("DELETE FROM enrollments WHERE learner_id = %s", (learner_id,))
        execute_query("DELETE FROM learners WHERE learner_id = %s", (learner_id,))
        flash("Learner record deleted successfully.", "success")
    except Exception as exc:
        flash(f"Failed to delete learner: {exc}", "error")

    return redirect(url_for("learners"))


# ─────────────────────────────────────────────────────────────
#  4. ENROLMENTS MANAGEMENT
# ─────────────────────────────────────────────────────────────
@app.route("/enrollments")
def enrollments():
    db_info = check_db_status()
    enrollment_list = []
    all_learners = []
    all_courses = []

    if db_info["connected"] and db_info["db_exists"]:
        try:
            enrollment_list = fetch_all("""
                SELECT
                    e.enrollment_id,
                    l.learner_id,
                    l.learner_name,
                    l.roll_no,
                    c.course_id,
                    c.course_name,
                    e.enrolled_at,
                    e.status,
                    COUNT(a.activity_id) AS total_activities
                FROM enrollments e
                JOIN learners l ON l.learner_id = e.learner_id
                JOIN courses  c ON c.course_id  = e.course_id
                LEFT JOIN activities a ON a.enrollment_id = e.enrollment_id
                GROUP BY e.enrollment_id, l.learner_id, l.learner_name, l.roll_no,
                         c.course_id, c.course_name, e.enrolled_at, e.status
                ORDER BY e.enrolled_at DESC, e.enrollment_id DESC
            """)
            all_learners = fetch_all("SELECT learner_id, learner_name, roll_no FROM learners ORDER BY learner_name ASC")
            all_courses = fetch_all("SELECT course_id, course_name FROM courses ORDER BY course_name ASC")
        except Exception as exc:
            flash(f"Error fetching enrolments: {exc}", "error")

    return render_template(
        "enrollments.html",
        enrollments=enrollment_list,
        learners=all_learners,
        courses=all_courses,
    )


@app.route("/enrollments/add", methods=["POST"])
def add_enrollment():
    learner_id = request.form.get("learner_id")
    course_id = request.form.get("course_id")
    enrolled_at = request.form.get("enrolled_at") or datetime.now().strftime("%Y-%m-%d")

    if not learner_id or not course_id:
        flash("Both learner and course must be selected.", "error")
        return redirect(url_for("enrollments"))

    try:
        existing = fetch_one(
            "SELECT enrollment_id FROM enrollments WHERE learner_id = %s AND course_id = %s",
            (learner_id, course_id)
        )
        if existing:
            flash("This learner is already enrolled in the selected course.", "error")
            return redirect(url_for("enrollments"))

        execute_query(
            "INSERT INTO enrollments (learner_id, course_id, enrolled_at, status) VALUES (%s, %s, %s, 'active')",
            (learner_id, course_id, enrolled_at)
        )
        flash("Enrolment created successfully.", "success")
    except Exception as exc:
        flash(f"Failed to create enrolment: {exc}", "error")

    return redirect(url_for("enrollments"))


@app.route("/enrollments/status/<int:enrollment_id>", methods=["POST"])
def update_enrollment_status(enrollment_id):
    new_status = request.form.get("status")
    if new_status not in ("active", "completed", "dropped"):
        flash("Invalid status selection.", "error")
        return redirect(url_for("enrollments"))

    try:
        execute_query("UPDATE enrollments SET status = %s WHERE enrollment_id = %s", (new_status, enrollment_id))
        flash(f"Enrolment status updated to '{new_status}'.", "success")
    except Exception as exc:
        flash(f"Failed to update enrolment: {exc}", "error")

    return redirect(url_for("enrollments"))


@app.route("/enrollments/delete/<int:enrollment_id>", methods=["POST"])
def delete_enrollment(enrollment_id):
    try:
        execute_query("DELETE FROM activities WHERE enrollment_id = %s", (enrollment_id,))
        execute_query("DELETE FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
        flash("Enrolment deleted successfully.", "success")
    except Exception as exc:
        flash(f"Failed to delete enrolment: {exc}", "error")

    return redirect(url_for("enrollments"))


# ─────────────────────────────────────────────────────────────
#  5. ACTIVITIES MANAGEMENT
# ─────────────────────────────────────────────────────────────
@app.route("/activities")
def activities():
    db_info = check_db_status()
    activities_list = []
    enrollments_options = []

    if db_info["connected"] and db_info["db_exists"]:
        try:
            activities_list = fetch_all("""
                SELECT
                    a.activity_id,
                    a.enrollment_id,
                    l.learner_name,
                    l.roll_no,
                    c.course_name,
                    a.activity_date,
                    a.activity_type,
                    a.completed
                FROM activities a
                JOIN enrollments e ON e.enrollment_id = a.enrollment_id
                JOIN learners l    ON l.learner_id    = e.learner_id
                JOIN courses c     ON c.course_id     = e.course_id
                ORDER BY a.activity_date DESC, a.activity_id DESC
                LIMIT 100
            """)
            enrollments_options = fetch_all("""
                SELECT
                    e.enrollment_id,
                    CONCAT(l.learner_name, ' (', l.roll_no, ') — ', c.course_name) AS label
                FROM enrollments e
                JOIN learners l ON l.learner_id = e.learner_id
                JOIN courses c  ON c.course_id  = e.course_id
                WHERE e.status = 'active'
                ORDER BY l.learner_name ASC
            """)
        except Exception as exc:
            flash(f"Error fetching activities: {exc}", "error")

    return render_template(
        "activities.html",
        activities=activities_list,
        enrollments=enrollments_options,
    )


@app.route("/activities/add", methods=["POST"])
def add_activity():
    enrollment_id = request.form.get("enrollment_id")
    activity_type = request.form.get("activity_type", "").strip()
    activity_date = request.form.get("activity_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    completed = 1 if request.form.get("completed") == "1" else 0

    if not enrollment_id or not activity_type:
        flash("Please select an enrolment and specify the activity type.", "error")
        return redirect(url_for("activities"))

    try:
        execute_query("""
            INSERT INTO activities (enrollment_id, activity_date, activity_type, completed)
            VALUES (%s, %s, %s, %s)
        """, (enrollment_id, activity_date, activity_type, completed))
        flash("Learning activity recorded successfully.", "success")
    except Exception as exc:
        flash(f"Failed to record activity: {exc}", "error")

    return redirect(url_for("activities"))


@app.route("/activities/toggle/<int:activity_id>", methods=["POST"])
def toggle_activity(activity_id):
    try:
        row = fetch_one("SELECT completed FROM activities WHERE activity_id = %s", (activity_id,))
        if row:
            new_val = 0 if row["completed"] else 1
            execute_query("UPDATE activities SET completed = %s WHERE activity_id = %s", (new_val, activity_id))
            status_text = "Completed" if new_val else "In Progress"
            flash(f"Activity marked as {status_text}.", "success")
    except Exception as exc:
        flash(f"Failed to toggle activity: {exc}", "error")

    return redirect(url_for("activities"))


@app.route("/activities/delete/<int:activity_id>", methods=["POST"])
def delete_activity(activity_id):
    try:
        execute_query("DELETE FROM activities WHERE activity_id = %s", (activity_id,))
        flash("Activity record deleted.", "success")
    except Exception as exc:
        flash(f"Failed to delete activity: {exc}", "error")

    return redirect(url_for("activities"))


# ─────────────────────────────────────────────────────────────
#  6. ANALYTICS
# ─────────────────────────────────────────────────────────────
@app.route("/analytics")
def analytics_page():
    db_info = check_db_status()
    if not db_info["connected"] or not db_info["db_exists"]:
        return render_template(
            "analytics.html",
            summary={"completion_rate": 0.0, "total_enrollments": 0, "completed": 0},
            course_comp={"labels": [], "enrolled": [], "completed": [], "rates": [], "records": []},
            weekly={"weeks": [], "counts": []},
            status_dist={"labels": ["Completed", "Active", "Dropped"], "counts": [0, 0, 0]},
            activity_types={"types": [], "counts": []},
            inactive_enrollments=[],
        )

    summary = analytics.get_dashboard_summary()
    course_comp = analytics.course_wise_enrollment_comparison()
    weekly = analytics.weekly_activity_trends(weeks=8)
    status_dist = analytics.enrollment_status_distribution()
    activity_types = analytics.activity_type_distribution()
    inactive = analytics.inactive_enrollment_report(threshold_days=14)

    return render_template(
        "analytics.html",
        summary=summary,
        course_comp=course_comp,
        weekly=weekly,
        status_dist=status_dist,
        activity_types=activity_types,
        inactive_enrollments=inactive,
    )


# ─────────────────────────────────────────────────────────────
#  7. REPORTS & CSV EXPORTS
# ─────────────────────────────────────────────────────────────
@app.route("/reports")
def reports():
    inactive = analytics.inactive_enrollment_report(threshold_days=14)
    summary = analytics.get_dashboard_summary()
    return render_template("reports.html", inactive_enrollments=inactive, summary=summary)


def _generate_csv_response(rows, fieldnames, filename):
    """Utility to generate streamed CSV file downloads from list of dicts."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/reports/download/learners")
def download_learners_csv():
    rows = fetch_all("SELECT roll_no, learner_name, email FROM learners ORDER BY learner_name ASC")
    return _generate_csv_response(rows, ["roll_no", "learner_name", "email"], "learners_report.csv")


@app.route("/reports/download/courses")
def download_courses_csv():
    rows = fetch_all("""
        SELECT c.course_id, c.course_name, c.category,
               COUNT(e.enrollment_id) AS total_enrolled,
               SUM(CASE WHEN e.status='completed' THEN 1 ELSE 0 END) AS completed
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.course_id
        GROUP BY c.course_id, c.course_name, c.category
        ORDER BY c.course_name ASC
    """)
    return _generate_csv_response(rows, ["course_id", "course_name", "category", "total_enrolled", "completed"], "courses_report.csv")


@app.route("/reports/download/enrollments")
def download_enrollments_csv():
    rows = fetch_all("""
        SELECT l.roll_no, l.learner_name, c.course_name, e.enrolled_at, e.status
        FROM enrollments e
        JOIN learners l ON l.learner_id = e.learner_id
        JOIN courses  c ON c.course_id  = e.course_id
        ORDER BY e.enrolled_at DESC
    """)
    return _generate_csv_response(rows, ["roll_no", "learner_name", "course_name", "enrolled_at", "status"], "enrollments_report.csv")


@app.route("/reports/download/inactive")
def download_inactive_csv():
    rows = analytics.inactive_enrollment_report(threshold_days=14)
    if not rows:
        flash("No inactive enrolments found.", "info")
        return redirect(url_for("reports"))
    fields = ["roll_no", "learner_name", "email", "course_name", "enrolled_at", "last_activity", "days_inactive", "urgency"]
    return _generate_csv_response(rows, fields, "inactive_enrollments_report.csv")


@app.route("/reports/download/weekly")
def download_weekly_csv():
    weekly = analytics.weekly_activity_trends(weeks=8)
    rows = [{"week": w, "activity_count": c} for w, c in zip(weekly["weeks"], weekly["counts"])]
    return _generate_csv_response(rows, ["week", "activity_count"], "weekly_activity_report.csv")


# ─────────────────────────────────────────────────────────────
#  8. DB STATUS API
# ─────────────────────────────────────────────────────────────
@app.route("/api/db-status")
def db_status_api():
    """Live JSON endpoint for checking database connectivity."""
    return jsonify(check_db_status())


# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="127.0.0.1", port=port)
