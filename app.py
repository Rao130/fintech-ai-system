from flask import Flask, render_template, request, jsonify
import pickle
import os
history = []
app = Flask(__name__)

# Load model safely
model = pickle.load(open(os.path.join('model', 'model.pkl'), 'rb'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/check_transaction', methods=['POST'])
def check_transaction():
    data = request.json
    
    amount = data.get("amount")
    time = data.get("time")
    location = data.get("location")

    prediction = model.predict([[amount, time, location]])[0]
    probability = model.predict_proba([[amount, time, location]])[0][1]
    result = "Fraud" if prediction == 1 else "Safe"
    risk_score = round(probability * 100, 2)
    history.append({"amount": amount, "time": time, "location": location, "result": result, "risk_score": risk_score})
    reason = generate_reason(amount, time, location, risk_score)
    return jsonify({"result": result, "risk_score": risk_score, "reason": reason})

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(history)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))