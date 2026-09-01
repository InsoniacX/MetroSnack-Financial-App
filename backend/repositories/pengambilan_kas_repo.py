from database.connection import execute, fetch_all, fetch_one


_TABLE_BY_SUMBER = {
    "pabrik": "pengambilan_pabrik",
    "balaraja": "pengambilan_balaraja",
}


def _get_table(sumber):
    try:
        return _TABLE_BY_SUMBER[sumber]
    except KeyError as exc:
        raise ValueError(
            "Sumber pengambilan kas tidak valid"
        ) from exc


def get_pengambilan_kas(
    sumber,
    cabang_id,
    tanggal_awal=None,
    tanggal_akhir=None,
    limit=200,
):
    table = _get_table(sumber)

    query = f"""
        SELECT
            p.id,
            p.cabang_id,
            p.tanggal,
            p.keterangan,
            p.nominal,
            p.user_id,
            u.username,
            p.created_at,
            p.updated_at
        FROM {table} p
        JOIN users u
          ON u.id = p.user_id
        WHERE p.cabang_id = %s
    """
    params = [cabang_id]

    if tanggal_awal is not None:
        query += " AND p.tanggal >= %s"
        params.append(tanggal_awal)

    if tanggal_akhir is not None:
        query += " AND p.tanggal <= %s"
        params.append(tanggal_akhir)

    query += " ORDER BY p.tanggal DESC, p.id DESC LIMIT %s"
    params.append(limit)

    return fetch_all(query, tuple(params))


def get_pengambilan_kas_header(sumber, entry_id):
    table = _get_table(sumber)

    return fetch_one(
        f"""
        SELECT id, cabang_id
        FROM {table}
        WHERE id = %s
        """,
        (entry_id,),
    )


def create_pengambilan_kas(
    sumber,
    cabang_id,
    tanggal,
    keterangan,
    nominal,
    user_id,
):
    table = _get_table(sumber)

    return execute(
        f"""
        INSERT INTO {table} (
            cabang_id,
            tanggal,
            keterangan,
            nominal,
            user_id
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            cabang_id,
            tanggal,
            keterangan,
            nominal,
            user_id,
        ),
        returning=True,
    )


def update_pengambilan_kas(
    sumber,
    entry_id,
    tanggal,
    keterangan,
    nominal,
):
    table = _get_table(sumber)

    execute(
        f"""
        UPDATE {table}
        SET
            tanggal = %s,
            keterangan = %s,
            nominal = %s
        WHERE id = %s
        """,
        (
            tanggal,
            keterangan,
            nominal,
            entry_id,
        ),
    )


def delete_pengambilan_kas(sumber, entry_id):
    table = _get_table(sumber)

    execute(
        f"DELETE FROM {table} WHERE id = %s",
        (entry_id,),
    )


def get_pengambilan_kas_summary(
    sumber,
    cabang_id,
    tanggal_awal=None,
    tanggal_akhir=None,
):
    table = _get_table(sumber)

    query = f"""
        SELECT
            COUNT(*),
            COALESCE(SUM(nominal), 0)
        FROM {table}
        WHERE cabang_id = %s
    """
    params = [cabang_id]

    if tanggal_awal is not None:
        query += " AND tanggal >= %s"
        params.append(tanggal_awal)

    if tanggal_akhir is not None:
        query += " AND tanggal <= %s"
        params.append(tanggal_akhir)

    total_data, total_nominal = fetch_one(
        query,
        tuple(params),
    )

    return {
        "sumber": sumber,
        "total_data": total_data,
        "total_nominal": total_nominal,
    }