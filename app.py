from flask import Flask, render_template, request, jsonify
import pickle
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

model = pickle.load(open('model/model.pkl', 'rb'))

@app.route('/check_transaction', methods=['POST'])
def check_transaction():
    data = request.json
    
    amount = data.get("amount")
    time = data.get("time")
    location = data.get("location")

    prediction = model.predict([[amount, time, location]])[0]

    result = "Fraud" if prediction == 1 else "Safe"

    return jsonify({"result": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

