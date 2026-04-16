from flask import Flask, render_template, request, jsonify
import pickle
import os
import requests

app = Flask(__name__)

# Load model
model = pickle.load(open(os.path.join('model', 'model.pkl'), 'rb'))

# Store history & user profiles
history = []
user_profiles = {}

# -------------------------------
# 🧠 Rule-based Reason
# -------------------------------
def generate_reason(amount, time, location, risk_score):
    reasons = []

    if amount > 5000:
        reasons.append("High transaction amount")

    if time < 6 or time > 22:
        reasons.append("Unusual transaction time")

    if location > 50:
        reasons.append("Suspicious location pattern")

    if risk_score > 80:
        reasons.append("Very high fraud probability")

    if not reasons:
        return "Transaction looks normal."

    return ", ".join(reasons)

# -------------------------------
# ⚡ Behavior AI
# -------------------------------
def calculate_behavior_risk(user_id, amount, time, location):
    profile = user_profiles.get(user_id)

    # New user
    if not profile:
        user_profiles[user_id] = {
            "avg_amount": amount,
            "avg_time": time,
            "avg_location": location,
            "count": 1
        }
        return 0

    # Deviation
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

    # Update profile (learning)
    profile["count"] += 1
    profile["avg_amount"] = (profile["avg_amount"] + amount) / 2
    profile["avg_time"] = (profile["avg_time"] + time) / 2
    profile["avg_location"] = (profile["avg_location"] + location) / 2

    return risk

# -------------------------------
# 🤖 AI Explanation (Ollama)
# -------------------------------
def get_ai_explanation(amount, time, location, risk_score):
    prompt = f"""
    Analyze this financial transaction:

    Amount: {amount}
    Time: {time}
    Location: {location}
    Risk Score: {risk_score}%

    Explain if this transaction is suspicious or safe.
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

        return response.json().get("response", "No AI response.")

    except:
        return "AI explanation not available (Ollama not running)."

# -------------------------------
# 🌐 Routes
# -------------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/check_transaction', methods=['POST'])
def check_transaction():
    try:
        data = request.json

        amount = float(data.get("amount", 0))
        time = float(data.get("time", 0))
        location = float(data.get("location", 0))
        user_id = data.get("user_id", "default_user")

        # ML prediction
        prediction = model.predict([[amount, time, location]])[0]
        probability = model.predict_proba([[amount, time, location]])[0][1]
        ml_risk = round(probability * 100, 2)

        # Behavior AI
        behavior_risk = calculate_behavior_risk(user_id, amount, time, location)

        # Final Risk
        final_risk = min(ml_risk + behavior_risk, 100)

        result = "Fraud" if final_risk > 60 else "Safe"

        # Reason + AI
        reason = generate_reason(amount, time, location, final_risk)
        ai_explanation = get_ai_explanation(amount, time, location, final_risk)

        # Save history
        history.append({
            "user_id": user_id,
            "amount": amount,
            "result": result,
            "risk_score": final_risk
        })

        return jsonify({
            "result": result,
            "risk_score": final_risk,
            "behavior_risk": behavior_risk,
            "reason": reason,
            "ai_explanation": ai_explanation
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(history)

# -------------------------------
# 🚀 Run
# -------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))