from database.connection import execute, fetch_all, fetch_one


def get_supir_kenek(cabang_id, active_only=True):
    query = """
        SELECT id, cabang_id, nama, aktif, created_at, updated_at
        FROM supir_kenek
        WHERE cabang_id = %s
    """
    params = [cabang_id]

    if active_only:
        query += " AND aktif = TRUE"

    query += " ORDER BY aktif DESC, nama ASC"

    return fetch_all(query, tuple(params))


def get_supir_kenek_header(supir_kenek_id):
    return fetch_one(
        """
        SELECT id, cabang_id, nama, aktif
        FROM supir_kenek
        WHERE id = %s
        """,
        (supir_kenek_id,),
    )


def name_exists(cabang_id, nama, exclude_id=None):
    query = """
        SELECT id
        FROM supir_kenek
        WHERE cabang_id = %s
            AND LOWER(nama) = LOWER(%s)
    """
    params = [cabang_id, nama]

    if exclude_id is not None:
        query += " AND id <> %s"
        params.append(exclude_id)

    return fetch_one(query, tuple(params)) is not None


def create_supir_kenek(cabang_id, nama):
    return execute(
        """
        INSERT INTO supir_kenek (cabang_id, nama)
        VALUES (%s, %s)
        RETURNING id
        """,
        (cabang_id, nama),
        returning=True,
    )


def update_supir_kenek(supir_kenek_id, nama):
    execute(
        """
        UPDATE supir_kenek
        SET nama = %s
        WHERE id = %s
        """,
        (nama, supir_kenek_id),
    )


def set_supir_kenek_aktif(supir_kenek_id, aktif):
    execute(
        """
        UPDATE supir_kenek
        SET aktif = %s
        WHERE id = %s
        """,
        (aktif, supir_kenek_id),
    )