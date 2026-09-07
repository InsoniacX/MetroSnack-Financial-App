from calendar import monthrange
from datetime import date
from decimal import Decimal

from ._convert import to_date, to_decimal
from .cabang_repo import get_active_cabang
from .http_client import (
    ApiError,
    api_delete,
    api_get,
    api_post,
    api_put,
)

DEFAULT_KATEGORI_PENDAPATAN = [
    "Penjualan Langsung",
    "Penjualan Grosir",
    "Pendapatan Lain",
    "Komisi / Cashback",
    "Investasi / Modal",
]

DEFAULT_KATEGORI_PENGELUARAN = [
    "Bahan Baku",
    "Operasional",
    "Gaji",
    "Sewa",
    "Listrik & Air",
    "Transportasi & Logistik",
    "Kemasan & Perlengkapan",
    "Perbaikan & Perawatan",
    "Lain-lain",
]

API_ROW_LIMIT = 500


class IncompleteDataError(RuntimeError):
    """Data tidak boleh dipakai ketika API kemungkinan memotong hasil."""


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

    if (bulan is None) != (tahun is None):
        raise ValueError(
            "Bulan dan tahun harus diberikan bersama-sama."
        )

    if bulan is not None:
        try:
            selected_month = int(bulan)
            selected_year = int(tahun)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Bulan atau tahun tidak valid."
            ) from error

        if not 1 <= selected_month <= 12:
            raise ValueError("Bulan harus berada antara 1 sampai 12.")

        if not 2000 <= selected_year <= 2100:
            raise ValueError("Tahun harus berada antara 2000 sampai 2100.")

        month_start = date(
            selected_year,
            selected_month,
            1,
        )
        month_end = date(
            selected_year,
            selected_month,
            monthrange(
                selected_year,
                selected_month,
            )[1],
        )

        resolved_start = (
            max(resolved_start, month_start)
            if resolved_start
            else month_start
        )
        resolved_end = (
            min(resolved_end, month_end)
            if resolved_end
            else month_end
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


def _parse_item_name(nama_str):
    """
    Ekstrak kategori dan keterangan dari kolom nama_pengeluaran.
    Format yang didukung:
    - '[Kategori] Keterangan'
    - 'Kategori - Keterangan'
    - 'Keterangan' (default kategori: 'Lain-lain')
    """
    nama = str(nama_str or "").strip()
    if not nama:
        return "Lain-lain", ""
    if nama.startswith("[") and "]" in nama:
        parts = nama[1:].split("]", 1)
        kat = parts[0].strip()
        ket = parts[1].strip()
        return kat or "Lain-lain", ket or kat
    if " - " in nama:
        parts = nama.split(" - ", 1)
        kat = parts[0].strip()
        ket = parts[1].strip()
        return kat or "Lain-lain", ket or kat
    return "Lain-lain", nama


def _format_item_name(kategori, keterangan):
    """Menggabungkan kategori dan keterangan menjadi format nama_pengeluaran backend."""
    ket = (keterangan or "").strip()
    kat = (kategori or "").strip()
    if kat and kat not in ("Lain-lain", "") and (kat.lower() not in ket.lower()):
        return f"[{kat}] {ket}" if ket else kat
    return ket or kat or "Transaksi Kas"


def get_transaksi_kas(
    cabang_id=None,
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
    jenis=None,
    kategori=None,
    search=None,
    sort_order="desc",
):
    """
    Mengambil transaksi pendapatan dan pengeluaran dari backend.

    Data yang mencapai batas API tidak akan dianggap lengkap.
    Pengguna harus mempersempit rentang tanggalnya.
    """
    start_date, end_date = _resolve_date_range(
        bulan=bulan,
        tahun=tahun,
        start_date=start_date,
        end_date=end_date,
    )

    normalized_jenis = None
    if jenis and str(jenis).lower() in (
        "pendapatan",
        "pengeluaran",
    ):
        normalized_jenis = str(jenis).lower()

    cabang_name_map = {}

    if cabang_id is None:
        active_cabangs = get_active_cabang()

        if not active_cabangs:
            return []

        cabang_name_map = {
            int(item[0]): item[1]
            for item in active_cabangs
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

        if normalized_jenis is not None:
            params["jenis"] = normalized_jenis

        try:
            response = api_get(
                "/pendapatan-pengeluaran",
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
        (
            entry_id,
            item_cabang_id,
            tanggal,
            item_jenis,
            nama_pengeluaran,
            nominal,
            *rest,
        ) = row

        tanggal_data = to_date(tanggal)

        # Pemeriksaan tambahan jika fungsi dipanggil memakai bulan/tahun.
        if (
            bulan is not None
            and tanggal_data
            and tanggal_data.month != int(bulan)
        ):
            continue

        if (
            tahun is not None
            and tanggal_data
            and tanggal_data.year != int(tahun)
        ):
            continue

        kategori_data, keterangan_data = _parse_item_name(
            nama_pengeluaran
        )

        if (
            kategori
            and kategori != "Semua"
            and kategori_data.lower() != kategori.lower()
        ):
            continue

        nama_cabang = (
            cabang_name_map.get(item_cabang_id)
            or f"Cabang {item_cabang_id}"
        )

        if search:
            keyword = search.lower().strip()
            nama_full = str(
                nama_pengeluaran or ""
            ).lower()

            searchable_values = (
                nama_full,
                nama_cabang.lower(),
                kategori_data.lower(),
                keterangan_data.lower(),
            )

            if not any(
                keyword in value
                for value in searchable_values
            ):
                continue

        items.append(
            {
                "id": entry_id,
                "cabang_id": item_cabang_id,
                "nama_cabang": nama_cabang,
                "tanggal": tanggal_data or date.today(),
                "jenis": (
                    "Pendapatan"
                    if str(item_jenis).lower()
                    == "pendapatan"
                    else "Pengeluaran"
                ),
                "kategori": kategori_data,
                "nominal": to_decimal(nominal),
                "keterangan": (
                    keterangan_data
                    or nama_pengeluaran
                    or "-"
                ),
                "nota": "",
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


def add_transaksi_kas(cabang_id, nama_cabang, tanggal, jenis, kategori, nominal, keterangan, nota=""):
    """
    Menambahkan transaksi pendapatan/pengeluaran baru ke backend API (POST /pendapatan-pengeluaran).
    """
    nama_item = _format_item_name(kategori, keterangan)
    body = {
        "cabang_id": int(cabang_id),
        "tanggal": _iso(tanggal),
        "jenis": "pendapatan" if str(jenis).lower() == "pendapatan" else "pengeluaran",
        "nama_pengeluaran": nama_item[:150],
        "nominal": str(nominal),
    }
    resp = api_post("/pendapatan-pengeluaran", body)
    return resp.get("id") if resp else None


def update_transaksi_kas(transaksi_id, tanggal, jenis, kategori, nominal, keterangan, nota="", cabang_id=None, nama_cabang=None):
    """
    Memperbarui transaksi pendapatan/pengeluaran di backend API (PUT /pendapatan-pengeluaran/{id}).
    """
    nama_item = _format_item_name(kategori, keterangan)
    body = {
        "tanggal": _iso(tanggal),
        "jenis": "pendapatan" if str(jenis).lower() == "pendapatan" else "pengeluaran",
        "nama_pengeluaran": nama_item[:150],
        "nominal": str(nominal),
    }
    api_put(f"/pendapatan-pengeluaran/{transaksi_id}", body)
    return True


def delete_transaksi_kas(transaksi_id):
    """
    Menghapus transaksi pendapatan/pengeluaran dari backend API (DELETE /pendapatan-pengeluaran/{id}).
    """
    api_delete(f"/pendapatan-pengeluaran/{transaksi_id}")
    return True


def get_daily_summary(cabang_id, tanggal):
    """
    Mengambil summary harian kas dari backend API (GET /pendapatan-pengeluaran/summary/harian).
    """
    return api_get(
        "/pendapatan-pengeluaran/summary/harian",
        params={"cabang_id": cabang_id, "tanggal": _iso(tanggal)},
    )


def get_monthly_summary(cabang_id, bulan, tahun):
    """
    Mengambil summary bulanan kas dari backend API (GET /pendapatan-pengeluaran/summary/bulanan).
    """
    return api_get(
        "/pendapatan-pengeluaran/summary/bulanan",
        params={"cabang_id": cabang_id, "bulan": bulan, "tahun": tahun},
    )


# Alias untuk keseragaman penamaan dengan backend
get_entries = get_transaksi_kas
create_entry = add_transaksi_kas
update_entry = update_transaksi_kas
delete_entry = delete_transaksi_kas
