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
    conn = sqlite3.connect("transactions.db")
    cursor = conn.cursor()

    # Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            amount REAL,
            location TEXT,
            status TEXT,
            risk_score REAL
        )
    """)

    # User profiles table for behavior tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            name TEXT PRIMARY KEY,
            avg_amount REAL,
            last_location TEXT,
            total_tx INTEGER
        )
    """)

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
            "avg_location": location,
            "last_location": location
        }
        return 0

    risk = 0

    # Check if amount exceeds 3x average user spending
    if amount > (profile["avg_amount"] * 3):
        risk += 40

    if abs(amount - profile["avg_amount"]) > 3000:
        risk += 20
    if abs(time - profile["avg_time"]) > 5:
        risk += 15
    
    # Check if location differs from user's last location
    if location != profile["last_location"]:
        risk += 20

    profile["avg_amount"] = (profile["avg_amount"] + amount) / 2
    profile["avg_time"] = (profile["avg_time"] + time) / 2
    profile["avg_location"] = (profile["avg_location"] + location) / 2
    profile["last_location"] = location

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
    try:
        data = request.json
        name = data.get('name', 'guest')
        amount = float(data.get('amount', 0))
        location = data.get('location', 'unknown')

        conn = sqlite3.connect("transactions.db", check_same_thread=False)
        cursor = conn.cursor()

        # 👇 USER PROFILE FETCH
        cursor.execute("SELECT avg_amount, last_location, total_tx FROM user_profiles WHERE name=?", (name,))
        user = cursor.fetchone()

        risk_score = 0

        if user:
            avg_amount, last_location, total_tx = user

            # 💰 Amount behavior check
            if amount > avg_amount * 3:
                risk_score += 40

            # 🌍 Location change check
            if location != last_location:
                risk_score += 30

            # 📊 Sudden spike in activity
            if total_tx > 5:
                risk_score += 10

            # UPDATE USER PROFILE
            new_avg = (avg_amount * total_tx + amount) / (total_tx + 1)
            cursor.execute("""
                UPDATE user_profiles
                SET avg_amount=?, last_location=?, total_tx=?
                WHERE name=?
            """, (new_avg, location, total_tx + 1, name))

        else:
            # 👶 New user
            cursor.execute("""
                INSERT INTO user_profiles (name, avg_amount, last_location, total_tx)
                VALUES (?, ?, ?, ?)
            """, (name, amount, location, 1))

        # 🎯 FINAL DECISION
        if risk_score < 40:
            status = "Safe"
            action = "Allow"
        elif risk_score < 70:
            status = "Suspicious"
            action = "Review"
        else:
            status = "Fraud"
            action = "Block"

        # 💾 SAVE TRANSACTION
        cursor.execute("""
            INSERT INTO transactions (name, amount, location, status, risk_score)
            VALUES (?, ?, ?, ?, ?)
        """, (name, amount, location, status, risk_score))

        conn.commit()
        conn.close()

        return jsonify({
            "status": status,
            "risk_score": risk_score,
            "action": action
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500
# -------------------------------
# History API
# -------------------------------
@app.route('/history', methods=['GET'])
def get_history():
    try:
        conn = sqlite3.connect('transactions.db')
        c = conn.cursor()

        c.execute("SELECT name, amount, status, risk_score FROM transactions")
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
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Analytics API
# -------------------------------
@app.route('/analytics', methods=['GET'])
def analytics():
    try:
        conn = sqlite3.connect('transactions.db')
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM transactions")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM transactions WHERE status='Fraud'")
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
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/top_risky_users')
def top_risky_users():
    try:
        conn = sqlite3.connect('transactions.db')
        cursor = conn.cursor()

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
                "risk": round(u[2], 2) if u[2] else 0
            })

        return jsonify({"users": result})
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/get_alert')
def get_alert():
    global last_alert

    if last_alert:
        alert = last_alert
        last_alert = None  # reset after showing
        return jsonify({"alert": alert})

    return jsonify({"alert": None})
@app.route('/filter_transactions')
def filter_transactions():
    try:
        search = request.args.get('search', '')
        status = request.args.get('status', '')

        conn = sqlite3.connect('transactions.db')
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

        return jsonify({"data": result})
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/trend_data')
def trend_data():
    try:
        conn = sqlite3.connect('transactions.db')
        cursor = conn.cursor()

        # Get fraud transactions count
        cursor.execute("""
            SELECT COUNT(*) 
            FROM transactions 
            WHERE status='Fraud'
        """)

        rows = cursor.fetchall()
        conn.close()

        dates = ["Fraud Trend"]
        counts = [rows[0][0] if rows and rows[0][0] else 0]

        return jsonify({"dates": dates, "counts": counts})
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"dates": [], "counts": [], "error": str(e)}), 200

@app.route('/export')
def export_data():
    try:
        from flask import Response

        conn = sqlite3.connect('transactions.db')
        cursor = conn.cursor()

        cursor.execute("SELECT name, amount, location, status, risk_score FROM transactions")
        rows = cursor.fetchall()
        conn.close()

        def generate():
            yield "Name,Amount,Location,Status,Risk Score\n"
            for r in rows:
                yield f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]}\n"

        return Response(generate(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment;filename=transactions.csv"})
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Run
# -------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))