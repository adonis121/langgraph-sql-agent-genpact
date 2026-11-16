# Examples from real runs

All runs used `gpt-4.1-mini` on the seeded database. Each SQL block, result and answer
below is copied from the trace file named in the example. Nothing is invented or edited. The
SQL is shown after `validate_sql`, which adds `LIMIT 200` when it is missing. View any run with
`python -m src.show_trace traces/examples/<file>`.

| # | Shows | Trace |
|---|---|---|
| 1 | Aggregation with the pass-mark rule | `aggregation-failed-students.jsonl` |
| 2 | Join over 4 tables, teacher + semester filter, a student with the same name | `join-teacher-semester.jsonl` |
| 3 | Multi-step: step 2 uses an id from step 1 | `multi-step.jsonl` |
| 4 | Two students with the same name | `duplicate-names.jsonl` |
| 5 | Clarification with `interrupt()` and resume | `clarification-interrupt.jsonl` |
| 6 | Write request rejected, no SQL | `out-of-scope-delete.jsonl` |
| 7 | Empty result, one retry, no widening | `empty-result-two-steps.jsonl` |

---

## 1. Aggregation: "How many students failed at least one course?"

Plan: `answerable`, 1 step: *Find all students who have at least one enrollment with a grade
below 60 (excluding NULL grades), returning their ids and names.* The pass mark (60) and
"NULL means not graded" come from `config/university_notes.md`, not from the question.

```sql
SELECT DISTINCT students.id, students.name
FROM students
JOIN enrollments ON students.id = enrollments.student_id
WHERE enrollments.grade IS NOT NULL AND enrollments.grade < 60
LIMIT 200
```

11 rows:

| id | name |
|---|---|
| 16 | Mateo Lopez |
| 4 | John Smith |
| 8 | Noah Williams |
| 15 | Chloe Martin |
| 12 | Ethan Miller |
| 10 | Liam Davis |
| 6 | Lucas Silva |
| 17 | Hannah Schmidt |
| 19 | Omar Haddad |
| 21 | Ivan Novak |
| 23 | Leo Fischer |

> 11 students failed at least one course. Their names and ids are: Mateo Lopez (16), John
> Smith (4), Noah Williams (8), Chloe Martin (15), Ethan Miller (12), Liam Davis (10), Lucas
> Silva (6), Hannah Schmidt (17), Omar Haddad (19), Ivan Novak (21), and Leo Fischer (23).

## 2. Join + filters: "Which courses did Daniel Kim teach in Spring 2026?"

There is a teacher **and** a student called Daniel Kim (student id 3). "teach" makes it the
teacher, so the query joins `teachers`.

```sql
SELECT c.id, c.title
FROM courses c
JOIN course_offerings co ON c.id = co.course_id
JOIN teachers t ON co.teacher_id = t.id
JOIN semesters s ON co.semester_id = s.id
WHERE t.name = 'Daniel Kim' AND s.name = 'Spring 2026'
LIMIT 200
```

| id | title |
|---|---|
| 1 | Introduction to Programming |

> Daniel Kim taught the course "Introduction to Programming" in Spring 2026.

## 3. Multi-step: "Which teacher had the highest average grade in Fall 2025, and which students failed a course taught by that teacher"

Plan: `answerable`, 2 steps:
1. Find the teacher(s) with the highest average grade in Fall 2025, returning their ids and names.
2. Find the students who failed any course taught by the teacher(s) from step 1 in Fall 2025, returning their ids and names.

Step 1 keeps ties (`= MAX(...)`, not `LIMIT 1`):

```sql
WITH teacher_avg AS (
  SELECT
    t.id AS teacher_id,
    t.name AS teacher_name,
    AVG(e.grade) AS avg_grade
  FROM teachers t
  JOIN course_offerings co ON co.teacher_id = t.id
  JOIN semesters s ON s.id = co.semester_id
  JOIN enrollments e ON e.offering_id = co.id
  WHERE s.name = 'Fall 2025' AND e.grade IS NOT NULL
  GROUP BY t.id, t.name
)
SELECT teacher_id AS id, teacher_name AS name
FROM teacher_avg
WHERE avg_grade = (SELECT MAX(avg_grade) FROM teacher_avg)
LIMIT 200
```

| id | name |
|---|---|
| 3 | Priya Shah |

Step 2 uses `teacher_id = 3`, copied from step 1's result:

```sql
SELECT DISTINCT s.id, s.name
FROM students s
JOIN enrollments e ON e.student_id = s.id
JOIN course_offerings co ON co.id = e.offering_id
JOIN semesters sem ON sem.id = co.semester_id
WHERE co.teacher_id = 3
  AND sem.name = 'Fall 2025'
  AND e.grade IS NOT NULL
  AND e.grade < 60
LIMIT 200
```

0 rows → the empty-result retry ran → the model returned the same query → 0 rows again, accepted.

> The teacher with the highest average grade in Fall 2025 was Priya Shah (id 3). No students
> failed any course taught by Priya Shah in Fall 2025.

The planner read the second part as "in Fall 2025" as well. In any semester the answer would be
Lucas Silva and Ethan Miller. See [known-limitations.md](known-limitations.md).

## 4. Same name: "What grades did Maria Garcia get?"

Two students are called Maria Garcia. The planner does not ask which one is meant. Step 1 finds
both, and step 2 uses both ids.

```sql
SELECT id, name FROM students WHERE name = 'Maria Garcia'
LIMIT 200
```

| id | name |
|---|---|
| 1 | Maria Garcia |
| 2 | Maria Garcia |

```sql
SELECT 
  e.student_id,
  c.id AS course_id,
  c.title AS course_title,
  s.id AS semester_id,
  s.name AS semester_name,
  e.grade
FROM enrollments e
JOIN course_offerings co ON e.offering_id = co.id
JOIN courses c ON co.course_id = c.id
JOIN semesters s ON co.semester_id = s.id
WHERE e.student_id IN (1, 2)
ORDER BY e.student_id, s.year, s.term, c.id
LIMIT 200
```

| student_id | course_id | course_title | semester_id | semester_name | grade |
|---|---|---|---|---|---|
| 1 | 2 | Data Structures | 1 | Fall 2024 | 82.0 |
| 1 | 7 | Linear Algebra | 1 | Fall 2024 | 75.0 |
| 1 | 4 | Machine Learning | 3 | Fall 2025 | 85.0 |
| 1 | 8 | Probability Theory | 3 | Fall 2025 | 91.0 |
| 1 | 3 | Databases | 2 | Spring 2025 | 88.0 |
| 1 | 5 | Statistics for Computing | 4 | Spring 2026 | 90.0 |
| 2 | 1 | Introduction to Programming | 1 | Fall 2024 | 78.0 |
| 2 | 6 | Calculus I | 1 | Fall 2024 | 70.0 |
| 2 | 2 | Data Structures | 3 | Fall 2025 | 81.0 |
| 2 | 7 | Linear Algebra | 3 | Fall 2025 | 73.0 |
| 2 | 5 | Statistics for Computing | 2 | Spring 2025 | 68.0 |
| 2 | 3 | Databases | 5 | Fall 2026 | NULL |
| 2 | 4 | Machine Learning | 4 | Spring 2026 | 83.0 |

> Maria Garcia (id 1) got these grades:
> - Data Structures (Fall 2024): 82.0
> - Linear Algebra (Fall 2024): 75.0
> - Databases (Spring 2025): 88.0
> - Machine Learning (Fall 2025): 85.0
> - Probability Theory (Fall 2025): 91.0
> - Statistics for Computing (Spring 2026): 90.0
>
> Maria Garcia (id 2) got these grades:
> - Introduction to Programming (Fall 2024): 78.0
> - Calculus I (Fall 2024): 70.0
> - Data Structures (Fall 2025): 81.0
> - Linear Algebra (Fall 2025): 73.0
> - Statistics for Computing (Spring 2025): 68.0
> - Machine Learning (Spring 2026): 83.0
> - Databases (Fall 2026): not graded yet (NULL)

The NULL grade (current semester) is reported as "not graded yet", not as a fail. Note the SQL's
`ORDER BY s.term` sorts by text, so Spring 2025 comes after Fall 2025 in the table. The
answer fixed the order for student 1 but not for student 2.

## 5. Clarification: "Who is the best teacher?"

```
[1] plan   decision=needs_clarification
           reason: The term 'best' is subjective and needs a measurable criterion.
           clarifying question: By what measure do you want to determine the best teacher?
    -- paused, asked the user: By what measure do you want to determine the best teacher?
    -- user replied: the highest average grade in Fall 2025
[2] ask_user      clarification: the highest average grade in Fall 2025
[3] plan   decision=answerable, 2 steps
```

The graph paused inside `ask_user` (`interrupt()`), and the CLI asked in the terminal. The run
then resumed on the same thread with `Command(resume=reply)`. The original question was not
rewritten. The reply went to the planner as `clarification`.

Step 1: all teachers' averages in Fall 2025.

```sql
SELECT t.id, t.name, AVG(e.grade) AS average_grade
FROM teachers t
JOIN course_offerings co ON t.id = co.teacher_id
JOIN semesters s ON co.semester_id = s.id
JOIN enrollments e ON co.id = e.offering_id
WHERE s.name = 'Fall 2025' AND e.grade IS NOT NULL
GROUP BY t.id, t.name
LIMIT 200
```

| id | name | average_grade |
|---|---|---|
| 1 | Alice Morgan | 79.83333333333333 |
| 2 | Daniel Kim | 75.0 |
| 3 | Priya Shah | 89.0 |
| 4 | Robert Chen | 69.0 |
| 6 | Samuel Okafor | 78.66666666666667 |
| 7 | Laura Bianchi | 74.42857142857143 |

Step 2 (the highest of those, ties kept) returned `3 | Priya Shah`. The full SQL is in the trace.

> The best teacher in Fall 2025, with the highest average student grade of 89.0, is Priya Shah (id 3).

## 6. Rejected: "Delete all students who failed a course"

```
[1] plan      decision=out_of_scope
              reason: The request asks to delete data, which is out of scope.
[2] decline   status=rejected
```

No SQL is generated or run.

> I can't help with that: The request asks to delete data, which is out of scope.
> I can only answer questions that read data from this database; I never change it.

Before the planner existed (milestone 4), this question produced a `SELECT` and the answer
"Delete students with these IDs: …". The data was safe because of the read-only connection, but the answer was wrong.

## 7. Empty result: "Which students took the course Quantum Basket Weaving?"

There is no such course. Plan: 2 steps (find the course, then its students).

```sql
SELECT id, title
FROM courses
WHERE title = 'Quantum Basket Weaving'
LIMIT 200
```

0 rows. `check_result` used the one empty-result retry, with a hint that the model may fix
spelling or a join but must never widen or remove a filter. The model returned the same query,
which again gave 0 rows and was accepted. Step 2 then ran (and was also retried once):

```sql
SELECT students.id, students.name
FROM enrollments
JOIN course_offerings ON enrollments.offering_id = course_offerings.id
JOIN students ON enrollments.student_id = students.id
WHERE course_offerings.course_id IN (
    SELECT id FROM courses WHERE title = 'Quantum Basket Weaving'
)
LIMIT 200
```

0 rows. All results were empty, so `answer` made no LLM call:

> The query returned no matching records.

Step 2 running after an empty step 1 costs extra calls. This is listed in
[known-limitations.md](known-limitations.md).
