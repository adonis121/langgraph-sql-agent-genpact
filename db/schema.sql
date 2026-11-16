-- University database schema (SQLite).
-- Drop in reverse FK order so the script can be re-run.
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS course_offerings;
DROP TABLE IF EXISTS semesters;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS teachers;
DROP TABLE IF EXISTS departments;

-- Academic departments that own courses and employ teachers.
CREATE TABLE departments (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- People who teach course offerings. Names are not unique; email is.
CREATE TABLE teachers (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,                 -- full name, e.g. 'Daniel Kim'
    email         TEXT NOT NULL UNIQUE,
    department_id INTEGER NOT NULL REFERENCES departments(id)
);

-- People who enroll in course offerings. Names are not unique; email is.
CREATE TABLE students (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,               -- full name, e.g. 'Maria Garcia'
    email           TEXT NOT NULL UNIQUE,
    enrollment_year INTEGER NOT NULL CHECK (enrollment_year BETWEEN 2000 AND 2100)
);

-- The course catalogue: a subject that can be taught in many semesters.
CREATE TABLE courses (
    id            INTEGER PRIMARY KEY,
    code          TEXT NOT NULL UNIQUE,          -- e.g. 'CS301'
    title         TEXT NOT NULL,
    credits       INTEGER NOT NULL CHECK (credits > 0),
    department_id INTEGER NOT NULL REFERENCES departments(id)
);

-- Teaching periods, e.g. 'Fall 2025'.
CREATE TABLE semesters (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    year       INTEGER NOT NULL,
    term       TEXT NOT NULL CHECK (term IN ('Spring', 'Fall')),
    start_date TEXT NOT NULL,                    -- ISO date 'YYYY-MM-DD'
    end_date   TEXT NOT NULL,
    UNIQUE (year, term),
    CHECK (start_date < end_date)
);

-- A course taught by one teacher in one semester.
CREATE TABLE course_offerings (
    id          INTEGER PRIMARY KEY,
    course_id   INTEGER NOT NULL REFERENCES courses(id),
    teacher_id  INTEGER NOT NULL REFERENCES teachers(id),
    semester_id INTEGER NOT NULL REFERENCES semesters(id),
    UNIQUE (course_id, semester_id)              -- one section per course per semester
);

-- A student taking a course offering. The grade lives here.
CREATE TABLE enrollments (
    id          INTEGER PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    offering_id INTEGER NOT NULL REFERENCES course_offerings(id),
    grade       REAL CHECK (grade BETWEEN 0 AND 100),  -- NULL = not graded yet
    UNIQUE (student_id, offering_id)
);
