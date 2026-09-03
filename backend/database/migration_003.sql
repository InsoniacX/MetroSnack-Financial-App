-- ============================================================
--  MetroSnack Financial App — migration_003.sql (REVISI)
--  Menambahkan 5 tabel baru:
--    1. pendapatan_pengeluaran_harian  (1 tabel gabungan, dibedakan kolom "jenis")
--    2. supir_kenek                    (master roster nama sopir/kenek)
--    3. operasional_mobil              (trip harian, 1 baris = 1 pasangan sopir+kenek)
--    4. pengambilan_pabrik
--    5. pengambilan_balaraja
--
--  PENDAPATAN diasumsikan INPUT MANUAL oleh staf cabang (sama seperti
--  pengeluaran), BUKAN dihitung otomatis dari sistem invoice/hutang
--  yang sudah ada -- lihat catatan di chat untuk alasannya. Kalau nanti
--  proses bisnisnya berubah jadi otomatis, cukup ubah cara backend
--  mengisi kolom nominal, tabel ini tidak perlu diubah.
--
--  Jalankan di VPS dengan:
--    psql -U admin_metrosnack -d metrosnack_financial -f migration_003.sql
--
--  CATATAN SEBELUM DIJALANKAN:
--  - Skrip ini mengasumsikan tabel "cabang" dan "users" sudah ada,
--    dengan primary key "id" (integer) di masing-masing.
--  - Idempotent-safe untuk re-run (IF NOT EXISTS), TAPI tidak mengubah
--    struktur kalau tabel sudah ada dengan skema berbeda -- backup dulu
--    sebelum run di production.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. pendapatan_pengeluaran_harian
--    Satu tabel gabungan untuk pendapatan & pengeluaran harian.
--    Dibedakan lewat kolom "jenis" (pendapatan/pengeluaran), supaya
--    akumulasi/pendapatan bersih tinggal SUM() dengan filter jenis,
--    tanpa perlu JOIN dua tabel terpisah.
--
--    Kolom nama item sengaja dinamai "nama_pengeluaran" sesuai
--    permintaan, dipakai untuk kedua jenis baris (pendapatan maupun
--    pengeluaran) -- backend cukup label berbeda di UI sesuai "jenis".
--
--    Saat ini hanya dipakai cabang Zebor; cabang_id tetap generik
--    (bukan di-hardcode) supaya scalable ke cabang lain nanti --
--    pembatasan akses ditegakkan di backend (task "Permission/akses
--    fitur"), bukan di database.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pendapatan_pengeluaran_harian (
    id                  SERIAL PRIMARY KEY,
    cabang_id           INTEGER NOT NULL REFERENCES cabang(id) ON DELETE RESTRICT,
    tanggal             DATE NOT NULL,
    jenis               VARCHAR(20) NOT NULL CHECK (jenis IN ('pendapatan', 'pengeluaran')),
    nama_pengeluaran    VARCHAR(150) NOT NULL,      -- ex: "BIAYA LISTRIK", "SARAPAN", "Pendapatan Toko"
    nominal             NUMERIC(14, 2) NOT NULL CHECK (nominal > 0),
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE pendapatan_pengeluaran_harian IS 'Pendapatan & pengeluaran harian per cabang dalam satu tabel, dibedakan kolom jenis. Saat ini dipakai cabang Zebor; pembatasan akses cabang ditegakkan di backend.';
COMMENT ON COLUMN pendapatan_pengeluaran_harian.jenis IS 'pendapatan = uang masuk, pengeluaran = uang keluar. Dipakai untuk akumulasi/pendapatan bersih di backend.';
COMMENT ON COLUMN pendapatan_pengeluaran_harian.nominal IS 'Untuk PENDAPATAN, nilai ini saat ini diasumsikan diinput manual oleh staf cabang (belum ada sumber otomatis dari sistem lain).';

CREATE INDEX IF NOT EXISTS idx_pendapatan_pengeluaran_harian_cabang_tanggal
    ON pendapatan_pengeluaran_harian (cabang_id, tanggal);

CREATE INDEX IF NOT EXISTS idx_pendapatan_pengeluaran_harian_cabang_tanggal_jenis
    ON pendapatan_pengeluaran_harian (cabang_id, tanggal, jenis);

-- ------------------------------------------------------------
-- 2. supir_kenek
--    Master roster nama sopir/kenek per cabang (tanpa pembeda peran,
--    sesuai konfirmasi). Dibuat sebagai tabel terpisah supaya nama
--    tidak diketik ulang bebas tiap input (typo-prone) dan bisa
--    dipakai untuk pelaporan per-orang di masa depan.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS supir_kenek (
    id          SERIAL PRIMARY KEY,
    cabang_id   INTEGER NOT NULL REFERENCES cabang(id) ON DELETE RESTRICT,
    nama        VARCHAR(100) NOT NULL,
    aktif       BOOLEAN NOT NULL DEFAULT TRUE,   -- nonaktifkan tanpa hapus riwayat trip lama
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (cabang_id, nama)
);

COMMENT ON TABLE supir_kenek IS 'Master roster nama sopir/kenek per cabang, tanpa pembeda peran (bisa jadi sopir maupun kenek).';
COMMENT ON COLUMN supir_kenek.aktif IS 'FALSE untuk nonaktifkan orang dari daftar pilihan baru, tanpa menghapus riwayat trip lama (FK tetap valid).';

CREATE INDEX IF NOT EXISTS idx_supir_kenek_cabang
    ON supir_kenek (cabang_id);

-- ------------------------------------------------------------
-- 3. operasional_mobil
--    1 baris = 1 trip = 1 pasangan sopir+kenek berbagi 1 uang_jalan
--    (sesuai konfirmasi). kenek_id dibuat NULLABLE untuk jaga-jaga
--    kalau suatu saat ada trip solo tanpa kenek.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operasional_mobil (
    id          SERIAL PRIMARY KEY,
    cabang_id   INTEGER NOT NULL REFERENCES cabang(id) ON DELETE RESTRICT,
    tanggal     DATE NOT NULL,
    supir_id    INTEGER NOT NULL REFERENCES supir_kenek(id) ON DELETE RESTRICT,
    kenek_id    INTEGER REFERENCES supir_kenek(id) ON DELETE RESTRICT,
    uang_jalan  NUMERIC(14, 2) NOT NULL CHECK (uang_jalan > 0),
    keterangan  TEXT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (kenek_id IS NULL OR kenek_id <> supir_id)
);

COMMENT ON TABLE operasional_mobil IS 'Trip operasional kendaraan harian per cabang; 1 baris = 1 pasangan sopir+kenek berbagi 1 uang_jalan. Saat ini dipakai cabang Zebor, tapi cabang_id generik supaya scalable ke cabang lain.';
COMMENT ON COLUMN operasional_mobil.uang_jalan IS 'Nominal uang jalan untuk 1 trip/pasangan (bukan per-orang). Dulu bernama "Total" di dokumen sumber.';

CREATE INDEX IF NOT EXISTS idx_operasional_mobil_cabang_tanggal
    ON operasional_mobil (cabang_id, tanggal);

-- ------------------------------------------------------------
-- 4. pengambilan_pabrik
--    Struktur mengikuti PDF apa adanya: keterangan + nominal per baris.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pengambilan_pabrik (
    id          SERIAL PRIMARY KEY,
    cabang_id   INTEGER NOT NULL REFERENCES cabang(id) ON DELETE RESTRICT,
    tanggal     DATE NOT NULL,
    keterangan  VARCHAR(150) NOT NULL,   -- ex: "BAYAR TERIGU", "BAYAR PELLET"
    nominal     NUMERIC(14, 2) NOT NULL CHECK (nominal > 0),
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE pengambilan_pabrik IS 'Kas yang diambil dari pabrik untuk cabang tertentu, per baris (keterangan + nominal).';

CREATE INDEX IF NOT EXISTS idx_pengambilan_pabrik_cabang_tanggal
    ON pengambilan_pabrik (cabang_id, tanggal);

-- ------------------------------------------------------------
-- 5. pengambilan_balaraja
--    Struktur mengikuti PDF apa adanya: keterangan (mis. "SAGU",
--    "BREM") + nominal per baris.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pengambilan_balaraja (
    id          SERIAL PRIMARY KEY,
    cabang_id   INTEGER NOT NULL REFERENCES cabang(id) ON DELETE RESTRICT,
    tanggal     DATE NOT NULL,
    keterangan  VARCHAR(150) NOT NULL,   -- ex: "SAGU", "BREM"
    nominal     NUMERIC(14, 2) NOT NULL CHECK (nominal > 0),
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE pengambilan_balaraja IS 'Kas yang diambil dari Balaraja untuk cabang tertentu, per baris (keterangan + nominal).';

CREATE INDEX IF NOT EXISTS idx_pengambilan_balaraja_cabang_tanggal
    ON pengambilan_balaraja (cabang_id, tanggal);

-- ------------------------------------------------------------
-- Trigger updated_at (generik, dipakai ulang oleh kelima tabel di
-- atas). Kalau function dengan nama ini SUDAH ada di database Anda,
-- CREATE OR REPLACE ini aman -- akan menimpa dengan definisi yang
-- identik secara fungsional.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pendapatan_pengeluaran_harian_updated_at ON pendapatan_pengeluaran_harian;
CREATE TRIGGER trg_pendapatan_pengeluaran_harian_updated_at
    BEFORE UPDATE ON pendapatan_pengeluaran_harian
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_supir_kenek_updated_at ON supir_kenek;
CREATE TRIGGER trg_supir_kenek_updated_at
    BEFORE UPDATE ON supir_kenek
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_operasional_mobil_updated_at ON operasional_mobil;
CREATE TRIGGER trg_operasional_mobil_updated_at
    BEFORE UPDATE ON operasional_mobil
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_pengambilan_pabrik_updated_at ON pengambilan_pabrik;
CREATE TRIGGER trg_pengambilan_pabrik_updated_at
    BEFORE UPDATE ON pengambilan_pabrik
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_pengambilan_balaraja_updated_at ON pengambilan_balaraja;
CREATE TRIGGER trg_pengambilan_balaraja_updated_at
    BEFORE UPDATE ON pengambilan_balaraja
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;

-- ============================================================
-- Verifikasi cepat setelah run (jalankan manual, bukan bagian
-- dari migration):
--
--   \d pendapatan_pengeluaran_harian
--   \d supir_kenek
--   \d operasional_mobil
--   \d pengambilan_pabrik
--   \d pengambilan_balaraja
--
-- Contoh query akumulasi bulanan pendapatan bersih (referensi buat
-- backend nanti):
--
--   SELECT
--       cabang_id,
--       date_trunc('month', tanggal) AS bulan,
--       SUM(nominal) FILTER (WHERE jenis = 'pendapatan')   AS total_pendapatan,
--       SUM(nominal) FILTER (WHERE jenis = 'pengeluaran')  AS total_pengeluaran,
--       SUM(nominal) FILTER (WHERE jenis = 'pendapatan')
--         - SUM(nominal) FILTER (WHERE jenis = 'pengeluaran') AS pendapatan_bersih
--   FROM pendapatan_pengeluaran_harian
--   WHERE cabang_id = :cabang_id
--   GROUP BY cabang_id, date_trunc('month', tanggal);
-- ============================================================