"""
test_db.py — Diagnostic utility to test MySQL database connectivity and tables.
"""

import sys
from config import check_db_status, get_db_connection, get_masked_config

def run_diagnostics():
    print("=" * 60)
    print("  LEARNLYTICS DATABASE DIAGNOSTIC UTILITY")
    print("=" * 60)

    cfg = get_masked_config()
    print(f"Host:     {cfg['host']}:{cfg['port']}")
    print(f"User:     {cfg['user']}")
    print(f"Password: {cfg['password']}")
    print(f"Database: {cfg['database']}")
    print("-" * 60)

    status = check_db_status()

    if not status["connected"]:
        print("[ERROR] Cannot connect to MySQL server!")
        print(f"Details: {status['error']}")
        print("\nACTION NEEDED:")
        print(f"  {status['advice']}")
        print("\nPlease update MYSQL_PASSWORD in .env with your actual password.")
        print("=" * 60)
        return False

    print("[SUCCESS] Connected to MySQL server!")

    if not status["db_exists"]:
        print(f"[WARNING] Database '{cfg['database']}' does not exist.")
        print(f"Advice: {status['advice']}")
        print("Run: mysql -u root -p < database.sql")
        print("=" * 60)
        return False

    print(f"[SUCCESS] Database '{cfg['database']}' exists.")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = [list(r.values())[0] for r in cursor.fetchall()]
        print(f"[INFO] Tables present in database: {tables}")

        required = ["courses", "learners", "enrollments", "activities"]
        all_ok = True
        for tbl in required:
            if tbl in tables:
                cursor.execute(f"SELECT COUNT(*) AS c FROM {tbl}")
                cnt = cursor.fetchone()["c"]
                print(f"  [OK] Table '{tbl}': {cnt} records")
            else:
                print(f"  [MISSING] Table '{tbl}' is missing! Please re-run database.sql.")
                all_ok = False

        conn.close()
        print("-" * 60)
        if all_ok:
            print("[READY] All database tables are present and ready!")
        else:
            print("[NOTICE] Some tables are missing. Import database.sql to create them.")
        print("=" * 60)
        return all_ok

    except Exception as e:
        print(f"[ERROR] Querying tables failed: {e}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
