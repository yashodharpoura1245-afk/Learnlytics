"""
analytics.py — Data Analytics & Mathematical Engine for Learnlytics.
Uses Pandas and NumPy for vectorized aggregations, statistical summaries,
time-series resampling, and inactive enrolment risk evaluation.
"""

import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from config import get_db_connection

# Suppress minor Pandas SQL execution warnings
warnings.filterwarnings("ignore", category=UserWarning)


def _safe_query_df(sql, params=None):
    """Safely query MySQL into a Pandas DataFrame; returns empty DataFrame on failure."""
    try:
        conn = get_db_connection()
        try:
            df = pd.read_sql(sql, conn, params=params)
            return df
        finally:
            conn.close()
    except Exception:
        return pd.DataFrame()


def get_dashboard_summary():
    """
    Compute core headline metrics using NumPy for vectorized rate calculation.
    
    COMPLETION RATE DENOMINATOR DOCUMENTATION:
    Denominator = Total number of enrolments across all courses.
    Formula: (Completed Enrolments / Total Enrolments) * 100
    If Total Enrolments == 0, Completion Rate = 0.0% (avoids division-by-zero).
    """
    sql = """
        SELECT
            (SELECT COUNT(*) FROM courses) AS total_courses,
            (SELECT COUNT(*) FROM learners) AS total_learners,
            (SELECT COUNT(*) FROM enrollments) AS total_enrollments,
            (SELECT COUNT(*) FROM enrollments WHERE status = 'completed') AS completed_enrollments,
            (SELECT COUNT(*) FROM enrollments WHERE status = 'active') AS active_enrollments,
            (SELECT COUNT(*) FROM enrollments WHERE status = 'dropped') AS dropped_enrollments,
            (SELECT COUNT(*) FROM activities) AS total_activities
    """
    df = _safe_query_df(sql)
    if df.empty:
        return {
            "total_courses": 0,
            "total_learners": 0,
            "total_enrollments": 0,
            "completed": 0,
            "active": 0,
            "dropped": 0,
            "total_activities": 0,
            "completion_rate": 0.0,
        }

    total_courses = int(df["total_courses"].iloc[0] or 0)
    total_learners = int(df["total_learners"].iloc[0] or 0)
    total_enrollments = int(df["total_enrollments"].iloc[0] or 0)
    completed = int(df["completed_enrollments"].iloc[0] or 0)
    active = int(df["active_enrollments"].iloc[0] or 0)
    dropped = int(df["dropped_enrollments"].iloc[0] or 0)
    total_activities = int(df["total_activities"].iloc[0] or 0)

    # NumPy vectorized calculation with zero division safety
    counts = np.array([total_enrollments, completed], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = np.where(counts[0] > 0, (counts[1] / counts[0]) * 100.0, 0.0)
    completion_rate = round(float(rate), 1)

    return {
        "total_courses": total_courses,
        "total_learners": total_learners,
        "total_enrollments": total_enrollments,
        "completed": completed,
        "active": active,
        "dropped": dropped,
        "total_activities": total_activities,
        "completion_rate": completion_rate,
    }


def course_wise_enrollment_comparison():
    """
    Compute course-by-course enrollment, completion, and completion percentages.
    
    DENOMINATOR:
    For each course, denominator = total enrolments in that specific course.
    Formula: (Course Completed Enrolments / Course Total Enrolments) * 100
    """
    sql = """
        SELECT
            c.course_id,
            c.course_name,
            c.category,
            COUNT(e.enrollment_id) AS total_enrolled,
            SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END) AS completed_count,
            SUM(CASE WHEN e.status = 'active' THEN 1 ELSE 0 END) AS active_count,
            SUM(CASE WHEN e.status = 'dropped' THEN 1 ELSE 0 END) AS dropped_count
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.course_id
        GROUP BY c.course_id, c.course_name, c.category
        ORDER BY total_enrolled DESC, c.course_name ASC
    """
    df = _safe_query_df(sql)
    if df.empty:
        return {
            "labels": [],
            "enrolled": [],
            "completed": [],
            "active": [],
            "dropped": [],
            "rates": [],
            "records": [],
        }

    df["total_enrolled"] = df["total_enrolled"].fillna(0).astype(int)
    df["completed_count"] = df["completed_count"].fillna(0).astype(int)
    df["active_count"] = df["active_count"].fillna(0).astype(int)
    df["dropped_count"] = df["dropped_count"].fillna(0).astype(int)

    # NumPy vectorized rate calculation
    enrolled_arr = df["total_enrolled"].to_numpy(dtype=float)
    completed_arr = df["completed_count"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        rates = np.where(enrolled_arr > 0, np.round((completed_arr / enrolled_arr) * 100.0, 1), 0.0)

    df["completion_rate"] = rates

    return {
        "labels": df["course_name"].tolist(),
        "enrolled": df["total_enrolled"].tolist(),
        "completed": df["completed_count"].tolist(),
        "active": df["active_count"].tolist(),
        "dropped": df["dropped_count"].tolist(),
        "rates": df["completion_rate"].tolist(),
        "records": df.to_dict("records"),
    }


def weekly_activity_trends(weeks=8):
    """
    Aggregate learning activities by calendar week over the last N weeks
    using Pandas datetime resampling. Handles empty periods seamlessly.
    """
    cutoff_date = (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    sql = """
        SELECT activity_date, completed, activity_type
        FROM activities
        WHERE activity_date >= %s
        ORDER BY activity_date ASC
    """
    df = _safe_query_df(sql, params=(cutoff_date,))
    
    # If no activities recorded or DB down
    if df.empty:
        # Generate empty weekly date bins for clean chart display
        labels = [(datetime.now() - timedelta(weeks=i)).strftime("%d %b") for i in range(weeks - 1, -1, -1)]
        return {
            "weeks": labels,
            "counts": [0] * len(labels),
            "completed_counts": [0] * len(labels),
        }

    df["activity_date"] = pd.to_datetime(df["activity_date"])
    df = df.set_index("activity_date")

    # Resample by week (W-MON)
    weekly_resample = df.resample("W")
    weekly_total = weekly_resample["activity_type"].count()
    weekly_completed = weekly_resample["completed"].sum()

    labels = [d.strftime("%d %b") for d in weekly_total.index]
    counts = [int(x) for x in weekly_total.tolist()]
    completed_counts = [int(x) for x in weekly_completed.tolist()]

    # Guarantee at least some points for chart rendering
    if not labels:
        labels = [datetime.now().strftime("%d %b")]
        counts = [0]
        completed_counts = [0]

    return {
        "weeks": labels,
        "counts": counts,
        "completed_counts": completed_counts,
    }


def enrollment_status_distribution():
    """Compute completed vs incomplete (active, dropped) enrolments for Chart.js."""
    sql = """
        SELECT status, COUNT(*) AS count
        FROM enrollments
        GROUP BY status
    """
    df = _safe_query_df(sql)
    status_map = {"completed": 0, "active": 0, "dropped": 0}
    if not df.empty:
        for _, row in df.iterrows():
            st = str(row["status"]).lower()
            if st in status_map:
                status_map[st] = int(row["count"])

    return {
        "labels": ["Completed", "Active (In Progress)", "Dropped"],
        "counts": [status_map["completed"], status_map["active"], status_map["dropped"]],
    }


def activity_type_distribution():
    """Breakdown of learning activities by category (Video, Quiz, Assignment, etc.)."""
    sql = """
        SELECT activity_type, COUNT(*) AS cnt
        FROM activities
        GROUP BY activity_type
        ORDER BY cnt DESC
    """
    df = _safe_query_df(sql)
    if df.empty:
        return {"types": [], "counts": []}
    return {
        "types": df["activity_type"].tolist(),
        "counts": [int(x) for x in df["cnt"].tolist()],
    }


def inactive_enrollment_report(threshold_days=14):
    """
    Identify active enrolments with no learning activity during the previous 14 days.
    
    CRITICAL METHODOLOGY NOTE:
    Missing activity is treated as a proactive signal for instructor support and early
    intervention, not definitive proof that a learner has ceased learning offline.
    
    Urgency classification using NumPy:
    - Critical: >= 30 days inactive
    - High:     21 - 29 days inactive
    - Medium:   14 - 20 days inactive
    """
    sql = """
        SELECT
            e.enrollment_id,
            l.learner_id,
            l.roll_no,
            l.learner_name,
            l.email,
            c.course_name,
            e.enrolled_at,
            MAX(a.activity_date) AS last_activity_raw
        FROM enrollments e
        JOIN learners l ON l.learner_id = e.learner_id
        JOIN courses c  ON c.course_id = e.course_id
        LEFT JOIN activities a ON a.enrollment_id = e.enrollment_id
        WHERE e.status = 'active'
        GROUP BY
            e.enrollment_id,
            l.learner_id,
            l.roll_no,
            l.learner_name,
            l.email,
            c.course_name,
            e.enrolled_at
        HAVING last_activity_raw IS NULL
            OR last_activity_raw < DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY last_activity_raw ASC, e.enrolled_at ASC
    """
    df = _safe_query_df(sql, params=(threshold_days,))
    if df.empty:
        return []

    now = pd.Timestamp.now()
    
    # Calculate days inactive from last activity or enrolment date if never active
    def calc_days_inactive(row):
        last_act = row["last_activity_raw"]
        if pd.notnull(last_act):
            diff = (now - pd.to_datetime(last_act)).days
            return max(0, diff)
        else:
            # Fall back to days since enrolment
            enrolled = pd.to_datetime(row["enrolled_at"])
            return max(0, (now - enrolled).days)

    df["days_inactive"] = df.apply(calc_days_inactive, axis=1).astype(int)

    # Format human-readable dates
    df["last_activity"] = df["last_activity_raw"].apply(
        lambda x: pd.to_datetime(x).strftime("%Y-%m-%d %H:%M") if pd.notnull(x) else "Never (No activity logged)"
    )
    df["enrolled_at_str"] = pd.to_datetime(df["enrolled_at"]).dt.strftime("%Y-%m-%d")

    # NumPy conditional urgency assignment
    days = df["days_inactive"].to_numpy()
    conditions = [days >= 30, days >= 21, days >= threshold_days]
    choices = ["critical", "high", "medium"]
    df["urgency"] = np.select(conditions, choices, default="low")

    # Sort most urgent first
    df = df.sort_values(by="days_inactive", ascending=False)

    return df[[
        "enrollment_id",
        "roll_no",
        "learner_name",
        "email",
        "course_name",
        "enrolled_at_str",
        "last_activity",
        "days_inactive",
        "urgency",
    ]].rename(columns={"enrolled_at_str": "enrolled_at"}).to_dict("records")
