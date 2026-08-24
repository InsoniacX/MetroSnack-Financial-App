-- =====================================================================
-- Migrasi #2: Sisa Barang manual (item #3) + Nota teks transaksi (item #4)
--
-- CARA JALANKAN di VPS:
--   sudo -u postgres psql -d metrosnack_financial -f migration_002.sql
--
-- AMAN dijalankan ke database production yang sedang dipakai:
--   - Cuma ADD COLUMN, tidak ada DROP/ALTER tipe data existing
--   - Kedua kolom baru NULLABLE, tidak ada NOT NULL -- jadi baris lama
--     otomatis dapat NULL (artinya "belum diisi"), tidak error
--   - Tidak ada downtime yang berarti untuk tabel sebesar ini
-- =====================================================================

-- Item #3: nilai "Sisa Barang di Toko" yang diinput manual staff
-- (dicek fisik setiap hari, ditimpa tiap kali dicek ulang -- BUKAN riwayat harian).
ALTER TABLE invoice
    ADD COLUMN IF NOT EXISTS sisa_barang_manual NUMERIC(15,2);

COMMENT ON COLUMN invoice.sisa_barang_manual IS
    'Sisa barang fisik di toko, diinput manual staff (dicek tiap hari, nilai TERKINI saja, bukan riwayat). NULL = belum pernah diisi.';

-- Item #4: nota/keterangan teks per baris transaksi harian (BUKAN file).
ALTER TABLE transaksi_harian
    ADD COLUMN IF NOT EXISTS nota VARCHAR(100);

COMMENT ON COLUMN transaksi_harian.nota IS
    'Nomor/keterangan nota transaksi (teks bebas, opsional).';

-- Verifikasi setelah migrasi (jalankan manual untuk cek):
--   \d invoice
--   \d transaksi_harian
