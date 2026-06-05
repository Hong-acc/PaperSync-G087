from flask import Flask, request, jsonify, redirect, session, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import db
from functools import wraps

app = Flask(__name__)
app.secret_key = "papersync-admin-key"
CORS(app)

# ================= ADMIN CHECK =================
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
    return redirect('/frontend')

@app.route('/frontend')
def frontend():
    return send_file("frontend/home.html")

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
    email    = data.get("email", "").strip()
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
    password    = data.get("password", "")

    user = db.get_user_by_username(login_input)
    if not user:
        user = db.get_user_by_email(login_input)

    if user and check_password_hash(user["password_hash"], password):
        return jsonify({
            "message": "Login success",
            "success": True,
            "user": {
                "user_id":  user["user_id"],
                "username": user["username"]
            }
        })

    return jsonify({"message": "Invalid login", "success": False})

# ================= COMMENT =================
@app.route('/comment', methods=['POST'])
def comment():
    data = request.get_json()

    user = data.get("user", "").strip()

    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401

    comments = db.read_json("comments.json")

    comments.append({
        "id":      str(len(comments) + 1),
        "user":    user,
        "paper":   data.get("paper", ""),
        "text":    data.get("text", ""),
        "votes":   0,
        "voters":  {},
        "replies": []
    })

    db.write_json("comments.json", comments)

    return jsonify({"message": "Comment added"})

# ================= VOTE =================
@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()

    cid    = str(data.get("id"))
    action = data.get("action")
    user   = data.get("user", "")

    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401

    comments = db.read_json("comments.json")

    for c in comments:
        if str(c.get("id")) != cid:
            continue

        c.setdefault("votes",  0)
        c.setdefault("voters", {})

        previous = c["voters"].get(user)

        if previous == action:
            return jsonify({"message": "Already voted", "votes": c["votes"]})

        if previous == "upvote":
            c["votes"] -= 1
        elif previous == "downvote":
            c["votes"] += 1

        if action == "upvote":
            c["votes"] += 1
            c["voters"][user] = "upvote"
        elif action == "downvote":
            c["votes"] -= 1
            c["voters"][user] = "downvote"

        db.write_json("comments.json", comments)

        return jsonify({"message": "Vote updated", "votes": c["votes"]})

    return jsonify({"message": "Not found"}), 404

# ================= REPLY =================
@app.route('/reply', methods=['POST'])
def reply():
    data = request.get_json()

    user = data.get("user", "")
    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401

    cid      = str(data.get("id"))
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
        c.setdefault("votes",   0)
        c.setdefault("voters",  {})
        c.setdefault("replies", [])

    comments.sort(key=lambda x: x.get("votes", 0), reverse=True)

    return jsonify(comments)

# ================= FILE UPLOAD =================
import os
from werkzeug.utils import secure_filename

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route('/upload', methods=['POST'])
def upload():
    user        = request.form.get("user", "")
    subject     = request.form.get("subject", "")
    answer_type = request.form.get("type", "")
    paper_id    = request.form.get("paper_id", "")   # ← NEW: capture paper_id

    if not user:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"success": False, "message": "Empty file"}), 400

    filename    = secure_filename(file.filename)
    stored_name = f"{len(os.listdir(UPLOAD_DIR))}_{filename}"
    save_path   = os.path.join(UPLOAD_DIR, stored_name)

    file.save(save_path)

    solutions = db.read_json("solutions.json")

    solutions.append({
        "id":       str(len(solutions) + 1),
        "user":     user,
        "subject":  subject,
        "type":     answer_type,
        "paper_id": paper_id,     # ← NEW: store paper_id so solutions are grouped by trimester
        "filename": filename,
        "stored":   stored_name
    })

    db.write_json("solutions.json", solutions)

    return jsonify({"success": True, "message": "Upload success"})


# ================= GET SOLUTIONS =================
@app.route('/solutions')
def solutions():
    subject  = request.args.get("subject")
    paper_id = request.args.get("paper_id")   # ← NEW: optional paper_id filter
    data     = db.read_json("solutions.json")

    if subject:
        data = [s for s in data if s.get("subject") == subject]

    if paper_id:
        data = [s for s in data if str(s.get("paper_id", "")) == str(paper_id)]

    return jsonify(data)


# ================= DOWNLOAD =================
@app.route('/download/<file_id>')
def download(file_id):
    data = db.read_json("solutions.json")

    for s in data:
        if str(s.get("id")) == str(file_id):
            return send_file(
                os.path.join(UPLOAD_DIR, s["stored"]),
                as_attachment=True
            )

    return jsonify({"message": "File not found"}), 404

# ================= ADMIN VERIFY =================
@app.route('/admin/verify', methods=['POST'])
def admin_verify():
    data = request.get_json()

    login_input = data.get("username", "").strip()
    password    = data.get("password", "")

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

    session["admin_verified"]  = True
    session["admin_user_id"]   = user.get("user_id")

    return jsonify({
        "success": True,
        "message": "Admin verified"
    })

# ================= ADMIN PAGES =================
@app.route('/admin-dashboard')
@require_admin
def admin_dashboard():
    return send_file("frontend/admin.html")

@app.route('/admin/stats')
@require_admin
def admin_stats():
    stats = db.get_system_stats()
    return jsonify({
        "subjects":     stats["total_subjects"],
        "papers":       stats["total_papers"],
        "users":        stats["total_users"],
        "solutions":    stats["total_solutions"],
        "comments":     stats["total_comments"],
        "banned_users": sum(1 for u in db.get_all_users() if u.get("status") == "banned")
    })

# ================= RUN =================
if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)