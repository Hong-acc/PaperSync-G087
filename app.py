from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash
import db
import os
import json

app = Flask(__name__)
CORS(app)

# ================= IMPORTANT: SESSION =================
app.secret_key = "student_peer_support_secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DATA_DIR = os.path.join(BASE_DIR, "data")


# ================= FRONTEND FILE SERVING =================

@app.route('/')
def root():
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route('/login')
def login_page():
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route('/home')
def home_page():
    return send_from_directory(FRONTEND_DIR, "home.html")

@app.route('/style.css')
def style():
    return send_from_directory(FRONTEND_DIR, "style.css")

@app.route('/frontend/<path:filename>')
def frontend_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route('/<path:filename>')
def serve_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


# ================= USER SESSION (NEW FIX) =================

@app.route('/me', methods=['GET'])
def me():
    user = session.get("user")

    if not user:
        return jsonify({"user": "guest"})

    return jsonify({"user": user})


# ================= SUBJECTS =================

@app.route('/subjects', methods=['GET'])
def get_subjects():
    subjects_file = os.path.join(DATA_DIR, "subjects.json")

    if not os.path.exists(subjects_file):
        return jsonify([])

    with open(subjects_file, "r", encoding="utf-8") as f:
        subjects = json.load(f)

    return jsonify(subjects)


# ================= COMMENTS =================

@app.route('/comments')
def get_comments():

    target_id = request.args.get("target_id")

    comments = db.read_json("comments.json")

    for c in comments:
        c.setdefault("votes", 0)
        c.setdefault("voters", {})
        c.setdefault("replies", [])

    if target_id:
        comments = [c for c in comments if c.get("target_id") == target_id]

    comments.sort(key=lambda x: x.get("votes", 0), reverse=True)

    return jsonify(comments)


# ================= SIGNUP =================

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    user = db.add_user(
        data.get("username", ""),
        data.get("email", ""),
        data.get("password", "")
    )

    if not user:
        return jsonify({"message": "User exists"}), 400

    return jsonify({"message": "Signup success"})


# ================= LOGIN (FIXED SESSION) =================

@app.route('/login', methods=['POST'])
def login_api():
    data = request.get_json()

    login_input = data.get("username", "")
    password = data.get("password", "")

    user = db.get_user_by_username(login_input)
    if not user:
        user = db.get_user_by_email(login_input)

    if user and check_password_hash(user["password_hash"], password):

        # ✅ STORE LOGIN SESSION (IMPORTANT FIX)
        session["user"] = {
            "user_id": user["user_id"],
            "username": user["username"]
        }

        return jsonify({
            "message": "Login success",
            "success": True,
            "user": session["user"]
        })

    return jsonify({"message": "Invalid login", "success": False})


# ================= COMMENT POST (FIXED USER) =================

@app.route('/comment', methods=['POST'])
def comment():

    data = request.get_json()
    user = data.get("user", "")

    if not user or user in ["undefined", "null"]:
        return jsonify({"message": "Not logged in"}), 401

    comments = db.read_json("comments.json")

    comments.append({
        "id": str(len(comments) + 1),
        "user": user,
        "target_id": data.get("target_id", ""),
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

        c.setdefault("votes", 0)
        c.setdefault("voters", {})

        prev = c["voters"].get(user)

        if prev == action:
            return jsonify({"message": "Already voted", "votes": c["votes"]})

        if prev == "upvote":
            c["votes"] -= 1
        elif prev == "downvote":
            c["votes"] += 1

        if action == "upvote":
            c["votes"] += 1
            c["voters"][user] = "upvote"
        else:
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


# ================= RUN =================

if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)