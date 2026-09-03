from database.connection import execute, fetch_all, fetch_one


def get_operasional_mobil(
    cabang_id,
    tanggal_awal=None,
    tanggal_akhir=None,
    limit=200,
):
    query = """
        SELECT
            o.id,
            o.cabang_id,
            o.tanggal,
            o.supir_id,
            supir.nama AS nama_supir,
            o.kenek_id,
            kenek.nama AS nama_kenek,
            o.uang_jalan,
            o.keterangan,
            o.user_id,
            u.username,
            o.created_at,
            o.updated_at
        FROM operasional_mobil o
        JOIN supir_kenek supir
          ON supir.id = o.supir_id
        LEFT JOIN supir_kenek kenek
          ON kenek.id = o.kenek_id
        JOIN users u
          ON u.id = o.user_id
        WHERE o.cabang_id = %s
    """
    params = [cabang_id]

    if tanggal_awal is not None:
        query += " AND o.tanggal >= %s"
        params.append(tanggal_awal)

    if tanggal_akhir is not None:
        query += " AND o.tanggal <= %s"
        params.append(tanggal_akhir)

    query += " ORDER BY o.tanggal DESC, o.id DESC LIMIT %s"
    params.append(limit)

    return fetch_all(query, tuple(params))


def get_operasional_mobil_header(operasional_id):
    return fetch_one(
        """
        SELECT id, cabang_id, supir_id, kenek_id
        FROM operasional_mobil
        WHERE id = %s
        """,
        (operasional_id,),
    )


def create_operasional_mobil(
    cabang_id,
    tanggal,
    supir_id,
    kenek_id,
    uang_jalan,
    keterangan,
    user_id,
):
    return execute(
        """
        INSERT INTO operasional_mobil (
            cabang_id,
            tanggal,
            supir_id,
            kenek_id,
            uang_jalan,
            keterangan,
            user_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            cabang_id,
            tanggal,
            supir_id,
            kenek_id,
            uang_jalan,
            keterangan,
            user_id,
        ),
        returning=True,
    )


def update_operasional_mobil(
    operasional_id,
    tanggal,
    supir_id,
    kenek_id,
    uang_jalan,
    keterangan,
):
    execute(
        """
        UPDATE operasional_mobil
        SET
            tanggal = %s,
            supir_id = %s,
            kenek_id = %s,
            uang_jalan = %s,
            keterangan = %s
        WHERE id = %s
        """,
        (
            tanggal,
            supir_id,
            kenek_id,
            uang_jalan,
            keterangan,
            operasional_id,
        ),
    )


def delete_operasional_mobil(operasional_id):
    execute(
        "DELETE FROM operasional_mobil WHERE id = %s",
        (operasional_id,),
    )


def get_operasional_summary(
    cabang_id,
    tanggal_awal=None,
    tanggal_akhir=None,
):
    query = """
        SELECT
            COUNT(*),
            COALESCE(SUM(uang_jalan), 0)
        FROM operasional_mobil
        WHERE cabang_id = %s
    """
    params = [cabang_id]

    if tanggal_awal is not None:
        query += " AND tanggal >= %s"
        params.append(tanggal_awal)

    if tanggal_akhir is not None:
        query += " AND tanggal <= %s"
        params.append(tanggal_akhir)

    total_trip, total_uang_jalan = fetch_one(
        query,
        tuple(params),
    )

    return {
        "total_trip": total_trip,
        "total_uang_jalan": total_uang_jalan,
    }