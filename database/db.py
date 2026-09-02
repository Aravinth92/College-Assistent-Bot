import os
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'student')),
            status TEXT NOT NULL CHECK(status IN ('active', 'inactive')) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. departments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            hod TEXT,
            faculty_count INTEGER DEFAULT 0,
            labs TEXT,
            timetable TEXT
        )
    ''')

    # 3. courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            department_id INTEGER,
            duration TEXT,
            eligibility TEXT,
            fees REAL,
            syllabus TEXT,
            seats INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
        )
    ''')

    # 4. students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            department_id INTEGER,
            course_id INTEGER,
            year INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
        )
    ''')

    # 5. faculty table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            designation TEXT,
            email TEXT,
            phone TEXT,
            department_id INTEGER,
            qualification TEXT,
            specialization TEXT,
            office_location TEXT,
            FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
        )
    ''')
    for col in ['phone TEXT', 'qualification TEXT', 'specialization TEXT', 'office_location TEXT']:
        try:
            cursor.execute(f"ALTER TABLE faculty ADD COLUMN {col}")
        except Exception:
            pass

    # 6. subjects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            department_id INTEGER,
            course_id INTEGER,
            semester INTEGER NOT NULL,
            credits INTEGER DEFAULT 3,
            syllabus_content TEXT,
            FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
    ''')
    try:
        cursor.execute("ALTER TABLE subjects ADD COLUMN credits INTEGER DEFAULT 3")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE subjects ADD COLUMN syllabus_content TEXT")
    except Exception:
        pass

    # 7. documents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            filepath TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 8. prospectus_chunks table (for RAG vector database storage)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prospectus_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            chunk_text TEXT NOT NULL,
            embedding BLOB NOT NULL, -- Serialized float list of embedding vectors
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    ''')

    # 9. faqs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE NOT NULL,
            answer TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General'
        )
    ''')

    # 10. announcements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('general', 'exam', 'holiday', 'admission', 'placement', 'event')),
            date_posted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 11. placements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS placements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            job_role TEXT NOT NULL,
            eligibility TEXT,
            salary TEXT,
            recruitment_date TEXT,
            skills_required TEXT,
            internship_info TEXT
        )
    ''')

    # 12. chatbot_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chatbot_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            is_answered INTEGER DEFAULT 1, -- 1 for answered, 0 for unanswered/fallback
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # 13. student_inquiries table (for student questionnaires and direct admin responses)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General Inquiry',
            message TEXT NOT NULL,
            admin_response TEXT,
            status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Answered', 'Closed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            answered_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

def seed_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if we already have users. If yes, skip seeding.
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    print("Seeding database with initial mock data...")

    # Seed Admin User
    admin_pw = generate_password_hash("admin123")
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, role, status)
        VALUES (?, ?, ?, ?, ?)
    ''', ('admin', 'admin@college.com', admin_pw, 'admin', 'active'))

    # Seed departments
    departments = [
        ("Computer Science & Engineering", "Dr. Rajesh Kumar", 15, "DBMS Lab, Networks Lab, AI Lab", "Mon-Fri: 9:00 AM - 4:30 PM"),
        ("Electronics & Communication Engineering", "Dr. S. K. Sharma", 12, "Microcontroller Lab, DSP Lab", "Mon-Fri: 9:00 AM - 4:30 PM"),
        ("Mechanical Engineering", "Dr. Amit Patel", 10, "CAD/CAM Lab, Thermodynamics Lab", "Mon-Fri: 9:00 AM - 4:30 PM"),
        ("Information Technology", "Dr. Neha Gupta", 8, "Web Tech Lab, Cloud Computing Lab", "Mon-Fri: 9:00 AM - 4:30 PM")
    ]
    cursor.executemany('''
        INSERT INTO departments (name, hod, faculty_count, labs, timetable)
        VALUES (?, ?, ?, ?, ?)
    ''', departments)

    # Fetch departments to map IDs
    cursor.execute("SELECT id, name FROM departments")
    dept_map = {row['name']: row['id'] for row in cursor.fetchall()}

    # Seed courses
    courses = [
        ("Bachelor of Technology in Computer Science", "BTECH-CSE", dept_map["Computer Science & Engineering"], "4 Years", "10+2 with Physics, Chemistry, Math (Minimum 60%)", 125000.0, "Semester 1-8 syllabus covering OS, DS, Algo, AI, Databases", 120),
        ("Bachelor of Technology in Electronics", "BTECH-ECE", dept_map["Electronics & Communication Engineering"], "4 Years", "10+2 with Physics, Chemistry, Math (Minimum 55%)", 115000.0, "Semester 1-8 syllabus covering VLSI, Signal processing, Microcontrollers", 60),
        ("Bachelor of Technology in Mechanical", "BTECH-ME", dept_map["Mechanical Engineering"], "4 Years", "10+2 with Physics, Chemistry, Math (Minimum 55%)", 110000.0, "Semester 1-8 syllabus covering Solid Mechanics, CAD, Thermal power", 60),
        ("Master of Technology in Computer Science", "MTECH-CSE", dept_map["Computer Science & Engineering"], "2 Years", "B.Tech/B.E. in CSE or related (Minimum 60%)", 85000.0, "Advanced algorithms, Big data analytics, Deep learning", 18)
    ]
    cursor.executemany('''
        INSERT INTO courses (name, code, department_id, duration, eligibility, fees, syllabus, seats)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', courses)

    # Fetch courses to map IDs
    cursor.execute("SELECT id, code FROM courses")
    course_map = {row['code']: row['id'] for row in cursor.fetchall()}

    # Seed Student User
    student_pw = generate_password_hash("student123")
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, role, status)
        VALUES (?, ?, ?, ?, ?)
    ''', ('student', 'student@college.com', student_pw, 'student', 'active'))
    student_user_id = cursor.lastrowid

    # Seed Student details
    cursor.execute('''
        INSERT INTO students (user_id, student_id, name, email, phone, department_id, course_id, year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (student_user_id, 'STU2026001', 'Aravind S', 'student@college.com', '9876543210', dept_map["Computer Science & Engineering"], course_map["BTECH-CSE"], 3))

    # Seed Faculty members
    faculty = [
        ("Dr. Rajesh Kumar", "Professor & HOD", "rajesh.cs@college.com", "+91 98765 11001", dept_map["Computer Science & Engineering"], "Ph.D. in Computer Science (IIT Delhi)", "Artificial Intelligence, Machine Learning, Data Structures", "CSE Block, Room 301"),
        ("Dr. Priyan Sen", "Associate Professor", "priyan.cs@college.com", "+91 98765 11002", dept_map["Computer Science & Engineering"], "Ph.D. in Software Engineering, M.E.", "Database Management Systems, Cloud Computing", "CSE Block, Room 305"),
        ("Dr. S. K. Sharma", "Professor & HOD", "sharma.ece@college.com", "+91 98765 22001", dept_map["Electronics & Communication Engineering"], "Ph.D. in VLSI Design, M.Tech", "VLSI Design, Signal Processing, Embedded Systems", "ECE Block, Room 201"),
        ("Dr. Ananya Roy", "Assistant Professor", "ananya.ece@college.com", "+91 98765 22002", dept_map["Electronics & Communication Engineering"], "M.Tech in Digital Communications, B.E.", "Wireless Communications, Microcontrollers", "ECE Block, Room 204"),
        ("Dr. Amit Patel", "Professor & HOD", "patel.me@college.com", "+91 98765 33001", dept_map["Mechanical Engineering"], "Ph.D. in Thermal Engineering (IIT Bombay)", "Thermodynamics, Fluid Mechanics, CAD/CAM", "Mech Block, Room 101"),
        ("Dr. Neha Gupta", "Professor & HOD", "neha.it@college.com", "+91 98765 44001", dept_map["Information Technology"], "Ph.D. in Information Security, M.Tech", "Cybersecurity, Web Technologies, Computer Networks", "IT Block, Room 401")
    ]
    cursor.executemany('''
        INSERT INTO faculty (name, designation, email, phone, department_id, qualification, specialization, office_location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', faculty)

    # Seed Subjects & Detailed Syllabus
    subjects = [
        ("Programming in C & Problem Solving", "CS101", dept_map["Computer Science & Engineering"], course_map["BTECH-CSE"], 1, 4, 
         "Unit 1: Introduction to Algorithms, Flowcharts, C Basics, Data Types & Operators.\nUnit 2: Control Structures (if-else, switch, loops), Functions & Recursion.\nUnit 3: Arrays, Strings, Pointers & Dynamic Memory Allocation.\nUnit 4: Structures, Unions, File Handling & Preprocessor directives.\nReference Books: 'Programming in ANSI C' by E. Balagurusamy, 'C Programming Language' by Kernighan & Ritchie."),
        
        ("Data Structures & Algorithms", "CS301", dept_map["Computer Science & Engineering"], course_map["BTECH-CSE"], 3, 4, 
         "Unit 1: Linear Data Structures: Stacks, Queues, Circular Queues, Linked Lists.\nUnit 2: Trees: Binary Trees, BST, AVL Trees, B-Trees, Heap Trees.\nUnit 3: Graphs: Representation, BFS, DFS, Minimum Spanning Trees (Kruskal, Prim), Shortest Path (Dijkstra).\nUnit 4: Sorting & Searching: Quick Sort, Merge Sort, Heap Sort, Hashing & Collision Resolution.\nReference Books: 'Data Structures and Algorithm Analysis' by Mark Allen Weiss."),
        
        ("Database Management Systems", "CS501", dept_map["Computer Science & Engineering"], course_map["BTECH-CSE"], 5, 4, 
         "Unit 1: Database Architecture, ER Modeling, Relational Algebra & Calculus.\nUnit 2: SQL Queries, Views, Triggers, Stored Procedures, Normalization (1NF, 2NF, 3NF, BCNF).\nUnit 3: Transaction Processing, ACID Properties, Concurrency Control (Locking, Timestamping).\nUnit 4: Indexing, B+ Trees, Crash Recovery & NoSQL Overview.\nReference Books: 'Database System Concepts' by Silberschatz, Korth, Sudarshan."),
        
        ("Artificial Intelligence & Machine Learning", "CS601", dept_map["Computer Science & Engineering"], course_map["BTECH-CSE"], 6, 3, 
         "Unit 1: AI Search Strategies (Uninformed, Heuristic A*, Minimax Games).\nUnit 2: Supervised Learning: Linear/Logistic Regression, Decision Trees, Support Vector Machines (SVM).\nUnit 3: Unsupervised Learning: K-Means Clustering, PCA Dimensionality Reduction.\nUnit 4: Neural Networks, Deep Learning Fundamentals & Natural Language Processing (NLP).\nReference Books: 'Artificial Intelligence: A Modern Approach' by Russell & Norvig."),
        
        ("Analog & Digital Circuits", "EC301", dept_map["Electronics & Communication Engineering"], course_map["BTECH-ECE"], 3, 4, 
         "Unit 1: Semiconductor Diodes, BJT, FET Amplifiers, Operational Amplifiers (Op-Amps).\nUnit 2: Boolean Algebra, Karnaugh Maps, Combinational Circuits (Adders, Mux, Demux).\nUnit 3: Sequential Circuits: Flip-Flops, Counters, Shift Registers.\nUnit 4: A/D and D/A Converters, Waveform Generators.\nReference Books: 'Digital Design' by M. Morris Mano."),
        
        ("Thermodynamics & Fluid Mechanics", "ME301", dept_map["Mechanical Engineering"], course_map["BTECH-ME"], 3, 4, 
         "Unit 1: Zeroth, First & Second Laws of Thermodynamics, Entropy & Pure Substances.\nUnit 2: Vapor & Gas Power Cycles (Rankine, Otto, Diesel, Dual Cycles).\nUnit 3: Fluid Statics & Kinematics, Bernoulli's Equation, Viscous Flow in Pipes.\nUnit 4: Boundary Layer Theory, Hydraulic Turbines & Pumps.\nReference Books: 'Engineering Thermodynamics' by P. K. Nag.")
    ]
    cursor.executemany('''
        INSERT INTO subjects (name, code, department_id, course_id, semester, credits, syllabus_content)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', subjects)

    # Seed FAQs
    faqs = [
        ("What are the college timings?", "The college functions from 9:00 AM to 4:30 PM, Monday to Friday. Library is open until 6:00 PM.", "General"),
        ("What is the hostel fee?", "The hostel fee is Rs. 75,000 per academic year, which includes lodging, boarding (mess), and high-speed Wi-Fi.", "Hostel"),
        ("What courses are available?", "We offer B.Tech in CSE, ECE, ME, and M.Tech in CSE. Please navigate to the Courses tab on your dashboard for more details.", "Academics"),
        ("What documents are required for admission?", "Required documents include: 10th and 12th Marks Sheets, Transfer Certificate, Migration Certificate, Passport size photographs, and Aadhaar Card copy.", "Admission"),
        ("When are the semester exams?", "Odd semester exams are typically conducted in November-December, and even semester exams in April-May. Detailed timetables are posted in the Exams section of the dashboard.", "Exams"),
        ("What are the library timings?", "The Central Library is open from 8:30 AM to 6:30 PM on all working days, and from 9:00 AM to 2:00 PM on Saturdays.", "Facilities"),
        ("What are the bus routes?", "The college operates 15 buses across the city covering major residential areas. Detailed route maps and timings are available at the admin office.", "Transport"),
        ("How do I apply for a bonafide certificate?", "You can apply for a bonafide certificate by submitting a written request form signed by your HOD to the administrative block counter 2. Processing takes 2 working days.", "Administrative")
    ]
    cursor.executemany('''
        INSERT INTO faqs (question, answer, category)
        VALUES (?, ?, ?)
    ''', faqs)

    # Seed announcements
    announcements = [
        ("Semester Exam Registration Open", "All students must register for the upcoming End Semester Examination by September 15th. Fine applies post deadline.", "exam"),
        ("On-Campus Recruitment Drive: TCS", "TCS will be visiting our campus on September 22nd. Registration link is active under the placements tab for eligible B.Tech CSE/ECE students.", "placement"),
        ("Ganesh Chaturthi Holiday Notice", "The college will remain closed on September 5th on account of Ganesh Chaturthi.", "holiday"),
        ("Annual Tech Fest - 'Invento 2026'", "We are proud to announce our Annual National level Technical Festival 'Invento 2026' on October 12th-13th. Register now for project display and hackathons!", "event")
    ]
    cursor.executemany('''
        INSERT INTO announcements (title, content, category)
        VALUES (?, ?, ?)
    ''', announcements)

    # Seed placements
    placements = [
        ("TCS", "Systems Engineer", "B.Tech CSE/ECE, CGPA > 6.5, No Active Backlogs", "3.6 - 7.0 LPA", "Sept 22, 2026", "Java/Python, Aptitude, DBMS, Communication Skills", "Internship stipend of 15k/month for 6 months prior to joining"),
        ("Microsoft", "Software Engineer Intern", "B.Tech CSE, CGPA > 8.0", "1.2 Lakhs / Month (Stipend)", "Oct 10, 2026", "Data Structures, Algorithms, Coding Excellence", "12-week summer internship with pre-placement offer possibility"),
        ("Infosys", "Specialist Programmer", "B.Tech CSE/ECE/IT, CGPA > 6.0", "9.5 LPA", "Oct 28, 2026", "Advanced coding, Problem solving, OOPs concepts", "6 months training at Mysore campus")
    ]
    cursor.executemany('''
        INSERT INTO placements (company_name, job_role, eligibility, salary, recruitment_date, skills_required, internship_info)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', placements)

    # Seed student inquiries / questionnaires
    inquiries = [
        (student_user_id, "Request for Hostel Room Allotment Letter", "Hostel", "Can I get my official room allotment letter for scholarship verification?", None, "Pending"),
        (student_user_id, "Syllabus details for elective Artificial Intelligence", "Academics", "Where can I view the detailed syllabus for the 6th-semester AI elective course?", "The detailed syllabus has been updated under the Courses tab on your dashboard under B.Tech CSE.", "Answered")
    ]
    cursor.executemany('''
        INSERT INTO student_inquiries (user_id, subject, category, message, admin_response, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', inquiries)

    conn.commit()
    conn.close()
    print("Database seeding completed.")

if __name__ == "__main__":
    init_db()
    seed_db()
