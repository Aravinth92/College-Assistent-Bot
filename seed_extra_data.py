import os
import sqlite3
import json
from database.db import get_db_connection

def seed_extra_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("--- Seeding Extra Department & Academic Data ---")

    # 1. Departments
    extra_departments = [
        ("Civil Engineering", "Dr. K. R. Ramanathan", 14, "Structural Engg Lab, Surveying Lab, Concrete Tech Lab", "Mon-Fri: 9:00 AM - 4:30 PM"),
        ("Electrical & Electronics Engineering", "Dr. V. Meenakshi", 11, "Power Systems Lab, Electrical Machines Lab, Control Systems Lab", "Mon-Fri: 9:00 AM - 4:30 PM"),
        ("Artificial Intelligence & Data Science", "Dr. R. Anitha", 10, "Deep Learning Lab, Data Analytics Lab, High Performance Computing Lab", "Mon-Fri: 9:00 AM - 4:30 PM"),
        ("Master of Business Administration (MBA)", "Dr. S. Venkataraman", 8, "Business Analytics Lab, Communication Lab, Finance Lab", "Mon-Fri: 9:00 AM - 4:30 PM")
    ]
    for name, hod, count, labs, timetable in extra_departments:
        try:
            cursor.execute('''
                INSERT INTO departments (name, hod, faculty_count, labs, timetable)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, hod, count, labs, timetable))
        except sqlite3.IntegrityError:
            pass

    # Map departments
    cursor.execute("SELECT id, name FROM departments")
    dept_map = {row['name']: row['id'] for row in cursor.fetchall()}

    # 2. Courses
    extra_courses = [
        ("Bachelor of Technology in Civil Engineering", "BTECH-CIVIL", dept_map.get("Civil Engineering"), "4 Years", "10+2 with Physics, Chemistry, Math (Minimum 55%)", 105000.0, "Semesters 1-8 covering Surveying, Structural Analysis, RCC Design, Environmental Engg", 60),
        ("Bachelor of Technology in Electrical Engineering", "BTECH-EEE", dept_map.get("Electrical & Electronics Engineering"), "4 Years", "10+2 with Physics, Chemistry, Math (Minimum 55%)", 110000.0, "Semesters 1-8 covering Electrical Machines, Power Systems, Control Systems, Power Electronics", 60),
        ("Bachelor of Technology in AI & Data Science", "BTECH-AIDS", dept_map.get("Artificial Intelligence & Data Science"), "4 Years", "10+2 with Physics, Chemistry, Math (Minimum 65%)", 135000.0, "Semesters 1-8 covering Machine Learning, Big Data, Deep Learning, NLP, Computer Vision", 120),
        ("Master of Business Administration", "MBA-GEN", dept_map.get("Master of Business Administration (MBA)"), "2 Years", "Bachelor Degree in any discipline (Minimum 50%) + TANCET/MAT/CAT Score", 95000.0, "Semesters 1-4 covering Financial Management, Marketing, HR, Business Analytics", 60)
    ]
    for name, code, dept_id, duration, eligibility, fees, syllabus, seats in extra_courses:
        try:
            cursor.execute('''
                INSERT INTO courses (name, code, department_id, duration, eligibility, fees, syllabus, seats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, code, dept_id, duration, eligibility, fees, syllabus, seats))
        except sqlite3.IntegrityError:
            pass

    # Map courses
    cursor.execute("SELECT id, code FROM courses")
    course_map = {row['code']: row['id'] for row in cursor.fetchall()}

    # 3. Faculty Members
    extra_faculty = [
        ("Dr. K. R. Ramanathan", "Professor & HOD", "ramanathan.civil@college.com", "+91 98765 55001", dept_map.get("Civil Engineering"), "Ph.D. in Structural Engineering (IIT Madras)", "Structural Analysis, Concrete Technology, Earthquake Engg", "Civil Block, Room 101"),
        ("Dr. V. Meenakshi", "Professor & HOD", "meenakshi.eee@college.com", "+91 98765 66001", dept_map.get("Electrical & Electronics Engineering"), "Ph.D. in Power Systems (Anna University)", "Smart Grids, Power Electronics, Renewable Energy", "EEE Block, Room 201"),
        ("Dr. R. Anitha", "Professor & HOD", "anitha.aids@college.com", "+91 98765 77001", dept_map.get("Artificial Intelligence & Data Science"), "Ph.D. in Machine Learning (IISc Bangalore)", "Deep Learning, Computer Vision, Generative AI", "AIDS Block, Room 301"),
        ("Dr. S. Venkataraman", "Professor & HOD", "venkat.mba@college.com", "+91 98765 88001", dept_map.get("Master of Business Administration (MBA)"), "Ph.D. in Financial Management (IIM Kozhikode), MBA", "Corporate Finance, Investment Analysis, Strategic Management", "Management Block, Room 401"),
        ("Prof. Karthik Raja", "Assistant Professor", "karthik.cs@college.com", "+91 98765 11003", dept_map.get("Computer Science & Engineering"), "M.Tech in Cybersecurity, B.Tech", "Ethical Hacking, Network Security, Operating Systems", "CSE Block, Room 308")
    ]
    for name, desig, email, phone, d_id, qual, spec, office in extra_faculty:
        cursor.execute("SELECT id FROM faculty WHERE email = ?", (email,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO faculty (name, designation, email, phone, department_id, qualification, specialization, office_location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, desig, email, phone, d_id, qual, spec, office))

    # 4. Subjects & Detailed Syllabus
    extra_subjects = [
        ("Structural Mechanics", "CE301", dept_map.get("Civil Engineering"), course_map.get("BTECH-CIVIL"), 3, 4,
         "Unit 1: Stress & Strain, Bending Moments & Shear Force Diagrams.\nUnit 2: Deflection of Beams, Columns & Struts (Euler Formula).\nUnit 3: Torsion of Shafts, Thin & Thick Cylinders.\nUnit 4: Strain Energy Methods, Slope Deflection Method.\nReference Books: 'Strength of Materials' by R. K. Bansal."),

        ("Electrical Machines I", "EE301", dept_map.get("Electrical & Electronics Engineering"), course_map.get("BTECH-EEE"), 3, 4,
         "Unit 1: Magnetic Circuits, Electromechanical Energy Conversion.\nUnit 2: DC Generators & DC Motors: Performance & Speed Control.\nUnit 3: Single Phase & Three Phase Transformers: Equivalent Circuit & Efficiency.\nUnit 4: Testing of DC Machines & Transformers.\nReference Books: 'Electrical Machinery' by P. S. Bimbhra."),

        ("Machine Learning Algorithms", "AD301", dept_map.get("Artificial Intelligence & Data Science"), course_map.get("BTECH-AIDS"), 3, 4,
         "Unit 1: Linear & Polynomial Regression, Gradient Descent Optimization.\nUnit 2: Classification: Naive Bayes, K-Nearest Neighbors, Logistic Regression.\nUnit 3: Decision Trees, Random Forests, Ensemble Learning (Boosting & Bagging).\nUnit 4: Model Evaluation: Confusion Matrix, ROC-AUC, K-Fold Cross Validation.\nReference Books: 'Pattern Recognition and Machine Learning' by Christopher Bishop."),

        ("Financial Management & Accounting", "MB101", dept_map.get("Master of Business Administration (MBA)"), course_map.get("MBA-GEN"), 1, 3,
         "Unit 1: Accounting Principles, Balance Sheet & Profit & Loss Statement.\nUnit 2: Ratio Analysis, Cash Flow & Fund Flow Statements.\nUnit 3: Capital Budgeting Decisions (NPV, IRR, Payback Period).\nUnit 4: Working Capital Management & Cost of Capital.\nReference Books: 'Financial Management' by I. M. Pandey.")
    ]
    for name, code, d_id, c_id, sem, cred, content in extra_subjects:
        try:
            cursor.execute('''
                INSERT INTO subjects (name, code, department_id, course_id, semester, credits, syllabus_content)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, code, d_id, c_id, sem, cred, content))
        except sqlite3.IntegrityError:
            pass

    # 5. Extra Announcements
    extra_announcements = [
        ("National Hackathon 2026 Registration Open", "Registrations are open for the 24-hour National Student Hackathon 'HackVerse 2026' scheduled for October 25th. Cash prizes up to 1.5 Lakhs. Register your teams before October 15th.", "event"),
        ("Mid-Semester Academic Assessment Schedule", "Mid-Semester internal examinations for 2nd, 3rd, and 4th-year B.Tech students will commence from October 10th. Attendance is mandatory.", "exam"),
        ("On-Campus Recruitment Drive: Amazon & Google", "Amazon & Google Software Engineering recruitment drives are scheduled for October 18th-20th. Eligible B.Tech CSE/AIDS students must submit updated resumes by October 10th.", "placement"),
        ("Diwali Festival Holiday Notice", "The college will remain closed from October 31st to November 3rd on account of Diwali holidays. Hostel mess will function as per holiday schedule.", "holiday")
    ]
    for title, content, cat in extra_announcements:
        cursor.execute("SELECT id FROM announcements WHERE title = ?", (title,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO announcements (title, content, category)
                VALUES (?, ?, ?)
            ''', (title, content, cat))

    # 6. Extra Placements
    extra_placements = [
        ("Amazon", "Software Development Engineer (SDE 1)", "B.Tech CSE/AIDS/ECE, CGPA > 7.5, No Active Backlogs", "28.0 - 32.0 LPA", "Oct 18, 2026", "Data Structures, System Design, Java/Python", "6 months pre-joining internship stipend of Rs. 80,000/month"),
        ("Google", "Associate Software Engineer", "B.Tech CSE/AIDS, CGPA > 8.0", "30.0 - 35.0 LPA", "Oct 20, 2026", "Competitive Programming, Graph Theory, Algorithms", "Summer Internship stipend of Rs. 1,00,000/month"),
        ("Wipro", "Project Engineer (Turbo)", "All Engineering Branches, CGPA > 6.0", "6.5 - 8.0 LPA", "Nov 05, 2026", "Java/C++, DBMS, Basic Web Development, Aptitude", "3 months training with Rs. 20,000/month stipend"),
        ("Larsen & Toubro (L&T)", "Graduate Engineer Trainee (GET)", "B.Tech Civil / Mechanical / EEE, CGPA > 6.5", "6.0 - 7.5 LPA", "Nov 12, 2026", "Core Engineering Fundamentals, CAD Software, Site Management", "1-year probation with performance appraisal")
    ]
    for company, role, elig, salary, date, skills, intern in extra_placements:
        cursor.execute("SELECT id FROM placements WHERE company_name = ? AND job_role = ?", (company, role))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO placements (company_name, job_role, eligibility, salary, recruitment_date, skills_required, internship_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (company, role, elig, salary, date, skills, intern))

    # 7. Prospectus RAG Document & Vector Chunks
    cursor.execute("SELECT id FROM documents WHERE filename = ?", ("College_Prospectus_2026_Handbook.pdf",))
    doc_row = cursor.fetchone()
    if not doc_row:
        cursor.execute('''
            INSERT INTO documents (filename, filepath)
            VALUES (?, ?)
        ''', ("College_Prospectus_2026_Handbook.pdf", "uploads/College_Prospectus_2026_Handbook.pdf"))
        doc_id = cursor.lastrowid
    else:
        doc_id = doc_row['id']

    prospectus_rag_chunks = [
        "FINANCIAL AID & SCHOLARSHIP POLICY: The college awards 100% tuition fee waiver to top 5% entrance rank holders in B.Tech programs. Merit-cum-means scholarships of up to Rs. 50,000 per year are available for students with family income below 3.0 Lakhs per annum.",
        "CENTRAL LIBRARY & DIGITAL RESOURCES: The central library houses over 45,000 volumes, 120 national and international journals, and provides 24/7 digital access to IEEE Xplore, ScienceDirect, ACM Digital Library, and Springer Link via campus Wi-Fi.",
        "HOSTEL AMENITIES & RULES: Male and female residential hostels offer 2-seater and 3-seater air-conditioned and non-AC rooms. Facilities include 24/7 power backup, high-speed Wi-Fi, laundry service, indoor games room, and a 4-meal nutritious mess menu.",
        "CAMPUS SPORTS COMPLEX & GYM: The campus features an Olympic-size swimming pool, 400m synthetic running track, basketball and volleyball courts, and a fully equipped gymnasium open from 6:00 AM - 8:30 AM and 4:30 PM - 7:30 PM.",
        "ANTI-RAGGING DISCIPLINARY POLICY: The college enforces a strict zero-tolerance policy against ragging in accordance with UGC guidelines. Anti-ragging committee contacts and helpline 1800-180-5522 are available 24/7."
    ]

    dummy_embedding = json.dumps([0.01 * (i % 10) for i in range(128)]).encode('utf-8')
    for chunk in prospectus_rag_chunks:
        cursor.execute("SELECT id FROM prospectus_chunks WHERE chunk_text = ?", (chunk,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO prospectus_chunks (document_id, chunk_text, embedding)
                VALUES (?, ?, ?)
            ''', (doc_id, chunk, dummy_embedding))

    conn.commit()
    conn.close()
    print("Extra data seeding successfully completed!")

if __name__ == "__main__":
    seed_extra_data()
