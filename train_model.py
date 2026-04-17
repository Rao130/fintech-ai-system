import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
import pickle

# Load data
data = pd.read_csv('data/transactions.csv')

# 🔥 FIX: location ko encode karo
le = LabelEncoder()
data['location'] = le.fit_transform(data['location'])

# Features
X = data[['amount', 'time', 'location']]
y = data['fraud']

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Model
model = RandomForestClassifier(n_estimators=150)
model.fit(X_train, y_train)

# Accuracy
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("Model Accuracy:", accuracy)

# 🔥 SAVE BOTH model + encoder
with open('model/model.pkl', 'wb') as f:
    pickle.dump(model, f)

with open('model/encoder.pkl', 'wb') as f:
    pickle.dump(le, f)

print("Model + Encoder saved!")