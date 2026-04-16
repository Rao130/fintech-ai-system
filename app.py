from flask import Flask, render_template, request, jsonify
import pickle
import os
import sqlite3
import requests

app = Flask(__name__)

# -------------------------------
# Load ML Model
# -------------------------------
model = pickle.load(open(os.path.join('model', 'model.pkl'), 'rb'))

# -------------------------------
# Database Init
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
# Behavior AI System
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

    # update profile
    profile["avg_amount"] = (profile["avg_amount"] + amount) / 2
    profile["avg_time"] = (profile["avg_time"] + time) / 2
    profile["avg_location"] = (profile["avg_location"] + location) / 2

    return risk

# -------------------------------
# 🧠 AI Explanation (OLLAMA)
# -------------------------------
def get_ai_explanation(amount, time, location, risk_score, result):
    prompt = f"""
You are a fintech fraud detection AI.

Transaction:
Amount: {amount}
Time: {time}
Location: {location}
Risk Score: {risk_score}
Result: {result}

Explain in 2-3 lines why this transaction is safe or fraud.
Be professional and short.
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=5
        )

        return response.json().get("response", "No AI response")

    except:
        return "AI explanation not available (local AI not running)"

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

        # ML prediction
        prediction = model.predict([[amount, time, location]])[0]
        probability = model.predict_proba([[amount, time, location]])[0][1]
        ml_risk = round(probability * 100, 2)

        # Behavior risk
        behavior_risk = calculate_behavior_risk(user_id, amount, time, location)

        # Final risk
        final_risk = min(ml_risk + behavior_risk, 100)

        result = "Fraud" if final_risk > 60 else "Safe"

        # 🚨 Alert system
        alert = True if final_risk > 75 else False

        # 🧠 AI explanation
        ai_explanation = get_ai_explanation(
            amount, time, location, final_risk, result
        )

        # Save to DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO transactions (user_id, amount, time, location, result, risk_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, amount, time, location, result, final_risk))

        conn.commit()
        conn.close()

        return jsonify({
            "result": result,
            "risk_score": final_risk,
            "behavior_risk": behavior_risk,
            "alert": alert,
            "ai_explanation": ai_explanation
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
            "risk_score": r[3]
        }
        for r in rows
    ])

# -------------------------------
# Run
# -------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))