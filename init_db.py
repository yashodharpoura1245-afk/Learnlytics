"""
init_db.py — Automated Python Database Initializer for Learnlytics.
Reads database.sql and executes all SQL statements directly.
Fixes the PowerShell '<' redirection error by running entirely in Python!
"""

import os
import re
import mysql.connector
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

def get_credentials():
    host = os.getenv("MYSQL_HOST") or os.getenv("DB_HOST") or "localhost"
    port = int(os.getenv("MYSQL_PORT") or os.getenv("DB_PORT") or 3306)
    user = os.getenv("MYSQL_USER") or os.getenv("DB_USER") or "root"
    password = os.getenv("MYSQL_PASSWORD") if os.getenv("MYSQL_PASSWORD") is not None else os.getenv("DB_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME") or "elearning_db"
    return host, port, user, password, database

def update_env_password(new_password):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        env_path = ".env"
    
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("MYSQL_PASSWORD="):
            new_lines.append(f"MYSQL_PASSWORD={new_password}\n")
            updated = True
        elif line.startswith("DB_PASSWORD="):
            new_lines.append(f"DB_PASSWORD={new_password}\n")
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"\nMYSQL_PASSWORD={new_password}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def run():
    print("=" * 60)
    print("  LEARNLYTICS DATABASE INITIALIZER")
    print("=" * 60)

    host, port, user, password, database = get_credentials()

    # Step 1: Connect to MySQL Server
    conn = None
    while not conn:
        try:
            print(f"Connecting to MySQL ({user}@{host}:{port})...")
            conn = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                connect_timeout=5
            )
            print("[OK] Connected to MySQL successfully!")
            # If user provided a password and it worked, save it in .env
            if password:
                update_env_password(password)
                print("[OK] Updated .env file with working password.")
        except mysql.connector.Error as err:
            if err.errno == 1045:
                print(f"\n[ACCESS DENIED] Access denied for user '{user}'@'{host}'.")
                print("Your MySQL root account requires a password.")
                password = input("Please enter your MySQL root password: ").strip()
            elif err.errno in (2002, 2003):
                print(f"\n[ERROR] Cannot reach MySQL at {host}:{port}.")
                print("Please ensure your MySQL service (e.g., MySQL80 or XAMPP) is running.")
                return
            else:
                print(f"\n[ERROR] {err}")
                return

    # Step 2: Read database.sql
    sql_path = os.path.join(os.path.dirname(__file__), "database.sql")
    if not os.path.exists(sql_path):
        print(f"[ERROR] Cannot find {sql_path}!")
        conn.close()
        return

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Step 3: Execute SQL statements
    cursor = conn.cursor()
    print(f"\nExecuting {sql_path} into database '{database}'...")

    # Split statements safely by semicolon (ignoring comments)
    statements = sql_content.split(";")
    count = 0
    for stmt in statements:
        # Strip comments and whitespace
        clean_stmt = re.sub(r"--.*?\n", "", stmt).strip()
        if clean_stmt:
            try:
                cursor.execute(clean_stmt)
                count += 1
            except mysql.connector.Error as e:
                print(f"  [Notice] Statement notice: {e.msg}")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"[SUCCESS] Executed {count} SQL commands successfully!")
    print("\nVerifying tables...")

    # Step 4: Verify tables
    try:
        check_conn = mysql.connector.connect(
            host=host, port=port, user=user, password=password, database=database
        )
        cur = check_conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
        print(f"Tables created in '{database}': {tables}")
        for t in ["courses", "learners", "enrollments", "activities"]:
            if t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                cnt = cur.fetchone()[0]
                print(f"  • {t}: {cnt} records")
        check_conn.close()
        print("-" * 60)
        print("[READY] Database setup complete! You can now run: python app.py")
        print("=" * 60)
    except Exception as exc:
        print("Verification note:", exc)

if __name__ == "__main__":
    run()
