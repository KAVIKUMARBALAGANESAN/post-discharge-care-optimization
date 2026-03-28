import joblib
import pandas as pd

model = joblib.load("model/readmission_model.pkl")
print(type(model))


FEATURES = [
    "age",
    "gender",
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_diagnoses"
]

def predict_risk(features):
    df = pd.DataFrame([features], columns=FEATURES)
    prob = model.predict_proba(df)[0][1]

    if prob >= 0.7:
        return prob, "High"
    elif prob >= 0.4:
        return prob, "Medium"
    else:
        return prob, "Low"
