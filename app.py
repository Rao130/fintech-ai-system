from flask import Flask, render_template, request, jsonify
import pickle
import os
import sqlite3

app = Flask(__name__)

# -------------------------------
# Load ML Model
# -------------------------------
model = pickle.load(open(os.path.join('model', 'model.pkl'), 'rb'))

# -------------------------------
# Database Setup
# -------------------------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            amount REAL,
            time REAL,
            location REAL,
            result TEXT,
            risk_score REAL
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# -------------------------------
# Behavior AI (simple learning)
# -------------------------------
user_profiles = {}

def calculate_behavior_risk(user_id, amount, time, location):
    profile = user_profiles.get(user_id)

    if not profile:
        user_profiles[user_id] = {
            "avg_amount": amount,
            "avg_time": time,
            "avg_location": location
        }
        return 0

    risk = 0

    if abs(amount - profile["avg_amount"]) > 3000:
        risk += 20
    if abs(time - profile["avg_time"]) > 5:
        risk += 15
    if abs(location - profile["avg_location"]) > 20:
        risk += 15

    profile["avg_amount"] = (profile["avg_amount"] + amount) / 2
    profile["avg_time"] = (profile["avg_time"] + time) / 2
    profile["avg_location"] = (profile["avg_location"] + location) / 2

    return risk

# -------------------------------
# Routes
# -------------------------------
@app.route('/')
def home():
    return render_template('index.html')
# last alert store karne ke liye (top me define karo)
last_alert = None

@app.route('/check_transaction', methods=['POST'])
def check_transaction():
    global last_alert
    data = request.json

    name = data['name']
    amount = float(data['amount'])
    location = data['location']

    risk_score = 0

    if amount > 10000:
        risk_score += 50
    if location.lower() != "india":
        risk_score += 30

    status = "Fraud" if risk_score > 50 else "Safe"

    # ALERT STORE
    if status == "Fraud":
        last_alert = {
            "name": name,
            "amount": amount,
            "location": location,
            "risk": risk_score
        }

    # DB SAVE (assumed already)
    import sqlite3
    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO transactions (name, amount, location, status, risk_score)
        VALUES (?, ?, ?, ?, ?)
    """, (name, amount, location, status, risk_score))

    conn.commit()
    conn.close()

    return {"status": status, "risk_score": risk_score}
# -------------------------------
# History API
# -------------------------------
@app.route('/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT user_id, amount, result, risk_score FROM transactions")
    rows = c.fetchall()

    conn.close()

    return jsonify([
        {
            "user_id": r[0],
            "amount": r[1],
            "result": r[2],
            "risk_score": r[3],
            "credit_score": max(300, 900 - int(r[3]))
        }
        for r in rows
    ])

# -------------------------------
# Analytics API
# -------------------------------
@app.route('/analytics', methods=['GET'])
def analytics():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM transactions")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM transactions WHERE result='Fraud'")
    fraud = c.fetchone()[0]

    safe = total - fraud

    fraud_percent = round((fraud / total) * 100, 2) if total > 0 else 0

    conn.close()

    return jsonify({
        "total": total,
        "fraud": fraud,
        "safe": safe,
        "fraud_percent": fraud_percent
    })
@app.route('/top_risky_users')
def top_risky_users():
    import sqlite3

    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()

    # assuming table columns: name, amount, location, status, risk_score
    cursor.execute("""
        SELECT name, COUNT(*) as total, AVG(risk_score) as avg_risk
        FROM transactions
        GROUP BY name
        ORDER BY avg_risk DESC
        LIMIT 5
    """)

    users = cursor.fetchall()
    conn.close()

    result = []
    for u in users:
        result.append({
            "name": u[0],
            "transactions": u[1],
            "risk": round(u[2], 2)
        })

@app.route('/top_risky_users')
def top_risky_users():
    import sqlite3

    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()

    # assuming table columns: name, amount, location, status, risk_score
    cursor.execute("""
        SELECT name, COUNT(*) as total, AVG(risk_score) as avg_risk
        FROM transactions
        GROUP BY name
        ORDER BY avg_risk DESC
        LIMIT 5
    """)

    users = cursor.fetchall()
    conn.close()

    result = []
    for u in users:
        result.append({
            "name": u[0],
            "transactions": u[1],
            "risk": round(u[2], 2)
        })

    return {"users": result}
@app.route('/get_alert')
def get_alert():
    global last_alert

    if last_alert:
        alert = last_alert
        last_alert = None  # reset after showing
        return {"alert": alert}

    return {"alert": None}
@app.route('/filter_transactions')
def filter_transactions():
    import sqlite3
    from flask import request

    search = request.args.get('search', '')
    status = request.args.get('status', '')

    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()

    query = "SELECT name, amount, status FROM transactions WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")

    if status:
        query += " AND status=?"
        params.append(status)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "name": r[0],
            "amount": r[1],
            "status": r[2]
        })

    return {"data": result}
# -------------------------------
# Run
# -------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))