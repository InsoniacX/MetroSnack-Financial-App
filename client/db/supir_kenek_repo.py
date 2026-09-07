from calendar import monthrange
from datetime import date
from decimal import Decimal
from .http_client import api_get, api_post, api_put, api_patch, api_delete, ApiError
from ._convert import to_date, to_datetime, to_decimal
from .cabang_repo import get_active_cabang


API_ROW_LIMIT = 500


class IncompleteDataError(RuntimeError):
    """Data tidak boleh dipakai jika API mungkin memotong hasil."""


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


# =========================================================================
# PERSONEL MASTER CRUD (/supir-kenek)
# =========================================================================
def get_personel_list(
    cabang_id=None,
    active_only=False,
    search=None,
):
    """
    Mengambil daftar master Supir/Kenek dari backend.

    Akun cabang hanya meminta data cabangnya sendiri.
    Admin pusat mengambil data dari seluruh cabang aktif.
    """
    cabang_name_map = {}

    if cabang_id is None:
        active_cabangs = get_active_cabang()

        if not active_cabangs:
            return []

        cabang_name_map = {
            int(cabang[0]): cabang[1]
            for cabang in active_cabangs
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

    raw_rows = []

    for target_id, target_name in target_cabangs:
        params = {
            "cabang_id": target_id,
            "active_only": bool(active_only),
        }

        try:
            response = api_get(
                "/supir-kenek",
                params=params,
            )
        except ApiError as error:
            raise ApiError(
                error.status_code,
                (
                    f"Data Supir/Kenek {target_name} "
                    f"gagal dimuat: {error}"
                ),
            ) from error
        except Exception as error:
            raise RuntimeError(
                f"Data Supir/Kenek {target_name} "
                f"gagal dimuat: {error}"
            ) from error

        rows = response or []

        if not isinstance(rows, list):
            raise RuntimeError(
                f"Respons Supir/Kenek {target_name} "
                "tidak valid."
            )

        raw_rows.extend(rows)

    keyword = (
        str(search).lower().strip()
        if search
        else ""
    )
    results = []

    for row in raw_rows:
        if (
            not isinstance(row, (list, tuple))
            or len(row) < 4
        ):
            raise RuntimeError(
                "Format data Supir/Kenek dari server "
                "tidak valid."
            )

        (
            personel_id,
            item_cabang_id,
            nama,
            aktif,
            *rest,
        ) = row

        normalized_cabang_id = int(item_cabang_id)
        nama_personel = str(nama or "").strip()
        nama_cabang = (
            cabang_name_map.get(normalized_cabang_id)
            or f"Cabang {normalized_cabang_id}"
        )

        if keyword:
            searchable_values = (
                nama_personel.lower(),
                nama_cabang.lower(),
            )

            if not any(
                keyword in value
                for value in searchable_values
            ):
                continue

        status_aktif = bool(aktif)

        results.append(
            {
                "id": personel_id,
                "cabang_id": normalized_cabang_id,
                "nama_cabang": nama_cabang,
                "nama": nama_personel,
                "aktif": status_aktif,
                "status": (
                    "Aktif"
                    if status_aktif
                    else "Nonaktif"
                ),
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

    results.sort(
        key=lambda item: (
            not item["aktif"],
            item["nama"].lower(),
        )
    )

    return results


def add_personel(nama, cabang_id):
    """Menambahkan supir/kenek baru ke master data."""
    body = {
        "cabang_id": int(cabang_id),
        "nama": str(nama).strip(),
    }
    resp = api_post("/supir-kenek", json_body=body)
    return resp.get("id") if resp else None


def update_personel(personel_id, nama):
    """Mengubah nama supir/kenek."""
    body = {
        "nama": str(nama).strip(),
    }
    api_put(f"/supir-kenek/{personel_id}", json_body=body)
    return True


def set_personel_aktif(personel_id, aktif):
    """Mengubah status aktif/nonaktif supir/kenek."""
    api_patch(f"/supir-kenek/{personel_id}/aktif", params={"aktif": bool(aktif)})
    return True


# =========================================================================
# PENGELUARAN OPERASIONAL CRUD (/operasional-mobil)
# =========================================================================
def get_pengeluaran_supir_kenek(
    cabang_id=None,
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
    supir_id=None,
    kenek_id=None,
    personel_id=None,
    search=None,
    sort_order="desc",
):
    """
    Mengambil daftar catatan operasional kendaraan dari backend.

    Data yang mencapai batas API tidak dianggap lengkap.
    Pengguna harus mempersempit rentang tanggalnya.
    """
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

    selected_month = None
    selected_year = None

    if bulan is not None:
        try:
            selected_month = int(bulan)
            selected_year = int(tahun)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Bulan atau tahun tidak valid."
            ) from error

        if not 1 <= selected_month <= 12:
            raise ValueError(
                "Bulan harus berada antara 1 sampai 12."
            )

        if not 2000 <= selected_year <= 2100:
            raise ValueError(
                "Tahun harus berada antara 2000 sampai 2100."
            )

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
            if resolved_start is not None
            else month_start
        )
        resolved_end = (
            min(resolved_end, month_end)
            if resolved_end is not None
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

    def normalize_optional_id(value, label):
        if value is None:
            return None

        try:
            normalized_value = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{label} tidak valid."
            ) from error

        if normalized_value <= 0:
            raise ValueError(
                f"{label} harus lebih besar dari nol."
            )

        return normalized_value

    selected_supir_id = normalize_optional_id(
        supir_id,
        "ID supir",
    )
    selected_kenek_id = normalize_optional_id(
        kenek_id,
        "ID kenek",
    )
    selected_personel_id = normalize_optional_id(
        personel_id,
        "ID personel",
    )

    cabang_name_map = {}

    if cabang_id is None:
        active_cabangs = get_active_cabang()

        if not active_cabangs:
            return []

        cabang_name_map = {
            int(cabang[0]): cabang[1]
            for cabang in active_cabangs
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

    raw_rows = []

    for target_id, target_name in target_cabangs:
        params = {
            "cabang_id": target_id,
            "limit": API_ROW_LIMIT,
        }

        if resolved_start is not None:
            params["tanggal_awal"] = _iso(resolved_start)

        if resolved_end is not None:
            params["tanggal_akhir"] = _iso(resolved_end)

        try:
            response = api_get(
                "/operasional-mobil",
                params=params,
            )
        except ApiError as error:
            raise ApiError(
                error.status_code,
                (
                    f"Data operasional {target_name} "
                    f"gagal dimuat: {error}"
                ),
            ) from error
        except Exception as error:
            raise RuntimeError(
                f"Data operasional {target_name} "
                f"gagal dimuat: {error}"
            ) from error

        rows = response or []

        if not isinstance(rows, list):
            raise RuntimeError(
                f"Respons operasional {target_name} "
                "tidak valid."
            )

        if len(rows) >= API_ROW_LIMIT:
            raise IncompleteDataError(
                f"Data operasional {target_name} mencapai "
                f"batas {API_ROW_LIMIT} transaksi. "
                "Persempit rentang tanggal agar laporan "
                "dapat ditampilkan secara lengkap."
            )

        raw_rows.extend(rows)

    items = []

    for row in raw_rows:
        if (
            not isinstance(row, (list, tuple))
            or len(row) < 11
        ):
            raise RuntimeError(
                "Format data operasional dari server "
                "tidak valid."
            )

        (
            operasional_id,
            item_cabang_id,
            tanggal,
            item_supir_id,
            nama_supir,
            item_kenek_id,
            nama_kenek,
            uang_jalan,
            keterangan,
            user_id,
            username,
            *rest,
        ) = row

        tanggal_data = to_date(tanggal)

        if tanggal_data is None:
            raise RuntimeError(
                f"Tanggal operasional ID {operasional_id} "
                "tidak valid."
            )

        normalized_cabang_id = int(item_cabang_id)
        normalized_supir_id = int(item_supir_id)
        normalized_kenek_id = (
            int(item_kenek_id)
            if item_kenek_id is not None
            else None
        )

        if (
            resolved_start is not None
            and tanggal_data < resolved_start
        ):
            continue

        if (
            resolved_end is not None
            and tanggal_data > resolved_end
        ):
            continue

        if (
            selected_supir_id is not None
            and normalized_supir_id != selected_supir_id
        ):
            continue

        if (
            selected_kenek_id is not None
            and normalized_kenek_id != selected_kenek_id
        ):
            continue

        if (
            selected_personel_id is not None
            and normalized_supir_id != selected_personel_id
            and normalized_kenek_id != selected_personel_id
        ):
            continue

        nama_cabang = (
            cabang_name_map.get(normalized_cabang_id)
            or f"Cabang {normalized_cabang_id}"
        )
        nama_supir_data = str(
            nama_supir or "Supir"
        ).strip()
        nama_kenek_data = str(
            nama_kenek or ""
        ).strip()

        if search:
            keyword = str(search).lower().strip()
            searchable_values = (
                nama_supir_data.lower(),
                nama_kenek_data.lower(),
                str(keterangan or "").lower(),
                str(username or "").lower(),
                nama_cabang.lower(),
            )

            if not any(
                keyword in value
                for value in searchable_values
            ):
                continue

        nominal_data = to_decimal(uang_jalan)
        peran = f"Supir: {nama_supir_data}"

        if nama_kenek_data:
            peran += f", Kenek: {nama_kenek_data}"

        items.append(
            {
                "id": operasional_id,
                "cabang_id": normalized_cabang_id,
                "nama_cabang": nama_cabang,
                "tanggal": tanggal_data,
                "supir_id": normalized_supir_id,
                "nama_supir": nama_supir_data,
                "nama_personel": nama_supir_data,
                "kenek_id": normalized_kenek_id,
                "nama_kenek": nama_kenek_data or "-",
                "peran": peran,
                "uang_jalan": nominal_data,
                "nominal": nominal_data,
                "keterangan": keterangan or "",
                "kategori_biaya": "Uang Jalan",
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


def add_pengeluaran_supir_kenek(
    tanggal,
    supir_id,
    kenek_id=None,
    uang_jalan=0,
    keterangan="",
    cabang_id=None,
    **kwargs,
):
    """Menambahkan catatan operasional mobil baru."""
    if cabang_id is None:
        raise ValueError("Cabang wajib ditentukan.")

    body = {
        "tanggal": _iso(tanggal),
        "supir_id": int(supir_id),
        "kenek_id": int(kenek_id) if kenek_id and int(kenek_id) > 0 else None,
        "uang_jalan": float(uang_jalan),
        "keterangan": (keterangan or "").strip() or None,
        "cabang_id": int(cabang_id),
    }
    resp = api_post("/operasional-mobil", json_body=body)
    return resp.get("id") if resp else None


def update_pengeluaran_supir_kenek(
    pengeluaran_id,
    tanggal,
    supir_id,
    kenek_id=None,
    uang_jalan=0,
    keterangan="",
    **kwargs,
):
    """Mengubah data catatan operasional mobil."""
    body = {
        "tanggal": _iso(tanggal),
        "supir_id": int(supir_id),
        "kenek_id": int(kenek_id) if kenek_id and int(kenek_id) > 0 else None,
        "uang_jalan": float(uang_jalan),
        "keterangan": (keterangan or "").strip() or None,
    }
    api_put(f"/operasional-mobil/{pengeluaran_id}", json_body=body)
    return True


def delete_pengeluaran_supir_kenek(pengeluaran_id):
    """Menghapus catatan operasional mobil."""
    api_delete(f"/operasional-mobil/{pengeluaran_id}")
    return True


def get_rekap_supir_kenek_bulanan(bulan, tahun, cabang_id=None):
    """Mengembalikan total nominal dan breakdown biaya operasional supir & kenek bulanan."""
    items = get_pengeluaran_supir_kenek(cabang_id=cabang_id, bulan=bulan, tahun=tahun)
    total_biaya = sum((it["nominal"] for it in items), Decimal(0))

    supir_totals = {}
    kenek_totals = {}
    for it in items:
        s_name = it["nama_supir"]
        supir_totals[s_name] = supir_totals.get(s_name, Decimal(0)) + it["nominal"]
        if it.get("nama_kenek") and it["nama_kenek"] != "-":
            k_name = it["nama_kenek"]
            kenek_totals[k_name] = kenek_totals.get(k_name, Decimal(0)) + it["nominal"]

    return {
        "items": items,
        "total": total_biaya,
        "count": len(items),
        "supir_totals": supir_totals,
        "kenek_totals": kenek_totals,
        "personel_totals": supir_totals,  # alias
    }

