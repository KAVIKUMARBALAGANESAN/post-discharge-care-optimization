from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db


# ================= GENERATE UNIQUE ID =================
def generate_unique_id(role):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT last_number FROM id_counter WHERE role = ?", (role,))
    row = cur.fetchone()

    if not row:
        db.close()
        return None

    last_number = row[0] + 1

    prefix = "DOC" if role == "doctor" else "PAT"
    unique_id = f"{prefix}-{last_number:04d}"

    cur.execute(
        "UPDATE id_counter SET last_number = ? WHERE role = ?",
        (last_number, role)
    )

    db.commit()
    db.close()
    return unique_id


# ================= REGISTER USER =================
def register_user(name, email, password, role):
    db = get_db()
    cur = db.cursor()

    # Check if email already exists
    cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    if cur.fetchone():
        db.close()
        return None

    unique_id = generate_unique_id(role)
    if not unique_id:
        db.close()
        return None

    hashed_password = generate_password_hash(password)

    cur.execute("""
        INSERT INTO users (unique_id, name, email, password, role)
        VALUES (?, ?, ?, ?, ?)
    """, (unique_id, name, email, hashed_password, role))

    db.commit()
    db.close()
    return unique_id


# ================= LOGIN USER =================
def login_user(unique_id, password):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT password, role, name
        FROM users
        WHERE unique_id = ?
    """, (unique_id,))

    user = cur.fetchone()
    db.close()

    if user and check_password_hash(user[0], password):
        # return role, name (same as your existing app.py expects)
        return user[1], user[2]

    return None


# ================= GET USER ROLE =================
def get_user_role(unique_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT role FROM users WHERE unique_id = ?
    """, (unique_id,))

    role = cur.fetchone()
    db.close()

    return role[0] if role else None


# ================= GET USER DETAILS =================
def get_user_details(unique_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT unique_id, name, email, role
        FROM users
        WHERE unique_id = ?
    """, (unique_id,))

    user = cur.fetchone()
    db.close()

    return user