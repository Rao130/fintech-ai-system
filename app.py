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
# Initialize Database
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
# Behavior Tracking (Simple AI)
# -------------------------------
user_profiles = {}

def calculate_behavior_risk(user_id, amount, time, location):
    profile = user_profiles.get(user_id)

    if not profile:
        user_profiles[user_id] = {
            "avg_amount": amount,
            "avg_time": time,
            "avg_location": location,
            "count": 1
        }
        return 0

    amount_diff = abs(amount - profile["avg_amount"])
    time_diff = abs(time - profile["avg_time"])
    location_diff = abs(location - profile["avg_location"])

    risk = 0

    if amount_diff > 3000:
        risk += 20
    if time_diff > 5:
        risk += 15
    if location_diff > 20:
        risk += 15

    # update profile
    profile["count"] += 1
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

        # Behavior Risk
        behavior_risk = calculate_behavior_risk(user_id, amount, time, location)

        # Final Risk
        final_risk = min(ml_risk + behavior_risk, 100)

        result = "Fraud" if final_risk > 60 else "Safe"

        # Save to DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO transactions (user_id, amount, time, location, result, risk_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, time, location, result, final_risk))

        conn.commit()
        conn.close()

        is_alert = False

        if final_risk > 75:
            is_alert = True

        return jsonify({
            "result": result,
            "risk_score": final_risk,
            "behavior_risk": behavior_risk,
            "is_alert": is_alert
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT user_id, amount, result, risk_score FROM transactions")
    rows = c.fetchall()

    conn.close()

    history = []
    for row in rows:
        history.append({
            "user_id": row[0],
            "amount": row[1],
            "result": row[2],
            "risk_score": row[3]
        })

    return jsonify(history)

@app.route('/analytics', methods=['GET'])
def analytics():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Total transactions
    c.execute("SELECT COUNT(*) FROM transactions")
    total = c.fetchone()[0]

    # Fraud count
    c.execute("SELECT COUNT(*) FROM transactions WHERE result='Fraud'")
    fraud = c.fetchone()[0]

    # Safe count
    safe = total - fraud

    # Fraud %
    fraud_percent = round((fraud / total) * 100, 2) if total > 0 else 0

    conn.close()

    return jsonify({
        "total": total,
        "fraud": fraud,
        "safe": safe,
        "fraud_percent": fraud_percent
    })

# -------------------------------
# Run
# -------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))