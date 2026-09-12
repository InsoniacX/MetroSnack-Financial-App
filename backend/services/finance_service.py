"""
finance_service.py — SATU-SATUNYA tempat rumus finansial MetroSnack
boleh ditulis. Jangan hitung Lebih/Kurang/Sisa Hutang di tempat lain
(dashboard, PDF, endpoint) — semua harus panggil fungsi di sini.

=======================================================================
STATUS: CONFIRMED (19 Agustus 2026) — dicocokkan langsung ke data
production lewat backend ini (endpoint GET /invoices/{id}/sisa-hutang)
dan dibandingkan ke ledger asli oleh pemilik project. Angkanya cocok.
Kalau di masa depan ditemukan kasus yang tidak cocok (misal ada
cicilan/setoran tambahan yang belum tertangkap), catat contohnya dan
revisi HANYA di file ini.
=======================================================================
"""
from decimal import Decimal

# Carry-forward dinamis disetujui pemilik proyek pada 12 September 2026.
# Aturan periode/kompatibilitas: backend/DEBT_CARRY_FORWARD.md.


def hitung_lebih_kurang(masuk_uang: Decimal, masuk_barang: Decimal) -> dict:
    """
    Selisih = Masuk Uang - Masuk Barang
    Jika positif -> Lebih Uang
    Jika negatif -> Kurang Uang (nilai absolut)
    Jika nol -> keduanya 0
    """
    selisih = Decimal(masuk_uang) - Decimal(masuk_barang)
    if selisih > 0:
        return {"lebih_uang": selisih, "kurang_uang": Decimal("0")}
    elif selisih < 0:
        return {"lebih_uang": Decimal("0"), "kurang_uang": abs(selisih)}
    return {"lebih_uang": Decimal("0"), "kurang_uang": Decimal("0")}


def hitung_sisa_hutang(modal_pusat: Decimal, masuk_uang: Decimal, masuk_barang: Decimal,
                      hutang_bawaan: Decimal = Decimal("0")) -> dict:
    """
    CONFIRMED FORMULA (lihat header file ini):

        Sisa Hutang = Hutang Bawaan + Modal Pusat - Lebih Uang + Kurang Uang

    Mengembalikan breakdown lengkap supaya gampang ditelusuri kalau
    suatu saat perlu diaudit ulang.
    """
    lk = hitung_lebih_kurang(masuk_uang, masuk_barang)
    sisa_hutang_raw = (
        Decimal(hutang_bawaan) + Decimal(modal_pusat)
        - lk["lebih_uang"]
        + lk["kurang_uang"]
    )
    
    sisa_hutang = max(sisa_hutang_raw, Decimal("0"))
    return {
        "modal_pusat": Decimal(modal_pusat),
        "hutang_bawaan": Decimal(hutang_bawaan),
        "masuk_uang": Decimal(masuk_uang),
        "masuk_barang": Decimal(masuk_barang),
        "lebih_uang": lk["lebih_uang"],
        "kurang_uang": lk["kurang_uang"],
        "sisa_hutang": sisa_hutang,
        "formula_status": "CONFIRMED",
    }


def hitung_riwayat_hutang(monthly_rows):
    """Replay monthly balances in calendar order, independently per branch.

    Only a nonnegative closing debt carries forward (no credit carry). Empty
    months retain the previous balance. Within a month, all legacy invoices
    are aggregated BEFORE clamping, so opening debt is counted exactly once.
    Recomputed on every request; corrections/deletions need no cached updates.
    """
    periods = []
    branches = {}
    for row in sorted(monthly_rows, key=lambda r: (
        r["cabang_id"], r["tahun"] or 0, r["bulan"] or 0,
    )):
        cid = row["cabang_id"]
        branch = branches.setdefault(cid, {
            "cabang_id": cid, "nama_cabang": row["nama_cabang"],
            **hitung_sisa_hutang(Decimal(0), Decimal(0), Decimal(0)),
        })
        if row["folder_id"] is None:
            continue
        result = hitung_sisa_hutang(
            row["modal_pusat"], row["masuk_uang"], row["masuk_barang"],
            branch["sisa_hutang"],
        )
        periods.append({**row, **result, "cakupan": "folder_bulan"})
        for key in ("modal_pusat", "masuk_uang", "masuk_barang"):
            branch[key] += result[key]
        branch.update(hitung_lebih_kurang(branch["masuk_uang"], branch["masuk_barang"]))
        branch["sisa_hutang"] = result["sisa_hutang"]
        branch["folder_terakhir_id"] = row["folder_id"]
    return periods, list(branches.values())


def ringkasan_seluruh_cabang(branches):
    """Sum real movements and each branch's latest debt, never monthly balances."""
    totals = {key: sum((b[key] for b in branches), Decimal(0))
              for key in ("modal_pusat", "masuk_uang", "masuk_barang", "sisa_hutang")}
    result = hitung_sisa_hutang(totals["modal_pusat"], totals["masuk_uang"], totals["masuk_barang"])
    result["sisa_hutang"] = totals["sisa_hutang"]
    result["cakupan"] = "saldo_terakhir_per_cabang"
    return result
