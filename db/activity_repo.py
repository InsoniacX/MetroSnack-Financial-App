from db.connection import fetch_all, execute

def log_activity(user_id, username, action, entity, entity_id, description=None, cabang_id=None):
    execute("""
        INSERT INTO activity_log (user_id, username, action, entity, entity_id, description, cabang_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (user_id, username, action, entity, entity_id, description, cabang_id))


def get_recent_activities(cabang_id=None, limit=200):
    if cabang_id is None:
        return fetch_all("""
            SELECT a.id, a.username, a.action, a.entity, a.entity_id, a.description, a.created_at, c.nama_cabang
            FROM activity_log a
            LEFT JOIN cabang c ON c.id = a.cabang_id
            ORDER BY a.created_at DESC
            LIMIT %s
        """, (limit,))
    return fetch_all("""
        SELECT a.id, a.username, a.action, a.entity, a.entity_id, a.description, a.created_at, c.nama_cabang
        FROM activity_log a
        LEFT JOIN cabang c ON c.id = a.cabang_id
        WHERE a.cabang_id = %s
        ORDER BY a.created_at DESC
        LIMIT %s
    """, (cabang_id, limit))