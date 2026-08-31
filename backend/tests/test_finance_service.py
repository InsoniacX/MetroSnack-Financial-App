from decimal import Decimal

from services.finance_service import (
    hitung_lebih_kurang,
    hitung_sisa_hutang,
)


def test_lebih_uang():
    result = hitung_lebih_kurang(
        Decimal("700000"),
        Decimal("300000"),
    )

    assert result["lebih_uang"] == Decimal("400000")
    assert result["kurang_uang"] == Decimal("0")


def test_kurang_uang():
    result = hitung_lebih_kurang(
        Decimal("300000"),
        Decimal("700000"),
    )

    assert result["lebih_uang"] == Decimal("0")
    assert result["kurang_uang"] == Decimal("400000")


def test_sisa_hutang_tepat_lunas():
    result = hitung_sisa_hutang(
        modal_pusat=Decimal("1000000"),
        masuk_uang=Decimal("1500000"),
        masuk_barang=Decimal("500000"),
    )

    assert result["sisa_hutang"] == Decimal("0")


def test_sisa_hutang_lebih_bayar_tetap_nol():
    result = hitung_sisa_hutang(
        modal_pusat=Decimal("1000000"),
        masuk_uang=Decimal("1600000"),
        masuk_barang=Decimal("500000"),
    )

    assert result["sisa_hutang"] == Decimal("0")


def test_sisa_hutang_belum_lunas():
    result = hitung_sisa_hutang(
        modal_pusat=Decimal("1000000"),
        masuk_uang=Decimal("1200000"),
        masuk_barang=Decimal("500000"),
    )

    assert result["sisa_hutang"] == Decimal("300000")