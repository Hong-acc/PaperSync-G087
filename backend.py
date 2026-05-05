from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# ---------- Helper ----------
def read_json(file):
    if not os.path.exists(file):
        return []
    with open(file, "r") as f:
        content = f.read().strip()
        return json.loads(content) if content else []

def write_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ---------- HOME ----------
@app.route('/')
def home():
    return redirect('/frontend')

@app.route('/frontend')
def frontend():
    with open("frontend.html", "r", encoding="utf-8") as f:
        return f.read()

# ---------- SEARCH ----------
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

# ---------- COMMENT ----------
@app.route('/comment', methods=['POST'])
def add_comment():
    data = request.get_json()
    comments = read_json("comments.json")

    comments.append({
        "id": str(len(comments) + 1),
        "user": data.get("user", ""),
        "paper": data.get("paper", ""),
        "text": data.get("text", ""),
        "votes": 0,
        "voters": {},
        "replies": []
    })

    write_json("comments.json", comments)
    return jsonify({"message": "Comment added"})

# ---------- VOTE ----------
@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    comments = read_json("comments.json")

    cid = str(data.get("id"))
    action = data.get("action")
    user = "user1"

    for c in comments:
        if str(c.get("id")) == cid:

            if "voters" not in c:
                c["voters"] = {}

            previous = c["voters"].get(user)

            if previous == action:
                return jsonify({"message": "Already voted"})

            # remove old vote
            if previous == "upvote":
                c["votes"] -= 1
            elif previous == "downvote":
                c["votes"] += 1

            # apply new vote
            if action == "upvote":
                c["votes"] += 1
            elif action == "downvote":
                c["votes"] -= 1

            c["voters"][user] = action

    write_json("comments.json", comments)
    return jsonify({"message": "Vote updated"})

# ---------- REPLY ----------
@app.route('/reply', methods=['POST'])
def reply():
    data = request.get_json()
    comments = read_json("comments.json")

    cid = str(data.get("id"))

    for c in comments:
        if str(c.get("id")) == cid:

            if "replies" not in c:
                c["replies"] = []

            c["replies"].append({
                "user": data.get("user", "anonymous"),
                "text": data.get("text", "")
            })

    write_json("comments.json", comments)
    return jsonify({"message": "Reply added"})

# ---------- COMMENTS (🔥 SORTED BY VOTES) ----------
@app.route('/comments', methods=['GET'])
def get_comments():
    comments = read_json("comments.json")

    # 🔥 SORT BY VOTES (highest first)
    comments.sort(key=lambda x: x.get("votes", 0), reverse=True)

    return jsonify(comments)

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)