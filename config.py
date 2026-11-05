"""
config.py — Database configuration and connection manager for Learnlytics.
Supports MYSQL_* and DB_* environment variables, connection testing,
safe credential masking, and robust error diagnostics.
"""

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load variables from .env file if available
load_dotenv()


def get_db_config():
    """
    Read database credentials from environment variables.
    Supports both standard MYSQL_* prefixes and legacy DB_* variables.
    """
    host = os.getenv("MYSQL_HOST") or os.getenv("DB_HOST") or "localhost"
    try:
        port = int(os.getenv("MYSQL_PORT") or os.getenv("DB_PORT") or 3306)
    except ValueError:
        port = 3306
    user = os.getenv("MYSQL_USER") or os.getenv("DB_USER") or "root"
    
    # Check MYSQL_PASSWORD first, then DB_PASSWORD
    if os.getenv("MYSQL_PASSWORD") is not None:
        password = os.getenv("MYSQL_PASSWORD")
    else:
        password = os.getenv("DB_PASSWORD", "")

    database = os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME") or "elearning_db"

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }


def get_masked_config():
    """Return config with password masked for safe diagnostic display."""
    cfg = get_db_config()
    pw = cfg["password"]
    masked_pw = "[EMPTY (no password)]" if not pw else ("*" * min(len(pw), 8) + " (set)")
    return {
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "password": masked_pw,
        "database": cfg["database"],
    }


def check_db_status():
    """
    Test connectivity to MySQL and check whether the target database exists.
    Returns a dict with detailed status and troubleshooting advice.
    """
    cfg = get_db_config()
    status = {
        "connected": False,
        "db_exists": False,
        "error": None,
        "error_code": None,
        "advice": "",
        "config": get_masked_config(),
    }

    # Step 1: Attempt connection to MySQL server (without selecting DB first)
    try:
        server_conn = mysql.connector.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            connect_timeout=3,
        )
        status["connected"] = True
    except Error as err:
        status["error"] = str(err)
        status["error_code"] = err.errno
        if err.errno == 1045:
            if not cfg["password"]:
                status["advice"] = (
                    "MySQL rejected access: Access denied for user 'root'@'localhost' (using password: NO). "
                    "Your MySQL root account requires a password. Open the .env file in the project folder and "
                    "set MYSQL_PASSWORD=your_actual_mysql_password."
                )
            else:
                status["advice"] = (
                    "MySQL rejected access: Invalid password. Check your password in the .env file."
                )
        elif err.errno in (2003, 2002):
            status["advice"] = (
                f"Cannot connect to MySQL server at {cfg['host']}:{cfg['port']}. "
                "Ensure your MySQL service (e.g. MySQL80 or XAMPP) is running."
            )
        else:
            status["advice"] = f"MySQL Error {err.errno}: {err.msg}"
        return status

    # Step 2: Check if target database exists
    try:
        cursor = server_conn.cursor()
        cursor.execute("SHOW DATABASES LIKE %s", (cfg["database"],))
        result = cursor.fetchone()
        cursor.close()
        server_conn.close()

        if result:
            status["db_exists"] = True
            status["advice"] = "MySQL connected and database exists."
        else:
            status["db_exists"] = False
            status["advice"] = (
                f"Connected to MySQL server, but database '{cfg['database']}' does not exist yet. "
                "Import database.sql using MySQL Workbench, or run: mysql -u root -p < database.sql"
            )
    except Error as err:
        status["error"] = str(err)
        status["advice"] = f"Error checking database: {err}"

    return status


def get_db_connection(select_db=True):
    """
    Establish and return a new connection to MySQL.
    Raises mysql.connector.Error if connection fails.
    """
    cfg = get_db_config()
    conn_params = {
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "password": cfg["password"],
        "connect_timeout": 5,
        "autocommit": False,
    }
    if select_db:
        conn_params["database"] = cfg["database"]

    return mysql.connector.connect(**conn_params)


def fetch_all(query, params=None):
    """Execute a SELECT query and return all matching rows as dictionaries."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        conn.close()


def fetch_one(query, params=None):
    """Execute a SELECT query and return the first matching row as a dictionary."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        cursor.close()
        return row
    finally:
        conn.close()


def execute_query(query, params=None):
    """
    Execute an INSERT, UPDATE, or DELETE query within a transaction.
    Commits on success, rolls back on error, and returns the cursor.lastrowid.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        return last_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
