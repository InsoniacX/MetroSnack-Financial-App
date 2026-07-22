PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    password_salt   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'admin'
                        CHECK (role IN ('superadmin','admin')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS month_folders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    status          TEXT NOT NULL DEFAULT 'diproses'
                        CHECK (status IN ('diproses','selesai')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (year, month)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    phone           TEXT,
    address         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    month_folder_id INTEGER NOT NULL REFERENCES month_folders(id) ON DELETE CASCADE,
    supplier_id     INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    nota_number     TEXT NOT NULL,
    invoice_date    TEXT NOT NULL,
    total_amount    INTEGER NOT NULL DEFAULT 0,
    hpp_amount      INTEGER NOT NULL DEFAULT 0,
    laba_amount     INTEGER NOT NULL DEFAULT 0,
    beban_amount    INTEGER NOT NULL DEFAULT 0,
    source          TEXT NOT NULL DEFAULT 'manual'
                        CHECK (source IN ('manual','auto_scan')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (month_folder_id, nota_number)
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL
                        CHECK (type IN ('restock','penjualan','operasional','invoice_added')),
    title           TEXT NOT NULL,
    amount          INTEGER NOT NULL,
    direction       TEXT NOT NULL CHECK (direction IN ('masuk','keluar')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIEW IF NOT EXISTS v_month_folder_summary AS
SELECT
    mf.id AS month_folder_id,
    mf.year,
    mf.month,
    mf.status,
    COUNT(i.id) AS total_invoice,
    COALESCE(SUM(i.total_amount), 0) AS total_omzet,
    COALESCE(SUM(i.hpp_amount), 0) AS total_hpp,
    COALESCE(SUM(i.laba_amount), 0) AS laba_kotor,
    COALESCE(SUM(i.beban_amount), 0) AS total_beban,
    COALESCE(SUM(i.laba_amount), 0) - COALESCE(SUM(i.beban_amount), 0) AS laba_bersih
FROM month_folders mf
LEFT JOIN invoices i ON i.month_folder_id = mf.id
GROUP BY mf.id;