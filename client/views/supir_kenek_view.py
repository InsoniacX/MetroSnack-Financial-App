import flet as ft
from decimal import Decimal
from datetime import date, datetime
from components.metric_card import metric_card
from utils.formatting import rp
from utils.validation import require_text, parse_date, parse_positive_decimal
from utils.pdf_export import generate_supir_kenek_pdf
from db.activity_repo import log_activity
from db.supir_kenek_repo import (
    get_personel_list,
    add_personel,
    update_personel,
    delete_personel,
    get_pengeluaran_supir_kenek,
    add_pengeluaran_supir_kenek,
    update_pengeluaran_supir_kenek,
    delete_pengeluaran_supir_kenek,
    KATEGORI_BIAYA_KENEK,
    PERAN_OPTIONS,
)
from db.cabang_repo import get_active_cabang
from state import app_state


def build_view(page: ft.Page):
    actor = app_state.user or {}
    is_pusat = actor.get("cabang_id") is None
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    today = date.today()

    filter_state = {
        "start_date": None,
        "end_date": None,
        "personel_id": None,
        "kategori": "Semua",
        "cabang_id": None if is_pusat else actor.get("cabang_id"),
        "search": "",
        "sort_order": "desc",
    }

    cabang_list = []
    if is_pusat:
        try:
            cabang_list = get_active_cabang()
        except Exception:
            cabang_list = [(1, "Cabang Utama"), (2, "Cabang Barat")]

    def close_dialog(e=None):
        page.pop_dialog()
        page.update()

    # =========================================================================
    # DIALOG TAMBAH & EDIT PENGELUARAN
    # =========================================================================
    exp_id_target = {"id": None}
    personel_cached = get_personel_list(cabang_id=filter_state["cabang_id"])

    exp_tanggal = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=190, value=today.isoformat())
    exp_personel_dropdown = ft.Dropdown(
        label="Supir / Kenek",
        width=240,
        options=[
            ft.dropdown.Option(str(p["id"]), f"{p['nama']} ({p['peran']})")
            for p in personel_cached
        ],
        value=str(personel_cached[0]["id"]) if personel_cached else "",
    )
    exp_kategori_dropdown = ft.Dropdown(
        label="Kategori Biaya",
        width=240,
        options=[ft.dropdown.Option(k, k) for k in KATEGORI_BIAYA_KENEK],
        value=KATEGORI_BIAYA_KENEK[0],
    )
    exp_nominal = ft.TextField(label="Nominal (Rp)", width=190, value="0")
    exp_keterangan = ft.TextField(label="Keterangan / Rute / Catatan", width=440, multiline=True, min_lines=2, max_lines=3)
    exp_nota = ft.TextField(label="No. Bukti / Nota (opsional)", width=200)

    exp_cabang_dropdown = ft.Dropdown(
        label="Cabang",
        width=230,
        options=[ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value=str(cabang_list[0][0]) if cabang_list else "1",
    )

    def refresh_personel_dropdown():
        nonlocal personel_cached
        personel_cached = get_personel_list(cabang_id=None if is_pusat else actor.get("cabang_id"))
        exp_personel_dropdown.options = [
            ft.dropdown.Option(str(p["id"]), f"{p['nama']} ({p['peran']})")
            for p in personel_cached
        ]
        if personel_cached and (not exp_personel_dropdown.value or exp_personel_dropdown.value not in [str(p["id"]) for p in personel_cached]):
            exp_personel_dropdown.value = str(personel_cached[0]["id"])

        filter_personel_dropdown.options = [ft.dropdown.Option("Semua", "Semua Personel")] + [
            ft.dropdown.Option(str(p["id"]), f"{p['nama']} ({p['peran']})")
            for p in personel_cached
        ]

    def submit_exp_form(e):
        try:
            tgl_val = parse_date("Tanggal", exp_tanggal.value)
            nom_val = parse_positive_decimal("Nominal", exp_nominal.value)
            ket_val = require_text("Keterangan", exp_keterangan.value, max_length=200)
            kat_val = exp_kategori_dropdown.value or "Lain-lain"
            nota_val = (exp_nota.value or "").strip()

            if not exp_personel_dropdown.value:
                raise ValueError("Silakan pilih Supir / Kenek terlebih dahulu.")

            pid_val = int(exp_personel_dropdown.value)
            sel_person = next((p for p in personel_cached if p["id"] == pid_val), None)
            nama_person = sel_person["nama"] if sel_person else "Supir/Kenek"
            peran_person = sel_person["peran"] if sel_person else "Supir"

            if is_pusat:
                sel_cid = int(exp_cabang_dropdown.value or 1)
                nama_cbg = next((c[1] for c in cabang_list if c[0] == sel_cid), "Cabang")
            else:
                sel_cid = actor.get("cabang_id", 1)
                nama_cbg = actor.get("nama_cabang", "Cabang")

            is_edit = exp_id_target["id"] is not None
            if not is_edit:
                add_pengeluaran_supir_kenek(
                    tanggal=tgl_val,
                    personel_id=pid_val,
                    nama_personel=nama_person,
                    peran=peran_person,
                    kategori_biaya=kat_val,
                    nominal=nom_val,
                    keterangan=ket_val,
                    nota=nota_val,
                    cabang_id=sel_cid,
                    nama_cabang=nama_cbg,
                )
                success_msg = "Catatan operasional berhasil disimpan!"
            else:
                update_pengeluaran_supir_kenek(
                    pengeluaran_id=exp_id_target["id"],
                    tanggal=tgl_val,
                    personel_id=pid_val,
                    nama_personel=nama_person,
                    peran=peran_person,
                    kategori_biaya=kat_val,
                    nominal=nom_val,
                    keterangan=ket_val,
                    nota=nota_val,
                    cabang_id=sel_cid,
                    nama_cabang=nama_cbg,
                )
                success_msg = "Catatan operasional berhasil diperbarui!"

            close_dialog()
            refresh_table_content()
            page.show_dialog(ft.SnackBar(ft.Text(success_msg), bgcolor=ft.Colors.GREEN_700))
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal simpan: {ex}"), bgcolor=ft.Colors.RED_400))

    exp_dialog_title = ft.Text("Catat Pengeluaran Operasional Supir / Kenek", weight=ft.FontWeight.W_500)
    exp_dialog = ft.AlertDialog(
        title=exp_dialog_title,
        content=ft.Container(
            content=ft.Column([
                ft.Row([exp_tanggal, exp_personel_dropdown], spacing=10),
                ft.Row([exp_kategori_dropdown, exp_nominal], spacing=10),
                exp_keterangan,
                ft.Row([
                    exp_nota,
                    exp_cabang_dropdown if is_pusat else ft.Container(),
                ], spacing=10),
            ], tight=True, spacing=12),
            width=480,
        ),
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Simpan", on_click=submit_exp_form, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ],
    )

    def open_add_exp_dialog(e=None):
        refresh_personel_dropdown()
        if not personel_cached:
            page.show_dialog(ft.SnackBar(ft.Text("Belum ada data supir/kenek. Tambahkan personel terlebih dahulu."), bgcolor=ft.Colors.ORANGE_800))
            return
        exp_id_target["id"] = None
        exp_dialog_title.value = "Catat Pengeluaran Operasional Supir / Kenek"
        exp_tanggal.value = date.today().isoformat()
        exp_kategori_dropdown.value = KATEGORI_BIAYA_KENEK[0]
        exp_nominal.value = "0"
        exp_keterangan.value = ""
        exp_nota.value = ""
        if is_pusat and cabang_list:
            exp_cabang_dropdown.value = str(cabang_list[0][0])
        page.show_dialog(exp_dialog)

    def open_edit_exp_dialog(item):
        refresh_personel_dropdown()
        exp_id_target["id"] = item["id"]
        exp_dialog_title.value = f"Edit Pengeluaran Operasional #{item['id']}"
        exp_tanggal.value = item["tanggal"].isoformat() if hasattr(item["tanggal"], "isoformat") else str(item["tanggal"])
        exp_personel_dropdown.value = str(item["personel_id"])
        exp_kategori_dropdown.value = item["kategori_biaya"]
        exp_nominal.value = str(item["nominal"])
        exp_keterangan.value = item["keterangan"]
        exp_nota.value = item["nota"]
        if is_pusat:
            exp_cabang_dropdown.value = str(item["cabang_id"])
        page.show_dialog(exp_dialog)

    # =========================================================================
    # DIALOG TAMBAH & EDIT MASTER PERSONEL
    # =========================================================================
    p_id_target = {"id": None}
    p_nama = ft.TextField(label="Nama Lengkap", width=240)
    p_peran = ft.Dropdown(
        label="Peran / Jabatan",
        width=200,
        options=[ft.dropdown.Option(p, p) for p in PERAN_OPTIONS],
        value=PERAN_OPTIONS[0],
    )
    p_telp = ft.TextField(label="Nomor Telepon / WhatsApp", width=220)
    p_armada = ft.TextField(label="Armada / Plat Kendaraan (opsional)", width=220, hint_text="Contoh: B 9123 SCD (Grand Max)")
    p_status = ft.Dropdown(
        label="Status",
        width=180,
        options=[ft.dropdown.Option("Aktif", "Aktif"), ft.dropdown.Option("Nonaktif", "Nonaktif")],
        value="Aktif",
    )
    p_cabang_dropdown = ft.Dropdown(
        label="Cabang Penugasan",
        width=240,
        options=[ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value=str(cabang_list[0][0]) if cabang_list else "1",
    )

    def submit_personel_form(e):
        try:
            nama_val = require_text("Nama Personel", p_nama.value, max_length=100)
            peran_val = p_peran.value or "Supir"
            telp_val = (p_telp.value or "").strip()
            armada_val = (p_armada.value or "").strip()
            status_val = p_status.value or "Aktif"

            if is_pusat:
                sel_cid = int(p_cabang_dropdown.value or 1)
                nama_cbg = next((c[1] for c in cabang_list if c[0] == sel_cid), "Cabang")
            else:
                sel_cid = actor.get("cabang_id", 1)
                nama_cbg = actor.get("nama_cabang", "Cabang")

            is_edit = p_id_target["id"] is not None
            if not is_edit:
                add_personel(
                    nama=nama_val,
                    peran=peran_val,
                    no_telp=telp_val,
                    armada=armada_val,
                    cabang_id=sel_cid,
                    nama_cabang=nama_cbg,
                    status=status_val,
                )
                success_msg = f"Personel '{nama_val}' berhasil didaftarkan!"
            else:
                update_personel(
                    personel_id=p_id_target["id"],
                    nama=nama_val,
                    peran=peran_val,
                    no_telp=telp_val,
                    armada=armada_val,
                    cabang_id=sel_cid,
                    nama_cabang=nama_cbg,
                    status=status_val,
                )
                success_msg = f"Data personel '{nama_val}' berhasil diperbarui!"

            close_dialog()
            refresh_personel_dropdown()
            refresh_table_content()
            refresh_personel_table()
            page.show_dialog(ft.SnackBar(ft.Text(success_msg), bgcolor=ft.Colors.GREEN_700))
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal simpan personel: {ex}"), bgcolor=ft.Colors.RED_400))

    personel_dialog_title = ft.Text("Tambah Personel Supir / Kenek", weight=ft.FontWeight.W_500)
    personel_dialog = ft.AlertDialog(
        title=personel_dialog_title,
        content=ft.Container(
            content=ft.Column([
                ft.Row([p_nama, p_peran], spacing=10),
                ft.Row([p_telp, p_armada], spacing=10),
                ft.Row([
                    p_status,
                    p_cabang_dropdown if is_pusat else ft.Container(),
                ], spacing=10),
            ], tight=True, spacing=12),
            width=480,
        ),
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Simpan", on_click=submit_personel_form, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ],
    )

    def open_add_personel_dialog(e=None):
        p_id_target["id"] = None
        personel_dialog_title.value = "Tambah Personel Supir / Kenek"
        p_nama.value = ""
        p_peran.value = "Supir"
        p_telp.value = ""
        p_armada.value = ""
        p_status.value = "Aktif"
        if is_pusat and cabang_list:
            p_cabang_dropdown.value = str(cabang_list[0][0])
        page.show_dialog(personel_dialog)

    def open_edit_personel_dialog(item):
        p_id_target["id"] = item["id"]
        personel_dialog_title.value = f"Edit Personel #{item['id']} - {item['nama']}"
        p_nama.value = item["nama"]
        p_peran.value = item["peran"]
        p_telp.value = item["no_telp"]
        p_armada.value = item["armada"]
        p_status.value = item["status"]
        if is_pusat:
            p_cabang_dropdown.value = str(item["cabang_id"])
        page.show_dialog(personel_dialog)

    # =========================================================================
    # DIALOG KONFIRMASI HAPUS
    # =========================================================================
    del_target = {"type": None, "id": None}
    del_msg = ft.Text("")

    def confirm_general_delete(e):
        try:
            if del_target["type"] == "exp":
                delete_pengeluaran_supir_kenek(del_target["id"])
                close_dialog()
                refresh_table_content()
                page.show_dialog(ft.SnackBar(ft.Text("Catatan operasional berhasil dihapus!"), bgcolor=ft.Colors.GREEN_700))
            elif del_target["type"] == "personel":
                delete_personel(del_target["id"])
                close_dialog()
                refresh_personel_dropdown()
                refresh_table_content()
                refresh_personel_table()
                page.show_dialog(ft.SnackBar(ft.Text("Personel berhasil dihapus!"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal menghapus: {ex}"), bgcolor=ft.Colors.RED_400))

    delete_dialog = ft.AlertDialog(
        title=ft.Text("Konfirmasi Hapus Data"),
        content=del_msg,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Ya, Hapus", on_click=confirm_general_delete, bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
        ],
    )

    def open_delete_exp_dialog(item):
        del_target["type"] = "exp"
        del_target["id"] = item["id"]
        del_msg.value = f"Hapus catatan operasional {item['nama_personel']} ({item['kategori_biaya']}) senilai {rp(item['nominal'])}?"
        page.show_dialog(delete_dialog)

    def open_delete_personel_dialog(item):
        del_target["type"] = "personel"
        del_target["id"] = item["id"]
        del_msg.value = f"Apakah Anda yakin ingin menghapus data supir/kenek '{item['nama']}' ({item['peran']})?"
        page.show_dialog(delete_dialog)

    # =========================================================================
    # FILTER CONTROLS (TAB 1: OPERASIONAL)
    # =========================================================================
    filter_start_field = ft.TextField(label="Dari Tanggal (YYYY-MM-DD)", width=175)
    filter_end_field = ft.TextField(label="Sampai Tanggal (YYYY-MM-DD)", width=175)
    
    filter_sort_dropdown = ft.Dropdown(
        label="Urutan Tanggal",
        width=175,
        options=[
            ft.dropdown.Option("desc", "Terbaru (Desc)"),
            ft.dropdown.Option("asc", "Terlama (Asc)"),
        ],
        value="desc",
    )

    filter_personel_dropdown = ft.Dropdown(
        label="Personel",
        width=190,
        options=[ft.dropdown.Option("Semua", "Semua Personel")] + [
            ft.dropdown.Option(str(p["id"]), f"{p['nama']} ({p['peran']})")
            for p in personel_cached
        ],
        value="Semua",
    )

    filter_kategori_dropdown = ft.Dropdown(
        label="Kategori Biaya",
        width=190,
        options=[ft.dropdown.Option("Semua", "Semua Kategori")] + [
            ft.dropdown.Option(k, k) for k in KATEGORI_BIAYA_KENEK
        ],
        value="Semua",
    )

    filter_cabang_dropdown = ft.Dropdown(
        label="Cabang",
        width=180,
        options=[ft.dropdown.Option("Semua", "Semua Cabang")] + [ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value="Semua" if filter_state["cabang_id"] is None else str(filter_state["cabang_id"]),
    )

    search_field = ft.TextField(
        label="Cari Transaksi",
        hint_text="Nama personel, keterangan, nota...",
        prefix_icon=ft.Icons.SEARCH,
        width=230,
        value=filter_state["search"],
    )

    def apply_filter(e=None):
        try:
            filter_state["start_date"] = parse_date("Dari Tanggal", filter_start_field.value) if filter_start_field.value else None
        except Exception:
            filter_state["start_date"] = None

        try:
            filter_state["end_date"] = parse_date("Sampai Tanggal", filter_end_field.value) if filter_end_field.value else None
        except Exception:
            filter_state["end_date"] = None

        filter_state["sort_order"] = filter_sort_dropdown.value or "desc"

        sel_p = filter_personel_dropdown.value
        filter_state["personel_id"] = None if sel_p == "Semua" or not sel_p else int(sel_p)

        filter_state["kategori"] = filter_kategori_dropdown.value or "Semua"

        if is_pusat:
            sel_cbg = filter_cabang_dropdown.value
            filter_state["cabang_id"] = None if sel_cbg == "Semua" else int(sel_cbg)

        filter_state["search"] = search_field.value or ""
        refresh_table_content()

    def reset_filter(e=None):
        filter_start_field.value = ""
        filter_end_field.value = ""
        filter_sort_dropdown.value = "desc"
        filter_personel_dropdown.value = "Semua"
        filter_kategori_dropdown.value = "Semua"
        if is_pusat:
            filter_cabang_dropdown.value = "Semua"
        search_field.value = ""
        apply_filter()

    search_field.on_submit = apply_filter
    filter_sort_dropdown.on_change = apply_filter
    filter_personel_dropdown.on_change = apply_filter
    filter_kategori_dropdown.on_change = apply_filter

    filter_controls = [
        filter_start_field,
        filter_end_field,
        filter_sort_dropdown,
        filter_personel_dropdown,
        filter_kategori_dropdown,
    ]
    if is_pusat:
        filter_controls.append(filter_cabang_dropdown)
    filter_controls.append(search_field)

    filter_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FILTER_LIST, size=20, color=ft.Colors.BLUE_700),
                ft.Text("Filter Data Operasional", weight=ft.FontWeight.W_500, size=15),
                ft.Container(expand=True),
                ft.TextButton("Reset Filter", icon=ft.Icons.RESTART_ALT, on_click=reset_filter),
                ft.ElevatedButton("Terapkan", icon=ft.Icons.CHECK, on_click=apply_filter, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
            ]),
            ft.Divider(height=1),
            ft.Row(filter_controls, wrap=True, spacing=10, run_spacing=10),
        ], spacing=10),
        bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
        border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
        border_radius=10,
        padding=16,
    )

    # =========================================================================
    # METRICS & TABLES
    # =========================================================================
    metric_total_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_jalan_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_bbm_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_count_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    table_exp_container = ft.Container()
    table_personel_container = ft.Container()

    def on_sort_exp_tanggal(col_idx, ascending):
        filter_state["sort_order"] = "asc" if ascending else "desc"
        filter_sort_dropdown.value = filter_state["sort_order"]
        refresh_table_content()

    def build_exp_table_rows(items):
        rows = []
        for it in items:
            tgl_str = it["tanggal"].strftime("%d-%m-%Y") if hasattr(it["tanggal"], "strftime") else str(it["tanggal"])
            is_supir = "supir" in it["peran"].lower()
            role_color = ft.Colors.BLUE_700 if is_supir else ft.Colors.TEAL_700
            role_bg = ft.Colors.BLUE_50 if is_supir else ft.Colors.TEAL_50
            if is_dark:
                role_color = ft.Colors.BLUE_300 if is_supir else ft.Colors.TEAL_300
                role_bg = ft.Colors.BLUE_900 if is_supir else ft.Colors.TEAL_900

            cells = [
                ft.DataCell(ft.Text(tgl_str, size=13)),
            ]
            if is_pusat:
                cells.append(ft.DataCell(ft.Text(it.get("nama_cabang", "-"), size=13)))

            cells.extend([
                ft.DataCell(
                    ft.Column([
                        ft.Text(it["nama_personel"], size=13, weight=ft.FontWeight.W_600),
                    ], spacing=1, alignment=ft.MainAxisAlignment.CENTER)
                ),
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(it["peran"], size=11, weight=ft.FontWeight.W_500, color=role_color),
                        bgcolor=role_bg,
                        padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                        border_radius=6,
                    )
                ),
                ft.DataCell(ft.Text(it["kategori_biaya"], size=13, weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(it["keterangan"] or "-", size=13)),
                ft.DataCell(
                    ft.Text(
                        f"- {rp(it['nominal'])}",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.RED_400 if is_dark else ft.Colors.RED_700,
                    )
                ),
                ft.DataCell(ft.Text(it["nota"] or "-", size=12, color=ft.Colors.GREY_500)),
                ft.DataCell(
                    ft.Row([
                        ft.IconButton(
                            ft.Icons.EDIT,
                            icon_size=18,
                            tooltip="Edit Catatan",
                            on_click=lambda e, item=it: open_edit_exp_dialog(item),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_size=18,
                            icon_color=ft.Colors.RED_400,
                            tooltip="Hapus Catatan",
                            on_click=lambda e, item=it: open_delete_exp_dialog(item),
                        ),
                    ], spacing=2)
                ),
            ])
            rows.append(ft.DataRow(cells=cells))
        return rows

    def refresh_table_content():
        items = get_pengeluaran_supir_kenek(
            cabang_id=filter_state["cabang_id"],
            start_date=filter_state["start_date"],
            end_date=filter_state["end_date"],
            personel_id=filter_state["personel_id"],
            kategori=filter_state["kategori"],
            search=filter_state["search"],
            sort_order=filter_state["sort_order"],
        )

        total_sum = sum([it["nominal"] for it in items])
        jalan_sum = sum([it["nominal"] for it in items if "jalan" in it["kategori_biaya"].lower() or "makan" in it["kategori_biaya"].lower() or "saku" in it["kategori_biaya"].lower()])
        bbm_sum = sum([it["nominal"] for it in items if "bbm" in it["kategori_biaya"].lower() or "bensin" in it["kategori_biaya"].lower() or "tol" in it["kategori_biaya"].lower() or "parkir" in it["kategori_biaya"].lower()])
        personel_list_all = get_personel_list(cabang_id=filter_state["cabang_id"])
        active_personel_count = len([p for p in personel_list_all if p.get("status") == "Aktif"])

        metric_total_card.content = metric_card(
            page,
            "Total Biaya Supir & Kenek",
            rp(total_sum),
            light_color=ft.Colors.RED_50,
            light_text_color=ft.Colors.RED_900,
            dark_color=ft.Colors.RED_900,
            dark_text_color=ft.Colors.RED_100,
        )
        metric_jalan_card.content = metric_card(
            page,
            "Uang Jalan & Makan",
            rp(jalan_sum),
            light_color=ft.Colors.ORANGE_50,
            light_text_color=ft.Colors.ORANGE_900,
            dark_color=ft.Colors.ORANGE_900,
            dark_text_color=ft.Colors.ORANGE_100,
        )
        metric_bbm_card.content = metric_card(
            page,
            "BBM & Tol / Parkir",
            rp(bbm_sum),
            light_color=ft.Colors.BLUE_50,
            light_text_color=ft.Colors.BLUE_900,
            dark_color=ft.Colors.BLUE_900,
            dark_text_color=ft.Colors.BLUE_100,
        )
        metric_count_card.content = metric_card(
            page,
            "Personel Aktif / Transaksi",
            f"{active_personel_count} Org · {len(items)} Trx",
            light_color=ft.Colors.GREY_100,
            light_text_color=ft.Colors.GREY_900,
            dark_color=ft.Colors.GREY_800,
            dark_text_color=ft.Colors.WHITE,
        )

        if not items:
            table_exp_container.content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.LOCAL_SHIPPING_OUTLINED, size=48, color=ft.Colors.GREY_400),
                    ft.Container(height=8),
                    ft.Text("Tidak ada data operasional", size=15, weight=ft.FontWeight.W_500),
                    ft.Text("Klik 'Catat Pengeluaran' untuk menambahkan biaya baru.", size=12, color=ft.Colors.GREY_500),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment.CENTER,
                padding=40,
                border_radius=10,
                border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
                bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
            )
        else:
            columns = [
                ft.DataColumn(
                    ft.Text("Tanggal"),
                    on_sort=lambda e: on_sort_exp_tanggal(0, e.ascending),
                ),
            ]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend([
                ft.DataColumn(ft.Text("Nama Personel")),
                ft.DataColumn(ft.Text("Peran")),
                ft.DataColumn(ft.Text("Kategori")),
                ft.DataColumn(ft.Text("Keterangan / Rute")),
                ft.DataColumn(ft.Text("Nominal")),
                ft.DataColumn(ft.Text("Nota")),
                ft.DataColumn(ft.Text("Aksi")),
            ])

            dt = ft.DataTable(
                sort_column_index=0,
                sort_ascending=(filter_state["sort_order"] == "asc"),
                columns=columns,
                rows=build_exp_table_rows(items),
                border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200),
                border_radius=10,
                heading_row_color=ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100,
                show_bottom_border=True,
            )
            table_exp_container.content = ft.Row([dt], scroll=ft.ScrollMode.AUTO)
        if page.views:
            page.update()

    def refresh_personel_table():
        personel_list = get_personel_list(cabang_id=None if is_pusat else actor.get("cabang_id"))
        if not personel_list:
            table_personel_container.content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=48, color=ft.Colors.GREY_400),
                    ft.Container(height=8),
                    ft.Text("Belum ada data personel", size=15, weight=ft.FontWeight.W_500),
                    ft.Text("Klik 'Tambah Personel' untuk mendaftarkan supir atau kenek baru.", size=12, color=ft.Colors.GREY_500),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment.CENTER,
                padding=40,
                border_radius=10,
                border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
                bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
            )
        else:
            rows = []
            for p in personel_list:
                is_active = p.get("status") == "Aktif"
                is_supir = "supir" in p["peran"].lower()

                cells = [
                    ft.DataCell(ft.Text(str(p["id"]), size=12, color=ft.Colors.GREY_500)),
                    ft.DataCell(ft.Text(p["nama"], size=13, weight=ft.FontWeight.W_600)),
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(
                                p["peran"],
                                size=11,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.BLUE_700 if is_supir else ft.Colors.TEAL_700,
                            ),
                            bgcolor=ft.Colors.BLUE_50 if is_supir else ft.Colors.TEAL_50,
                            padding=ft.Padding.symmetric(vertical=3, horizontal=8),
                            border_radius=6,
                        )
                    ),
                    ft.DataCell(ft.Text(p["no_telp"] or "-", size=13)),
                    ft.DataCell(ft.Text(p["armada"] or "-", size=13)),
                ]
                if is_pusat:
                    cells.append(ft.DataCell(ft.Text(p.get("nama_cabang", "-"), size=13)))

                cells.extend([
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(
                                "Aktif" if is_active else "Nonaktif",
                                size=11,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.GREEN_700 if is_active else ft.Colors.GREY_600,
                            ),
                            bgcolor=ft.Colors.GREEN_50 if is_active else ft.Colors.GREY_200,
                            padding=ft.Padding.symmetric(vertical=3, horizontal=8),
                            border_radius=6,
                        )
                    ),
                    ft.DataCell(
                        ft.Row([
                            ft.IconButton(
                                ft.Icons.EDIT,
                                icon_size=18,
                                tooltip="Edit Personel",
                                on_click=lambda e, item=p: open_edit_personel_dialog(item),
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_size=18,
                                icon_color=ft.Colors.RED_400,
                                tooltip="Hapus Personel",
                                on_click=lambda e, item=p: open_delete_personel_dialog(item),
                            ),
                        ], spacing=2)
                    ),
                ])
                rows.append(ft.DataRow(cells=cells))

            columns = [
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Nama")),
                ft.DataColumn(ft.Text("Peran")),
                ft.DataColumn(ft.Text("Kontak / HP")),
                ft.DataColumn(ft.Text("Armada / Plat")),
            ]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend([
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Aksi")),
            ])

            dt = ft.DataTable(
                columns=columns,
                rows=rows,
                border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200),
                border_radius=10,
                heading_row_color=ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100,
                show_bottom_border=True,
            )
            table_personel_container.content = ft.Row([dt], scroll=ft.ScrollMode.AUTO)
        if page.views:
            page.update()

    def get_filtered_data():
        return get_pengeluaran_supir_kenek(
            cabang_id=filter_state["cabang_id"],
            start_date=filter_state["start_date"],
            end_date=filter_state["end_date"],
            personel_id=filter_state["personel_id"],
            kategori=filter_state["kategori"],
            search=filter_state["search"],
            sort_order=filter_state["sort_order"],
        )

    # Export PDF Picker & Handler
    export_picker = ft.FilePicker()
    if export_picker not in page.services:
        page.services.append(export_picker)

    async def export_pdf(e):
        items = get_filtered_data()
        if not items:
            page.show_dialog(ft.SnackBar(ft.Text("Tidak ada data pengeluaran supir/kenek untuk diexport."), bgcolor=ft.Colors.RED_400))
            return

        cbg_name = "Semua Cabang"
        if filter_state["cabang_id"]:
            cbg_name = next((c[1] for c in cabang_list if c[0] == filter_state["cabang_id"]), f"Cabang {filter_state['cabang_id']}")
        elif not is_pusat:
            cbg_name = actor.get("nama_cabang", "Cabang")

        periode_str = "Semua Periode"
        if filter_state["start_date"] and filter_state["end_date"]:
            periode_str = f"{filter_state['start_date'].strftime('%d-%m-%Y')} s/d {filter_state['end_date'].strftime('%d-%m-%Y')}"
        elif filter_state["start_date"]:
            periode_str = f"Mulai {filter_state['start_date'].strftime('%d-%m-%Y')}"
        elif filter_state["end_date"]:
            periode_str = f"Sampai {filter_state['end_date'].strftime('%d-%m-%Y')}"

        personel_name = "Semua Personel"
        if filter_state["personel_id"]:
            p_obj = next((p for p in personel_cached if p["id"] == filter_state["personel_id"]), None)
            if p_obj:
                personel_name = f"{p_obj['nama']} ({p_obj['peran']})"

        filter_info = {
            "periode": periode_str,
            "cabang": cbg_name,
            "extra": f"Personel: {personel_name} | Total: {len(items)} Trx",
        }

        nama_file_default = f"Laporan_Operasional_SupirKenek_{today.strftime('%Y%m%d')}.pdf"
        try:
            if page.platform == ft.PagePlatform.ANDROID or page.platform == ft.PagePlatform.IOS:
                pdf_bytes = generate_supir_kenek_pdf(items, filter_info, is_pusat=is_pusat, output_path=None)
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Supir & Kenek PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
                if not save_path:
                    return
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Supir & Kenek PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if not save_path:
                    return
                if not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                generate_supir_kenek_pdf(items, filter_info, is_pusat=is_pusat, output_path=save_path)

            log_activity(
                actor.get("id"),
                actor.get("username", "user"),
                "CREATE",
                "export_pdf",
                filter_state.get("cabang_id") or 0,
                f"Export PDF Operasional Supir & Kenek ({periode_str})",
                filter_state.get("cabang_id"),
            )
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    # Initial data
    refresh_table_content()
    refresh_personel_table()

    # Tabs
    tab_views = [
        ft.Container(
            content=ft.Column([
                ft.Container(height=8),
                filter_card,
                ft.Container(height=16),
                ft.Row([
                    ft.Text("Daftar Transaksi Operasional", size=16, weight=ft.FontWeight.W_500, expand=True),
                ]),
                ft.Container(height=8),
                table_exp_container,
            ], spacing=0),
            padding=ft.Padding.only(top=12),
        ),
        ft.Container(
            content=ft.Column([
                ft.Container(height=8),
                ft.Row([
                    ft.Text("Daftar Supir & Kenek Terdaftar", size=16, weight=ft.FontWeight.W_500, expand=True),
                    ft.ElevatedButton(
                        "Tambah Personel",
                        icon=ft.Icons.PERSON_ADD,
                        on_click=open_add_personel_dialog,
                        bgcolor=ft.Colors.BLUE_700,
                        color=ft.Colors.WHITE,
                    ),
                ]),
                ft.Container(height=8),
                table_personel_container,
            ], spacing=0),
            padding=ft.Padding.only(top=12),
        ),
    ]

    active_tab_container = ft.Container(content=tab_views[0])

    def on_tab_change(e):
        idx = int(e.data)
        active_tab_container.content = tab_views[idx]
        active_tab_container.update()

    tabs = ft.Tabs(
        length=2,
        selected_index=0,
        animation_duration=200,
        on_change=on_tab_change,
        content=ft.TabBar(
            tabs=[
                ft.Tab(label="Catatan Pengeluaran Operasional", icon=ft.Icons.RECEIPT_LONG),
                ft.Tab(label="Daftar Supir & Kenek (Master)", icon=ft.Icons.BADGE_OUTLINED),
            ]
        ),
    )

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Operasional Supir & Kenek", size=22, weight=ft.FontWeight.W_600),
                ft.Text("Pencatatan pengeluaran operasional supir, kenek, uang jalan, BBM, tol, dan master personel.", size=13, color=ft.Colors.GREY_500),
            ], expand=True),
            ft.OutlinedButton(
                "Export ke PDF",
                icon=ft.Icons.PICTURE_AS_PDF,
                on_click=export_pdf,
            ),
            ft.ElevatedButton(
                "Catat Pengeluaran",
                icon=ft.Icons.ADD,
                on_click=open_add_exp_dialog,
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
            ft.OutlinedButton(
                "Tambah Personel",
                icon=ft.Icons.PERSON_ADD,
                on_click=open_add_personel_dialog,
            ),
            ft.IconButton(
                ft.Icons.REFRESH,
                tooltip="Segarkan Data",
                on_click=lambda e: (refresh_personel_dropdown(), refresh_table_content(), refresh_personel_table()),
            ),
        ]),
        ft.Container(height=8),
        ft.ResponsiveRow([
            metric_total_card,
            metric_jalan_card,
            metric_bbm_card,
            metric_count_card,
        ], spacing=12, run_spacing=12),
        ft.Container(height=12),
        tabs,
        active_tab_container,
        ft.Container(height=24),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return body
