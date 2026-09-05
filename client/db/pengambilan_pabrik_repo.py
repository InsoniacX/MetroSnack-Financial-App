from calendar import monthrange
from datetime import date
from decimal import Decimal

from ._convert import to_date, to_datetime, to_decimal
from .cabang_repo import get_all_cabang
from .http_client import (
    ApiError,
    api_delete,
    api_get,
    api_post,
    api_put,
)


API_ROW_LIMIT = 500


class IncompleteDataError(RuntimeError):
    """Data tidak boleh dipakai jika API mungkin memotong hasil."""


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _resolve_date_range(
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
):
    resolved_start = (
        to_date(start_date)
        if start_date is not None
        else None
    )
    resolved_end = (
        to_date(end_date)
        if end_date is not None
        else None
    )

    selected_month = None
    selected_year = None

    if bulan is not None:
        try:
            selected_month = int(bulan)
        except (TypeError, ValueError) as error:
            raise ValueError("Bulan tidak valid.") from error

        if not 1 <= selected_month <= 12:
            raise ValueError(
                "Bulan harus berada antara 1 sampai 12."
            )

    if tahun is not None:
        try:
            selected_year = int(tahun)
        except (TypeError, ValueError) as error:
            raise ValueError("Tahun tidak valid.") from error

        if not 2000 <= selected_year <= 2100:
            raise ValueError(
                "Tahun harus berada antara 2000 sampai 2100."
            )

    if selected_month is not None and selected_year is None:
        raise ValueError(
            "Tahun wajib dipilih ketika menggunakan filter bulan."
        )

    if selected_year is not None:
        if selected_month is not None:
            period_start = date(
                selected_year,
                selected_month,
                1,
            )
            period_end = date(
                selected_year,
                selected_month,
                monthrange(
                    selected_year,
                    selected_month,
                )[1],
            )
        else:
            period_start = date(selected_year, 1, 1)
            period_end = date(selected_year, 12, 31)

        resolved_start = (
            max(resolved_start, period_start)
            if resolved_start is not None
            else period_start
        )
        resolved_end = (
            min(resolved_end, period_end)
            if resolved_end is not None
            else period_end
        )

    if (
        resolved_start is not None
        and resolved_end is not None
        and resolved_start > resolved_end
    ):
        raise ValueError(
            "Tanggal awal tidak boleh melewati tanggal akhir."
        )

    return resolved_start, resolved_end


def get_pengambilan_pabrik(
    cabang_id=None,
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
    search=None,
    sort_order="desc",
    **kwargs,
):
    """
    Mengambil data pengambilan kas pabrik dari backend.

    Data yang mencapai batas API tidak dianggap lengkap.
    Pengguna harus mempersempit rentang tanggalnya.
    """
    del kwargs

    start_date, end_date = _resolve_date_range(
        bulan=bulan,
        tahun=tahun,
        start_date=start_date,
        end_date=end_date,
    )

    cabang_name_map = {}

    if cabang_id is None:
        all_cabangs = get_all_cabang()

        if not all_cabangs:
            return []

        cabang_name_map = {
            int(cabang[0]): cabang[1]
            for cabang in all_cabangs
        }
        target_cabangs = list(cabang_name_map.items())
    else:
        try:
            selected_cabang_id = int(cabang_id)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "ID cabang tidak valid."
            ) from error

        if selected_cabang_id <= 0:
            raise ValueError(
                "ID cabang harus lebih besar dari nol."
            )

        target_cabangs = [
            (
                selected_cabang_id,
                f"Cabang {selected_cabang_id}",
            )
        ]

    def fetch_branch_rows(target_id, target_name):
        params = {
            "cabang_id": target_id,
            "limit": API_ROW_LIMIT,
        }

        if start_date is not None:
            params["tanggal_awal"] = _iso(start_date)

        if end_date is not None:
            params["tanggal_akhir"] = _iso(end_date)

        try:
            response = api_get(
                "/pengambilan-kas/pabrik",
                params=params,
            )
        except ApiError as error:
            raise ApiError(
                error.status_code,
                (
                    f"Data {target_name} gagal dimuat: "
                    f"{error}"
                ),
            ) from error
        except Exception as error:
            raise RuntimeError(
                f"Data {target_name} gagal dimuat: {error}"
            ) from error

        rows = response or []

        if not isinstance(rows, list):
            raise RuntimeError(
                f"Respons data {target_name} tidak valid."
            )

        if len(rows) >= API_ROW_LIMIT:
            raise IncompleteDataError(
                f"Data {target_name} mencapai batas "
                f"{API_ROW_LIMIT} transaksi. "
                "Persempit rentang tanggal agar laporan "
                "dapat ditampilkan secara lengkap."
            )

        return rows

    raw_rows = []

    for target_id, target_name in target_cabangs:
        branch_rows = fetch_branch_rows(
            target_id,
            target_name,
        )
        raw_rows.extend(branch_rows)

    items = []

    for row in raw_rows:
        if not isinstance(row, (list, tuple)) or len(row) < 7:
            raise RuntimeError(
                "Format data pengambilan pabrik dari server "
                "tidak valid."
            )

        (
            entry_id,
            item_cabang_id,
            tanggal,
            keterangan,
            nominal,
            user_id,
            username,
            *rest,
        ) = row

        tanggal_data = to_date(tanggal)

        if tanggal_data is None:
            raise RuntimeError(
                f"Tanggal transaksi ID {entry_id} tidak valid."
            )

        normalized_cabang_id = int(item_cabang_id)

        if (
            start_date is not None
            and tanggal_data < start_date
        ):
            continue

        if (
            end_date is not None
            and tanggal_data > end_date
        ):
            continue

        nama_cabang = (
            cabang_name_map.get(normalized_cabang_id)
            or f"Cabang {normalized_cabang_id}"
        )

        if search:
            keyword = str(search).lower().strip()
            searchable_values = (
                str(keterangan or "").lower(),
                str(username or "").lower(),
                nama_cabang.lower(),
            )

            if not any(
                keyword in value
                for value in searchable_values
            ):
                continue

        nominal_data = to_decimal(nominal)

        items.append(
            {
                "id": entry_id,
                "cabang_id": normalized_cabang_id,
                "nama_cabang": nama_cabang,
                "tanggal": tanggal_data,
                "keterangan": keterangan or "",
                "nama_pabrik": keterangan or "Pabrik",
                "nama_barang": keterangan or "",
                "qty": Decimal(1),
                "satuan": "Trx",
                "harga_satuan": nominal_data,
                "total_harga": nominal_data,
                "nominal": nominal_data,
                "user_id": user_id,
                "username": username or "",
                "created_at": (
                    to_datetime(rest[0])
                    if len(rest) > 0
                    else None
                ),
                "updated_at": (
                    to_datetime(rest[1])
                    if len(rest) > 1
                    else None
                ),
            }
        )

    descending = (
        (sort_order or "desc").lower() == "desc"
    )

    items.sort(
        key=lambda item: (
            item["tanggal"],
            item["id"],
        ),
        reverse=descending,
    )

    return items


def add_pengambilan_pabrik(
    tanggal,
    keterangan,
    nominal,
    cabang_id,
    **kwargs,
):
    """Menambahkan catatan pengambilan kas pabrik baru."""
    body = {
        "cabang_id": int(cabang_id),
        "tanggal": _iso(tanggal),
        "keterangan": str(keterangan).strip(),
        "nominal": float(nominal),
    }
    resp = api_post("/pengambilan-kas/pabrik", json_body=body)
    return resp.get("id") if resp else None


def update_pengambilan_pabrik(
    entry_id,
    tanggal,
    keterangan,
    nominal,
    **kwargs,
):
    """Mengubah catatan pengambilan kas pabrik."""
    body = {
        "tanggal": _iso(tanggal),
        "keterangan": str(keterangan).strip(),
        "nominal": float(nominal),
    }
    api_put(f"/pengambilan-kas/pabrik/{entry_id}", json_body=body)
    return True


def delete_pengambilan_pabrik(entry_id):
    """Menghapus catatan pengambilan kas pabrik."""
    api_delete(f"/pengambilan-kas/pabrik/{entry_id}")
    return True


def get_akumulasi_bulanan_pabrik(bulan=None, tahun=None, cabang_id=None):
    """Mengembalikan rekap total biaya pengambilan pabrik pada bulan/tahun tertentu."""
    items = get_pengambilan_pabrik(cabang_id=cabang_id, bulan=bulan, tahun=tahun)
    total_biaya = sum((it["nominal"] for it in items), Decimal(0))
    return {
        "items": items,
        "total": total_biaya,
        "count": len(items),
    }

