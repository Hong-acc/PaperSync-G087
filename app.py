from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

app = Flask(__name__)
CORS(app)

# ======================================================
# HELPER
# ======================================================

def read_json(file):
    if not os.path.exists(file):
        return []
    with open(file, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else []

def write_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ======================================================
# HOME
# ======================================================

@app.route('/')
def home():
    return redirect('/frontend')


@app.route('/frontend')
def frontend():
    with open("frontend.html", "r", encoding="utf-8") as f:
        return f.read()


# ======================================================
# SEARCH
# ======================================================

@app.route('/search', methods=['GET'])
def search():

    keyword = request.args.get('q', '').lower()
    papers = read_json('papers.json')

    results = [
        p for p in papers
        if keyword in p.get('subject_name', '').lower()
        or keyword in p.get('subject_code', '').lower()
    ]

    return jsonify(results)


# ======================================================
# AUTH SYSTEM (FIXED SIGNUP)
# ======================================================

@app.route('/signup', methods=['POST'])
def signup():

    data = request.get_json()
    users = read_json("users.json")

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    # ❌ prevent empty signup
    if not username or not email or not password:
        return jsonify({"message": "Please fill in all fields"}), 400

    # ❌ duplicate check
    for u in users:
        if u["username"] == username or u["user_email"] == email:
            return jsonify({"message": "User already exists"}), 400

    # ✅ create user
    new_user = {
        "user_id": str(len(users) + 1),
        "user_email": email,
        "username": username,
        "password_hash": generate_password_hash(password),
        "role": "student"
    }

    users.append(new_user)
    write_json("users.json", users)

    return jsonify({"message": "Signup successful"})


@app.route('/login', methods=['POST'])
def login():

    data = request.get_json()
    users = read_json("users.json")

    login_input = data.get("username")
    password = data.get("password")

    for u in users:
        if login_input == u["username"] or login_input == u["user_email"]:
            if check_password_hash(u["password_hash"], password):

                return jsonify({
                    "message": "Login success",
                    "success": True,
                    "user": {
                        "user_id": u["user_id"],
                        "username": u["username"],
                        "role": u["role"]
                    }
                })

    return jsonify({"message": "Invalid credentials", "success": False})


# ======================================================
# COMMENT SYSTEM
# ======================================================

@app.route('/comment', methods=['POST'])
def add_comment():

    data = request.get_json()
    comments = read_json("comments.json")

    comments.append({
        "id": str(len(comments) + 1),
        "user": data.get("user", "anonymous"),
        "paper": data.get("paper", ""),
        "text": data.get("text", ""),
        "votes": 0,
        "voters": {},
        "replies": []
    })

    write_json("comments.json", comments)

    return jsonify({"message": "Comment added"})


# ======================================================
# VOTE SYSTEM
# ======================================================

@app.route('/vote', methods=['POST'])
def vote():

    data = request.get_json()
    comments = read_json("comments.json")

    cid = str(data.get("id"))
    action = data.get("action")
    user = data.get("user", "guest")

    for c in comments:

        if "votes" not in c:
            c["votes"] = 0

        if "voters" not in c:
            c["voters"] = {}

        if str(c.get("id")) == cid:

            previous = c["voters"].get(user)

            if previous == action:
                return jsonify({"message": "Already voted"})

            if previous == "upvote":
                c["votes"] -= 1
            elif previous == "downvote":
                c["votes"] += 1

            if action == "upvote":
                c["votes"] += 1
            elif action == "downvote":
                c["votes"] -= 1

            c["voters"][user] = action

    write_json("comments.json", comments)

    return jsonify({"message": "Vote updated"})


# ======================================================
# REPLY SYSTEM
# ======================================================

@app.route('/reply', methods=['POST'])
def reply():

    data = request.get_json()
    comments = read_json("comments.json")

    cid = str(data.get("id"))

    for c in comments:

        if "replies" not in c:
            c["replies"] = []

        if str(c.get("id")) == cid:

            c["replies"].append({
                "user": data.get("user", "anonymous"),
                "text": data.get("text", "")
            })

    write_json("comments.json", comments)

    return jsonify({"message": "Reply added"})


# ======================================================
# GET COMMENTS (SORTED)
# ======================================================

@app.route('/comments', methods=['GET'])
def get_comments():

    comments = read_json("comments.json")

    for c in comments:
        if "votes" not in c:
            c["votes"] = 0
        if "voters" not in c:
            c["voters"] = {}
        if "replies" not in c:
            c["replies"] = []

    comments.sort(key=lambda x: x.get("votes", 0), reverse=True)

    return jsonify(comments)


# ======================================================
# RUN
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)