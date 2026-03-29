import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "database.db"


def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        unique_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS id_counter (
        role TEXT PRIMARY KEY,
        last_number INTEGER
    )""")

    cur.execute("INSERT OR IGNORE INTO id_counter VALUES ('doctor', 0)")
    cur.execute("INSERT OR IGNORE INTO id_counter VALUES ('patient', 0)")
    cur.execute("INSERT OR IGNORE INTO id_counter VALUES ('hospital', 0)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        risk TEXT,
        probability REAL,
        care_plan TEXT,
        created_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        FOREIGN KEY (patient_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS discharge_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        status TEXT DEFAULT 'PENDING',
        requested_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        reviewed_by TEXT,
        reviewed_at DATETIME,
        remarks TEXT DEFAULT NULL,
        acknowledged INTEGER DEFAULT 0,
        FOREIGN KEY (patient_id) REFERENCES users(unique_id),
        FOREIGN KEY (reviewed_by) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS symptoms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        fever TEXT,
        pain_level INTEGER,
        breathing TEXT,
        notes TEXT,
        submitted_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        is_flagged INTEGER DEFAULT 0,
        FOREIGN KEY (patient_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        doctor_id TEXT,
        appointment_date TEXT,
        appointment_time TEXT,
        reason TEXT,
        status TEXT DEFAULT 'SCHEDULED',
        created_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        FOREIGN KEY (patient_id) REFERENCES users(unique_id),
        FOREIGN KEY (doctor_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        doctor_id TEXT,
        medicine_name TEXT,
        dosage TEXT,
        frequency TEXT,
        duration TEXT,
        instructions TEXT,
        prescribed_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        FOREIGN KEY (patient_id) REFERENCES users(unique_id),
        FOREIGN KEY (doctor_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        FOREIGN KEY (user_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vital_signs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        blood_pressure TEXT,
        heart_rate INTEGER,
        temperature REAL,
        blood_sugar REAL,
        recorded_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        is_abnormal INTEGER DEFAULT 0,
        FOREIGN KEY (patient_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id TEXT,
        receiver_id TEXT,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        sent_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        FOREIGN KEY (sender_id) REFERENCES users(unique_id),
        FOREIGN KEY (receiver_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        rating INTEGER,
        comments TEXT,
        submitted_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        FOREIGN KEY (patient_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action TEXT,
        details TEXT,
        logged_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes'))
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sos_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        message TEXT,
        triggered_at DATETIME DEFAULT (datetime('now','+5 hours','+30 minutes')),
        is_resolved INTEGER DEFAULT 0,
        FOREIGN KEY (patient_id) REFERENCES users(unique_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        message    TEXT NOT NULL,
        response   TEXT NOT NULL,
        timestamp  TEXT NOT NULL
    )""")

    # Safe column additions for existing databases
    safe_alters = [
        "ALTER TABLE discharge_requests ADD COLUMN remarks TEXT DEFAULT NULL",
        "ALTER TABLE discharge_requests ADD COLUMN acknowledged INTEGER DEFAULT 0",
    ]
    for sql in safe_alters:
        try:
            cur.execute(sql)
            db.commit()
        except sqlite3.OperationalError:
            pass

    db.commit()
    db.close()


# ================= GENERATE UNIQUE ID =================
def generate_unique_id(role):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT last_number FROM id_counter WHERE role=?", (role,))
    last_number = cur.fetchone()[0] + 1
    prefix = "DOC" if role == "doctor" else "PAT" if role == "patient" else "HOS"
    unique_id = f"{prefix}-{last_number:04d}"
    cur.execute("UPDATE id_counter SET last_number=? WHERE role=?", (last_number, role))
    db.commit()
    db.close()
    return unique_id


# ================= CREATE USER =================
def create_user(name, email, password, role):
    db = get_db()
    cur = db.cursor()
    unique_id = generate_unique_id(role)
    try:
        cur.execute("""
        INSERT INTO users (unique_id, name, email, password, role)
        VALUES (?, ?, ?, ?, ?)
        """, (unique_id, name, email, password, role))
        db.commit()
        return unique_id
    except sqlite3.IntegrityError:
        return None
    finally:
        db.close()


# ================= LOGIN =================
def get_user_for_login(unique_id, password):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT role, name FROM users WHERE unique_id=? AND password=?",
                (unique_id, password))
    user = cur.fetchone()
    db.close()
    return user


# ================= AUDIT LOG =================
def log_action(user_id, action, details=""):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO audit_log (user_id, action, details)
    VALUES (?, ?, ?)
    """, (user_id, action, details))
    db.commit()
    db.close()


def get_audit_log():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT a.id, a.user_id, u.name, u.role, a.action, a.details, a.logged_at
    FROM audit_log a
    LEFT JOIN users u ON a.user_id = u.unique_id
    ORDER BY a.logged_at DESC
    LIMIT 200
    """)
    data = cur.fetchall()
    db.close()
    return data


# ================= PREDICTIONS =================
def save_prediction(patient_id, risk, probability, care_plan):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO predictions (patient_id, risk, probability, care_plan, created_at)
    VALUES (?, ?, ?, ?, datetime('now','+5 hours','+30 minutes'))
    """, (patient_id, risk, probability, care_plan))
    db.commit()
    db.close()


def get_latest_prediction(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT risk, probability, care_plan, created_at FROM predictions
    WHERE patient_id=? ORDER BY created_at DESC LIMIT 1
    """, (patient_id,))
    data = cur.fetchone()
    db.close()
    return data


def get_patient_predictions(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT risk, probability, created_at FROM predictions
    WHERE patient_id=? ORDER BY created_at ASC
    """, (patient_id,))
    data = cur.fetchall()
    db.close()
    return data


def get_all_predictions():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT p.id, p.patient_id, u.name, p.risk, p.probability, p.created_at
    FROM predictions p JOIN users u ON p.patient_id=u.unique_id
    ORDER BY p.created_at DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


# ================= DISCHARGE =================
def request_discharge(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO discharge_requests (patient_id, requested_at)
    VALUES (?, datetime('now','+5 hours','+30 minutes'))
    """, (patient_id,))
    db.commit()
    db.close()


def get_discharge_status(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT status, requested_at, reviewed_at, remarks, acknowledged
    FROM discharge_requests WHERE patient_id=?
    ORDER BY requested_at DESC LIMIT 1
    """, (patient_id,))
    data = cur.fetchone()
    db.close()
    return data


def acknowledge_care_plan(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    UPDATE discharge_requests SET acknowledged=1
    WHERE patient_id=? AND id=(SELECT MAX(id) FROM discharge_requests WHERE patient_id=?)
    """, (patient_id, patient_id))
    db.commit()
    db.close()


def get_pending_discharges():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT d.id, u.unique_id, u.name, d.requested_at, p.risk
    FROM discharge_requests d
    JOIN users u ON d.patient_id=u.unique_id
    LEFT JOIN (
        SELECT patient_id, risk FROM predictions
        WHERE id IN (SELECT MAX(id) FROM predictions GROUP BY patient_id)
    ) p ON p.patient_id=d.patient_id
    WHERE d.status='PENDING' ORDER BY d.requested_at DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


def get_all_discharge_history():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT d.id, u.unique_id, u.name, d.requested_at, d.status,
           d.reviewed_by, d.reviewed_at, d.remarks, p.risk
    FROM discharge_requests d
    JOIN users u ON d.patient_id=u.unique_id
    LEFT JOIN (
        SELECT patient_id, risk FROM predictions
        WHERE id IN (SELECT MAX(id) FROM predictions GROUP BY patient_id)
    ) p ON p.patient_id=d.patient_id
    ORDER BY d.requested_at DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


def update_discharge(request_id, status, doctor_id, remarks=None):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    UPDATE discharge_requests
    SET status=?, reviewed_by=?,
        reviewed_at=datetime('now','+5 hours','+30 minutes'), remarks=?
    WHERE id=?
    """, (status, doctor_id, remarks, request_id))
    db.commit()
    db.close()


# ================= USERS =================
def get_patient_email(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT name, email FROM users WHERE unique_id=?", (patient_id,))
    data = cur.fetchone()
    db.close()
    return data


def get_all_patients():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT unique_id, name, email FROM users WHERE role='patient'")
    data = cur.fetchall()
    db.close()
    return data


# ================= FORGOT PASSWORD FUNCTIONS =================

def get_user_by_email(email):
    """
    Returns (unique_id, name) for the given email address.
    Returns None if email is not found.
    Used by forgot_password route in app.py
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT unique_id, name FROM users WHERE email = ?", (email,)
    )
    row = cur.fetchone()
    db.close()
    return row  # returns (uid, name) or None


def update_user_password(unique_id, new_password):
    """
    Updates the password for the given user.
    Uses werkzeug's generate_password_hash (same as auth.py) so that
    login_user / check_password_hash can verify it correctly after a reset.
    """
    hashed = generate_password_hash(new_password)   # ← FIX: was hashlib.sha256
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE users SET password = ? WHERE unique_id = ?",
        (hashed, unique_id)
    )
    db.commit()
    db.close()
    return True


# ================= PROFILE FUNCTIONS =================

def get_user_profile(unique_id):
    """
    Returns user profile as a dictionary.
    Used by profile route in app.py
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT unique_id, name, email, role FROM users WHERE unique_id = ?",
        (unique_id,)
    )
    row = cur.fetchone()
    db.close()
    if row:
        return {
            "unique_id": row[0],
            "name":      row[1],
            "email":     row[2],
            "role":      row[3]
        }
    return None


def update_user_profile(unique_id, name, email, password=None):
    """
    Updates user profile (name, email, and optionally password).
    Returns True on success, False if email is already taken by another user.
    Uses werkzeug's generate_password_hash (same as auth.py) so that
    login_user / check_password_hash can verify it correctly after a profile update.
    """
    db  = get_db()
    cur = db.cursor()

    # Check if email is already used by another user
    cur.execute(
        "SELECT unique_id FROM users WHERE email = ? AND unique_id != ?",
        (email, unique_id)
    )
    if cur.fetchone():
        db.close()
        return False  # Email already taken

    if password:
        hashed = generate_password_hash(password)   # ← FIX: was hashlib.sha256
        cur.execute(
            "UPDATE users SET name=?, email=?, password=? WHERE unique_id=?",
            (name, email, hashed, unique_id)
        )
    else:
        cur.execute(
            "UPDATE users SET name=?, email=? WHERE unique_id=?",
            (name, email, unique_id)
        )

    db.commit()
    db.close()
    return True


# ================= SYMPTOMS =================
def save_symptom(patient_id, fever, pain_level, breathing, notes):
    is_flagged = 1 if (fever == "Yes" or int(pain_level) >= 7
                       or breathing == "Difficulty") else 0
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO symptoms (patient_id, fever, pain_level, breathing,
                          notes, submitted_at, is_flagged)
    VALUES (?, ?, ?, ?, ?, datetime('now','+5 hours','+30 minutes'), ?)
    """, (patient_id, fever, pain_level, breathing, notes, is_flagged))
    db.commit()
    db.close()
    return is_flagged


def get_all_symptoms():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT s.id, s.patient_id, u.name, s.fever, s.pain_level,
           s.breathing, s.notes, s.submitted_at, s.is_flagged
    FROM symptoms s JOIN users u ON s.patient_id=u.unique_id
    ORDER BY s.is_flagged DESC, s.submitted_at DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


def get_flagged_symptom_count():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM symptoms WHERE is_flagged=1")
    count = cur.fetchone()[0]
    db.close()
    return count


# ================= APPOINTMENTS =================
def schedule_appointment(patient_id, doctor_id, date, time, reason):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO appointments (patient_id, doctor_id,
                              appointment_date, appointment_time, reason)
    VALUES (?, ?, ?, ?, ?)
    """, (patient_id, doctor_id, date, time, reason))
    db.commit()
    db.close()


def get_patient_appointments(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT a.id, a.appointment_date, a.appointment_time,
           a.reason, a.status, u.name
    FROM appointments a JOIN users u ON a.doctor_id=u.unique_id
    WHERE a.patient_id=? ORDER BY a.appointment_date DESC
    """, (patient_id,))
    data = cur.fetchall()
    db.close()
    return data


def get_all_appointments():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT a.id, u.unique_id, u.name, a.appointment_date,
           a.appointment_time, a.reason, a.status
    FROM appointments a JOIN users u ON a.patient_id=u.unique_id
    ORDER BY a.appointment_date DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


# ================= MEDICATIONS =================
def prescribe_medication(patient_id, doctor_id, medicine_name,
                         dosage, frequency, duration, instructions):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO medications (patient_id, doctor_id, medicine_name,
                             dosage, frequency, duration, instructions)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (patient_id, doctor_id, medicine_name,
          dosage, frequency, duration, instructions))
    db.commit()
    db.close()


def get_patient_medications(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT m.id, m.medicine_name, m.dosage, m.frequency,
           m.duration, m.instructions, m.prescribed_at, u.name
    FROM medications m JOIN users u ON m.doctor_id=u.unique_id
    WHERE m.patient_id=? ORDER BY m.prescribed_at DESC
    """, (patient_id,))
    data = cur.fetchall()
    db.close()
    return data


def get_all_medications():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT m.id, u.unique_id, u.name, m.medicine_name,
           m.dosage, m.frequency, m.duration, m.prescribed_at
    FROM medications m JOIN users u ON m.patient_id=u.unique_id
    ORDER BY m.prescribed_at DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


# ================= NOTIFICATIONS =================
def add_notification(user_id, message):
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                (user_id, message))
    db.commit()
    db.close()


def get_notifications(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT id, message, is_read, created_at FROM notifications
    WHERE user_id=? ORDER BY created_at DESC LIMIT 20
    """, (user_id,))
    data = cur.fetchall()
    db.close()
    return data


def mark_notifications_read(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
    db.commit()
    db.close()


def get_unread_count(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
                (user_id,))
    count = cur.fetchone()[0]
    db.close()
    return count


# ================= ANALYTICS =================
def get_analytics():
    db = get_db()
    cur = db.cursor()
    stats = {}

    for key, sql in [
        ("total_patients",    "SELECT COUNT(*) FROM users WHERE role='patient'"),
        ("total_predictions", "SELECT COUNT(*) FROM predictions"),
        ("high_risk",         "SELECT COUNT(*) FROM predictions WHERE risk='High'"),
        ("medium_risk",       "SELECT COUNT(*) FROM predictions WHERE risk='Medium'"),
        ("low_risk",          "SELECT COUNT(*) FROM predictions WHERE risk='Low'"),
        ("approved",          "SELECT COUNT(*) FROM discharge_requests WHERE status='APPROVED'"),
        ("rejected",          "SELECT COUNT(*) FROM discharge_requests WHERE status='REJECTED'"),
        ("pending",           "SELECT COUNT(*) FROM discharge_requests WHERE status='PENDING'"),
        ("flagged_symptoms",  "SELECT COUNT(*) FROM symptoms WHERE is_flagged=1"),
        ("total_sos",         "SELECT COUNT(*) FROM sos_alerts"),
        ("total_messages",    "SELECT COUNT(*) FROM messages"),
    ]:
        cur.execute(sql)
        stats[key] = cur.fetchone()[0]

    db.close()
    return stats


# ================= VITAL SIGNS =================
def save_vital_signs(patient_id, blood_pressure, heart_rate,
                     temperature, blood_sugar):
    is_abnormal = 0
    try:
        hr   = int(heart_rate)
        temp = float(temperature)
        bs   = float(blood_sugar)
        if hr < 50 or hr > 120:        is_abnormal = 1
        if temp > 38.5 or temp < 35.0: is_abnormal = 1
        if bs > 200 or bs < 60:        is_abnormal = 1
    except Exception:
        pass

    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO vital_signs (patient_id, blood_pressure, heart_rate,
                             temperature, blood_sugar, recorded_at, is_abnormal)
    VALUES (?, ?, ?, ?, ?, datetime('now','+5 hours','+30 minutes'), ?)
    """, (patient_id, blood_pressure, heart_rate,
          temperature, blood_sugar, is_abnormal))
    db.commit()
    db.close()
    return is_abnormal


def get_patient_vitals(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT id, blood_pressure, heart_rate, temperature,
           blood_sugar, recorded_at, is_abnormal
    FROM vital_signs WHERE patient_id=?
    ORDER BY recorded_at DESC LIMIT 30
    """, (patient_id,))
    data = cur.fetchall()
    db.close()
    return data


def get_all_vitals():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT v.id, v.patient_id, u.name, v.blood_pressure, v.heart_rate,
           v.temperature, v.blood_sugar, v.recorded_at, v.is_abnormal
    FROM vital_signs v JOIN users u ON v.patient_id=u.unique_id
    ORDER BY v.is_abnormal DESC, v.recorded_at DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


# ================= MESSAGES =================
def send_message(sender_id, receiver_id, message):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO messages (sender_id, receiver_id, message)
    VALUES (?, ?, ?)
    """, (sender_id, receiver_id, message))
    db.commit()
    db.close()


def get_messages_for_patient(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT m.id, u.name, m.message, m.is_read, m.sent_at
    FROM messages m JOIN users u ON m.sender_id=u.unique_id
    WHERE m.receiver_id=?
    ORDER BY m.sent_at DESC
    """, (patient_id,))
    data = cur.fetchall()
    db.close()
    return data


def get_unread_message_count(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT COUNT(*) FROM messages
    WHERE receiver_id=? AND is_read=0
    """, (patient_id,))
    count = cur.fetchone()[0]
    db.close()
    return count


def mark_messages_read(patient_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE messages SET is_read=1 WHERE receiver_id=?", (patient_id,))
    db.commit()
    db.close()


# ================= SOS ALERTS =================
def trigger_sos(patient_id, message):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO sos_alerts (patient_id, message)
    VALUES (?, ?)
    """, (patient_id, message))
    db.commit()
    db.close()


def get_all_sos_alerts():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT s.id, s.patient_id, u.name, s.message,
           s.triggered_at, s.is_resolved
    FROM sos_alerts s JOIN users u ON s.patient_id=u.unique_id
    ORDER BY s.is_resolved ASC, s.triggered_at DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


def resolve_sos(sos_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE sos_alerts SET is_resolved=1 WHERE id=?", (sos_id,))
    db.commit()
    db.close()


def get_unresolved_sos_count():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM sos_alerts WHERE is_resolved=0")
    count = cur.fetchone()[0]
    db.close()
    return count


# ================= FEEDBACK =================
def save_feedback(patient_id, rating, comments):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    INSERT INTO feedback (patient_id, rating, comments)
    VALUES (?, ?, ?)
    """, (patient_id, rating, comments))
    db.commit()
    db.close()


def get_all_feedback():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT f.id, u.name, f.rating, f.comments, f.submitted_at
    FROM feedback f JOIN users u ON f.patient_id=u.unique_id
    ORDER BY f.submitted_at DESC
    """)
    data = cur.fetchall()
    db.close()
    return data


def get_patient_report(patient_id):
    """Full patient report for doctor view."""
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT unique_id, name, email, role FROM users WHERE unique_id=?",
                (patient_id,))
    patient_info = cur.fetchone()

    cur.execute("""
    SELECT risk, probability, care_plan, created_at FROM predictions
    WHERE patient_id=? ORDER BY created_at DESC
    """, (patient_id,))
    predictions = cur.fetchall()

    cur.execute("""
    SELECT status, requested_at, reviewed_at, remarks FROM discharge_requests
    WHERE patient_id=? ORDER BY requested_at DESC
    """, (patient_id,))
    discharges = cur.fetchall()

    cur.execute("""
    SELECT medicine_name, dosage, frequency, duration, prescribed_at
    FROM medications WHERE patient_id=? ORDER BY prescribed_at DESC
    """, (patient_id,))
    medications = cur.fetchall()

    cur.execute("""
    SELECT appointment_date, appointment_time, reason, status
    FROM appointments WHERE patient_id=? ORDER BY appointment_date DESC
    """, (patient_id,))
    appointments = cur.fetchall()

    cur.execute("""
    SELECT fever, pain_level, breathing, notes, submitted_at, is_flagged
    FROM symptoms WHERE patient_id=? ORDER BY submitted_at DESC
    """, (patient_id,))
    symptoms = cur.fetchall()

    cur.execute("""
    SELECT blood_pressure, heart_rate, temperature, blood_sugar, recorded_at
    FROM vital_signs WHERE patient_id=? ORDER BY recorded_at DESC
    """, (patient_id,))
    vitals = cur.fetchall()

    db.close()

    info_dict = {}
    if patient_info:
        info_dict = {
            "unique_id": patient_info[0],
            "name":      patient_info[1],
            "email":     patient_info[2],
            "role":      patient_info[3],
        }

    return {
        "info":         patient_info,
        "name":         info_dict.get("name", "—"),
        "email":        info_dict.get("email", "—"),
        "role":         info_dict.get("role", "—"),
        "predictions":  predictions,
        "discharges":   discharges,
        "medications":  medications,
        "appointments": appointments,
        "symptoms":     symptoms,
        "vitals":       vitals
    }


# ================= COMPATIBILITY =================
def update_discharge_status(request_id, action, doctor_id):
    status = "APPROVED" if action == "approve" else "REJECTED"
    update_discharge(request_id, status, doctor_id)