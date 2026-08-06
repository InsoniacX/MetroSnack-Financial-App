import bcrypt
from db.connection import fetch_all, fetch_one, execute

def get_all_users():
    return fetch_all("SELECT id, username, nama_lengkap, role, aktif FROM users ORDER BY id")

def username_exists(username):
    row = fetch_one("SELECT id FROM users WHERE username=%s", (username, ))
    return row is not None

def create_user(username, password, nama_lengkap, role):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return execute(
        "INSERT INTO users (username, password_hash, nama_lengkap, role, aktif) VALUES (%s,%s,%s,%s,TRUE) RETURNING id",
        (username, password_hash, nama_lengkap, role),
        returning=True
    )

def update_user(user_id, nama_lengkap, role):
    execute("UPDATE users SET nama_lengkap=%s, role=%s, WHERE id=%s", (nama_lengkap, role, user_id))

def reset_password(user_id, new_password):
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    execute("UPDATE users SET password_hash=%s WHERE id=%s", (password_hash, user_id))

def set_aktif(user_id, aktif):
    execute("UPDATE users SET aktif=%s WHERE id=%s", (aktif, user_id))

def delete_user(user_id):
    execute("DELETE FROM users WHERE id=%s", (user_id,))