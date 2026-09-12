"""Monthly debt is calculated by the backend, never reconstructed by the UI."""
from .http_client import api_get
from ._convert import to_decimal


def parse_balance(data):
    if not isinstance(data, dict) or data.get("cakupan") != "folder_bulan":
        raise ValueError("Backend belum mendukung saldo hutang bulanan. Perbarui backend terlebih dahulu.")
    result = dict(data)
    for key in ("hutang_bawaan", "modal_pusat", "masuk_barang", "masuk_uang", "sisa_hutang"):
        if data.get(key) is None:
            raise ValueError(f"Data saldo hutang tidak lengkap: {key}")
        result[key] = to_decimal(data[key])
    return result


def get_folder_balance(folder_id):
    return parse_balance(api_get(f"/folders/{folder_id}/saldo-hutang"))


def get_folder_balances(cabang_id):
    rows = api_get("/folders/saldo-hutang", params={"cabang_id": cabang_id})
    return {r["folder_id"]: parse_balance(r) for r in rows}
