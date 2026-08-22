"""
seed_test_data.py — jalankan SEKALI untuk mengisi database test dengan
1 cabang contoh + 1 user admin, supaya bisa langsung login & testing
lewat Swagger UI tanpa perlu tulis SQL manual atau hash password sendiri.

Cara pakai (dari folder backend, setelah venv aktif & .env sudah diisi):
    python seed_test_data.py

JANGAN jalankan ini ke database produksi — ini untuk database TEST saja.
"""
from database.connection import init_pool, fetch_one, execute
from auth.security import hash_password

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # WAJIB diganti setelah login pertama kali
KARYAWAN_USERNAME = "karyawan1"
KARYAWAN_PASSWORD = "karyawan123"  # WAJIB diganti setelah login pertama kali
CABANG_NAME = "Cabang Contoh"


def main():
    init_pool()

    row = fetch_one("SELECT id FROM cabang WHERE nama_cabang=%s", (CABANG_NAME,))
    if row:
        cabang_id = row[0]
        print(f"Cabang '{CABANG_NAME}' sudah ada (id={cabang_id}), pakai yang ini.")
    else:
        cabang_id = execute(
            "INSERT INTO cabang (nama_cabang, alamat) VALUES (%s,%s) RETURNING id",
            (CABANG_NAME, "Alamat contoh"), returning=True,
        )
        print(f"Cabang '{CABANG_NAME}' dibuat (id={cabang_id}).")

    row = fetch_one("SELECT id FROM users WHERE username=%s", (ADMIN_USERNAME,))
    if row:
        print(f"User '{ADMIN_USERNAME}' sudah ada, tidak dibuat ulang.")
    else:
        password_hash = hash_password(ADMIN_PASSWORD)
        execute(
            "INSERT INTO users (username, password_hash, nama_lengkap, role, aktif, cabang_id) "
            "VALUES (%s,%s,%s,%s,TRUE,%s)",
            (ADMIN_USERNAME, password_hash, "Admin Test", "admin", cabang_id),
        )
        print(f"User admin dibuat. Login pakai username='{ADMIN_USERNAME}' password='{ADMIN_PASSWORD}'.")

    # User kedua dengan role 'karyawan' -> untuk test isolasi cabang
    # (karyawan cuma boleh lihat data cabang_id miliknya sendiri).
    row = fetch_one("SELECT id FROM users WHERE username=%s", (KARYAWAN_USERNAME,))
    if row:
        print(f"User '{KARYAWAN_USERNAME}' sudah ada, tidak dibuat ulang.")
    else:
        password_hash = hash_password(KARYAWAN_PASSWORD)
        execute(
            "INSERT INTO users (username, password_hash, nama_lengkap, role, aktif, cabang_id) "
            "VALUES (%s,%s,%s,%s,TRUE,%s)",
            (KARYAWAN_USERNAME, password_hash, "Karyawan Test", "karyawan", cabang_id),
        )
        print(f"User karyawan dibuat. Login pakai username='{KARYAWAN_USERNAME}' password='{KARYAWAN_PASSWORD}'.")

    print("\nSelesai. Sekarang buka http://localhost:8000/docs dan login lewat POST /auth/login.")


if __name__ == "__main__":
    main()
