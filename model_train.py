import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import joblib
import os


df = pd.read_csv("data/diabetic_data.csv")


df = df[['age','gender','time_in_hospital','number_inpatient','number_emergency','number_diagnoses','readmitted']]
df['age'] = df['age'].str.extract('(\d+)').astype(int)
df = df[df['gender'] != 'Unknown/Invalid']
df['gender'] = df['gender'].map({'Male':1,'Female':0})
df['readmitted'] = df['readmitted'].apply(lambda x: 0 if x == 'NO' else 1)


X = df.drop('readmitted', axis=1)
y = df['readmitted']


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)


os.makedirs("backend/model", exist_ok=True)
joblib.dump(model, "backend/model/readmission_model.pkl")
print("Model trained & saved")