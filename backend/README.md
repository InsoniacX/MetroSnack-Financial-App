# MetroSnack Backend API — Scaffold Awal

Ini adalah titik awal backend API untuk MetroSnack, dibuat mengikuti
arsitektur target di dokumen konteks project (Flet client → Backend API
→ PostgreSQL VPS). File-file ini SIAP DIJALANKAN, tapi baca dulu
bagian "Yang Masih Perlu Dikonfirmasi" di bawah sebelum dipakai serius.

## Cara menjalankan (di komputer/VPS Ubuntu)

```bash
# 1. Buat virtual environment (sekali saja)
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install semua library yang dibutuhkan
pip install -r requirements.txt

# 3. Siapkan file konfigurasi
cp .env.example .env
# lalu edit .env, isi DB_PASSWORD dan JWT_SECRET dengan nilai asli

# 4. (Kalau database belum ada tabelnya) buat skema
psql -U postgres -d metrosnack -f database/schema.sql

# 5. Isi data awal untuk testing (1 cabang + 1 user admin)
python seed_test_data.py

# 6. Jalankan server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Setelah jalan, buka `http://localhost:8000/docs` di browser — itu
dokumentasi API otomatis (Swagger UI), bisa langsung dicoba dari situ
tanpa nulis kode sama sekali. Login pakai `POST /auth/login` dengan
`username=admin` `password=admin123` (dari `seed_test_data.py`), copy
`access_token` dari responsnya, lalu klik tombol **Authorize** di
pojok kanan atas halaman `/docs` dan tempel token itu di sana. Setelah
itu semua endpoint lain bisa dites langsung dari browser.

## Struktur folder

```
backend/
├── main.py                # entry point, daftar semua route
├── config.py               # baca .env
├── database/
│   ├── connection.py        # connection pool ke PostgreSQL
│   └── schema.sql           # skema tabel (REKONSTRUKSI, lihat catatan di file-nya)
├── auth/
│   ├── security.py          # hash password, buat/cek JWT
│   └── dependencies.py      # cek login & isolasi cabang di tiap request
├── models/schemas.py        # bentuk data request/response (Pydantic)
├── repositories/            # query SQL, dipindah dari db/*.py lama
├── services/
│   └── finance_service.py   # SATU-SATUNYA tempat rumus Lebih/Kurang/Sisa Hutang
└── api/                     # route per resource (auth, cabang, users, dst)
```

## Sudah Selesai & Terverifikasi (19 Agustus 2026)

- Skema `database/schema.sql` identik dengan production asli.
- **`invoice_bon` = Modal Pusat / Nilai Awal** (dikonfirmasi).
- **Formula Sisa Hutang di `services/finance_service.py` sudah
  CONFIRMED** — dicocokkan langsung ke data production lewat endpoint
  `GET /invoices/{id}/sisa-hutang` dan dibandingkan ke ledger asli,
  hasilnya cocok. Status di kode sudah diubah dari `CANDIDATE` jadi
  `CONFIRMED`.
- **Celah keamanan di `routes_transaksi.py` sudah diperbaiki**: update
  dan delete transaksi sekarang mengecek kepemilikan cabang lewat
  `_assert_transaksi_access` (menelusuri transaksi → invoice →
  folder_bulan → cabang), jadi user cabang lain tidak bisa lagi
  ubah/hapus transaksi cabang orang lain walau tahu ID-nya.

## Yang Masih Bisa Ditingkatkan (opsional, tidak mendesak)

1. Validasi panjang string (`no_laporan` max 50 karakter, dst) belum
   ditegakkan di level Pydantic — kalau kepanjangan, error baru muncul
   dari database, bukan pesan ramah dari API.
2. Belum ada endpoint untuk generate PDF laporan (kalau versi lama
   MetroSnack punya fitur ini dan masih dibutuhkan).
3. Belum ada test otomatis (unit test / integration test) — semua
   verifikasi sejauh ini manual lewat Swagger UI.

## Yang Sudah Diperbaiki dari Kode Lama

- Bug lockout di `auth_repo.py` lama (pesan "akun terkunci" tidak pernah
  sampai ke user) — sekarang di `api/routes_auth.py`, error lockout
  dikirim jelas lewat HTTP 423.
- Kredensial PostgreSQL sekarang HANYA ada di backend (lewat `.env`),
  tidak lagi ada di client — sesuai target arsitektur di dokumen (poin 11.3).
- Isolasi cabang ditegakkan di server lewat `auth/dependencies.py`
  (`assert_cabang_access`), bukan cuma diasumsikan aman dari sisi client.
