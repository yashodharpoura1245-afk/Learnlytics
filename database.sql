-- ============================================================
--  Learnlytics — E-Learning Course Analytics System
--  Database Schema & Initial Safe Sample Data
-- ============================================================

CREATE DATABASE IF NOT EXISTS elearning_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE elearning_db;

-- ------------------------------------------------------------
-- 1. Courses Table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
    course_id   INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(150) NOT NULL UNIQUE,
    category    VARCHAR(100) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 2. Learners Table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS learners (
    learner_id   INT AUTO_INCREMENT PRIMARY KEY,
    roll_no      VARCHAR(50)  NOT NULL UNIQUE,
    learner_name VARCHAR(120) NOT NULL,
    email        VARCHAR(150) NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 3. Enrollments Table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    learner_id    INT NOT NULL,
    course_id     INT NOT NULL,
    enrolled_at   DATE NOT NULL,
    status        ENUM('active', 'completed', 'dropped') DEFAULT 'active',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_learner_course UNIQUE (learner_id, course_id),
    CONSTRAINT fk_enroll_learner FOREIGN KEY (learner_id)
        REFERENCES learners(learner_id) ON DELETE CASCADE,
    CONSTRAINT fk_enroll_course  FOREIGN KEY (course_id)
        REFERENCES courses(course_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- 4. Learning Activities Table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activities (
    activity_id   INT AUTO_INCREMENT PRIMARY KEY,
    enrollment_id INT NOT NULL,
    activity_date DATETIME NOT NULL,
    activity_type VARCHAR(60) NOT NULL,
    completed     TINYINT(1) DEFAULT 1,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_activity_enroll FOREIGN KEY (enrollment_id)
        REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Safe Initial Sample Records (INSERT IGNORE preserves data)
-- ============================================================

INSERT IGNORE INTO courses (course_id, course_name, category) VALUES
(1, 'Python for Data Analysis',       'Programming'),
(2, 'Full Stack Web Development',     'Web Development'),
(3, 'Machine Learning Fundamentals',  'Data Science'),
(4, 'Database Systems & SQL Mastery', 'Database'),
(5, 'Cloud Computing with AWS',       'Cloud & DevOps');

INSERT IGNORE INTO learners (learner_id, roll_no, learner_name, email) VALUES
(1, 'STU001', 'Alice Johnson',  'alice.johnson@example.com'),
(2, 'STU002', 'Bob Smith',      'bob.smith@example.com'),
(3, 'STU003', 'Carol White',    'carol.white@example.com'),
(4, 'STU004', 'David Brown',    'david.brown@example.com'),
(5, 'STU005', 'Eva Martinez',   'eva.martinez@example.com'),
(6, 'STU006', 'Frank Wilson',   'frank.wilson@example.com'),
(7, 'STU007', 'Grace Hopper',   'grace.hopper@example.com');

INSERT IGNORE INTO enrollments (enrollment_id, learner_id, course_id, enrolled_at, status) VALUES
(1, 1, 1, '2026-09-01', 'completed'),
(2, 1, 2, '2026-09-10', 'active'),
(3, 2, 1, '2026-09-12', 'active'),
(4, 2, 3, '2026-09-15', 'completed'),
(5, 3, 2, '2026-09-20', 'active'),
(6, 4, 4, '2026-08-15', 'active'),
(7, 5, 5, '2026-08-01', 'active'),
(8, 6, 1, '2026-10-01', 'active'),
(9, 7, 3, '2026-10-05', 'completed'),
(10, 7, 4, '2026-10-10', 'active');

-- Sample activities across recent dates
INSERT IGNORE INTO activities (activity_id, enrollment_id, activity_date, activity_type, completed) VALUES
(1, 1, '2026-09-05 10:30:00', 'Quiz', 1),
(2, 1, '2026-09-15 14:00:00', 'Assignment', 1),
(3, 1, '2026-09-28 16:45:00', 'Video Lecture', 1),
(4, 2, '2026-10-25 09:15:00', 'Video Lecture', 1),
(5, 3, '2026-10-26 11:30:00', 'Quiz', 1),
(6, 4, '2026-09-28 15:20:00', 'Assignment', 1),
(7, 6, '2026-08-20 10:00:00', 'Video Lecture', 1),
(8, 7, '2026-08-10 14:00:00', 'Reading', 1),
(9, 8, '2026-10-27 16:30:00', 'Discussion Forum', 1),
(10, 9, '2026-10-20 18:00:00', 'Quiz', 1),
(11, 10, '2026-10-26 13:45:00', 'Video Lecture', 1);
