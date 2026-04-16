from flask import Flask, render_template, request, jsonify
import pickle
import os

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
    return jsonify({"result": result, "risk_score": risk_score})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))