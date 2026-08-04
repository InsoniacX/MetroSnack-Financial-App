import bcrypt
from db.connection import fetch_one

def authenticate_user(username, password):
    row = fetch_one(
        "SELECT id, username, password_hash, nama_lengkap, role, aktif FROM users WHERE username=%s",
        (username,),
    )
    if row is None:
        return None
    uid, uname, phash, role, aktif = row
    if not aktif:
        return None
    if bcrypt.checkpw(password.encode(), phash.encode()):
        return {
            "id" : uid,
            "username": uname,
            "role": role,
        }
    return None