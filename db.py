import json
import os
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
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
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
                "user_email": "admin@mmu.edu.my",
                "username": "admin",
                "password_hash": generate_password_hash("admin123"),
                "role": "admin"
            },
            {
                "user_id": "2",
                "user_email": "student@student.mmu.edu.my",
                "username": "student",
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
                "flags": 0
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

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
