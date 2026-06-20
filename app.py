import os
import uuid
from flask import Flask, request, jsonify, redirect, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import db
from functools import wraps

app = Flask(__name__)
app.secret_key = "papersync-admin-key"
CORS(app)

reset_serializer = URLSafeTimedSerializer(app.secret_key, salt="password-reset")
RESET_TOKEN_MAX_AGE = 3600  # 1 hour

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'png', 'jpg', 'jpeg', 'zip', 'py'}

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def require_admin(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_verified"):
            return jsonify({"message": "Admin verification required"}), 401
        return route_func(*args, **kwargs)
    return wrapper

# ================= FRONTEND =================
@app.route('/')
def home():
    with open("login.html", "r", encoding="utf-8") as f:
        return f.read()

@app.route('/frontend')
def frontend():
    with open("home.html", "r", encoding="utf-8") as f:
        return f.read()

# ================= SUBJECTS =================
@app.route('/subjects')
def get_subjects():
    subjects = db.get_all_subjects()
    return jsonify(subjects)

# ================= SEARCH =================
@app.route('/search')
def search():
    keyword = request.args.get("q", "").lower()
    papers = db.read_json("subjects.json")

    results = [
        p for p in papers
        if keyword in p.get("subject_name", "").lower()
        or keyword in p.get("subject_code", "").lower()
    ]

    return jsonify(results)

# ================= SIGNUP =================
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not username or not email or not password:
        return jsonify({"message": "Missing fields"}), 400

    user = db.add_user(username, email, password)

    if not user:
        return jsonify({"message": "User already exists"}), 400

    return jsonify({"message": "Signup success"})

# ================= LOGIN =================
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    login_input = data.get("username", "")
    password = data.get("password", "")

    user = db.get_user_by_username(login_input)
    if not user:
        user = db.get_user_by_email(login_input)

    if user and check_password_hash(user["password_hash"], password):
        if user.get("status") == "banned":
            return jsonify({"message": "Your account has been banned.", "success": False}), 403

        return jsonify({
            "message": "Login success",
            "success": True,
            "user": {"user_id": user["user_id"], "username": user["username"]}
        })

    return jsonify({"message": "Invalid login", "success": False})

# ================= FORGOT PASSWORD =================
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    user = db.get_user_by_email(email)

    # Always respond success-like message to avoid leaking which emails are registered.
    if user:
        token = reset_serializer.dumps({"user_id": user["user_id"], "email": email})
        reset_link = f"{request.host_url.rstrip('/')}/reset-password?token={token}"
        # Simulate sending an email by logging the link to the server console.
        print(f"[PaperSync] Password reset link for {email}: {reset_link}")

    return jsonify({
        "success": True,
        "message": "If an account with that email exists, a password reset link has been sent."
    })

# ================= RESET PASSWORD =================
@app.route('/reset-password', methods=['GET'])
def reset_password_page():
    with open("reset_password.html", "r", encoding="utf-8") as f:
        return f.read()

@app.route('/reset-password', methods=['POST'])
def reset_password_submit():
    data = request.get_json()
    token = data.get("token", "").strip()
    new_password = data.get("password", "").strip()

    if not token or not new_password:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    try:
        payload = reset_serializer.loads(token, max_age=RESET_TOKEN_MAX_AGE)
    except SignatureExpired:
        return jsonify({"success": False, "message": "Reset link has expired"}), 400
    except BadSignature:
        return jsonify({"success": False, "message": "Invalid reset link"}), 400

    user_id = payload.get("user_id")
    users = db.read_json("users.json")
    for u in users:
        if u.get("user_id") == user_id:
            u["password_hash"] = generate_password_hash(new_password)
            db.write_json("users.json", users)
            return jsonify({"success": True, "message": "Password reset successful"})

    return jsonify({"success": False, "message": "Account not found"}), 400

# ================= COMMENT =================
@app.route('/comment', methods=['POST'])
def comment():
    data = request.get_json()

    user = data.get("user", "").strip()

    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401

    comments = db.read_json("comments.json")

    comments.append({
        "id": str(len(comments) + 1),
        "user": user,
        "paper": data.get("paper", ""),
        "text": data.get("text", ""),
        "votes": 0,
        "voters": {},
        "replies": []
    })

    db.write_json("comments.json", comments)

    return jsonify({"message": "Comment added"})

# ================= VOTE =================
@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()

    cid = str(data.get("id"))
    action = data.get("action")
    user = data.get("user", "")

    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401

    comments = db.read_json("comments.json")

    for c in comments:
        if str(c.get("id")) != cid:
            continue

        c.setdefault("voters", {})

        previous = c["voters"].get(user)

        if previous == action:
            # Toggle off: remove the vote entirely
            del c["voters"][user]
        else:
            c["voters"][user] = action

        upvotes = sum(1 for v in c["voters"].values() if v == "upvote")
        downvotes = sum(1 for v in c["voters"].values() if v == "downvote")

        c["upvotes"] = upvotes
        c["downvotes"] = downvotes
        c["votes"] = upvotes - downvotes

        db.write_json("comments.json", comments)

        return jsonify({
            "message": "Vote updated",
            "votes": c["votes"],
            "upvotes": upvotes,
            "downvotes": downvotes
        })

    return jsonify({"message": "Not found"}), 404

# ================= REPLY =================
@app.route('/reply', methods=['POST'])
def reply():
    data = request.get_json()

    user = data.get("user", "")
    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401

    cid = str(data.get("id"))
    comments = db.read_json("comments.json")

    for c in comments:
        if str(c.get("id")) == cid:

            c.setdefault("replies", [])
            c["replies"].append({
                "user": user,
                "text": data.get("text", "")
            })

            db.write_json("comments.json", comments)
            return jsonify({"message": "Reply added"})

    return jsonify({"message": "Not found"}), 404

# ================= GET COMMENTS =================
@app.route('/comments')
def get_comments():
    comments = db.read_json("comments.json")

    for c in comments:
        c.setdefault("voters", {})
        c.setdefault("replies", [])
        c["upvotes"] = sum(1 for v in c["voters"].values() if v == "upvote")
        c["downvotes"] = sum(1 for v in c["voters"].values() if v == "downvote")
        c["votes"] = c["upvotes"] - c["downvotes"]

    comments.sort(key=lambda x: x.get("votes", 0), reverse=True)

    return jsonify(comments)

# ================= ADMIN VERIFY =================
@app.route('/admin/verify', methods=['POST'])
def admin_verify():
    data = request.get_json()

    login_input = data.get("username", "").strip()
    password = data.get("password", "")

    user = db.get_user_by_username(login_input)
    if not user:
        user = db.get_user_by_email(login_input)

    if not user:
        return jsonify({
            "success": False,
            "message": "Account not found"
        }), 403

    email = user.get("user_email", "").lower()

    if user.get("role") != "admin" or not email.endswith("@mmu.edu.my") or email.endswith("@student.mmu.edu.my"):
        return jsonify({
            "success": False,
            "message": "Only admin email can access admin dashboard"
        }), 403

    if not check_password_hash(user["password_hash"], password):
        return jsonify({
            "success": False,
            "message": "Wrong password"
        }), 403

    session["admin_verified"] = True
    session["admin_user_id"] = user.get("user_id")

    return jsonify({
        "success": True,
        "message": "Admin verified"
    })

@app.route('/admin-dashboard')
@require_admin
def admin_dashboard():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()
    
@app.route('/admin/stats')
@require_admin
def admin_stats():
    users = db.read_json("users.json")
    subjects = db.read_json("subjects.json")
    comments = db.read_json("comments.json")
    solutions = db.read_json("solutions.json")

    return jsonify({
        "users": len(users),
        "subjects": len(subjects),
        "papers": sum(len(s.get("papers", [])) for s in subjects),
        "comments": len(comments),
        "solutions": len(solutions),
        "banned_users": sum(1 for u in users if u.get("status") == "banned")
    })
   
@app.route('/admin/flagged/solutions')
@require_admin
def admin_flagged_solutions():
    solutions = db.read_json("solutions.json")
    flagged = [s for s in solutions if s.get("flags", 0) > 0]
    return jsonify(flagged)

@app.route('/admin/flagged/comments')
@require_admin
def admin_flagged_comments():
    comments = db.read_json("comments.json")
    flagged = [c for c in comments if c.get("flags", 0) > 0]
    return jsonify(flagged)

@app.route('/admin/flag/dismiss', methods=['POST'])
@require_admin
def admin_flag_dismiss():
    data = request.get_json()
    content_type = data.get("type")
    content_id = str(data.get("id"))

    if content_type == "solution":
        solutions = db.read_json("solutions.json")
        for s in solutions:
            if str(s.get("solution_id")) == content_id:
                s["flags"] = 0
                s["flagged_by"] = []
        db.write_json("solutions.json", solutions)

    elif content_type == "comment":
        comments = db.read_json("comments.json")
        for c in comments:
            if str(c.get("comment_id", c.get("id", ""))) == content_id:
                c["flags"] = 0
        db.write_json("comments.json", comments)

    return jsonify({"success": True})

@app.route('/admin/solution/delete', methods=['POST'])
@require_admin
def admin_delete_solution():
    data = request.get_json()
    result = db.delete_solution(str(data.get("id")), role="admin")
    return jsonify({"success": bool(result)})

@app.route('/admin/comment/delete', methods=['POST'])
@require_admin
def admin_delete_comment():
    data = request.get_json()
    result = db.delete_comment(str(data.get("id")), role="admin")
    return jsonify({"success": bool(result)})

@app.route('/flag/comment', methods=['POST'])
def flag_comment():
    data = request.get_json()
    user = data.get("user", "")
    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401

    comment_id = str(data.get("comment_id"))
    comments = db.read_json("comments.json")
    for c in comments:
        if str(c.get("comment_id", c.get("id"))) == comment_id:
            c.setdefault("flags", 0)
            c["flags"] += 1
            db.write_json("comments.json", comments)
            return jsonify({"success": True})

    return jsonify({"message": "Not found"}), 404

@app.route('/solutions')
def get_solutions():
    paper_id = request.args.get("paper_id")
    solutions = db.read_json("solutions.json")
    if paper_id:
        solutions = [s for s in solutions if s.get("paper_id") == paper_id]
    return jsonify(solutions)

# ================= UPLOAD SOLUTION =================
@app.route('/upload', methods=['POST'])
def upload_solution():
    paper_id = request.form.get("paper_id", "").strip()
    uploader_username = request.form.get("uploader_username", "").strip()
    uploader_id = request.form.get("uploader_id", "").strip() or "anonymous"
    answer_type = request.form.get("answer_type", "").strip() or "Solution"

    if not paper_id or not uploader_username:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "File type not allowed"}), 400

    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    filepath = os.path.join(UPLOAD_DIR, unique_name)
    file.save(filepath)

    solution = db.add_solution(paper_id, uploader_id, uploader_username, unique_name, file.filename)

    # Attach answer_type without modifying db.py's add_solution signature
    solutions = db.read_json("solutions.json")
    for s in solutions:
        if s.get("solution_id") == solution.get("solution_id"):
            s["answer_type"] = answer_type
            solution = s
            break
    db.write_json("solutions.json", solutions)

    return jsonify({"success": True, "message": "Upload successful", "solution": solution})

# ================= DOWNLOAD SOLUTION =================
@app.route('/uploads/<filename>')
def download_solution(filename):
    solutions = db.read_json("solutions.json")
    match = next((s for s in solutions if s.get("filepath") == filename), None)
    download_name = match.get("original_filename", filename) if match else filename
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True, download_name=download_name)

@app.route('/solution/upvote', methods=['POST'])
def upvote_solution():
    data = request.get_json()
    user = data.get("user", "")
    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401
    result = db.update_solution_upvotes(str(data.get("solution_id")), user)
    if result:
        return jsonify({"success": True, "upvotes": result["upvotes"]})
    return jsonify({"message": "Not found"}), 404

@app.route('/flag/solution', methods=['POST'])
def flag_solution():
    data = request.get_json()
    user = data.get("user", "")
    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401
    result = db.update_solution_flags(str(data.get("solution_id")), user)
    if result:
        return jsonify({"success": True, "flags": result["flags"]})
    return jsonify({"message": "Not found"}), 404 

@app.route('/admin/subject/add', methods=['POST'])
@require_admin
def admin_add_subject():
    subject_code = request.form.get("subject_code")
    subject_name = request.form.get("subject_name")
    trimester = request.form.get("trimester")
    category = request.form.get("category")

    if not subject_code or not subject_name or not trimester or not category:
        return "Missing required fields", 400

    db.add_subject(subject_name, subject_code, trimester, category)
    return redirect('/admin-dashboard')

@app.route('/admin/paper/add', methods=['POST'])
@require_admin
def admin_add_paper():
    subject_id = request.form.get("subject_id")
    year = request.form.get("year")
    trimester = request.form.get("trimester")

    if not subject_id or not year or not trimester:
        return "Missing required fields", 400

    filepath = None
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '':
            if not file.filename.lower().endswith('.pdf'):
                return "Only PDF files allowed", 400
            safe_name = secure_filename(file.filename)
            unique_name = f"paper_{uuid.uuid4().hex[:8]}_{safe_name}"
            file.save(os.path.join(UPLOAD_DIR, unique_name))
            filepath = unique_name

    paper = db.add_paper_to_subject(subject_id, year, trimester, filepath)
    if not paper:
        return "Subject not found", 404
        
    return redirect('/admin-dashboard')

@app.route('/admin/users')
@require_admin
def admin_users():
    users = db.read_json("users.json")
    safe_users = [{
        "user_id": u.get("user_id"),
        "username": u.get("username"),
        "user_email": u.get("user_email"),
        "role": u.get("role"),
        "status": u.get("status", "active")
    } for u in users]
    return jsonify(safe_users)

@app.route('/admin/user/ban', methods=['POST'])
@require_admin
def admin_ban_user():
    data = request.get_json()
    user_id = str(data.get("user_id"))

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    if user.get("role") == "admin":
        return jsonify({"success": False, "message": "Cannot ban admin"}), 403

    db.update_user_status(user_id, "banned")
    return jsonify({"success": True})

@app.route('/admin/user/unban', methods=['POST'])
@require_admin
def admin_unban_user():
    data = request.get_json()
    user_id = str(data.get("user_id"))
    db.update_user_status(user_id, "active")
    return jsonify({"success": True})       
    
    # ================= RUN =================
if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)