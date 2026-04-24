from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ---------- Helper Functions ----------
def read_json(file):
    if not os.path.exists(file):
        return []
    with open(file, 'r') as f:
        return json.load(f)

def write_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

# ---------- HOME (ONLY ONE) ----------
@app.route('/')
def home():
    return redirect('/frontend')

# ---------- Search ----------
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

# ---------- Add Comment ----------
@app.route('/comment', methods=['POST'])
def add_comment():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        comments = read_json('comments.json')

        new_comment = {
            "user": data.get('user', ''),
            "paper": data.get('paper', ''),
            "text": data.get('text', '')
        }

        comments.append(new_comment)
        write_json('comments.json', comments)

        return jsonify({"message": "Comment added successfully"})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

# ---------- Reply ----------
@app.route('/reply', methods=['POST'])
def reply():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        comments = read_json('comments.json')

        for c in comments:
            if c.get('paper') == data.get('paper'):
                if 'replies' not in c:
                    c['replies'] = []

                c['replies'].append({
                    "user": data.get('user', ''),
                    "text": data.get('text', '')
                })

        write_json('comments.json', comments)

        return jsonify({"message": "Reply added successfully"})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

# ---------- FRONTEND ----------
@app.route('/frontend')
def frontend():
    with open("frontend.html", "r", encoding="utf-8") as f:
        return f.read()

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)