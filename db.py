import json
import os
import uuid
from werkzeug.security import generate_password_hash

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

# ==========================================
# FULL CRUD HELPER FUNCTIONS (API for app.py)
# ==========================================

# ------------------------------------------
# USER MANAGEMENT & AUTHENTICATION
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

def get_all_users():
    """Retrieve all users."""
    return read_json('users.json')

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

# ------------------------------------------
# SUBJECTS & PAPERS MANAGEMENT
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

def add_subject(name, subject_code):
    """Add a new subject."""
    subjects = read_json('subjects.json')
    new_subject = {
        "subject_id": str(uuid.uuid4()),
        "name": name,
        "subject_code": subject_code,
        "papers": []
    }
    subjects.append(new_subject)
    write_json('subjects.json', subjects)
    return new_subject

def add_paper_to_subject(subject_id, year, trimester):
    """Add a new past year paper to an existing subject."""
    subjects = read_json('subjects.json')
    for subject in subjects:
        if subject.get('subject_id') == subject_id:
            new_paper = {
                "paper_id": str(uuid.uuid4()),
                "year": year,
                "trimester": trimester
            }
            subject['papers'] = subject.get('papers', [])
            subject['papers'].append(new_paper)
            write_json('subjects.json', subjects)
            return new_paper
    return None

# ------------------------------------------
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

# ------------------------------------------
# INTERACTIVE FEATURES (VOTING & COMMENTS)
# ------------------------------------------

def update_solution_upvotes(solution_id, user_id):
    """Toggle the upvotes for a solution by a user."""
    solutions = read_json('solutions.json')
    for s in solutions:
        if s.get('solution_id') == solution_id:
            upvoted_by = s.get('upvoted_by', [])
            if user_id in upvoted_by:
                # Remove upvote
                upvoted_by.remove(user_id)
                s['upvotes'] = max(0, s.get('upvotes', 1) - 1)
            else:
                # Add upvote
                upvoted_by.append(user_id)
                s['upvotes'] = s.get('upvotes', 0) + 1
            s['upvoted_by'] = upvoted_by
            write_json('solutions.json', solutions)
            return s
    return None

def update_solution_flags(solution_id, user_id):
    """Toggle the flags for a solution by a user."""
    solutions = read_json('solutions.json')
    for s in solutions:
        if s.get('solution_id') == solution_id:
            flagged_by = s.get('flagged_by', [])
            if user_id in flagged_by:
                # Remove flag
                flagged_by.remove(user_id)
                s['flags'] = max(0, s.get('flags', 1) - 1)
            else:
                # Add flag
                flagged_by.append(user_id)
                s['flags'] = s.get('flags', 0) + 1
            s['flagged_by'] = flagged_by
            write_json('solutions.json', solutions)
            return s
    return None

def add_comment(target_type, target_id, user_id, username, text):
    """Add a new comment to comments.json."""
    comments = read_json('comments.json')
    new_comment = {
        "comment_id": str(uuid.uuid4()),
        "target_type": target_type,  # 'paper' or 'solution'
        "target_id": target_id,
        "user_id": user_id,
        "username": username,
        "text": text
    }
    comments.append(new_comment)
    write_json('comments.json', comments)
    return new_comment

def get_comments_by_target(target_type, target_id):
    """Retrieve all comments for a specific target (paper or solution)."""
    comments = read_json('comments.json')
    return [c for c in comments if c['target_type'] == target_type and c['target_id'] == target_id]

# ------------------------------------------
# ADMINISTRATIVE OPERATIONS
# ------------------------------------------

def update_user_status(user_id, status):
    """Update a user's status (e.g., 'active' or 'banned')."""
    users = read_json('users.json')
    for u in users:
        if u.get('user_id') == str(user_id):
            u['status'] = status
            write_json('users.json', users)
            return True
    return False

def delete_solution(solution_id, user_id=None, role=None):
    """Delete a solution by its ID. Users can delete their own solutions; admins can delete any."""
    solutions = read_json('solutions.json')
    initial_len = len(solutions)
    
    if user_id and role != 'admin':
        # Verify ownership
        solution = next((s for s in solutions if s.get('solution_id') == solution_id), None)
        if not solution or solution.get('uploader_id') != str(user_id):
            return False
            
    solutions = [s for s in solutions if s.get('solution_id') != solution_id]
    if len(solutions) < initial_len:
        write_json('solutions.json', solutions)
        return True
    return False

def delete_comment(comment_id, user_id=None, role=None):
    """Delete a comment by its ID. Users can delete their own comments; admins can delete any."""
    comments = read_json('comments.json')
    initial_len = len(comments)
    
    if user_id and role != 'admin':
        # Verify ownership
        comment = next((c for c in comments if c.get('comment_id') == comment_id), None)
        if not comment or comment.get('user_id') != str(user_id):
            return False
            
    comments = [c for c in comments if c.get('comment_id') != comment_id]
    if len(comments) < initial_len:
        write_json('comments.json', comments)
        return True
    return False

def delete_paper(subject_id, paper_id):
    """Delete a paper from a subject and cleanly remove associated solutions and comments. Returns list of deleted filepaths."""
    subjects = read_json('subjects.json')
    paper_found = False
    
    for subject in subjects:
        if subject.get('subject_id') == subject_id:
            initial_len = len(subject.get('papers', []))
            subject['papers'] = [p for p in subject.get('papers', []) if p.get('paper_id', p.get('id')) != paper_id]
            if len(subject['papers']) < initial_len:
                paper_found = True
            break
            
    if paper_found:
        write_json('subjects.json', subjects)
        
        # Cascade delete solutions
        solutions = read_json('solutions.json')
        solutions_to_keep = []
        deleted_filepaths = []
        for s in solutions:
            if s.get('paper_id') == paper_id:
                if s.get('filepath'):
                    deleted_filepaths.append(s.get('filepath'))
            else:
                solutions_to_keep.append(s)
                
        write_json('solutions.json', solutions_to_keep)
        
        # Cascade delete comments
        comments = read_json('comments.json')
        comments = [c for c in comments if not (c.get('target_type') == 'paper' and c.get('target_id') == paper_id)]
        write_json('comments.json', comments)
        
        return deleted_filepaths
        
    return False

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
