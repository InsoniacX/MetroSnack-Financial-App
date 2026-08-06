from db.connection import fetch_all, execute

def log_activity(user_id, username, action, entity, entity_id, description=None):
    execute(
        """
            INSERT INTO activity_log (user_id, username, action, entity, entity_id, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, username, action, entity, entity_id, description)
    )

def get_recent_activites(limit=200):
    return fetch_all(
        """
            SELECT id, username, action, entity, entity_id, description, created_at FROM activity_log
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit, )
    )

