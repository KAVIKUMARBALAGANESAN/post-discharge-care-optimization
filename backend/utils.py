def get_care_plan(risk):
    if risk == "High":
        return "Doctor follow-up within 48 hours, daily vitals monitoring"
    elif risk == "Medium":
        return "Weekly monitoring and medication reminders"
    else:
        return "Normal follow-up and healthy lifestyle"
