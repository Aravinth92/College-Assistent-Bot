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

FALLBACK_MESSAGE = "Sorry, I could not find this information in the available college documents. Please contact the college office."

def local_database_match(question):
    """
    Directly queries the SQLite database for FAQs, HODs, Courses, Placements, 
    Timings, and Admission details to guarantee fast, accurate responses without external API requirements.
    """
    q_lower = question.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Search FAQ table
    cursor.execute("SELECT question, answer FROM faqs")
    faqs = cursor.fetchall()
    
    # Exact or substring match with FAQ questions
    for faq in faqs:
        faq_q = faq['question'].lower()
        clean_faq_q = faq_q.replace('"', '').replace("'", "")
        clean_user_q = q_lower.replace('"', '').replace("'", "")
        
        if clean_faq_q in clean_user_q or clean_user_q in clean_faq_q:
            conn.close()
            return faq['answer']

    # Keyphrase matching for FAQs
    if "hostel" in q_lower and ("fee" in q_lower or "cost" in q_lower or "rent" in q_lower or "charge" in q_lower):
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

    if "bus" in q_lower or "transport" in q_lower or "route" in q_lower:
        for faq in faqs:
            if "bus" in faq['question'].lower() or "transport" in faq['question'].lower():
                conn.close()
                return faq['answer']

    if "admission" in q_lower or "document" in q_lower or "apply" in q_lower or "eligibility" in q_lower:
        for faq in faqs:
            if "admission" in faq['question'].lower() or "document" in faq['question'].lower():
                conn.close()
                return faq['answer']

    if "exam" in q_lower or "semester" in q_lower:
        for faq in faqs:
            if "exam" in faq['question'].lower() or "semester" in faq['question'].lower():
                conn.close()
                return faq['answer']

    # 2. HOD and Department Search
    if "hod" in q_lower or "head" in q_lower or "chair" in q_lower or "department" in q_lower:
        cursor.execute("SELECT name, hod, faculty_count, labs FROM departments")
        depts = cursor.fetchall()
        for d in depts:
            dept_name = d['name'].lower()
            if ("computer" in q_lower or "cs" in q_lower or "cse" in q_lower) and "computer" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is {d['hod']}."
            elif ("electronics" in q_lower or "ece" in q_lower) and "electronics" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is {d['hod']}."
            elif ("mechanical" in q_lower or "mech" in q_lower) and "mechanical" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is {d['hod']}."
            elif ("information" in q_lower or "it" in q_lower) and "information" in dept_name:
                conn.close()
                return f"The Head of Department (HOD) for {d['name']} is {d['hod']}."
                
        if "hod" in q_lower or "head" in q_lower:
            if depts:
                hod_list = "\n".join([f"• {d['name']}: {d['hod']}" for d in depts])
                conn.close()
                return f"Department Heads (HODs):\n{hod_list}"

    # 3. Available Courses Search
    if "course" in q_lower or "courses" in q_lower or "branch" in q_lower or "branches" in q_lower or "program" in q_lower:
        cursor.execute("SELECT name, code, duration, fees, eligibility FROM courses")
        courses = cursor.fetchall()
        if courses:
            c_list = "\n".join([f"• {c['name']} ({c['code']}) - {c['duration']} (Fee: Rs. {c['fees']}/yr)" for c in courses])
            conn.close()
            return f"The following courses are available:\n{c_list}"

    # 4. Placement Companies Search
    if "placement" in q_lower or "company" in q_lower or "companies" in q_lower or "recruiter" in q_lower or "package" in q_lower or "salary" in q_lower:
        cursor.execute("SELECT company_name, job_role, salary, recruitment_date FROM placements")
        placements = cursor.fetchall()
        if placements:
            p_list = "\n".join([f"• {p['company_name']} - Role: {p['job_role']}, Package: {p['salary']} (Drive Date: {p['recruitment_date']})" for p in placements])
            conn.close()
            return f"Top companies visiting for campus placements include:\n{p_list}"

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
                "temperature": 0.1
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
    Gathers structured information from the database (departments, courses, faculty, placements, and FAQs)
    to build a robust context for AI generation.
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

    # 3. Placements
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

    # 4. FAQs
    try:
        cursor.execute("SELECT question, answer FROM faqs")
        faqs = cursor.fetchall()
        if faqs:
            context_lines.append("=== Frequently Asked Questions (FAQs) ===")
            for faq in faqs:
                context_lines.append(f"Q: {faq['question']}\nA: {faq['answer']}\n")
    except Exception as e:
        print(f"Error fetching FAQs: {e}")
        
    conn.close()
    return "\n".join(context_lines)

def query_chatbot(question, user_id=None):
    """
    Answers the student's question by checking local database rules first,
    then Groq API, and finally Gemini API.
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
        "You are the official College Assistant Bot. Your goal is to help students with questions about the college, "
        "including courses, admissions, eligibility, HODs, timings, fees, placements, library, hostel, and general guidelines.\n\n"
        "CRITICAL RULES:\n"
        "1. You must answer the user's question ONLY using the provided college knowledge context below.\n"
        "2. Do not make up, hallucinate, or assume any information not present in the context.\n"
        "3. If the question cannot be answered completely and accurately using the context, you MUST output exactly and only the following fallback message:\n"
        f"\"{FALLBACK_MESSAGE}\"\n"
        "4. Be professional, concise, polite, and helpful when answering."
    )

    prompt = f"College Context:\n{full_context}\n\nUser Question: {question}\n\nAnswer:"

    # 2. Try Groq API Inference (Ultra-fast)
    groq_answer = query_groq(prompt, system_instruction)
    if groq_answer:
        is_fallback = FALLBACK_MESSAGE.lower() in groq_answer.lower() or "could not find this information" in groq_answer.lower()
        is_answered = 0 if is_fallback else 1
        if is_fallback:
            groq_answer = FALLBACK_MESSAGE
            
        log_chat_history(user_id, question, groq_answer, is_answered)
        return groq_answer, is_answered

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
                    generation_config={"temperature": 0.1}
                )
                answer = response.text.strip()
                
                is_fallback = FALLBACK_MESSAGE.lower() in answer.lower() or "could not find this information" in answer.lower()
                is_answered = 0 if is_fallback else 1
                if is_fallback:
                    answer = FALLBACK_MESSAGE
                    
                log_chat_history(user_id, question, answer, is_answered)
                return answer, is_answered
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
