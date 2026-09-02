import os
import sys

# Ensure current folder is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db, seed_db, get_db_connection

try:
    print("1. Initializing SQLite tables...")
    init_db()
    
    print("2. Seeding default admin, student, and academic details...")
    seed_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n================ COLLEGE DATABASE STATUS ================")
    cursor.execute("SELECT COUNT(*) FROM users")
    print(f"Total Registered Users : {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM students")
    print(f"Total Student Profiles : {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM departments")
    print(f"Total Departments      : {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM courses")
    print(f"Total Courses Offered  : {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM faqs")
    print(f"Total FAQs configured  : {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM announcements")
    print(f"Total Announcements    : {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM placements")
    print(f"Total Active Placements: {cursor.fetchone()[0]}")
    print("=========================================================\n")
    
    print("Listing Registered Admin Accounts:")
    cursor.execute("SELECT username, email, role, status FROM users WHERE role='admin'")
    for row in cursor.fetchall():
        print(f"  - Username: '{row['username']}' | Email: '{row['email']}' | Role: '{row['role']}' | Status: '{row['status']}'")
        
    print("\nListing Registered Student Accounts:")
    cursor.execute("SELECT username, email, role, status FROM users WHERE role='student'")
    for row in cursor.fetchall():
        print(f"  - Username: '{row['username']}' | Email: '{row['email']}' | Role: '{row['role']}' | Status: '{row['status']}'")
        
    conn.close()
    print("\nDatabase verification completed successfully!")
except Exception as e:
    print(f"\nVerification failed with error: {e}")
    sys.exit(1)
