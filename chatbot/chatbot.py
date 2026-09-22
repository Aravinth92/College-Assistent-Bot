import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from database.db import get_db_connection
from chatbot.embeddings import search_prospectus

load_dotenv()

# Configure Gemini if available
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    genai.configure(api_key=gemini_key)

FALLBACK_MESSAGE = "Sorry, I could not find this specific detail in the college records. Please submit an inquiry via your dashboard or visit the college office counter."

def local_database_match(question):
    """
    Queries SQLite database for FAQs, HODs, Courses, Faculty, Placements, 
    Timings, Syllabus, and Admission details for fast, accurate answers.
    """
    q_lower = question.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Syllabus & Subject Search (Check BEFORE bus route checks)
    if "syllabus" in q_lower or "unit" in q_lower or "module" in q_lower or "credit" in q_lower or "subject" in q_lower:
        cursor.execute("SELECT name, code, credits, syllabus_content FROM subjects")
        subjs = cursor.fetchall()
        for s in subjs:
            sub_name = s['name'].lower()
            sub_code = s['code'].lower()
            if sub_code in q_lower or any(part in q_lower for part in sub_name.split() if len(part) > 3 and part not in {'and', 'in', 'for', 'the', 'what', 'is', 'with', 'about'}):
                conn.close()
                return f"**Syllabus Outline for {s['name']} (`{s['code']}`) — {s['credits']} Credits**:\n\n{s['syllabus_content']}"

    # 2. Search FAQ table with word overlap matching
    cursor.execute("SELECT question, answer FROM faqs")
    faqs = cursor.fetchall()
    
    clean_user_q = q_lower.replace('"', '').replace("'", "").replace('?', '')
    user_words = set(clean_user_q.split())
    
    best_faq_match = None
    best_overlap = 0

    for faq in faqs:
        faq_q = faq['question'].lower()
        clean_faq_q = faq_q.replace('"', '').replace("'", "").replace('?', '')
        
        # Substring match
        if clean_faq_q in clean_user_q or clean_user_q in clean_faq_q:
            conn.close()
            return faq['answer']
            
        faq_words = set(clean_faq_q.split())
        common_words = user_words.intersection(faq_words)
        significant_words = {w for w in common_words if len(w) > 3 and w not in {'what', 'when', 'where', 'which', 'who', 'how', 'does', 'that', 'this', 'tell', 'show'}}
        if len(significant_words) >= 2 and len(significant_words) > best_overlap:
            best_overlap = len(significant_words)
            best_faq_match = faq['answer']

    if best_faq_match and best_overlap >= 2:
        conn.close()
        return best_faq_match

    # Keyphrase matching for FAQs
    if "hostel" in q_lower and ("fee" in q_lower or "cost" in q_lower or "rent" in q_lower or "charge" in q_lower or "room" in q_lower):
        for faq in faqs:
            if "hostel" in faq['question'].lower():
                conn.close()
                return faq['answer']
                
    if "timing" in q_lower or "timings" in q_lower or "open" in q_lower or "hours" in q_lower:
        if "library" in q_lower:
            for faq in faqs:
                if "library" in faq['question'].lower():
                    conn.close()
                    return faq['answer']
        else:
            for faq in faqs:
                if "timing" in faq['question'].lower() or "timings" in faq['question'].lower():
                    conn.close()
                    return faq['answer']

    if "bonafide" in q_lower or "certificate" in q_lower:
        for faq in faqs:
            if "bonafide" in faq['question'].lower():
                conn.close()
                return faq['answer']

    if (" bus " in f" {q_lower} " or "buses" in q_lower or "transport" in q_lower or "bus route" in q_lower) and "syllabus" not in q_lower:
        for faq in faqs:
            if "bus" in faq['question'].lower() or "transport" in faq['question'].lower():
                conn.close()
                return faq['answer']

    if "admission" in q_lower or "document" in q_lower or "apply" in q_lower or "eligibility" in q_lower:
        for faq in faqs:
            if "admission" in faq['question'].lower() or "document" in faq['question'].lower():
                conn.close()
                return faq['answer']

    if ("exam" in q_lower or "semester" in q_lower) and "syllabus" not in q_lower:
        for faq in faqs:
            if "exam" in faq['question'].lower() or "semester" in faq['question'].lower():
                conn.close()
                return faq['answer']

    # 3. HOD and Department Search
    if "hod" in q_lower or "head" in q_lower or "chair" in q_lower or "department" in q_lower:
        cursor.execute("SELECT name, hod, faculty_count, labs FROM departments")
        depts = cursor.fetchall()
        for d in depts:
            dept_name = d['name'].lower()
            if ("computer" in q_lower or "cs" in q_lower or "cse" in q_lower) and "computer" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is **{d['hod']}**."
            elif ("electronics" in q_lower or "ece" in q_lower) and "electronics" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is **{d['hod']}**."
            elif ("mechanical" in q_lower or "mech" in q_lower) and "mechanical" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is **{d['hod']}**."
            elif ("information" in q_lower or "it" in q_lower) and "information" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is **{d['hod']}**."
            elif ("civil" in q_lower) and "civil" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is **{d['hod']}**."
            elif ("electrical" in q_lower or "eee" in q_lower) and "electrical" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is **{d['hod']}**."
            elif ("ai" in q_lower or "data science" in q_lower or "aids" in q_lower) and "artificial" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is **{d['hod']}**."
            elif ("mba" in q_lower or "business" in q_lower) and "business" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is **{d['hod']}**."
                
        if "hod" in q_lower or "head" in q_lower:
            if depts:
                hod_list = "\n".join([f"• **{d['name']}**: {d['hod']}" for d in depts])
                conn.close()
                return f"Department Heads (HODs):\n{hod_list}"

    # 4. Faculty Member Search
    if "faculty" in q_lower or "professor" in q_lower or "teacher" in q_lower or "dr." in q_lower:
        cursor.execute("SELECT f.name, f.designation, f.email, f.qualification, f.specialization, d.name as dept_name FROM faculty f LEFT JOIN departments d ON f.department_id = d.id")
        facs = cursor.fetchall()
        for f in facs:
            fac_name = f['name'].lower()
            if any(part in q_lower for part in fac_name.split() if len(part) > 3):
                conn.close()
                return f"**{f['name']}** ({f['designation']})\nDepartment: {f['dept_name']}\nQualification: {f['qualification']}\nSpecialization: {f['specialization']}\nEmail: {f['email']}"

    # 5. Available Courses Search
    if "course" in q_lower or "courses" in q_lower or "branch" in q_lower or "branches" in q_lower or "program" in q_lower:
        cursor.execute("SELECT name, code, duration, fees, seats FROM courses")
        courses = cursor.fetchall()
        if courses:
            c_list = "\n".join([f"• **{c['name']}** (`{c['code']}`) - {c['duration']} (Annual Fee: Rs. {c['fees']:,.0f})" for c in courses])
            conn.close()
            return f"The following academic courses are offered:\n{c_list}"

    # 6. Placement Companies Search
    if "placement" in q_lower or "company" in q_lower or "companies" in q_lower or "recruiter" in q_lower or "package" in q_lower or "salary" in q_lower:
        cursor.execute("SELECT company_name, job_role, salary, recruitment_date FROM placements")
        placements = cursor.fetchall()
        if placements:
            p_list = "\n".join([f"• **{p['company_name']}** - Role: {p['job_role']}, Package: **{p['salary']}** (Drive: {p['recruitment_date']})" for p in placements])
            conn.close()
            return f"Top campus recruiting companies include:\n{p_list}"

    conn.close()
    return None

def query_groq(prompt, system_instruction):
    """
    Sends request to Groq API using high-speed models.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return None
        
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    
    models = [
        "openai/gpt-oss-120b",
        "groq/compound",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b"
    ]
    
    for model in models:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                content = data['choices'][0]['message']['content'].strip()
                if content:
                    return content
        except Exception as e:
            print(f"Error querying Groq model {model}: {e}")
            continue
            
    return None

def get_college_database_context():
    """
    Gathers comprehensive structured information from the database (departments, courses, faculty, syllabus, placements, announcements, and FAQs)
    to build context for AI responses.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    context_lines = []
    
    # 1. Departments & HODs
    try:
        cursor.execute("SELECT name, hod, faculty_count, labs, timetable FROM departments")
        depts = cursor.fetchall()
        if depts:
            context_lines.append("=== Departments & Faculty ===")
            for dept in depts:
                context_lines.append(
                    f"Department: {dept['name']}\n"
                    f"- HOD: {dept['hod']}\n"
                    f"- Faculty Count: {dept['faculty_count']}\n"
                    f"- Laboratories: {dept['labs']}\n"
                    f"- Operating Hours/Timetable Info: {dept['timetable']}\n"
                )
    except Exception as e:
        print(f"Error fetching departments: {e}")

    # 2. Courses
    try:
        cursor.execute("SELECT c.name as course_name, c.code, d.name as dept_name, c.duration, c.eligibility, c.fees, c.syllabus, c.seats FROM courses c LEFT JOIN departments d ON c.department_id = d.id")
        courses = cursor.fetchall()
        if courses:
            context_lines.append("=== Available Courses ===")
            for c in courses:
                context_lines.append(
                    f"Course Name: {c['course_name']} ({c['code']})\n"
                    f"- Department: {c['dept_name']}\n"
                    f"- Duration: {c['duration']}\n"
                    f"- Eligibility Criteria: {c['eligibility']}\n"
                    f"- Annual Fee: Rs. {c['fees']}\n"
                    f"- Seats: {c['seats']}\n"
                    f"- Syllabus Summary: {c['syllabus']}\n"
                )
    except Exception as e:
        print(f"Error fetching courses: {e}")

    # 3. Faculty Roster
    try:
        cursor.execute("SELECT f.name, f.designation, f.email, f.phone, f.qualification, f.specialization, f.office_location, d.name as dept_name FROM faculty f LEFT JOIN departments d ON f.department_id = d.id")
        facs = cursor.fetchall()
        if facs:
            context_lines.append("=== Faculty & Staff Roster ===")
            for f in facs:
                context_lines.append(
                    f"Name: {f['name']} ({f['designation']})\n"
                    f"- Department: {f['dept_name']}\n"
                    f"- Email: {f['email']} | Phone: {f['phone']}\n"
                    f"- Qualification: {f['qualification']}\n"
                    f"- Specialization: {f['specialization']}\n"
                    f"- Office: {f['office_location']}\n"
                )
    except Exception as e:
        print(f"Error fetching faculty: {e}")

    # 4. Syllabus & Subjects
    try:
        cursor.execute("SELECT s.name, s.code, s.semester, s.credits, s.syllabus_content, c.code as course_code FROM subjects s LEFT JOIN courses c ON s.course_id = c.id")
        subjs = cursor.fetchall()
        if subjs:
            context_lines.append("=== Syllabus & Subjects ===")
            for s in subjs:
                context_lines.append(
                    f"Subject: {s['name']} ({s['code']}) - {s['credits']} Credits (Sem {s['semester']}, {s['course_code']})\n"
                    f"- Syllabus Breakdown: {s['syllabus_content']}\n"
                )
    except Exception as e:
        print(f"Error fetching subjects: {e}")

    # 5. Placements
    try:
        cursor.execute("SELECT company_name, job_role, eligibility, salary, recruitment_date, skills_required, internship_info FROM placements")
        placements = cursor.fetchall()
        if placements:
            context_lines.append("=== Placement Information ===")
            for p in placements:
                context_lines.append(
                    f"Recruiter: {p['company_name']}\n"
                    f"- Job Role Offered: {p['job_role']}\n"
                    f"- Eligibility: {p['eligibility']}\n"
                    f"- Package: {p['salary']}\n"
                    f"- Drive Date: {p['recruitment_date']}\n"
                    f"- Required Skills: {p['skills_required']}\n"
                    f"- Internship Details: {p['internship_info']}\n"
                )
    except Exception as e:
        print(f"Error fetching placements: {e}")

    # 6. Announcements & Notices
    try:
        cursor.execute("SELECT title, content, category, date_posted FROM announcements ORDER BY date_posted DESC")
        notes = cursor.fetchall()
        if notes:
            context_lines.append("=== College Notices & Announcements ===")
            for n in notes:
                context_lines.append(f"Notice: {n['title']} ({n['category']})\n- {n['content']}\n")
    except Exception as e:
        print(f"Error fetching announcements: {e}")

    # 7. FAQs
    try:
        cursor.execute("SELECT question, answer, category FROM faqs")
        faqs = cursor.fetchall()
        if faqs:
            context_lines.append("=== Frequently Asked Questions (FAQs) ===")
            for faq in faqs:
                context_lines.append(f"Q ({faq['category']}): {faq['question']}\nA: {faq['answer']}\n")
    except Exception as e:
        print(f"Error fetching FAQs: {e}")
        
    conn.close()
    return "\n".join(context_lines)

def query_chatbot(question, user_id=None):
    """
    Answers any student question by checking local database rules first,
    then Groq AI API, and finally Gemini API.
    """
    # 1. Try local database matching first
    local_answer = local_database_match(question)
    if local_answer:
        log_chat_history(user_id, question, local_answer, 1)
        return local_answer, 1

    # Build context for AI inference
    db_context = get_college_database_context()
    matching_chunks = search_prospectus(question, top_k=5)
    pdf_context = ""
    if matching_chunks:
        pdf_context = "\n=== Extracted Prospectus Context (Similarity Ranked) ===\n" + \
                      "\n---\n".join([f"[Relevance Score: {sim:.2f}] {text}" for text, sim in matching_chunks])

    full_context = f"{db_context}\n{pdf_context}"

    system_instruction = (
        "You are the official College Assistant Bot. You have full permission to help students with ANY questions "
        "regarding courses, admissions, eligibility, HODs, faculty members, syllabus & subjects, timetables, fees, "
        "placements, library, hostel, scholarships, sports facilities, administrative procedures, and general student guidance.\n\n"
        "GUIDELINES:\n"
        "1. Use the provided College Context and Prospectus Documents below as your primary reference for factual details.\n"
        "2. For general student inquiries (e.g., study tips, exam advice, career guidance, greetings), provide a polite, "
        "encouraging, well-structured, and helpful academic response.\n"
        "3. Format answers clearly using markdown lists, bold titles, and bullet points where helpful.\n"
        "4. Always maintain a helpful, welcoming, and professional college assistant tone."
    )

    prompt = f"College Context:\n{full_context}\n\nUser Question: {question}\n\nAnswer:"

    # 2. Try Groq API Inference (Ultra-fast)
    groq_answer = query_groq(prompt, system_instruction)
    if groq_answer:
        log_chat_history(user_id, question, groq_answer, 1)
        return groq_answer, 1

    # 3. Fallback to Gemini API if Groq fails or key is missing
    global gemini_key
    if not gemini_key:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            
    if gemini_key:
        for model_name in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro"]:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )
                response = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.2}
                )
                answer = response.text.strip()
                if answer:
                    log_chat_history(user_id, question, answer, 1)
                    return answer, 1
            except Exception as e:
                print(f"Error querying Gemini with model {model_name}: {e}")
                continue

    # Fallback if no LLM was able to resolve
    log_chat_history(user_id, question, FALLBACK_MESSAGE, 0)
    return FALLBACK_MESSAGE, 0

def log_chat_history(user_id, question, answer, is_answered):
    """
    Logs the question and answer to the chatbot_history table in SQLite.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO chatbot_history (user_id, question, answer, is_answered)
            VALUES (?, ?, ?, ?)
        ''', (user_id, question, answer, is_answered))
        conn.commit()
    except Exception as e:
        print(f"Error writing to chat history: {e}")
    finally:
        conn.close()
