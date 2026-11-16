"""The eval set: questions about the university database with hand-written reference SQL.

This is the only university-specific file outside config/. Each reference query returns
only the columns that define a correct answer (see src/eval/compare.py); the agent may
return more. Expected results are fixed by db/seed.sql and checked in tests/test_eval.py.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class EvalQuestion:
    id: int
    question: str
    covers: str
    sql: str


_FAILED_BY_BEST_FALL_2025_TEACHER = """
WITH best AS (
    SELECT o.teacher_id FROM enrollments e
    JOIN course_offerings o ON o.id = e.offering_id
    JOIN semesters s ON s.id = o.semester_id
    WHERE s.name = 'Fall 2025'
    GROUP BY o.teacher_id ORDER BY AVG(e.grade) DESC LIMIT 1
)
SELECT DISTINCT st.id FROM enrollments e
JOIN students st ON st.id = e.student_id
JOIN course_offerings o ON o.id = e.offering_id
JOIN semesters s ON s.id = o.semester_id
WHERE o.teacher_id IN (SELECT teacher_id FROM best) AND e.grade < 60"""

QUESTIONS = [
    EvalQuestion(1, "How many students failed at least one course?",
                 "aggregation, pass-mark rule",
                 # The students, not the count: the agent lists them and the answer counts.
                 "SELECT DISTINCT student_id FROM enrollments WHERE grade < 60"),
    EvalQuestion(2, "What was the average grade in CS301 in Fall 2025?",
                 "aggregation, semester filter",
                 """SELECT AVG(e.grade) FROM enrollments e
                 JOIN course_offerings o ON o.id = e.offering_id
                 JOIN courses c ON c.id = o.course_id
                 JOIN semesters s ON s.id = o.semester_id
                 WHERE c.code = 'CS301' AND s.name = 'Fall 2025'"""),
    EvalQuestion(3, "How many students are enrolled in each course this semester?",
                 "semester filter ('this semester' = Fall 2026), course with 0 students",
                 """SELECT c.title, COUNT(e.id) FROM course_offerings o
                 JOIN courses c ON c.id = o.course_id
                 JOIN semesters s ON s.id = o.semester_id
                 LEFT JOIN enrollments e ON e.offering_id = o.id
                 WHERE s.name = 'Fall 2026'
                 GROUP BY c.title"""),
    EvalQuestion(4, "Which courses did Daniel Kim teach in Spring 2026?",
                 "teacher filter (a student has the same name)",
                 """SELECT c.title FROM course_offerings o
                 JOIN teachers t ON t.id = o.teacher_id
                 JOIN courses c ON c.id = o.course_id
                 JOIN semesters s ON s.id = o.semester_id
                 WHERE t.name = 'Daniel Kim' AND s.name = 'Spring 2026'"""),
    EvalQuestion(5, "What grades did John Smith get, and in which semester?",
                 "student filter",
                 """SELECT s.name, e.grade FROM enrollments e
                 JOIN students st ON st.id = e.student_id
                 JOIN course_offerings o ON o.id = e.offering_id
                 JOIN semesters s ON s.id = o.semester_id
                 WHERE st.name = 'John Smith'"""),
    EvalQuestion(6, "List every failing grade with the student, the course code and the semester.",
                 "joins over 5 tables, pass-mark rule",
                 """SELECT st.id, c.code, s.name, e.grade FROM enrollments e
                 JOIN students st ON st.id = e.student_id
                 JOIN course_offerings o ON o.id = e.offering_id
                 JOIN courses c ON c.id = o.course_id
                 JOIN semesters s ON s.id = o.semester_id
                 WHERE e.grade < 60"""),
    EvalQuestion(7, "What is Maria Garcia's average grade?",
                 "two students share the name: both must be answered",
                 """SELECT st.id, AVG(e.grade) FROM students st
                 JOIN enrollments e ON e.student_id = st.id
                 WHERE st.name = 'Maria Garcia'
                 GROUP BY st.id"""),
    EvalQuestion(8, "Which students failed a course in Fall 2026?",
                 "NULL grades (not graded yet) are not fails: the answer is empty",
                 """SELECT e.student_id FROM enrollments e
                 JOIN course_offerings o ON o.id = e.offering_id
                 JOIN semesters s ON s.id = o.semester_id
                 WHERE s.name = 'Fall 2026' AND e.grade < 60"""),
    EvalQuestion(9, "Which teacher had the highest average grade in Fall 2025, and which "
                    "students failed a course taught by that teacher in any semester?",
                 "multi-step, failures in any semester",
                 _FAILED_BY_BEST_FALL_2025_TEACHER),
    EvalQuestion(10, "Which teacher had the highest average grade in Fall 2025, and which "
                     "students failed a course taught by that teacher in Fall 2025?",
                 "multi-step, empty answer must not be widened to other semesters",
                 _FAILED_BY_BEST_FALL_2025_TEACHER + " AND s.name = 'Fall 2025'"),
]
