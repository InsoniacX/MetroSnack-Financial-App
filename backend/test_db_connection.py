"""
test_db_connection.py
======================
Script standalone untuk test koneksi backend -> PostgreSQL VPS.

CARA PAKAI
----------
1. Taruh file ini di folder "backend/" (sejajar dengan main.py FastAPI Anda).
2. Pastikan .env sudah ada di folder yang sama (atau di root project),
   berisi minimal:

     DB_HOST=103.67.244.71
     DB_PORT=5432
     DB_NAME=metrosnack_financial
     DB_USER=admin_metrosnack
     DB_PASSWORD=isi_password_disini

   -- SESUAIKAN nama variabel di atas dengan yang Anda pakai di
   config.py/.env backend Anda saat ini kalau namanya beda (misal
   POSTGRES_HOST, PGHOST, dst). Cukup ubah bagian ENV_VAR_MAP di
   bawah, tidak perlu ubah logic lain.

3. Jalankan:
     python test_db_connection.py

   Atau override langsung lewat CLI tanpa .env, contoh:
     python test_db_connection.py --host 103.67.244.71 --port 5432 \
         --dbname metrosnack_financial --user admin_metrosnack --password xxxxx

DEPENDENSI
----------
  pip install psycopg2 python-dotenv --break-system-packages
  (python-dotenv opsional -- kalau tidak ada, script tetap jalan
  asalkan environment variable sudah di-set manual di OS/shell)
"""

import argparse
import os
import sys
import time

# --- Nama environment variable yang dipakai project ini -------------------
# Ubah value di kanan kalau nama variabel di .env backend Anda berbeda.
ENV_VAR_MAP = {
    "host": "DB_HOST",
    "port": "DB_PORT",
    "dbname": "DB_NAME",
    "user": "DB_USER",
    "password": "DB_PASSWORD",
}

# Tabel yang WAJIB ada kalau migration_002 & migration_003 sudah dijalankan.
# Dipakai untuk cek tambahan setelah koneksi berhasil -- boleh dihapus
# isinya kalau tidak perlu.
EXPECTED_TABLES = [
    "cabang",
    "users",
    "folder_bulan",
    "invoice",
    "transaksi_harian",
    "activity_log",
    "pendapatan_pengeluaran_harian",
    "supir_kenek",
    "operasional_mobil",
    "pengambilan_pabrik",
    "pengambilan_balaraja",
]

CONNECT_TIMEOUT_SECONDS = 8


def load_dotenv_if_available():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("[info] .env berhasil dimuat (python-dotenv).")
    except ImportError:
        print("[info] python-dotenv tidak terpasang -- lanjut pakai "
              "environment variable yang sudah di-set di OS/shell.")


def get_config_from_env():
    cfg = {}
    missing = []
    for key, env_name in ENV_VAR_MAP.items():
        value = os.environ.get(env_name)
        if value is None:
            missing.append(env_name)
        cfg[key] = value
    return cfg, missing


def parse_cli_overrides():
    parser = argparse.ArgumentParser(
        description="Test koneksi backend ke PostgreSQL VPS MetroSnack."
    )
    parser.add_argument("--host", help="Override DB_HOST")
    parser.add_argument("--port", help="Override DB_PORT")
    parser.add_argument("--dbname", help="Override DB_NAME")
    parser.add_argument("--user", help="Override DB_USER")
    parser.add_argument("--password", help="Override DB_PASSWORD")
    parser.add_argument(
        "--skip-table-check",
        action="store_true",
        help="Lewati pengecekan keberadaan tabel migration_002/003.",
    )
    return parser.parse_args()


def main():
    args = parse_cli_overrides()
    load_dotenv_if_available()
    cfg, missing = get_config_from_env()

    # CLI override menang atas .env
    for key in cfg:
        cli_value = getattr(args, key, None)
        if cli_value:
            cfg[key] = cli_value
            missing = [m for m in missing if m != ENV_VAR_MAP[key]]

    if missing:
        print("\n[GAGAL] Environment variable berikut tidak ditemukan:")
        for m in missing:
            print(f"  - {m}")
        print(
            "\nIsi lewat .env, export manual di shell, atau pakai flag CLI "
            "(contoh: --host ... --user ...). Lihat docstring di atas file "
            "ini untuk detail."
        )
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("\n[GAGAL] Modul 'psycopg2' belum terpasang.")
        print("Install dengan: pip install psycopg2 --break-system-packages")
        print("(kalau di Windows/dev biasa, psycopg2-binary juga boleh; "
              "TAPI JANGAN dipakai untuk build Android -- lihat catatan "
              "project soal ini).")
        sys.exit(1)

    print("\n=== MetroSnack — Test Koneksi Database ===")
    print(f"Host     : {cfg['host']}")
    print(f"Port     : {cfg['port']}")
    print(f"Database : {cfg['dbname']}")
    print(f"User     : {cfg['user']}")
    print(f"Password : {'*' * len(cfg['password']) if cfg['password'] else '(kosong)'}")
    print("-" * 44)

    start = time.time()
    try:
        conn = psycopg2.connect(
            host=cfg["host"],
            port=cfg["port"],
            dbname=cfg["dbname"],
            user=cfg["user"],
            password=cfg["password"],
            connect_timeout=CONNECT_TIMEOUT_SECONDS,
        )
    except psycopg2.OperationalError as e:
        elapsed = time.time() - start
        print(f"\n[GAGAL] Tidak bisa konek setelah {elapsed:.1f} detik.\n")
        print(f"Detail error:\n  {e}")
        print("Kemungkinan penyebab & yang perlu dicek:")
        print("  1. Firewall VPS memblokir port 5432 dari IP Anda saat ini")
        print("     (cek: ufw status, atau security group kalau pakai cloud provider).")
        print("  2. PostgreSQL belum listen ke alamat luar")
        print("     (cek postgresql.conf: listen_addresses = '*').")
        print("  3. pg_hba.conf belum mengizinkan koneksi dari IP Anda")
        print("     (perlu baris 'host <db> <user> <ip>/32 md5' atau scram-sha-256).")
        print("  4. Username/password salah, atau role belum punya hak LOGIN.")
        print("  5. Nama database salah / belum dibuat.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[GAGAL] Error tidak terduga: {e}")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"[OK] Koneksi berhasil dalam {elapsed:.2f} detik.\n")

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            (pg_version,) = cur.fetchone()
            print(f"PostgreSQL version:\n  {pg_version}\n")

            cur.execute("SELECT current_database(), current_user;")
            db_name, db_user = cur.fetchone()
            print(f"Terhubung sebagai '{db_user}' ke database '{db_name}'.\n")

            if not args.skip_table_check:
                print("Mengecek keberadaan tabel-tabel utama...")
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
                existing_tables = {row[0] for row in cur.fetchall()}

                all_ok = True
                for t in EXPECTED_TABLES:
                    status = "OK" if t in existing_tables else "TIDAK DITEMUKAN"
                    marker = "  [✓]" if t in existing_tables else "  [x]"
                    print(f"{marker} {t:<32} {status}")
                    if t not in existing_tables:
                        all_ok = False

                print()
                if all_ok:
                    print("[OK] Semua tabel yang diharapkan sudah ada "
                          "(migration_002 & migration_003 sudah jalan).")
                else:
                    print("[PERHATIAN] Ada tabel yang belum ada -- kemungkinan "
                          "migration_003.sql belum dijalankan di database ini, "
                          "atau Anda konek ke database/host yang salah.")

    finally:
        conn.close()
        print("\nKoneksi ditutup. Selesai.")


if __name__ == "__main__":
    main()
