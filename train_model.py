import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle

# Load data
data = pd.read_csv('data/transactions.csv')

X = data[['amount', 'time', 'location']]
y = data['fraud']

# Train/Test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Model (improved)
model = RandomForestClassifier(n_estimators=100)

model.fit(X_train, y_train)

# Test accuracy
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("Model Accuracy:", accuracy)

# Save model
with open('model/model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Model trained and saved!")