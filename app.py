from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import db

app = Flask(__name__)
CORS(app)

# ================= FRONTEND =================
@app.route('/')
def home():
    return redirect('/frontend')

@app.route('/frontend')
def frontend():
    with open("frontend.html", "r", encoding="utf-8") as f:
        return f.read()

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
        return jsonify({
            "message": "Login success",
            "success": True,
            "user": {
                "user_id": user["user_id"],
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

        c.setdefault("votes", 0)
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
        c.setdefault("votes", 0)
        c.setdefault("voters", {})
        c.setdefault("replies", [])

    comments.sort(key=lambda x: x.get("votes", 0), reverse=True)

    return jsonify(comments)

# ================= RUN =================
if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)