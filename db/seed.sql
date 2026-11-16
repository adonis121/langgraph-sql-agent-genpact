-- Seed data. Hand-written so every edge case is intentional and eval answers stay stable.
-- Pass mark is 60 (business rule, documented outside the schema).
-- Fall 2026 is the current semester: its enrollments have no grade yet.

INSERT INTO departments (id, name) VALUES
    (1, 'Computer Science'),
    (2, 'Mathematics'),
    (3, 'Physics');

INSERT INTO teachers (id, name, email, department_id) VALUES
    (1, 'Alice Morgan',  'alice.morgan@uni.example',  1),
    (2, 'Daniel Kim',    'daniel.kim@uni.example',    1),  -- a student has the same name
    (3, 'Priya Shah',    'priya.shah@uni.example',    1),
    (4, 'Robert Chen',   'robert.chen@uni.example',   2),
    (5, 'Elena Petrova', 'elena.petrova@uni.example', 2),
    (6, 'Samuel Okafor', 'samuel.okafor@uni.example', 2),  -- Math teacher, teaches a CS course
    (7, 'Laura Bianchi', 'laura.bianchi@uni.example', 3),
    (8, 'Thomas Weber',  'thomas.weber@uni.example',  3);  -- on sabbatical: no offerings

INSERT INTO students (id, name, email, enrollment_year) VALUES
    (1,  'Maria Garcia',   'maria.garcia@student.uni.example',    2023),
    (2,  'Maria Garcia',   'maria.garcia2@student.uni.example',   2024),  -- same name as id 1
    (3,  'Daniel Kim',     'daniel.kim@student.uni.example',      2024),  -- same name as a teacher
    (4,  'John Smith',     'john.smith@student.uni.example',      2022),
    (5,  'Aisha Rahman',   'aisha.rahman@student.uni.example',    2022),
    (6,  'Lucas Silva',    'lucas.silva@student.uni.example',     2022),
    (7,  'Emma Johnson',   'emma.johnson@student.uni.example',    2022),
    (8,  'Noah Williams',  'noah.williams@student.uni.example',   2023),
    (9,  'Olivia Brown',   'olivia.brown@student.uni.example',    2023),
    (10, 'Liam Davis',     'liam.davis@student.uni.example',      2023),
    (11, 'Sofia Rossi',    'sofia.rossi@student.uni.example',     2023),
    (12, 'Ethan Miller',   'ethan.miller@student.uni.example',    2023),
    (13, 'Mia Wilson',     'mia.wilson@student.uni.example',      2023),
    (14, 'Arjun Patel',    'arjun.patel@student.uni.example',     2024),
    (15, 'Chloe Martin',   'chloe.martin@student.uni.example',    2024),
    (16, 'Mateo Lopez',    'mateo.lopez@student.uni.example',     2024),
    (17, 'Hannah Schmidt', 'hannah.schmidt@student.uni.example',  2024),
    (18, 'Yuki Tanaka',    'yuki.tanaka@student.uni.example',     2024),
    (19, 'Omar Haddad',    'omar.haddad@student.uni.example',     2024),
    (20, 'Grace Lee',      'grace.lee@student.uni.example',       2025),
    (21, 'Ivan Novak',     'ivan.novak@student.uni.example',      2025),
    (22, 'Zara Ahmed',     'zara.ahmed@student.uni.example',      2025),
    (23, 'Leo Fischer',    'leo.fischer@student.uni.example',     2025),
    (24, 'Nina Kowalski',  'nina.kowalski@student.uni.example',   2025),
    (25, 'Samuel Adeyemi', 'samuel.adeyemi@student.uni.example',  2025),
    (26, 'Ava Thompson',   'ava.thompson@student.uni.example',    2025),
    (27, 'Ben Carter',     'ben.carter@student.uni.example',      2026),
    (28, 'Lily Evans',     'lily.evans@student.uni.example',      2026),
    (29, 'Ryan O''Connor', 'ryan.oconnor@student.uni.example',    2026),  -- apostrophe in name
    (30, 'Sara Nilsson',   'sara.nilsson@student.uni.example',    2026);  -- no enrollments

INSERT INTO courses (id, code, title, credits, department_id) VALUES
    (1,  'CS101',   'Introduction to Programming', 6, 1),
    (2,  'CS201',   'Data Structures',             6, 1),
    (3,  'CS301',   'Databases',                   5, 1),
    (4,  'CS350',   'Machine Learning',            5, 1),
    (5,  'CS220',   'Statistics for Computing',    4, 1),  -- taught by a Math teacher
    (6,  'MATH101', 'Calculus I',                  6, 2),
    (7,  'MATH201', 'Linear Algebra',              5, 2),
    (8,  'MATH301', 'Probability Theory',          5, 2),
    (9,  'MATH410', 'Topology',                    4, 2),  -- never offered
    (10, 'PHYS101', 'Mechanics',                   6, 3),
    (11, 'PHYS201', 'Electromagnetism',            5, 3),
    (12, 'PHYS301', 'Quantum Physics',             4, 3);

INSERT INTO semesters (id, name, year, term, start_date, end_date) VALUES
    (1, 'Fall 2024',   2024, 'Fall',   '2024-09-01', '2025-01-31'),
    (2, 'Spring 2025', 2025, 'Spring', '2025-02-15', '2025-06-30'),
    (3, 'Fall 2025',   2025, 'Fall',   '2025-09-01', '2026-01-31'),
    (4, 'Spring 2026', 2026, 'Spring', '2026-02-15', '2026-06-30'),
    (5, 'Fall 2026',   2026, 'Fall',   '2026-09-01', '2027-01-31');  -- current, ungraded

INSERT INTO course_offerings (id, course_id, teacher_id, semester_id) VALUES
    -- Fall 2024
    (1,  1,  1, 1),   -- CS101   Alice Morgan
    (2,  2,  2, 1),   -- CS201   Daniel Kim
    (3,  6,  4, 1),   -- MATH101 Robert Chen
    (4,  10, 7, 1),   -- PHYS101 Laura Bianchi
    (5,  7,  5, 1),   -- MATH201 Elena Petrova
    -- Spring 2025
    (6,  3,  3, 2),   -- CS301   Priya Shah
    (7,  5,  6, 2),   -- CS220   Samuel Okafor
    (8,  6,  5, 2),   -- MATH101 Elena Petrova (other teacher than Fall 2024)
    (9,  11, 7, 2),   -- PHYS201 Laura Bianchi
    (10, 1,  1, 2),   -- CS101   Alice Morgan
    -- Fall 2025
    (11, 2,  2, 3),   -- CS201   Daniel Kim
    (12, 3,  3, 3),   -- CS301   Priya Shah
    (13, 7,  4, 3),   -- MATH201 Robert Chen
    (14, 8,  6, 3),   -- MATH301 Samuel Okafor
    (15, 10, 7, 3),   -- PHYS101 Laura Bianchi
    (16, 4,  1, 3),   -- CS350   Alice Morgan
    -- Spring 2026
    (17, 1,  2, 4),   -- CS101   Daniel Kim (other teacher than 2024/2025)
    (18, 4,  3, 4),   -- CS350   Priya Shah
    (19, 6,  4, 4),   -- MATH101 Robert Chen
    (20, 12, 7, 4),   -- PHYS301 Laura Bianchi
    (21, 5,  6, 4),   -- CS220   Samuel Okafor
    -- Fall 2026 (current)
    (22, 2,  2, 5),   -- CS201   Daniel Kim
    (23, 3,  3, 5),   -- CS301   Priya Shah
    (24, 7,  5, 5),   -- MATH201 Elena Petrova
    (25, 11, 7, 5),   -- PHYS201 Laura Bianchi
    (26, 8,  6, 5);   -- MATH301 Samuel Okafor: nobody enrolled

INSERT INTO enrollments (student_id, offering_id, grade) VALUES
    -- Fall 2024
    (2, 1, 78), (3, 1, 85), (14, 1, 91), (15, 1, 67), (16, 1, 55), (17, 1, 73), (18, 1, 88),
    (1, 2, 82), (4, 2, 45), (5, 2, 90), (6, 2, 71), (8, 2, 58), (9, 2, 66),  -- John Smith fails CS201
    (2, 3, 70), (3, 3, 62), (14, 3, 84), (15, 3, 48), (19, 3, 77), (16, 3, 61),  -- Chloe Martin fails MATH101
    (7, 4, 74), (10, 4, 81), (11, 4, 69), (12, 4, 52), (13, 4, 88),
    (1, 5, 75), (5, 5, 93), (6, 5, 64), (7, 5, 80), (8, 5, 71), (10, 5, 59),
    -- Spring 2025
    (1, 6, 88), (4, 6, 79), (5, 6, 95), (6, 6, 57), (9, 6, 82), (11, 6, 74),
    (2, 7, 68), (3, 7, 74), (7, 7, 83), (12, 7, 63), (13, 7, 90), (14, 7, 86),
    (15, 8, 65), (17, 8, 58), (18, 8, 79), (19, 8, 82), (16, 8, 70),  -- Chloe Martin retakes and passes
    (7, 9, 77), (10, 9, 72), (13, 9, 85), (8, 9, 49), (11, 9, 66),
    (19, 10, 80), (8, 10, 74), (12, 10, 69), (10, 10, 91), (9, 10, 60),  -- 60 = exactly the pass mark
    -- Fall 2025
    (4, 11, 72), (14, 11, 89), (15, 11, 76), (17, 11, 64), (2, 11, 81), (3, 11, 70), (18, 11, 93), (19, 11, 55),  -- John Smith retakes and passes
    (14, 12, 92), (18, 12, 90), (7, 12, 86), (8, 12, 84), (12, 12, 88), (13, 12, 94),
    (2, 13, 73), (3, 13, 66), (15, 13, 52), (16, 13, 77), (17, 13, 69), (20, 13, 85), (21, 13, 61),
    (1, 14, 91), (5, 14, 87), (6, 14, 70), (9, 14, 78), (11, 14, 82), (10, 14, 64),
    (20, 15, 79), (21, 15, 56), (22, 15, 83), (23, 15, 71), (24, 15, 68), (25, 15, 90), (26, 15, 74),
    (1, 16, 85), (4, 16, 68), (5, 16, 97), (6, 16, 73), (9, 16, 80), (11, 16, 76),
    -- Spring 2026
    (20, 17, 88), (21, 17, 59), (22, 17, 76), (23, 17, 82), (24, 17, 65), (26, 17, 71), (25, 17, 94),
    (14, 18, 87), (18, 18, 91), (12, 18, 54), (13, 18, 89), (7, 18, 79), (2, 18, 83),
    (20, 19, 72), (22, 19, 68), (23, 19, 47), (24, 19, 81), (25, 19, 86), (26, 19, 63),
    (10, 20, 84), (11, 20, 71), (7, 20, 66), (13, 20, 92), (4, 20, 58),
    (16, 21, 75), (17, 21, 82), (19, 21, 69), (15, 21, 61), (1, 21, 90), (3, 21, 77),
    -- Fall 2026 (current semester: not graded yet)
    (20, 22, NULL), (22, 22, NULL), (23, 22, NULL), (25, 22, NULL), (26, 22, NULL), (24, 22, NULL), (27, 22, NULL),
    (2, 23, NULL), (3, 23, NULL), (14, 23, NULL), (15, 23, NULL), (16, 23, NULL), (19, 23, NULL),
    (22, 24, NULL), (24, 24, NULL), (25, 24, NULL), (26, 24, NULL), (28, 24, NULL), (29, 24, NULL),
    (20, 25, NULL), (21, 25, NULL), (23, 25, NULL), (27, 25, NULL), (28, 25, NULL), (29, 25, NULL);
