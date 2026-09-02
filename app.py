import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from database.db import get_db_connection, init_db, seed_db
from werkzeug.security import generate_password_hash, check_password_hash
from chatbot.pdf_processor import extract_text_from_pdf, chunk_text
from chatbot.embeddings import get_embedding, serialize_vector
from chatbot.chatbot import query_chatbot

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(24))

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Database on Startup
with app.app_context():
    init_db()
    seed_db()

# --- Authentication Decorators ---
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash("Unauthorized access. Admin privileges required.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'student':
            flash("Authorized for student portal only.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            if user['status'] != 'active':
                flash("Your account has been deactivated. Please contact the college office.", "error")
                return redirect(url_for('login'))
                
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            flash("Successfully logged in!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "error")
            
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
            
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            if user['role'] != 'admin':
                flash("Access denied. This login portal is restricted to administrators.", "error")
                return redirect(url_for('admin_login'))
                
            if user['status'] != 'active':
                flash("Your admin account has been deactivated.", "error")
                return redirect(url_for('admin_login'))
                
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            flash("Welcome to the Admin Control Panel!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid administrator credentials.", "error")
            
    return render_template('admin_login.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    phone = request.form.get('phone')
    
    if not name or not email or not username or not password:
        flash("All fields are required.", "error")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if username or email exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
    if cursor.fetchone():
        flash("Username or email already exists.", "error")
        conn.close()
        return redirect(url_for('login'))
        
    try:
        pw_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, status)
            VALUES (?, ?, ?, 'student', 'active')
        ''', (username, email, pw_hash))
        user_id = cursor.lastrowid
        
        # Generate a unique student roll number
        student_id = f"STU{user_id:04d}{secrets.randbelow(100):02d}"
        
        cursor.execute('''
            INSERT INTO students (user_id, student_id, name, email, phone, year)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (user_id, student_id, name, email, phone))
        conn.commit()
        flash("Registration successful! You can now log in.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error during registration: {e}", "error")
    finally:
        conn.close()
        
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Successfully logged out.", "success")
    return redirect(url_for('login'))

# --- Student Portal Routes ---
@app.route('/student/dashboard')
@student_required
def student_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get student profile details
    cursor.execute('''
        SELECT s.name, s.student_id, s.phone, s.year, d.name as dept_name, c.name as course_name 
        FROM students s 
        LEFT JOIN departments d ON s.department_id = d.id 
        LEFT JOIN courses c ON s.course_id = c.id 
        WHERE s.user_id = ?
    ''', (session.get('user_id'),))
    student = cursor.fetchone()
    
    # Get announcements
    cursor.execute("SELECT title, content, category, date_posted FROM announcements ORDER BY date_posted DESC LIMIT 5")
    announcements = cursor.fetchall()
    
    # Get FAQs
    cursor.execute("SELECT question, answer, category FROM faqs LIMIT 5")
    faqs = cursor.fetchall()
    
    conn.close()
    return render_template('student_dashboard.html', student=student, announcements=announcements, faqs=faqs, active_page='dashboard')

@app.route('/student/chatbot')
@student_required
def student_chatbot():
    return render_template('chatbot.html', active_page='chatbot')

@app.route('/student/inquiries', methods=['GET', 'POST'])
@student_required
def student_inquiries():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        category = request.form.get('category')
        message = request.form.get('message')
        
        if subject and message:
            try:
                cursor.execute('''
                    INSERT INTO student_inquiries (user_id, subject, category, message, status)
                    VALUES (?, ?, ?, ?, 'Pending')
                ''', (user_id, subject, category, message))
                conn.commit()
                flash("Inquiry submitted successfully! The administration will review and respond.", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error submitting inquiry: {e}", "error")
        else:
            flash("Subject and Message are required.", "error")
            
        return redirect(url_for('student_inquiries'))
        
    cursor.execute('''
        SELECT id, subject, category, message, admin_response, status, created_at, answered_at
        FROM student_inquiries
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    inquiries = cursor.fetchall()
    conn.close()
    
    return render_template('student_inquiries.html', inquiries=inquiries, active_page='inquiries')

@app.route('/student/departments')
@student_required
def student_departments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, hod, faculty_count, labs, timetable FROM departments ORDER BY name")
    departments = cursor.fetchall()
    conn.close()
    return render_template('departments.html', departments=departments, active_page='departments')

@app.route('/student/faculty')
@student_required
def student_faculty():
    dept_id = request.args.get('department_id', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cursor.fetchall()
    
    query = '''
        SELECT f.id, f.name, f.designation, f.email, f.phone, f.qualification, f.specialization, f.office_location,
               d.name as dept_name
        FROM faculty f
        LEFT JOIN departments d ON f.department_id = d.id
        WHERE 1=1
    '''
    params = []
    
    if dept_id:
        query += " AND f.department_id = ?"
        params.append(dept_id)
        
    query += " ORDER BY f.name ASC"
    
    cursor.execute(query, params)
    faculty = cursor.fetchall()
    conn.close()
    
    return render_template('student_faculty.html', faculty=faculty, departments=departments, selected_dept=dept_id, active_page='faculty')

@app.route('/student/courses')
@student_required
def student_courses():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.name, c.code, c.duration, c.eligibility, c.fees, c.syllabus, c.seats, d.name as dept_name
        FROM courses c 
        LEFT JOIN departments d ON c.department_id = d.id
        ORDER BY c.name
    ''')
    courses = cursor.fetchall()
    conn.close()
    return render_template('courses.html', courses=courses, active_page='courses')

@app.route('/student/syllabus')
@student_required
def student_syllabus():
    dept_id = request.args.get('department_id', '')
    course_id = request.args.get('course_id', '')
    semester = request.args.get('semester', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cursor.fetchall()
    
    cursor.execute("SELECT id, name, code FROM courses ORDER BY name")
    courses = cursor.fetchall()
    
    query = '''
        SELECT s.id, s.name, s.code, s.semester, s.credits, s.syllabus_content,
               d.name as dept_name, c.name as course_name, c.code as course_code
        FROM subjects s
        LEFT JOIN departments d ON s.department_id = d.id
        LEFT JOIN courses c ON s.course_id = c.id
        WHERE 1=1
    '''
    params = []
    
    if dept_id:
        query += " AND s.department_id = ?"
        params.append(dept_id)
    if course_id:
        query += " AND s.course_id = ?"
        params.append(course_id)
    if semester:
        query += " AND s.semester = ?"
        params.append(semester)
        
    query += " ORDER BY s.semester ASC, s.code ASC"
    
    cursor.execute(query, params)
    subjects = cursor.fetchall()
    conn.close()
    
    return render_template('student_syllabus.html', 
                           subjects=subjects, 
                           departments=departments, 
                           courses=courses, 
                           selected_dept=dept_id, 
                           selected_course=course_id, 
                           selected_sem=semester, 
                           active_page='syllabus')

@app.route('/student/placements')
@student_required
def student_placements():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, company_name, job_role, eligibility, salary, recruitment_date, skills_required, internship_info FROM placements ORDER BY company_name")
    placements = cursor.fetchall()
    conn.close()
    return render_template('placements.html', placements=placements, active_page='placements')

@app.route('/student/faqs')
@student_required
def student_faqs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer, category FROM faqs ORDER BY category")
    faqs = cursor.fetchall()
    conn.close()
    return render_template('faqs.html', faqs=faqs, active_page='faqs')

# --- Chatbot API Route ---
@app.route('/chatbot/query', methods=['POST'])
@login_required
def chatbot_query():
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({"answer": "Please ask a question.", "is_answered": 0}), 400
        
    user_id = session.get('user_id')
    answer, is_answered = query_chatbot(question, user_id)
    
    return jsonify({"answer": answer, "is_answered": is_answered})

# --- Admin Portal Routes ---
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Gather numerical counts for statistics
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM students")
    stats['students'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM departments")
    stats['departments'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM courses")
    stats['courses'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM faqs")
    stats['faqs'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM documents")
    stats['documents'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM announcements")
    stats['announcements'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chatbot_history")
    stats['total_queries'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chatbot_history WHERE is_answered = 0")
    stats['unanswered_queries'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM student_inquiries WHERE status = 'Pending'")
    stats['pending_inquiries'] = cursor.fetchone()[0]
    
    # 2. Query chatbot history logs
    cursor.execute('''
        SELECT ch.question, ch.answer, ch.is_answered, ch.timestamp, u.username
        FROM chatbot_history ch
        LEFT JOIN users u ON ch.user_id = u.id
        ORDER BY ch.timestamp DESC LIMIT 10
    ''')
    chat_history = cursor.fetchall()
    
    # 3. Retrieve list of unanswered questions (questions requiring FAQ attention)
    cursor.execute('''
        SELECT ch.id, ch.question, ch.timestamp, u.username
        FROM chatbot_history ch
        LEFT JOIN users u ON ch.user_id = u.id
        WHERE ch.is_answered = 0
        ORDER BY ch.timestamp DESC
    ''')
    unanswered_list = cursor.fetchall()
    
    conn.close()
    return render_template('admin_dashboard.html', stats=stats, chat_history=chat_history, unanswered_list=unanswered_list, active_page='dashboard')

# Student Questionnaires & Inquiries (Admin)
@app.route('/admin/inquiries', methods=['GET', 'POST'])
@admin_required
def admin_inquiries():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        inquiry_id = request.form.get('inquiry_id')
        admin_response = request.form.get('admin_response')
        
        if inquiry_id and admin_response:
            try:
                cursor.execute('''
                    UPDATE student_inquiries
                    SET admin_response = ?, status = 'Answered', answered_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (admin_response, inquiry_id))
                conn.commit()
                flash("Response sent to student successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating inquiry: {e}", "error")
        return redirect(url_for('admin_inquiries'))
        
    active_filter = request.args.get('filter', 'all')
    
    if active_filter == 'pending':
        query = '''
            SELECT i.id, i.subject, i.category, i.message, i.admin_response, i.status, i.created_at, i.answered_at,
                   s.name as student_name, s.student_id, u.email
            FROM student_inquiries i
            JOIN users u ON i.user_id = u.id
            LEFT JOIN students s ON s.user_id = u.id
            WHERE i.status = 'Pending'
            ORDER BY i.created_at DESC
        '''
    elif active_filter == 'answered':
        query = '''
            SELECT i.id, i.subject, i.category, i.message, i.admin_response, i.status, i.created_at, i.answered_at,
                   s.name as student_name, s.student_id, u.email
            FROM student_inquiries i
            JOIN users u ON i.user_id = u.id
            LEFT JOIN students s ON s.user_id = u.id
            WHERE i.status = 'Answered'
            ORDER BY i.answered_at DESC
        '''
    else:
        query = '''
            SELECT i.id, i.subject, i.category, i.message, i.admin_response, i.status, i.created_at, i.answered_at,
                   s.name as student_name, s.student_id, u.email
            FROM student_inquiries i
            JOIN users u ON i.user_id = u.id
            LEFT JOIN students s ON s.user_id = u.id
            ORDER BY i.created_at DESC
        '''
        
    cursor.execute(query)
    inquiries = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM student_inquiries WHERE status = 'Pending'")
    pending_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM student_inquiries WHERE status = 'Answered'")
    answered_count = cursor.fetchone()[0]
    
    conn.close()
    return render_template('admin_inquiries.html', inquiries=inquiries, pending_count=pending_count, answered_count=answered_count, active_filter=active_filter, active_page='inquiries')

# A. Student Management (Admin)
@app.route('/admin/students', methods=['GET', 'POST'])
@admin_required
def manage_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        email = request.form.get('email')
        student_id = request.form.get('student_id')
        department_id = request.form.get('department_id') or None
        course_id = request.form.get('course_id') or None
        year = request.form.get('year')
        phone = request.form.get('phone')
        
        if action == 'add':
            username = request.form.get('username')
            password = request.form.get('password') or "student123"
            
            # Create user login first
            try:
                pw_hash = generate_password_hash(password)
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, role, status)
                    VALUES (?, ?, ?, 'student', 'active')
                ''', (username, email, pw_hash))
                user_id = cursor.lastrowid
                
                # Create student profile
                cursor.execute('''
                    INSERT INTO students (user_id, student_id, name, email, phone, department_id, course_id, year)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, student_id, name, email, phone, department_id, course_id, year))
                conn.commit()
                flash("Student added successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error adding student: {e}", "error")
                
        elif action == 'edit':
            student_db_id = request.form.get('student_db_id')
            try:
                # Update student table details
                cursor.execute('''
                    UPDATE students 
                    SET name = ?, email = ?, student_id = ?, phone = ?, department_id = ?, course_id = ?, year = ?
                    WHERE id = ?
                ''', (name, email, student_id, phone, department_id, course_id, year, student_db_id))
                
                # Fetch user_id to sync email change in user logins
                cursor.execute("SELECT user_id FROM students WHERE id = ?", (student_db_id,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("UPDATE users SET email = ? WHERE id = ?", (email, row['user_id']))
                    
                conn.commit()
                flash("Student profile updated successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating student: {e}", "error")
                
        return redirect(url_for('manage_students'))
        
    search_query = request.args.get('search')
    if search_query:
        cursor.execute('''
            SELECT s.id, s.student_id, s.name, s.email, s.phone, s.year, s.department_id, s.course_id, s.user_id,
                   d.name as dept_name, c.code as course_code, u.status
            FROM students s
            LEFT JOIN departments d ON s.department_id = d.id
            LEFT JOIN courses c ON s.course_id = c.id
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.name LIKE ? OR s.student_id LIKE ? OR s.email LIKE ?
            ORDER BY s.student_id
        ''', (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute('''
            SELECT s.id, s.student_id, s.name, s.email, s.phone, s.year, s.department_id, s.course_id, s.user_id,
                   d.name as dept_name, c.code as course_code, u.status
            FROM students s
            LEFT JOIN departments d ON s.department_id = d.id
            LEFT JOIN courses c ON s.course_id = c.id
            LEFT JOIN users u ON s.user_id = u.id
            ORDER BY s.student_id
        ''')
        
    students = cursor.fetchall()
    
    # Fetch lists for drop-downs
    cursor.execute("SELECT id, name FROM departments")
    departments = cursor.fetchall()
    cursor.execute("SELECT id, name FROM courses")
    courses = cursor.fetchall()
    
    conn.close()
    return render_template('students.html', students=students, departments=departments, courses=courses, search_query=search_query, active_page='students')

@app.route('/admin/students/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_student_status(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        new_status = 'inactive' if row['status'] == 'active' else 'active'
        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        flash(f"Student account is now {new_status}.", "success")
    conn.close()
    return redirect(url_for('manage_students'))

@app.route('/admin/students/delete/<int:student_id>', methods=['POST'])
@admin_required
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    if row:
        # Delete user logs (this cascades to student profile thanks to ON DELETE CASCADE)
        cursor.execute("DELETE FROM users WHERE id = ?", (row['user_id'],))
        conn.commit()
        flash("Student deleted successfully.", "success")
    conn.close()
    return redirect(url_for('manage_students'))

# B & D. Department Management (Admin)
@app.route('/admin/departments', methods=['GET', 'POST'])
@admin_required
def manage_departments():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        hod = request.form.get('hod')
        faculty_count = request.form.get('faculty_count')
        labs = request.form.get('labs')
        timetable = request.form.get('timetable')
        
        if action == 'add':
            try:
                cursor.execute('''
                    INSERT INTO departments (name, hod, faculty_count, labs, timetable)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, hod, faculty_count, labs, timetable))
                conn.commit()
                flash("Department added successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error adding department: {e}", "error")
        elif action == 'edit':
            dept_id = request.form.get('dept_id')
            try:
                cursor.execute('''
                    UPDATE departments 
                    SET name = ?, hod = ?, faculty_count = ?, labs = ?, timetable = ?
                    WHERE id = ?
                ''', (name, hod, faculty_count, labs, timetable, dept_id))
                conn.commit()
                flash("Department updated successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating department: {e}", "error")
                
        return redirect(url_for('manage_departments'))
        
    cursor.execute("SELECT id, name, hod, faculty_count, labs, timetable FROM departments ORDER BY name")
    departments = cursor.fetchall()
    conn.close()
    return render_template('departments.html', departments=departments, active_page='departments')

@app.route('/admin/departments/delete/<int:dept_id>', methods=['POST'])
@admin_required
def delete_department(dept_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM departments WHERE id = ?", (dept_id,))
        conn.commit()
        flash("Department deleted.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "error")
    conn.close()
    return redirect(url_for('manage_departments'))

# Faculty Management (Admin)
@app.route('/admin/faculty', methods=['GET', 'POST'])
@admin_required
def manage_faculty():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        faculty_id = request.form.get('faculty_id')
        name = request.form.get('name')
        designation = request.form.get('designation')
        department_id = request.form.get('department_id')
        email = request.form.get('email')
        phone = request.form.get('phone')
        qualification = request.form.get('qualification')
        specialization = request.form.get('specialization')
        office_location = request.form.get('office_location')
        
        if faculty_id:
            try:
                cursor.execute('''
                    UPDATE faculty
                    SET name = ?, designation = ?, department_id = ?, email = ?, phone = ?, qualification = ?, specialization = ?, office_location = ?
                    WHERE id = ?
                ''', (name, designation, department_id, email, phone, qualification, specialization, office_location, faculty_id))
                conn.commit()
                flash("Faculty profile updated successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating faculty profile: {e}", "error")
        else:
            try:
                cursor.execute('''
                    INSERT INTO faculty (name, designation, department_id, email, phone, qualification, specialization, office_location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, designation, department_id, email, phone, qualification, specialization, office_location))
                conn.commit()
                flash("New faculty member added successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error adding faculty member: {e}", "error")
                
        return redirect(url_for('manage_faculty'))
        
    cursor.execute('''
        SELECT f.id, f.name, f.designation, f.department_id, f.email, f.phone, f.qualification, f.specialization, f.office_location,
               d.name as dept_name
        FROM faculty f
        LEFT JOIN departments d ON f.department_id = d.id
        ORDER BY f.name ASC
    ''')
    faculty = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cursor.fetchall()
    
    conn.close()
    return render_template('admin_faculty.html', faculty=faculty, departments=departments, active_page='faculty')

@app.route('/admin/faculty/delete/<int:faculty_id>', methods=['POST'])
@admin_required
def delete_faculty(faculty_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM faculty WHERE id = ?", (faculty_id,))
        conn.commit()
        flash("Faculty record deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting faculty record: {e}", "error")
    conn.close()
    return redirect(url_for('manage_faculty'))

# C. Prospectus PDF & Document Management (Admin & RAG Pipeline)
@app.route('/admin/documents', methods=['GET', 'POST'])
@admin_required
def manage_documents():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part", "error")
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash("No selected file", "error")
            return redirect(request.url)
            
        if file and file.filename.endswith('.pdf'):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Save doc record to database
            try:
                cursor.execute("INSERT INTO documents (filename, filepath) VALUES (?, ?)", (filename, filepath))
                doc_id = cursor.lastrowid
                
                # Extract and process text
                pdf_text = extract_text_from_pdf(filepath)
                if pdf_text:
                    chunks = chunk_text(pdf_text)
                    print(f"Extracted {len(chunks)} chunks from {filename}. Generating embeddings...")
                    
                    # Generate embeddings and store
                    for chunk in chunks:
                        vector = get_embedding(chunk, is_query=False)
                        serialized_vector = serialize_vector(vector)
                        cursor.execute('''
                            INSERT INTO prospectus_chunks (document_id, chunk_text, embedding)
                            VALUES (?, ?, ?)
                        ''', (doc_id, chunk, serialized_vector))
                    
                    conn.commit()
                    flash(f"Successfully processed and indexed '{filename}' ({len(chunks)} chunks).", "success")
                else:
                    flash("Failed to extract text from PDF. Ensure it's not scanned or encrypted.", "error")
            except Exception as e:
                conn.rollback()
                flash(f"Database error while saving document: {e}", "error")
        else:
            flash("Invalid file type. Please upload a PDF.", "error")
            
        return redirect(url_for('manage_documents'))
        
    cursor.execute("SELECT id, filename, filepath, uploaded_at FROM documents ORDER BY uploaded_at DESC")
    documents = cursor.fetchall()
    conn.close()
    
    return render_template('documents.html', documents=documents, active_page='documents')

@app.route('/admin/documents/delete/<int:doc_id>', methods=['POST'])
@admin_required
def delete_document(doc_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Retrieve filepath to delete local file
        cursor.execute("SELECT filepath FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        if row:
            if os.path.exists(row['filepath']):
                os.remove(row['filepath'])
                
        # Delete document record (foreign keys delete prospectus_chunks automatically due to ON DELETE CASCADE)
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        flash("Document and associated vectors removed successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error removing document: {e}", "error")
    conn.close()
    return redirect(url_for('manage_documents'))

# E. Course Management (Admin)
@app.route('/admin/courses', methods=['GET', 'POST'])
@admin_required
def manage_courses():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        code = request.form.get('code')
        department_id = request.form.get('department_id')
        duration = request.form.get('duration')
        fees = request.form.get('fees')
        seats = request.form.get('seats')
        eligibility = request.form.get('eligibility')
        syllabus = request.form.get('syllabus')
        
        if action == 'add':
            try:
                cursor.execute('''
                    INSERT INTO courses (name, code, department_id, duration, eligibility, fees, syllabus, seats)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, code, department_id, duration, eligibility, fees, syllabus, seats))
                conn.commit()
                flash("Course added successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error adding course: {e}", "error")
        elif action == 'edit':
            course_id = request.form.get('course_id')
            try:
                cursor.execute('''
                    UPDATE courses 
                    SET name = ?, code = ?, department_id = ?, duration = ?, eligibility = ?, fees = ?, syllabus = ?, seats = ?
                    WHERE id = ?
                ''', (name, code, department_id, duration, eligibility, fees, syllabus, seats, course_id))
                conn.commit()
                flash("Course updated successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating course: {e}", "error")
                
        return redirect(url_for('manage_courses'))
        
    cursor.execute('''
        SELECT c.id, c.name, c.code, c.duration, c.eligibility, c.fees, c.syllabus, c.seats, c.department_id, d.name as dept_name
        FROM courses c 
        LEFT JOIN departments d ON c.department_id = d.id
        ORDER BY c.name
    ''')
    courses = cursor.fetchall()
    
    cursor.execute("SELECT id, name FROM departments")
    departments = cursor.fetchall()
    conn.close()
    return render_template('courses.html', courses=courses, departments=departments, active_page='courses')

@app.route('/admin/courses/delete/<int:course_id>', methods=['POST'])
@admin_required
def delete_course(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
        flash("Course deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "error")
    conn.close()
    return redirect(url_for('manage_courses'))

# Syllabus & Subject Management (Admin)
@app.route('/admin/syllabus', methods=['GET', 'POST'])
@admin_required
def manage_syllabus():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        name = request.form.get('name')
        code = request.form.get('code')
        department_id = request.form.get('department_id')
        course_id = request.form.get('course_id')
        semester = request.form.get('semester')
        credits = request.form.get('credits')
        syllabus_content = request.form.get('syllabus_content')
        
        if subject_id:
            try:
                cursor.execute('''
                    UPDATE subjects
                    SET name = ?, code = ?, department_id = ?, course_id = ?, semester = ?, credits = ?, syllabus_content = ?
                    WHERE id = ?
                ''', (name, code, department_id, course_id, semester, credits, syllabus_content, subject_id))
                conn.commit()
                flash("Subject & syllabus updated successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating subject: {e}", "error")
        else:
            try:
                cursor.execute('''
                    INSERT INTO subjects (name, code, department_id, course_id, semester, credits, syllabus_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, code, department_id, course_id, semester, credits, syllabus_content))
                conn.commit()
                flash("New subject added to syllabus successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error adding subject: {e}", "error")
                
        return redirect(url_for('manage_syllabus'))
        
    cursor.execute('''
        SELECT s.id, s.name, s.code, s.department_id, s.course_id, s.semester, s.credits, s.syllabus_content,
               d.name as dept_name, c.name as course_name, c.code as course_code
        FROM subjects s
        LEFT JOIN departments d ON s.department_id = d.id
        LEFT JOIN courses c ON s.course_id = c.id
        ORDER BY s.semester ASC, s.code ASC
    ''')
    subjects = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cursor.fetchall()
    
    cursor.execute("SELECT id, name, code FROM courses ORDER BY name")
    courses = cursor.fetchall()
    
    conn.close()
    return render_template('admin_syllabus.html', subjects=subjects, departments=departments, courses=courses, active_page='syllabus')

@app.route('/admin/syllabus/delete/<int:subject_id>', methods=['POST'])
@admin_required
def delete_subject(subject_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
        conn.commit()
        flash("Subject deleted from syllabus.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting subject: {e}", "error")
    conn.close()
    return redirect(url_for('manage_syllabus'))

# F. FAQ Management (Admin)
@app.route('/admin/faqs', methods=['GET', 'POST'])
@admin_required
def manage_faqs():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        question = request.form.get('question')
        answer = request.form.get('answer')
        category = request.form.get('category')
        
        if action == 'add':
            try:
                cursor.execute('''
                    INSERT INTO faqs (question, answer, category)
                    VALUES (?, ?, ?)
                ''', (question, answer, category))
                conn.commit()
                flash("FAQ added successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error adding FAQ: {e}", "error")
        elif action == 'edit':
            faq_id = request.form.get('faq_id')
            try:
                cursor.execute('''
                    UPDATE faqs 
                    SET question = ?, answer = ?, category = ?
                    WHERE id = ?
                ''', (question, answer, category, faq_id))
                conn.commit()
                flash("FAQ updated successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating FAQ: {e}", "error")
                
        return redirect(url_for('manage_faqs'))
        
    cursor.execute("SELECT id, question, answer, category FROM faqs ORDER BY category")
    faqs = cursor.fetchall()
    conn.close()
    return render_template('faqs.html', faqs=faqs, active_page='faqs')

@app.route('/admin/faqs/delete/<int:faq_id>', methods=['POST'])
@admin_required
def delete_faq(faq_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
        conn.commit()
        flash("FAQ deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "error")
    conn.close()
    return redirect(url_for('manage_faqs'))

# G. Announcement Management (Admin)
@app.route('/admin/announcements', methods=['GET', 'POST'])
@admin_required
def manage_announcements():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        
        if action == 'add':
            try:
                cursor.execute('''
                    INSERT INTO announcements (title, content, category)
                    VALUES (?, ?, ?)
                ''', (title, content, category))
                conn.commit()
                flash("Announcement published successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error publishing announcement: {e}", "error")
        elif action == 'edit':
            announce_id = request.form.get('announce_id')
            try:
                cursor.execute('''
                    UPDATE announcements 
                    SET title = ?, content = ?, category = ?
                    WHERE id = ?
                ''', (title, content, category, announce_id))
                conn.commit()
                flash("Announcement updated successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating announcement: {e}", "error")
                
        return redirect(url_for('manage_announcements'))
        
    cursor.execute("SELECT id, title, content, category, date_posted FROM announcements ORDER BY date_posted DESC")
    announcements = cursor.fetchall()
    conn.close()
    return render_template('announcements.html', announcements=announcements, active_page='announcements')

@app.route('/admin/announcements/delete/<int:announce_id>', methods=['POST'])
@admin_required
def delete_announcement(announce_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM announcements WHERE id = ?", (announce_id,))
        conn.commit()
        flash("Announcement removed successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "error")
    conn.close()
    return redirect(url_for('manage_announcements'))

# H. Placement Management (Admin)
@app.route('/admin/placements', methods=['GET', 'POST'])
@admin_required
def manage_placements():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        company_name = request.form.get('company_name')
        job_role = request.form.get('job_role')
        eligibility = request.form.get('eligibility')
        salary = request.form.get('salary')
        recruitment_date = request.form.get('recruitment_date')
        skills_required = request.form.get('skills_required')
        internship_info = request.form.get('internship_info')
        
        if action == 'add':
            try:
                cursor.execute('''
                    INSERT INTO placements (company_name, job_role, eligibility, salary, recruitment_date, skills_required, internship_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (company_name, job_role, eligibility, salary, recruitment_date, skills_required, internship_info))
                conn.commit()
                flash("Placement drive scheduled successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error scheduling placement: {e}", "error")
        elif action == 'edit':
            placement_id = request.form.get('placement_id')
            try:
                cursor.execute('''
                    UPDATE placements 
                    SET company_name = ?, job_role = ?, eligibility = ?, salary = ?, recruitment_date = ?, skills_required = ?, internship_info = ?
                    WHERE id = ?
                ''', (company_name, job_role, eligibility, salary, recruitment_date, skills_required, internship_info, placement_id))
                conn.commit()
                flash("Placement drive updated successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error updating placement: {e}", "error")
                
        return redirect(url_for('manage_placements'))
        
    cursor.execute("SELECT id, company_name, job_role, eligibility, salary, recruitment_date, skills_required, internship_info FROM placements ORDER BY company_name")
    placements = cursor.fetchall()
    conn.close()
    return render_template('placements.html', placements=placements, active_page='placements')

@app.route('/admin/placements/delete/<int:placement_id>', methods=['POST'])
@admin_required
def delete_placement(placement_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM placements WHERE id = ?", (placement_id,))
        conn.commit()
        flash("Placement drive removed successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "error")
    conn.close()
    return redirect(url_for('manage_placements'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
