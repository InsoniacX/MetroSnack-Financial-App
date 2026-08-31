-- ============================================================
-- MetroSnack Financial App
-- Migration 004
--
-- Tujuan:
-- 1. Menambahkan constraint nonnegatif pada tabel finansial lama.
-- 2. Menambahkan index pada foreign key yang belum terindeks.
-- 3. Menyesuaikan index dengan pola query activity log dan kas.
--
-- Migration ini tidak membuat, menggabungkan, atau menghapus tabel.
-- ============================================================

BEGIN;


-- ------------------------------------------------------------
-- Pemeriksaan data sebelum constraint ditambahkan.
-- Seluruh migration dibatalkan jika ditemukan nilai negatif.
-- ------------------------------------------------------------

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.invoice
        WHERE invoice_bon < 0
    ) THEN
        RAISE EXCEPTION
            'Migration dibatalkan: invoice.invoice_bon memiliki nilai negatif';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.invoice
        WHERE sisa_barang_manual < 0
    ) THEN
        RAISE EXCEPTION
            'Migration dibatalkan: invoice.sisa_barang_manual memiliki nilai negatif';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.transaksi_harian
        WHERE masuk_barang < 0
    ) THEN
        RAISE EXCEPTION
            'Migration dibatalkan: transaksi_harian.masuk_barang memiliki nilai negatif';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.transaksi_harian
        WHERE masuk_uang < 0
    ) THEN
        RAISE EXCEPTION
            'Migration dibatalkan: transaksi_harian.masuk_uang memiliki nilai negatif';
    END IF;
END
$$;


-- ------------------------------------------------------------
-- Constraint nonnegatif.
-- PostgreSQL tidak mendukung ADD CONSTRAINT IF NOT EXISTS,
-- sehingga keberadaan constraint diperiksa melalui pg_constraint.
-- ------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'invoice_invoice_bon_nonnegative'
          AND conrelid = 'public.invoice'::regclass
    ) THEN
        ALTER TABLE public.invoice
        ADD CONSTRAINT invoice_invoice_bon_nonnegative
        CHECK (invoice_bon >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'invoice_sisa_barang_manual_nonnegative'
          AND conrelid = 'public.invoice'::regclass
    ) THEN
        ALTER TABLE public.invoice
        ADD CONSTRAINT invoice_sisa_barang_manual_nonnegative
        CHECK (
            sisa_barang_manual IS NULL
            OR sisa_barang_manual >= 0
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'transaksi_harian_masuk_barang_nonnegative'
          AND conrelid = 'public.transaksi_harian'::regclass
    ) THEN
        ALTER TABLE public.transaksi_harian
        ADD CONSTRAINT transaksi_harian_masuk_barang_nonnegative
        CHECK (masuk_barang >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'transaksi_harian_masuk_uang_nonnegative'
          AND conrelid = 'public.transaksi_harian'::regclass
    ) THEN
        ALTER TABLE public.transaksi_harian
        ADD CONSTRAINT transaksi_harian_masuk_uang_nonnegative
        CHECK (masuk_uang >= 0);
    END IF;
END
$$;


-- ------------------------------------------------------------
-- Index foreign key yang belum tersedia.
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_folder_bulan_dibuat_oleh
    ON public.folder_bulan (dibuat_oleh);

CREATE INDEX IF NOT EXISTS idx_invoice_dibuat_oleh
    ON public.invoice (dibuat_oleh);

CREATE INDEX IF NOT EXISTS idx_operasional_mobil_supir_id
    ON public.operasional_mobil (supir_id);

CREATE INDEX IF NOT EXISTS idx_operasional_mobil_kenek_id
    ON public.operasional_mobil (kenek_id);

CREATE INDEX IF NOT EXISTS idx_operasional_mobil_user_id
    ON public.operasional_mobil (user_id);

CREATE INDEX IF NOT EXISTS idx_pendapatan_pengeluaran_harian_user_id
    ON public.pendapatan_pengeluaran_harian (user_id);

CREATE INDEX IF NOT EXISTS idx_pengambilan_pabrik_user_id
    ON public.pengambilan_pabrik (user_id);

CREATE INDEX IF NOT EXISTS idx_pengambilan_balaraja_user_id
    ON public.pengambilan_balaraja (user_id);


-- ------------------------------------------------------------
-- Index sesuai pola filter dan pengurutan backend.
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_activity_log_created_at_desc
    ON public.activity_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_log_cabang_created_at_desc
    ON public.activity_log (cabang_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pendapatan_pengeluaran_cabang_jenis_tanggal
    ON public.pendapatan_pengeluaran_harian (
        cabang_id,
        jenis,
        tanggal
    );


COMMIT;