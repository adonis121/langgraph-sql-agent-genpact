- Grades are numeric 0-100, stored on enrollments.grade.
- Pass mark is 60: grade >= 60 passes, grade < 60 fails.
- grade IS NULL means "not graded yet" (the course is still running). Exclude NULL grades from
  averages and pass/fail counts, and never treat NULL as 0.
- The current semester is 'Fall 2026' (semesters.name). "This semester" / "currently" means Fall 2026.
- Semester names look like 'Fall 2025' or 'Spring 2026'.
- A course (courses) is taught in a specific semester by one teacher as a course offering
  (course_offerings). Students enroll in course offerings (enrollments).
- Names are not unique (two people can share a name); use ids to tell them apart and say so in the answer.
