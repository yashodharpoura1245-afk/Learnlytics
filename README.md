# Learnlytics — E-Learning Course Analytics System

A modern, full-stack college project web application designed to monitor online learning engagement, analyze course completion rates, track weekly student activities, and detect inactive enrollments using data intelligence.

---

## 🛠️ Technology Stack

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Chart.js | Dark navy dashboard theme, responsive layouts, interactive bar, line, and doughnut charts |
| **Backend** | Python 3.10+, Flask | Application routing, business logic, transactions, and REST APIs |
| **Database** | MySQL (InnoDB) | Relational persistence, foreign key cascades, parameterized SQL queries |
| **Data Analytics** | Pandas, NumPy | Vectorized completion calculations, time-series weekly resampling, 14-day inactivity triage |
| **Configuration** | `python-dotenv` | Environment variable isolation (`.env` credentials) |

---

## 📂 Project Directory Structure

```text
elearning_analytics/
│
├── app.py                 # Main Flask server with web routes & API endpoints
├── config.py              # Secure database connection loader (.env support)
├── analytics.py           # Pandas & NumPy data analytics engine
├── database.sql           # Database schema & safe initial sample data
├── requirements.txt       # Python dependencies list
├── test_db.py             # Database connectivity & table validator
├── .env.example           # Credential template
├── .env                   # Local credentials (git-ignored)
├── .gitignore             # Git ignore file for secrets and environments
├── README.md              # Setup guide and documentation
│
├── templates/             # Jinja2 HTML Templates
│   ├── base.html          # Global dark-navy layout, sidebar, connection banner
│   ├── dashboard.html     # Live statistics dashboard with metric cards & Chart.js
│   ├── courses.html       # Course catalog with Add & Edit modals
│   ├── learners.html      # Learner directory with Add & Edit modals
│   ├── enrollments.html   # Course enrollment & status update workflow
│   ├── activities.html    # Learning activity logging & status toggle
│   ├── analytics.html     # Chart.js visualizer & 14-day inactivity monitor
│   └── reports.html       # Exportable data hub with CSV downloads
│
└── static/
    ├── css/
    │   └── style.css      # Dark navy theme (#0B0F19, #111827, #6366F1)
    └── js/
        └── main.js        # Dynamic scripts & chart controllers
```

---

## 🚀 Setup & Startup Instructions

### Step 1: Open the Project in VS Code
1. Open **VS Code**.
2. Go to **File** ➔ **Open Folder...**
3. Select `C:\Users\vtu21\Downloads\elearning_analytics`.
4. Open the integrated terminal (`Ctrl + ~`).

---

### Step 2: Configure Your MySQL Password in `.env`
Open the `.env` file in the project root:
```ini
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_actual_mysql_password
MYSQL_DATABASE=elearning_db
```
> **Note:** If your MySQL root account has a password, enter it in `MYSQL_PASSWORD`. If you use XAMPP and root has no password, leave it empty (`MYSQL_PASSWORD=`).

---

### Step 3: Initialize the MySQL Database
Ensure your MySQL service is running, then import the database schema:
```powershell
mysql -u root -p < database.sql
```
*(Enter your MySQL password when prompted).*

---

### Step 4: Test Database Connectivity
Run the diagnostic script:
```powershell
python test_db.py
```
You should see:
```text
[SUCCESS] Connected to MySQL server!
[SUCCESS] Database 'elearning_db' exists.
[OK] Table 'courses': 5 records
[OK] Table 'learners': 7 records
[OK] Table 'enrollments': 10 records
[OK] Table 'activities': 11 records
[READY] All database tables are present and ready!
```

---

### Step 5: Launch the Application
Start the Flask server:
```powershell
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 📊 Analytics & Metric Methodology

### 1. Course Completion Rate
* **Formula:** `(Completed Enrolments / Total Enrolments) * 100`
* **Denominator:** Total number of registered enrolments across the platform (or within that course).
* **Division-by-Zero Handling:** If total enrolments equal zero, the metric gracefully returns `0.0%` via NumPy `np.where`.

### 2. 14-Day Inactive Enrolment Early Warning Rule
* **Definition:** An active enrolment where the learner has logged **no activities in the previous 14 days** (or since enrolment date if never active).
* **Pedagogical Note:** Missing activity is a proactive trigger for instructor support, not conclusive proof that offline learning is absent.
* **Urgency Tiers:**
  * 🔴 **Critical:** $\ge 30$ days inactive
  * 🟡 **High:** $21 - 29$ days inactive
  * 🔵 **Medium:** $14 - 20$ days inactive
