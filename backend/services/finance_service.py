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


def hitung_sisa_hutang(modal_pusat: Decimal, masuk_uang: Decimal, masuk_barang: Decimal) -> dict:
    """
    CONFIRMED FORMULA (lihat header file ini):

        Sisa Hutang = Modal Pusat - Lebih Uang + Kurang Uang

    Mengembalikan breakdown lengkap supaya gampang ditelusuri kalau
    suatu saat perlu diaudit ulang.
    """
    lk = hitung_lebih_kurang(masuk_uang, masuk_barang)
    sisa_hutang = Decimal(modal_pusat) - lk["lebih_uang"] + lk["kurang_uang"]
    return {
        "modal_pusat": Decimal(modal_pusat),
        "masuk_uang": Decimal(masuk_uang),
        "masuk_barang": Decimal(masuk_barang),
        "lebih_uang": lk["lebih_uang"],
        "kurang_uang": lk["kurang_uang"],
        "sisa_hutang": sisa_hutang,
        "formula_status": "CONFIRMED",
    }
