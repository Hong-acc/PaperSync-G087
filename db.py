import json
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def read_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def write_json(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# Seed Initialization Helper
def init_db():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    # Initialize files if they don't exist
    for file in ['users.json', 'subjects.json', 'solutions.json', 'comments.json']:
        filepath = os.path.join(DATA_DIR, file)
        if not os.path.exists(filepath):
            write_json(file, [])
            
    # Add dummy users if empty
    users = read_json('users.json')
    if not users:
        users = [
            {
                "user_id": "1",
                "username": "admin",
                "user_email": "admin@mmu.edu.my",
                "password_hash": generate_password_hash("admin123"),
                "role": "admin"
            },
            {
                "user_id": "2",
                "username": "student",
                "user_email": "student@student.mmu.edu.my",
                "password_hash": generate_password_hash("student123"),
                "role": "student"
            }
        ]
        write_json('users.json', users)

    # Add dummy subjects and papers if empty
    subjects = read_json('subjects.json')
    if not subjects:
        subjects = [
            {
                "subject_id": "1",
                "name": "Mathematic I",
                "subject_code": "CMT1114",
                "papers": [
                    {
                        "paper_id": "p1",
                        "year": "2023",
                        "trimester": "Tri 1"
                    },
                    {
                        "paper_id": "p2",
                        "year": "2023",
                        "trimester": "Tri 2"
                    }
                ]
            },
            {
                "subject_id": "2",
                "name": "Problem Solving and Program Design",
                "subject_code": "CSP1114",
                "papers": [
                    {
                        "paper_id": "p3",
                        "year": "2023",
                        "trimester": "Tri 2"
                    }
                ]
            }
        ]
        write_json('subjects.json', subjects)
        
    solutions = read_json('solutions.json')
    if not solutions:
        solutions = [
            {
                "solution_id": "s1",
                "paper_id": "p1",
                "uploader_id": "2",
                "uploader_username": "student",
                "filepath": "dummy.pdf", 
                "upvotes": 5,
                "flags": 0,
                "upvoted_by": [],
                "flagged_by": []
            }
        ]
        write_json('solutions.json', solutions)
        
    comments = read_json('comments.json')
    if not comments:
        comments = [
            {
                "comment_id": "c1",
                "target_type": "paper",
                "target_id": "p1",
                "user_id": "2",
                "username": "student",
                "text": "Does anyone know how to solve Question 3b?"
            }
        ]
        write_json('comments.json', comments)

# CRUD Helper
# USER & AUTHENTICATION
# ------------------------------------------

def get_user_by_username(username):
    """Retrieve a user by their username."""
    users = read_json('users.json')
    for user in users:
        if user.get('username') == username:
            return user
    return None

def get_user_by_email(email):
    """Retrieve a user by their email."""
    users = read_json('users.json')
    for user in users:
        if user.get('user_email') == email:
            return user
    return None

def get_user_by_id(user_id):
    """Retrieve a user by their ID."""
    users = read_json('users.json')
    for user in users:
        if user.get('user_id') == str(user_id):
            return user
    return None

def add_user(username, email, password, role="student"):
    """Register a new user."""
    users = read_json('users.json')
    # Check if username or email already exists
    for u in users:
        if u.get('username') == username or u.get('user_email') == email:
            return None
    new_user = {
        "user_id": str(uuid.uuid4()),
        "username": username,
        "user_email": email,
        "password_hash": generate_password_hash(password),
        "role": role
    }
    users.append(new_user)
    write_json('users.json', users)
    return new_user

def add_admin(username, email, password):
    """Register a new admin."""
    return add_user(username, email, password, role="admin")

# SUBJECTS & PAPERS
# ------------------------------------------

def get_all_subjects():
    """Retrieve all subjects."""
    return read_json('subjects.json')

def get_subject_by_id(subject_id):
    """Retrieve a specific subject by its ID."""
    subjects = read_json('subjects.json')
    for subject in subjects:
        if subject.get('subject_id') == subject_id:
            return subject
    return None

def get_paper(subject_id, paper_id):
    """Retrieve details for a specific paper within a subject."""
    subject = get_subject_by_id(subject_id)
    if subject:
        for paper in subject.get('papers', []):
            if paper.get('paper_id', paper.get('id')) == paper_id:
                return paper
    return None

# SOLUTIONS & FILE UPLOADS
# ------------------------------------------

def add_solution(paper_id, uploader_id, uploader_username, filepath):
    """Add a new solution entry to solutions.json."""
    solutions = read_json('solutions.json')
    new_solution = {
        "solution_id": str(uuid.uuid4()),
        "paper_id": paper_id,
        "uploader_id": uploader_id,
        "uploader_username": uploader_username,
        "filepath": filepath,
        "upvotes": 0,
        "flags": 0,
        "upvoted_by": [],
        "flagged_by": []
    }
    solutions.append(new_solution)
    write_json('solutions.json', solutions)
    return new_solution

def get_solutions_by_paper_id(paper_id):
    """Retrieve all solutions for a specific paper."""
    solutions = read_json('solutions.json')
    return [s for s in solutions if s['paper_id'] == paper_id]

def get_solution_by_id(solution_id):
    """Retrieve a specific solution by its ID."""
    solutions = read_json('solutions.json')
    for s in solutions:
        if s.get('solution_id') == solution_id:
            return s
    return None

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
