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

        user_id = data.get("user_id", "guest")
        amount = float(data.get("amount", 0))
        time = float(data.get("time", 0))
        location = float(data.get("location", 0))

        # ML Prediction
        prediction = model.predict([[amount, time, location]])[0]
        probability = model.predict_proba([[amount, time, location]])[0][1]

        ml_risk = round(probability * 100, 2)

        # Behavior risk
        behavior_risk = calculate_behavior_risk(user_id, amount, time, location)

        # Final risk
        final_risk = min(ml_risk + behavior_risk, 100)

        result = "Fraud" if final_risk > 60 else "Safe"

        # Alert system
        alert = True if final_risk > 75 else False

        # Save DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO transactions (user_id, amount, time, location, result, risk_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, time, location, result, final_risk))

        conn.commit()
        conn.close()

        credit_score = max(300, 900 - int(final_risk))

        # Determine action based on risk score
        if final_risk < 40:
            action = "Allow"
        elif final_risk < 70:
            action = "Review"
        else:
            action = "Block"

        return jsonify({
            "status": result,
            "risk_score": final_risk,
            "behavior_risk": behavior_risk,
            "alert": alert,
            "credit_score": credit_score,
            "action": action,
            "ai_explanation": f"{result} detected based on ML probability {ml_risk}% and behavior analysis."
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500
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
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, COUNT(*) as total, AVG(risk_score) as avg_risk
            FROM transactions
            GROUP BY user_id
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

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        query = "SELECT user_id, amount, result FROM transactions WHERE 1=1"
        params = []

        if search:
            query += " AND user_id LIKE ?"
            params.append(f"%{search}%")

        if status:
            query += " AND result=?"
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
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Group by date and count fraud transactions
        cursor.execute("""
            SELECT date(datetime('now', '-' || (SELECT MAX(id) - id FROM transactions) || ' days')), COUNT(*) 
            FROM transactions 
            WHERE result='Fraud'
            GROUP BY date(datetime('now', '-' || (SELECT MAX(id) - id FROM transactions) || ' days'))
            ORDER BY date DESC
            LIMIT 7
        """)

        rows = cursor.fetchall()
        conn.close()

        dates = []
        counts = []

        for r in rows:
            dates.append(str(r[0]) if r[0] else "Today")
            counts.append(r[1])

        return jsonify({"dates": dates, "counts": counts})
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"dates": [], "counts": [], "error": str(e)}), 200

@app.route('/export')
def export_data():
    try:
        from flask import Response

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, amount, time, location, result, risk_score FROM transactions")
        rows = cursor.fetchall()
        conn.close()

        def generate():
            yield "User ID,Amount,Time,Location,Status,Risk Score\n"
            for r in rows:
                yield f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]}\n"

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