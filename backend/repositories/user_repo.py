from database.connection import fetch_all, fetch_one, execute
from auth.security import hash_password


def get_all_users(cabang_id=None):
    if cabang_id is None:
        return fetch_all("""
            SELECT u.id, u.username, u.nama_lengkap, u.role, u.aktif, u.cabang_id, c.nama_cabang
            FROM users u
            LEFT JOIN cabang c ON c.id = u.cabang_id
            ORDER BY u.id
        """)
    return fetch_all("""
        SELECT u.id, u.username, u.nama_lengkap, u.role, u.aktif, u.cabang_id, c.nama_cabang
        FROM users u
        LEFT JOIN cabang c ON c.id = u.cabang_id
        WHERE u.cabang_id = %s
        ORDER BY u.id
    """, (cabang_id,))


def username_exists(username):
    row = fetch_one("SELECT id FROM users WHERE username=%s", (username,))
    return row is not None


def create_user(username, password, nama_lengkap, role, cabang_id):
    password_hash = hash_password(password)
    return execute(
        "INSERT INTO users (username, password_hash, nama_lengkap, role, aktif, cabang_id) VALUES (%s,%s,%s,%s,TRUE,%s) RETURNING id",
        (username, password_hash, nama_lengkap, role, cabang_id),
        returning=True,
    )


def update_user(user_id, nama_lengkap, role):
    execute("UPDATE users SET nama_lengkap=%s, role=%s WHERE id=%s", (nama_lengkap, role, user_id))


def get_user_header(user_id):
    return fetch_one(
        """
        SELECT id, username, role, cabang_id, aktif
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    )


def reset_password(user_id, new_password):
    password_hash = hash_password(new_password)
    execute("UPDATE users SET password_hash=%s WHERE id=%s", (password_hash, user_id))


def set_aktif(user_id, aktif):
    execute("UPDATE users SET aktif=%s WHERE id=%s", (aktif, user_id))


def delete_user(user_id):
    execute("DELETE FROM users WHERE id=%s", (user_id,))
