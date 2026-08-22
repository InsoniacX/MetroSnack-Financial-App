-- =====================================================================
-- MetroSnack — schema.sql
--
-- STATUS: DIVERIFIKASI PENUH terhadap `pg_dump -s` database asli
-- (metrosnack_financial, PostgreSQL 14.23) pada 19 Agustus 2026.
-- Ini dipakai untuk membuat database TEST lokal yang strukturnya
-- identik dengan production. invoice_bon = Modal Pusat / Nilai Awal
-- (dikonfirmasi pemilik project).
-- =====================================================================

-- pgcrypto ada di database asli tapi TIDAK dipakai backend ini (hashing
-- password dilakukan di Python lewat bcrypt). Baris ini opsional dan
-- butuh privilege superuser -- boleh dihapus kalau bikin error di host
-- terbatas seperti sebagian managed PostgreSQL.
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS cabang (
    id SERIAL PRIMARY KEY,
    nama_cabang VARCHAR(100) NOT NULL UNIQUE,
    alamat TEXT,
    aktif BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nama_lengkap VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'karyawan',
    aktif BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    failed_attempts INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMP WITHOUT TIME ZONE,
    cabang_id INT REFERENCES cabang(id),
    CONSTRAINT chk_karyawan_has_cabang CHECK ((role <> 'karyawan') OR (cabang_id IS NOT NULL)),
    CONSTRAINT users_role_check CHECK (role IN ('admin', 'karyawan'))
);

CREATE TABLE IF NOT EXISTS folder_bulan (
    id SERIAL PRIMARY KEY,
    nama_folder VARCHAR(50) NOT NULL,
    bulan INT NOT NULL,
    tahun INT NOT NULL,
    dibuat_oleh INT REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    cabang_id INT NOT NULL REFERENCES cabang(id),
    CONSTRAINT folder_bulan_bulan_check CHECK (bulan BETWEEN 1 AND 12),
    CONSTRAINT folder_bulan_bulan_tahun_cabang_key UNIQUE (bulan, tahun, cabang_id)
);

CREATE TABLE IF NOT EXISTS invoice (
    id SERIAL PRIMARY KEY,
    folder_bulan_id INT NOT NULL REFERENCES folder_bulan(id) ON DELETE CASCADE,
    no_laporan VARCHAR(50),
    tanggal_dibuat DATE NOT NULL DEFAULT CURRENT_DATE,
    tanggal_laporan DATE NOT NULL,
    -- invoice_bon = Modal Pusat / Nilai Awal (lihat catatan di header file).
    invoice_bon NUMERIC(15,2) NOT NULL DEFAULT 0,
    dibuat_oleh INT REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transaksi_harian (
    id SERIAL PRIMARY KEY,
    invoice_id INT NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
    tanggal_transaksi DATE NOT NULL,
    masuk_barang NUMERIC(15,2) DEFAULT 0,
    masuk_uang NUMERIC(15,2) DEFAULT 0,
    -- GENERATED, tidak boleh di-INSERT/UPDATE manual dari kode manapun.
    lebih_kurang NUMERIC(15,2) GENERATED ALWAYS AS (masuk_uang - masuk_barang) STORED,
    keterangan VARCHAR(20) GENERATED ALWAYS AS (
        CASE WHEN (masuk_uang - masuk_barang) >= 0 THEN 'Lebih Uang' ELSE 'Kurang Uang' END
    ) STORED,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50),
    action VARCHAR(20) NOT NULL,
    entity VARCHAR(30) NOT NULL,
    entity_id INT,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    cabang_id INT REFERENCES cabang(id)
);

CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoice_folder ON invoice (folder_bulan_id);
CREATE INDEX IF NOT EXISTS idx_transaksi_invoice ON transaksi_harian (invoice_id);
