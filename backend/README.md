# MetroSnack Backend

Backend service untuk aplikasi **MetroSnack**, yang menyediakan API, autentikasi, akses database PostgreSQL, repository data, dan service untuk proses bisnis keuangan.

Project ini menggunakan arsitektur berlapis agar kode API, autentikasi, database, repository, dan business logic tidak tercampur dalam satu file.

## 1. Arsitektur

Secara umum alur backend adalah:

```text
Client / Flet Application
        |
        | HTTP / HTTPS
        v
     FastAPI
        |
        +----------------------+
        |                      |
        v                      v
   Authentication          API Routes
        |                      |
        |                      v
        |                Repositories
        |                      |
        |                      v
        +--------------> PostgreSQL

                    ^
                    |
              Finance Service
```

Tanggung jawab utama setiap lapisan:

- `api/` menangani endpoint HTTP.
- `auth/` menangani autentikasi, dependency, dan keamanan.
- `database/` menangani koneksi serta struktur database.
- `models/` berisi schema/data model yang digunakan API.
- `repositories/` menangani operasi pengambilan dan penyimpanan data.
- `services/` berisi business logic yang lebih kompleks.
- `main.py` menjadi entry point aplikasi backend.
- `config.py` menangani konfigurasi aplikasi.
- `seed_test_data.py` digunakan untuk memasukkan data pengujian.

## 2. Struktur Folder

```text
backend/
│
├── api/
│   ├── routes_activity.py
│   ├── routes_auth.py
│   ├── routes_cabang.py
│   ├── routes_dashboard.py
│   ├── routes_folder.py
│   ├── routes_invoice.py
│   ├── routes_transaksi.py
│   ├── routes_users.py
│   └── __init__.py
│
├── auth/
│   ├── dependencies.py
│   ├── security.py
│   └── __init__.py
│
├── database/
│   ├── connection.py
│   ├── schema.sql
│   └── __init__.py
│
├── models/
│   ├── schemas.py
│   └── __init__.py
│
├── repositories/
│   ├── activity_repo.py
│   ├── cabang_repo.py
│   ├── folder_repo.py
│   ├── invoice_repo.py
│   ├── transaksi_repo.py
│   ├── user_repo.py
│   └── __init__.py
│
├── services/
│   ├── finance_service.py
│   └── __init__.py
│
├── config.py
├── main.py
├── requirements.txt
├── seed_test_data.py
├── .env.example
└── README.md
```

## 3. Fungsi Setiap Komponen

### `api/`

Berisi route API berdasarkan fitur aplikasi.

| File | Fungsi |
|---|---|
| `routes_auth.py` | Endpoint autentikasi/login |
| `routes_users.py` | Endpoint pengguna |
| `routes_cabang.py` | Endpoint cabang |
| `routes_folder.py` | Endpoint folder |
| `routes_invoice.py` | Endpoint invoice |
| `routes_transaksi.py` | Endpoint transaksi |
| `routes_dashboard.py` | Endpoint data dashboard |
| `routes_activity.py` | Endpoint activity log |

Pembagian route berdasarkan fitur membuat backend lebih mudah dikembangkan dibandingkan menempatkan semua endpoint di `main.py`.

### `auth/`

Berisi mekanisme keamanan dan dependency autentikasi.

`security.py` bertanggung jawab terhadap fungsi keamanan seperti pembuatan atau verifikasi credential/token sesuai implementasi aplikasi.

`dependencies.py` digunakan oleh route yang membutuhkan user yang sudah terautentikasi atau dependency keamanan lainnya.

### `database/`

Berisi koneksi PostgreSQL dan schema database.

`connection.py` menjadi pusat konfigurasi koneksi database.

`schema.sql` berisi struktur tabel database yang dibutuhkan backend.

### `models/`

Berisi schema data yang digunakan untuk validasi request dan response API.

File utama:

```text
models/schemas.py
```

Schema membantu memastikan data yang diterima backend memiliki format yang sesuai sebelum diproses.

### `repositories/`

Repository menjadi lapisan yang berkomunikasi dengan database.

Contohnya:

```text
activity_repo.py
cabang_repo.py
folder_repo.py
invoice_repo.py
transaksi_repo.py
user_repo.py
```

Dengan pola ini, route tidak perlu menulis query database secara langsung.

Contoh alur:

```text
routes_invoice.py
       |
       v
invoice_repo.py
       |
       v
PostgreSQL
```

### `services/`

Berisi business logic.

File utama:

```text
services/finance_service.py
```

Service digunakan ketika sebuah proses membutuhkan perhitungan atau penggabungan beberapa operasi repository.

Dengan demikian:

```text
Route
  ↓
Service
  ↓
Repository
  ↓
Database
```

lebih mudah dipelihara daripada:

```text
Route
  ↓
semua logic + query database
```

## 4. Persyaratan

Backend membutuhkan:

- Python 3.12 atau versi yang kompatibel dengan dependency project.
- PostgreSQL.
- Virtual environment Python.
- Dependency yang tercantum di `requirements.txt`.

Disarankan menggunakan virtual environment lokal dan tidak menyimpan folder `venv/` ke Git.

## 5. Instalasi

Masuk ke folder backend:

```bash
cd backend
```

Buat virtual environment:

```bash
python -m venv venv
```

Aktifkan virtual environment pada Windows:

```powershell
venv\Scripts\activate
```

Pada Linux/macOS:

```bash
source venv/bin/activate
```

Install dependency:

```bash
pip install -r requirements.txt
```

## 6. Konfigurasi Environment

Salin file contoh environment:

```text
.env.example
```

menjadi:

```text
.env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Kemudian isi konfigurasi sesuai server PostgreSQL yang digunakan.

Contoh konsep konfigurasi:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

Gunakan nama variabel yang benar-benar didefinisikan oleh `config.py` dan `database/connection.py`.

**Jangan memasukkan password database, JWT secret, API key, atau credential lain ke Git.**

## 7. Database

Struktur database berada pada:

```text
database/schema.sql
```

Schema tersebut digunakan sebagai referensi struktur database MetroSnack.

Untuk database production, lakukan perubahan schema secara terkontrol dan selalu backup database sebelum perubahan yang berisiko.

Jangan menggunakan data production sebagai data pengujian tanpa prosedur yang jelas.

## 8. Menjalankan Backend

Dari folder `backend`:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Untuk development lokal:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Jika `main.py` menyediakan object FastAPI bernama `app`, perintah di atas akan menjalankan aplikasi tersebut.

Setelah backend berjalan, endpoint API dapat diakses melalui host dan port yang digunakan.

Untuk deployment di VPS, backend sebaiknya tidak langsung diekspos ke internet tanpa reverse proxy dan konfigurasi keamanan yang sesuai.

## 9. Health Check

Backend MetroSnack menyediakan endpoint health check pada deployment saat ini.

Contoh pengujian lokal:

```bash
curl http://127.0.0.1:8000/health
```

Response yang diharapkan:

```json
{
  "status": "ok"
}
```

Jika menggunakan Nginx sebagai reverse proxy, health check juga dapat digunakan untuk memastikan komunikasi:

```text
Client
  ↓
Nginx
  ↓
Backend :8000
```

## 10. Menambahkan Endpoint Baru

Jika menambahkan fitur baru, gunakan pola berikut.

### Langkah 1 — Buat route

Misalnya:

```text
api/routes_example.py
```

### Langkah 2 — Buat repository jika membutuhkan database

```text
repositories/example_repo.py
```

### Langkah 3 — Tambahkan schema

Jika request/response membutuhkan validasi:

```text
models/schemas.py
```

### Langkah 4 — Tambahkan service jika terdapat business logic

```text
services/example_service.py
```

### Langkah 5 — Daftarkan router pada `main.py`

Jangan menaruh seluruh logic fitur baru langsung ke `main.py`.

## 11. Prinsip Pengembangan

Backend sebaiknya mempertahankan pemisahan tanggung jawab:

```text
API Route
   ↓
Validation / Authentication
   ↓
Service
   ↓
Repository
   ↓
PostgreSQL
```

Route sebaiknya fokus pada HTTP request/response.

Repository sebaiknya fokus pada akses database.

Service sebaiknya fokus pada business logic.

Database connection sebaiknya dikelola melalui satu mekanisme koneksi yang konsisten.

## 12. Keamanan

Backend menggunakan beberapa lapisan keamanan:

- autentikasi pengguna;
- dependency untuk route yang membutuhkan autentikasi;
- penyimpanan credential melalui environment variable;
- validasi request;
- pembatasan akses database melalui konfigurasi PostgreSQL;
- reverse proxy untuk deployment.

Beberapa aturan penting:

1. Jangan commit `.env`.
2. Jangan commit password PostgreSQL.
3. Jangan commit JWT secret.
4. Jangan commit API key.
5. Jangan commit folder `venv/`.
6. Jangan commit `__pycache__/`.
7. Jangan membuka port PostgreSQL ke seluruh internet jika tidak diperlukan.
8. Gunakan HTTPS pada deployment production.
9. Gunakan user database dengan permission seminimal mungkin.
10. Backup database sebelum perubahan schema yang besar.

## 13. Git

File yang seharusnya tidak masuk repository antara lain:

```text
.env
venv/
__pycache__/
*.pyc
```

Pastikan `.gitignore` berada di root repository MetroSnack.

Jika file rahasia pernah terlanjur di-commit, menambahkan `.env` ke `.gitignore` saja tidak cukup. File tersebut harus dikeluarkan dari Git tracking dan credential yang sudah terekspos harus diganti.

## 14. Seed Data

File:

```text
seed_test_data.py
```

digunakan untuk kebutuhan data pengujian.

Gunakan seed data hanya pada environment development/testing kecuali script tersebut memang telah dirancang secara aman untuk environment production.

Sebelum menjalankannya terhadap database production, periksa isi script dan target database terlebih dahulu.

## 15. Deployment

Arsitektur deployment yang direkomendasikan:

```text
                    Internet
                       |
                       v
                    Nginx
                       |
                 HTTP :8000
                       |
                       v
             MetroSnack Backend
                    FastAPI
                       |
                       v
                  PostgreSQL
```

Nginx menangani akses HTTP/HTTPS dari luar, sedangkan backend berjalan sebagai service internal pada port aplikasi.

Untuk production, backend sebaiknya dijalankan sebagai service yang dapat otomatis restart ketika terjadi kegagalan.

## 16. Troubleshooting Dasar

### Backend tidak bisa dijalankan

Periksa virtual environment:

```bash
python --version
```

Kemudian:

```bash
pip install -r requirements.txt
```

### Database tidak dapat terhubung

Periksa:

- host PostgreSQL;
- port PostgreSQL;
- nama database;
- username;
- password;
- `DATABASE_URL` atau konfigurasi environment yang digunakan;
- firewall/VPS;
- status PostgreSQL.

### Port 8000 tidak dapat diakses

Periksa apakah backend berjalan:

```bash
curl http://127.0.0.1:8000/health
```

Jika lokal berhasil tetapi dari luar gagal, periksa Nginx, firewall, binding host, dan konfigurasi VPS.

### Nginx tidak dapat meneruskan request

Periksa konfigurasi Nginx:

```bash
sudo nginx -t
```

Jika konfigurasi valid:

```bash
sudo systemctl reload nginx
```

## 17. Status Project

Backend saat ini telah dipisahkan menjadi beberapa lapisan utama:

```text
API
├── Authentication
├── Activity
├── Cabang
├── Dashboard
├── Folder
├── Invoice
├── Transaksi
└── Users

Data Layer
├── PostgreSQL Connection
├── Repositories
└── Database Schema

Business Layer
└── Finance Service
```

Struktur ini menjadi dasar pengembangan backend MetroSnack selanjutnya.

---

## Catatan Repository

Arsip project yang digunakan sebagai referensi saat dokumentasi ini dibuat juga mengandung folder seperti:

```text
backend/venv/
backend/**/__pycache__/
backend/.env
```

Folder dan file tersebut **tidak seharusnya disimpan di repository Git**.

`venv/` berisi dependency lokal dan dapat dibuat ulang menggunakan `requirements.txt`.

`__pycache__/` dan `*.pyc` adalah file hasil kompilasi/cache Python.

`.env` dapat berisi credential dan secret sehingga harus tetap berada di luar repository.

Gunakan `.env.example` sebagai template konfigurasi tanpa credential asli.

---

## Lisensi

Dokumentasi lisensi dapat ditambahkan sesuai keputusan pemilik project MetroSnack.
