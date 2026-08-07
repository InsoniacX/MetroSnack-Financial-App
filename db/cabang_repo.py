from db.connection import execute, fetch_all, fetch_one

def get_active_cabang():
    return fetch_all("SELECT id, nama_cabang FROM cabang WHERE aktif = TRUE ORDER BY nama_cabang")

def get_all_cabang():
    return fetch_all(
        """
            SELECT c.id, c.nama_cabang, c.alamat, c.aktif,
                COUNT(DISTINCT u.id) AS total_user,
                COUNT(DISTINCT f.id) AS total_folder
            FROM cabang c
            LEFT JOIN users u ON u.cabang_id = c.id
            LEFT JOIN folder_bulan f ON f.cabang_id = c.id
            GROUP BY c.id
            ORDER BY c.nama_cabang
        """
    )

def create_cabang(nama_cabang, alamat):
    return execute(
        "INSERT INTO cabang (nama_cabang, alamat) VALUES (%s, %s) RETURNING id",
        (nama_cabang, alamat),
        returning=True,
    )

def update_cabang(cabang_id, nama_cabang, alamat):
    execute(
        "UPDATE cabang SET nama_cabang=%s, alamat=%s WHERE id=%s", 
        (nama_cabang, alamat, cabang_id)
    )

def set_cabang_aktif(cabang_id, aktif):
    execute(
        "UPDATE cabang SET aktif=%s WHERE id=%s",
        (aktif, cabang_id)
    )

def cabang_name_exist(nama_cabang, exclude_id=None):
    if exclude_id:
        row = fetch_one(
            "SELECT id FROM cabang WHERE nama_cabang=%s AND id != %s",
            (nama_cabang, exclude_id)
        )
    else:
        row = fetch_one(
            "SELECT id FROM cabang WHERE nama_cabang=%s", 
            (nama_cabang,)
        )
    return row is not None