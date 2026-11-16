"""Database tests: build, constraints, edge cases, and reference answers. No LLM."""
import sqlite3

import pytest

from src.db.build_db import build_database

PASS_MARK = 60


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "university.db"
    build_database(path)
    return path


@pytest.fixture
def conn(db_path):
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    yield connection
    connection.rollback()  # constraint tests must not leave rows behind
    connection.close()


def query(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


# --- Build -----------------------------------------------------------------

def test_build_returns_expected_row_counts(tmp_path):
    counts = build_database(tmp_path / "u.db")
    assert counts == {
        "departments": 3, "teachers": 8, "students": 30, "courses": 12,
        "semesters": 5, "course_offerings": 26, "enrollments": 152,
    }


# --- Constraints -----------------------------------------------------------

@pytest.mark.parametrize("sql", [
    "INSERT INTO enrollments (student_id, offering_id, grade) VALUES (999, 1, 70)",   # FK student
    "INSERT INTO course_offerings (course_id, teacher_id, semester_id) VALUES (1, 999, 1)",  # FK teacher
    "INSERT INTO enrollments (student_id, offering_id, grade) VALUES (2, 1, 70)",     # duplicate enrollment
    "INSERT INTO course_offerings (course_id, teacher_id, semester_id) VALUES (1, 2, 1)",  # 2nd section
    "INSERT INTO enrollments (student_id, offering_id, grade) VALUES (30, 1, 101)",   # grade > 100
    "INSERT INTO courses (code, title, credits, department_id) VALUES ('X1', 'X', 0, 1)",  # credits
    "INSERT INTO courses (code, title, credits, department_id) VALUES ('CS101', 'X', 3, 1)",  # code unique
    "INSERT INTO semesters (name, year, term, start_date, end_date) "
    "VALUES ('Summer 2026', 2026, 'Summer', '2026-07-01', '2026-08-31')",            # term
    "INSERT INTO students (name, email, enrollment_year) "
    "VALUES ('X', 'maria.garcia@student.uni.example', 2025)",                        # email unique
])
def test_constraint_rejects_bad_row(conn, sql):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql)


def test_names_are_not_unique(conn):
    conn.execute("INSERT INTO students (name, email, enrollment_year) "
                 "VALUES ('Maria Garcia', 'third.maria@student.uni.example', 2026)")


# --- Edge cases in the seed data ---------------------------------------------

def test_two_students_named_maria_garcia(conn):
    rows = query(conn, "SELECT id FROM students WHERE name = 'Maria Garcia'")
    assert len(rows) == 2


def test_daniel_kim_is_both_teacher_and_student(conn):
    assert query(conn, "SELECT COUNT(*) FROM teachers WHERE name = 'Daniel Kim'") == [(1,)]
    assert query(conn, "SELECT COUNT(*) FROM students WHERE name = 'Daniel Kim'") == [(1,)]


def test_current_semester_is_ungraded(conn):
    rows = query(conn, """
        SELECT COUNT(*), COUNT(e.grade) FROM enrollments e
        JOIN course_offerings o ON o.id = e.offering_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE s.name = 'Fall 2026'""")
    total, graded = rows[0]
    assert total > 0 and graded == 0


def test_past_semesters_are_fully_graded(conn):
    rows = query(conn, """
        SELECT COUNT(*) FROM enrollments e
        JOIN course_offerings o ON o.id = e.offering_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE s.name <> 'Fall 2026' AND e.grade IS NULL""")
    assert rows == [(0,)]


def test_one_grade_exactly_at_pass_mark(conn):
    assert query(conn, "SELECT COUNT(*) FROM enrollments WHERE grade = ?", (PASS_MARK,)) == [(1,)]


def test_john_smith_failed_then_passed_cs201(conn):
    rows = query(conn, """
        SELECT s.name, e.grade FROM enrollments e
        JOIN students st ON st.id = e.student_id
        JOIN course_offerings o ON o.id = e.offering_id
        JOIN courses c ON c.id = o.course_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE st.name = 'John Smith' AND c.code = 'CS201'
        ORDER BY s.start_date""")
    assert rows == [("Fall 2024", 45.0), ("Fall 2025", 72.0)]


def test_student_without_enrollments(conn):
    rows = query(conn, """
        SELECT st.name FROM students st
        LEFT JOIN enrollments e ON e.student_id = st.id
        WHERE e.id IS NULL""")
    assert rows == [("Sara Nilsson",)]


def test_teacher_without_offerings(conn):
    rows = query(conn, """
        SELECT t.name FROM teachers t
        LEFT JOIN course_offerings o ON o.teacher_id = t.id
        WHERE o.id IS NULL""")
    assert rows == [("Thomas Weber",)]


def test_course_never_offered(conn):
    rows = query(conn, """
        SELECT c.code FROM courses c
        LEFT JOIN course_offerings o ON o.course_id = c.id
        WHERE o.id IS NULL""")
    assert rows == [("MATH410",)]


def test_offering_without_enrollments(conn):
    rows = query(conn, """
        SELECT c.code, s.name FROM course_offerings o
        JOIN courses c ON c.id = o.course_id
        JOIN semesters s ON s.id = o.semester_id
        LEFT JOIN enrollments e ON e.offering_id = o.id
        WHERE e.id IS NULL""")
    assert rows == [("MATH301", "Fall 2026")]


def test_math101_taught_by_two_teachers(conn):
    rows = query(conn, """
        SELECT COUNT(DISTINCT o.teacher_id) FROM course_offerings o
        JOIN courses c ON c.id = o.course_id WHERE c.code = 'MATH101'""")
    assert rows == [(2,)]


def test_teacher_teaches_course_of_other_department(conn):
    rows = query(conn, """
        SELECT DISTINCT t.name, c.code FROM course_offerings o
        JOIN teachers t ON t.id = o.teacher_id
        JOIN courses c ON c.id = o.course_id
        WHERE t.department_id <> c.department_id""")
    assert rows == [("Samuel Okafor", "CS220")]


def test_name_with_apostrophe(conn):
    assert query(conn, "SELECT COUNT(*) FROM students WHERE name = 'Ryan O''Connor'") == [(1,)]


def test_students_never_enrolled_before_their_enrollment_year(conn):
    rows = query(conn, """
        SELECT st.name, s.name FROM enrollments e
        JOIN students st ON st.id = e.student_id
        JOIN course_offerings o ON o.id = e.offering_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE s.year < st.enrollment_year""")
    assert rows == []


# --- The five example questions (reference SQL) ------------------------------

def test_q1_average_grade_cs301_fall_2025(conn):
    rows = query(conn, """
        SELECT AVG(e.grade) FROM enrollments e
        JOIN course_offerings o ON o.id = e.offering_id
        JOIN courses c ON c.id = o.course_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE c.code = 'CS301' AND s.name = 'Fall 2025'""")
    assert rows == [(89.0,)]


def test_q2_courses_taught_by_daniel_kim_spring_2026(conn):
    rows = query(conn, """
        SELECT c.code, c.title FROM course_offerings o
        JOIN teachers t ON t.id = o.teacher_id
        JOIN courses c ON c.id = o.course_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE t.name = 'Daniel Kim' AND s.name = 'Spring 2026'""")
    assert rows == [("CS101", "Introduction to Programming")]


def test_q3_enrolled_students_per_course_current_semester(conn):
    rows = query(conn, """
        SELECT c.code, COUNT(e.id) FROM course_offerings o
        JOIN courses c ON c.id = o.course_id
        JOIN semesters s ON s.id = o.semester_id
        LEFT JOIN enrollments e ON e.offering_id = o.id
        WHERE s.name = 'Fall 2026'
        GROUP BY c.code ORDER BY c.code""")
    assert rows == [("CS201", 7), ("CS301", 6), ("MATH201", 6), ("MATH301", 0), ("PHYS201", 6)]


def test_q4_students_who_failed_a_course(conn):
    rows = query(conn, """
        SELECT st.id, c.code, s.name, e.grade FROM enrollments e
        JOIN students st ON st.id = e.student_id
        JOIN course_offerings o ON o.id = e.offering_id
        JOIN courses c ON c.id = o.course_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE e.grade < ?""", (PASS_MARK,))
    assert len(rows) == 16
    assert len({r[0] for r in rows}) == 11  # some students fail more than once
    assert all(r[3] is not None for r in rows)  # NULL grades are not failures


def test_q5_multi_step_best_teacher_then_their_failing_students(conn):
    step1 = query(conn, """
        SELECT t.id, t.name, AVG(e.grade) AS avg_grade FROM enrollments e
        JOIN course_offerings o ON o.id = e.offering_id
        JOIN teachers t ON t.id = o.teacher_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE s.name = 'Fall 2025'
        GROUP BY t.id ORDER BY avg_grade DESC""")
    best_id, best_name, best_avg = step1[0]
    assert (best_name, best_avg) == ("Priya Shah", 89.0)
    assert step1[1][2] < best_avg  # clear winner, no tie

    step2 = query(conn, """
        SELECT st.name, c.code, s.name, e.grade FROM enrollments e
        JOIN students st ON st.id = e.student_id
        JOIN course_offerings o ON o.id = e.offering_id
        JOIN courses c ON c.id = o.course_id
        JOIN semesters s ON s.id = o.semester_id
        WHERE o.teacher_id = ? AND e.grade < ?
        ORDER BY s.start_date""", (best_id, PASS_MARK))
    assert step2 == [
        ("Lucas Silva", "CS301", "Spring 2025", 57.0),
        ("Ethan Miller", "CS350", "Spring 2026", 54.0),
    ]


def test_bonus_maria_garcia_average_returns_both_students(conn):
    rows = query(conn, """
        SELECT st.id, st.email, ROUND(AVG(e.grade), 2) FROM students st
        JOIN enrollments e ON e.student_id = st.id
        WHERE st.name = 'Maria Garcia'
        GROUP BY st.id ORDER BY st.id""")
    assert rows == [
        (1, "maria.garcia@student.uni.example", 85.17),
        (2, "maria.garcia2@student.uni.example", 75.5),
    ]
