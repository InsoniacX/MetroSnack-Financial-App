from datetime import date
from decimal import Decimal

import flet as ft

from components.appbar import is_mobile_layout
from components.metric_card import metric_card
from db.activity_repo import log_activity
from db.cabang_repo import get_active_cabang
from db.supir_kenek_repo import (
    add_pengeluaran_supir_kenek,
    add_personel,
    delete_pengeluaran_supir_kenek,
    get_pengeluaran_supir_kenek,
    get_personel_list,
    set_personel_aktif,
    update_pengeluaran_supir_kenek,
    update_personel,
)
from state import app_state
from utils.formatting import rp
from utils.pdf_export import generate_supir_kenek_pdf
from utils.validation import parse_date, parse_positive_decimal, require_text


def build_view(page: ft.Page):
    actor = app_state.user or {}
    is_pusat = actor.get("cabang_id") is None
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    mobile = is_mobile_layout(page)
    today = date.today()

    page_width = getattr(page, "width", None) or 1100
    exp_dialog_width = min(500, max(260, page_width - 72))
    personel_dialog_width = min(380, max(260, page_width - 72))
    card_padding = 12 if mobile else 16
    state_padding = 24 if mobile else 40

    filter_state = {
        "start_date": None,
        "end_date": None,
        "personel_id": None,
        "cabang_id": None if is_pusat else actor.get("cabang_id"),
        "search": "",
        "sort_order": "desc",
    }

    cabang_list = []
    cabang_load_error = None

    if is_pusat:
        try:
            cabang_list = get_active_cabang()
            if not cabang_list:
                cabang_load_error = "Belum ada cabang aktif."
        except Exception as error:
            cabang_load_error = (
                f"Daftar cabang gagal dimuat: {error}"
            )

    def close_dialog(e=None):
        del e
        page.pop_dialog()
        page.update()

    # ---------------------------------------------------------------------
    # Dialog tambah dan edit pengeluaran operasional mobil
    # ---------------------------------------------------------------------
    exp_id_target = {"id": None}
    personel_cached = []

    try:
        personel_cached = get_personel_list(
            cabang_id=filter_state["cabang_id"],
            active_only=True,
        )
    except Exception:
        personel_cached = []

    exp_tanggal = ft.TextField(
        label="Tanggal (YYYY-MM-DD)",
        value=today.isoformat(),
        col={"xs": 12, "sm": 6},
    )

    exp_supir_dropdown = ft.Dropdown(
        label="Supir *",
        options=[
            ft.dropdown.Option(str(person["id"]), person["nama"])
            for person in personel_cached
        ],
        value=str(personel_cached[0]["id"]) if personel_cached else "",
        col={"xs": 12, "sm": 6},
    )

    exp_kenek_dropdown = ft.Dropdown(
        label="Kenek (Opsional)",
        options=[ft.dropdown.Option("", "Tanpa Kenek")]
        + [
            ft.dropdown.Option(str(person["id"]), person["nama"])
            for person in personel_cached
        ],
        value="",
        col={"xs": 12, "sm": 6},
    )

    exp_uang_jalan = ft.TextField(
        label="Uang Jalan / Operasional (Rp) *",
        value="",
        hint_text="Contoh: 150000 atau 150.000",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )

    exp_keterangan = ft.TextField(
        label="Keterangan / Rute / Catatan",
        multiline=True,
        min_lines=2,
        max_lines=3,
        col={"xs": 12},
    )

    exp_cabang_dropdown = ft.Dropdown(
        label="Cabang",
        options=[ft.dropdown.Option(str(cabang[0]), cabang[1]) for cabang in cabang_list],
        value=None,
        col={"xs": 12, "sm": 6},
    )

    def resolve_cabang_id(dropdown):
        if not is_pusat:
            cabang_id = actor.get("cabang_id")
            if cabang_id is None:
                raise ValueError(
                    "Akun ini belum terhubung dengan cabang."
                )
            return int(cabang_id)

        if cabang_load_error:
            raise ValueError(cabang_load_error)

        if not cabang_list:
            raise ValueError("Tidak ada cabang aktif yang dapat dipilih.")

        selected_value = dropdown.value
        if not selected_value:
            raise ValueError("Silakan pilih cabang terlebih dahulu.")

        try:
            cabang_id = int(selected_value)
        except (TypeError, ValueError) as error:
            raise ValueError("Cabang yang dipilih tidak valid.") from error

        valid_cabang_ids = {
            int(cabang[0])
            for cabang in cabang_list
        }

        if cabang_id not in valid_cabang_ids:
            raise ValueError(
                "Cabang yang dipilih tidak tersedia atau sudah tidak aktif."
            )

        return cabang_id

    def refresh_personel_dropdown():
        nonlocal personel_cached

        try:
            cabang_id = None if is_pusat else actor.get("cabang_id")
            personel_cached = get_personel_list(
                cabang_id=cabang_id,
                active_only=True,
            )
        except Exception:
            personel_cached = []

        if is_pusat:
            supir_options = [
                ft.dropdown.Option(
                    str(person["id"]),
                    (
                        f"{person['nama']} "
                        f"({person.get('nama_cabang', 'Pusat')})"
                        if person.get("nama_cabang")
                        else person["nama"]
                    ),
                )
                for person in personel_cached
            ]
            kenek_options = [ft.dropdown.Option("", "Tanpa Kenek")] + [
                ft.dropdown.Option(
                    str(person["id"]),
                    (
                        f"{person['nama']} "
                        f"({person.get('nama_cabang', 'Pusat')})"
                        if person.get("nama_cabang")
                        else person["nama"]
                    ),
                )
                for person in personel_cached
            ]
        else:
            supir_options = [
                ft.dropdown.Option(str(person["id"]), person["nama"])
                for person in personel_cached
            ]
            kenek_options = [ft.dropdown.Option("", "Tanpa Kenek")] + [
                ft.dropdown.Option(str(person["id"]), person["nama"])
                for person in personel_cached
            ]

        exp_supir_dropdown.options = supir_options
        exp_kenek_dropdown.options = kenek_options

        valid_personel_ids = [str(person["id"]) for person in personel_cached]
        if personel_cached and exp_supir_dropdown.value not in valid_personel_ids:
            exp_supir_dropdown.value = str(personel_cached[0]["id"])

        try:
            all_personel = get_personel_list(
                cabang_id=filter_state["cabang_id"]
            )
        except Exception:
            all_personel = []

        filter_personel_dropdown.options = [
            ft.dropdown.Option("Semua", "Semua Supir/Kenek")
        ] + [
            ft.dropdown.Option(
                str(person["id"]),
                (
                    f"{person['nama']} "
                    f"({person.get('nama_cabang', 'Pusat')}) - "
                    f"{'Aktif' if person['aktif'] else 'Nonaktif'}"
                    if is_pusat and person.get("nama_cabang")
                    else (
                        f"{person['nama']} "
                        f"({'Aktif' if person['aktif'] else 'Nonaktif'})"
                    )
                ),
            )
            for person in all_personel
        ]

    def submit_exp_form(e):
        del e
        try:
            tanggal = parse_date("Tanggal", exp_tanggal.value)
            uang_jalan = parse_positive_decimal(
                "Uang Jalan",
                exp_uang_jalan.value,
                allow_zero=False,
                max_digits=14,
                decimal_places=2,
            )
            keterangan = (exp_keterangan.value or "").strip()

            if not exp_supir_dropdown.value:
                raise ValueError("Silakan pilih Supir terlebih dahulu.")

            supir_id = int(exp_supir_dropdown.value)
            kenek_id = (
                int(exp_kenek_dropdown.value)
                if exp_kenek_dropdown.value
                else None
            )

            cabang_id = resolve_cabang_id(exp_cabang_dropdown)

            is_edit = exp_id_target["id"] is not None
            if is_edit:
                update_pengeluaran_supir_kenek(
                    pengeluaran_id=exp_id_target["id"],
                    tanggal=tanggal,
                    supir_id=supir_id,
                    kenek_id=kenek_id,
                    uang_jalan=uang_jalan,
                    keterangan=keterangan,
                )
                success_message = (
                    "Catatan operasional mobil berhasil diperbarui!"
                )
            else:
                add_pengeluaran_supir_kenek(
                    tanggal=tanggal,
                    supir_id=supir_id,
                    kenek_id=kenek_id,
                    uang_jalan=uang_jalan,
                    keterangan=keterangan,
                    cabang_id=cabang_id,
                )
                success_message = (
                    "Catatan operasional mobil berhasil disimpan!"
                )

            close_dialog()
            refresh_table_content()
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(success_message),
                    bgcolor=ft.Colors.GREEN_700,
                )
            )
        except ValueError as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(str(error)),
                    bgcolor=ft.Colors.RED_400,
                )
            )
        except Exception as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal simpan: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    exp_dialog_title = ft.Text(
        "Catat Operasional Mobil / Perjalanan",
        weight=ft.FontWeight.W_500,
    )

    exp_form_controls = [
        exp_tanggal,
        exp_uang_jalan,
        exp_supir_dropdown,
        exp_kenek_dropdown,
        exp_keterangan,
    ]
    if is_pusat:
        exp_form_controls.append(exp_cabang_dropdown)

    exp_dialog = ft.AlertDialog(
        modal=True,
        title=exp_dialog_title,
        content=ft.Container(
            content=ft.ResponsiveRow(
                exp_form_controls,
                spacing=10,
                run_spacing=10,
            ),
            width=exp_dialog_width,
        ),
        content_padding=ft.Padding.only(
            left=16,
            right=16,
            top=8,
            bottom=8,
        ),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Simpan",
                on_click=submit_exp_form,
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def open_add_exp_dialog(e=None):
        del e
        refresh_personel_dropdown()
        if not personel_cached:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(
                        "Belum ada supir/kenek aktif di cabang ini. "
                        "Tambahkan di tab Master terlebih dahulu."
                    ),
                    bgcolor=ft.Colors.ORANGE_800,
                )
            )
            return

        exp_id_target["id"] = None
        exp_dialog_title.value = "Catat Operasional Mobil / Perjalanan"
        exp_tanggal.value = date.today().isoformat()
        exp_uang_jalan.value = ""
        exp_keterangan.value = ""
        exp_kenek_dropdown.value = ""
        if is_pusat:
            exp_cabang_dropdown.value = None
        page.show_dialog(exp_dialog)

    def open_edit_exp_dialog(item):
        refresh_personel_dropdown()
        exp_id_target["id"] = item["id"]
        exp_dialog_title.value = f"Edit Catatan Operasional #{item['id']}"
        exp_tanggal.value = (
            item["tanggal"].isoformat()
            if hasattr(item["tanggal"], "isoformat")
            else str(item["tanggal"])
        )
        exp_supir_dropdown.value = str(item["supir_id"])
        exp_kenek_dropdown.value = (
            str(item["kenek_id"]) if item.get("kenek_id") else ""
        )
        exp_uang_jalan.value = str(item["uang_jalan"])
        exp_keterangan.value = item["keterangan"] or ""
        if is_pusat:
            exp_cabang_dropdown.value = str(item["cabang_id"])
        page.show_dialog(exp_dialog)

    # ---------------------------------------------------------------------
    # Dialog tambah dan edit master personel
    # ---------------------------------------------------------------------
    personel_id_target = {"id": None}

    personel_nama = ft.TextField(
        label="Nama Lengkap Supir / Kenek *",
        col={"xs": 12},
    )

    personel_cabang_dropdown = ft.Dropdown(
        label="Cabang Penugasan",
        options=[ft.dropdown.Option(str(cabang[0]), cabang[1]) for cabang in cabang_list],
        value=None,
        col={"xs": 12},
    )

    def submit_personel_form(e):
        del e
        try:
            nama = require_text(
                "Nama Supir/Kenek",
                personel_nama.value,
                max_length=100,
            )

            cabang_id = resolve_cabang_id(
                personel_cabang_dropdown
            )

            is_edit = personel_id_target["id"] is not None
            if is_edit:
                update_personel(
                    personel_id=personel_id_target["id"],
                    nama=nama,
                )
                success_message = (
                    f"Data personel '{nama}' berhasil diperbarui!"
                )
            else:
                add_personel(nama=nama, cabang_id=cabang_id)
                success_message = f"Personel '{nama}' berhasil didaftarkan!"

            close_dialog()
            refresh_personel_dropdown()
            refresh_table_content()
            refresh_personel_table()
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(success_message),
                    bgcolor=ft.Colors.GREEN_700,
                )
            )
        except ValueError as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(str(error)),
                    bgcolor=ft.Colors.RED_400,
                )
            )
        except Exception as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal simpan personel: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    personel_dialog_title = ft.Text(
        "Tambah Supir / Kenek",
        weight=ft.FontWeight.W_500,
    )

    personel_form_controls = [personel_nama]
    if is_pusat:
        personel_form_controls.append(personel_cabang_dropdown)

    personel_dialog = ft.AlertDialog(
        modal=True,
        title=personel_dialog_title,
        content=ft.Container(
            content=ft.ResponsiveRow(
                personel_form_controls,
                spacing=10,
                run_spacing=10,
            ),
            width=personel_dialog_width,
        ),
        content_padding=ft.Padding.only(
            left=16,
            right=16,
            top=8,
            bottom=8,
        ),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Simpan",
                on_click=submit_personel_form,
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def open_add_personel_dialog(e=None):
        del e
        personel_id_target["id"] = None
        personel_dialog_title.value = "Tambah Supir / Kenek"
        personel_nama.value = ""
        if is_pusat:
            personel_cabang_dropdown.value = None
        page.show_dialog(personel_dialog)

    def open_edit_personel_dialog(item):
        personel_id_target["id"] = item["id"]
        personel_dialog_title.value = f"Edit Nama Personel #{item['id']}"
        personel_nama.value = item["nama"]
        if is_pusat:
            personel_cabang_dropdown.value = str(item["cabang_id"])
        page.show_dialog(personel_dialog)

    def toggle_personel_status(item):
        try:
            new_status = not item["aktif"]
            set_personel_aktif(item["id"], new_status)
            status_text = "diaktifkan" if new_status else "dinonaktifkan"
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(
                        f"Status '{item['nama']}' berhasil {status_text}!"
                    ),
                    bgcolor=ft.Colors.GREEN_700,
                )
            )
            refresh_personel_dropdown()
            refresh_personel_table()
        except Exception as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal mengubah status: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    # ---------------------------------------------------------------------
    # Dialog konfirmasi hapus
    # ---------------------------------------------------------------------
    delete_target = {"id": None}
    delete_message = ft.Text("")

    def confirm_general_delete(e):
        del e
        try:
            delete_pengeluaran_supir_kenek(delete_target["id"])
            close_dialog()
            refresh_table_content()
            page.show_dialog(
                ft.SnackBar(
                    ft.Text("Catatan operasional berhasil dihapus!"),
                    bgcolor=ft.Colors.GREEN_700,
                )
            )
        except Exception as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal menghapus: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Konfirmasi Hapus Data"),
        content=delete_message,
        inset_padding=12 if mobile else 40,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Ya, Hapus",
                on_click=confirm_general_delete,
                bgcolor=ft.Colors.RED_600,
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def open_delete_exp_dialog(item):
        delete_target["id"] = item["id"]
        delete_message.value = (
            f"Hapus catatan operasional {item['nama_supir']} senilai "
            f"{rp(item['uang_jalan'])} pada tanggal {item['tanggal']}?"
        )
        page.show_dialog(delete_dialog)

    # ---------------------------------------------------------------------
    # Filter operasional
    # ---------------------------------------------------------------------
    filter_start_field = ft.TextField(
        label="Dari Tanggal (YYYY-MM-DD)",
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    filter_end_field = ft.TextField(
        label="Sampai Tanggal (YYYY-MM-DD)",
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    filter_sort_dropdown = ft.Dropdown(
        label="Urutan Tanggal",
        options=[
            ft.dropdown.Option("desc", "Terbaru (Desc)"),
            ft.dropdown.Option("asc", "Terlama (Asc)"),
        ],
        value="desc",
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    filter_personel_dropdown = ft.Dropdown(
        label="Supir / Kenek",
        options=[ft.dropdown.Option("Semua", "Semua Supir/Kenek")],
        value="Semua",
        col={"xs": 12, "sm": 6, "lg": 3},
    )

    search_field = ft.TextField(
        label="Cari Transaksi",
        hint_text="Nama supir, kenek, rute, keterangan...",
        prefix_icon=ft.Icons.SEARCH,
        value=filter_state["search"],
        col={"xs": 12, "sm": 12, "lg": 3},
    )

    def apply_filter(e=None):
        del e
        try:
            filter_state["start_date"] = (
                parse_date("Dari Tanggal", filter_start_field.value)
                if filter_start_field.value
                else None
            )
        except Exception:
            filter_state["start_date"] = None

        try:
            filter_state["end_date"] = (
                parse_date("Sampai Tanggal", filter_end_field.value)
                if filter_end_field.value
                else None
            )
        except Exception:
            filter_state["end_date"] = None

        filter_state["sort_order"] = filter_sort_dropdown.value or "desc"

        selected_personel = filter_personel_dropdown.value
        filter_state["personel_id"] = (
            None
            if selected_personel == "Semua" or not selected_personel
            else int(selected_personel)
        )

        filter_state["search"] = search_field.value or ""
        refresh_table_content()

    def reset_filter(e=None):
        del e
        filter_start_field.value = ""
        filter_end_field.value = ""
        filter_sort_dropdown.value = "desc"
        filter_personel_dropdown.value = "Semua"
        search_field.value = ""
        apply_filter()

    search_field.on_submit = apply_filter
    filter_sort_dropdown.on_change = apply_filter
    filter_personel_dropdown.on_change = apply_filter

    filter_title = ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.FILTER_LIST,
                    size=20,
                    color=ft.Colors.BLUE_700,
                ),
                ft.Text(
                    "Filter Data Operasional Mobil",
                    weight=ft.FontWeight.W_500,
                    size=15,
                ),
            ],
            spacing=8,
        ),
        col={"xs": 12, "md": 6},
    )

    filter_actions = ft.Container(
        content=ft.Row(
            [
                ft.TextButton(
                    "Reset Filter",
                    icon=ft.Icons.RESTART_ALT,
                    on_click=reset_filter,
                ),
                ft.ElevatedButton(
                    "Terapkan",
                    icon=ft.Icons.CHECK,
                    on_click=apply_filter,
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                ),
            ],
            wrap=True,
            spacing=6,
            run_spacing=6,
            alignment=(
                ft.MainAxisAlignment.START
                if mobile
                else ft.MainAxisAlignment.END
            ),
        ),
        col={"xs": 12, "md": 6},
    )

    filter_card = ft.Container(
        content=ft.Column(
            [
                ft.ResponsiveRow(
                    [filter_title, filter_actions],
                    spacing=8,
                    run_spacing=8,
                ),
                ft.Divider(height=1),
                ft.ResponsiveRow(
                    [
                        filter_start_field,
                        filter_end_field,
                        filter_sort_dropdown,
                        filter_personel_dropdown,
                        search_field,
                    ],
                    spacing=10,
                    run_spacing=10,
                ),
            ],
            spacing=10,
        ),
        bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
        border=ft.Border.all(
            0.5,
            ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
        ),
        border_radius=10,
        padding=card_padding,
    )

    # ---------------------------------------------------------------------
    # Metrik dan tabel
    # ---------------------------------------------------------------------
    metric_total_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_trip_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_avg_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_personel_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    table_exp_container = ft.Container()
    table_personel_container = ft.Container()

    def on_sort_exp_tanggal(column_index, ascending):
        del column_index
        filter_state["sort_order"] = "asc" if ascending else "desc"
        filter_sort_dropdown.value = filter_state["sort_order"]
        refresh_table_content()

    def build_exp_table_rows(items):
        rows = []
        for item in items:
            tanggal_text = (
                item["tanggal"].strftime("%d-%m-%Y")
                if hasattr(item["tanggal"], "strftime")
                else str(item["tanggal"])
            )

            cells = [ft.DataCell(ft.Text(tanggal_text, size=13))]
            if is_pusat:
                cells.append(
                    ft.DataCell(
                        ft.Text(item.get("nama_cabang", "-"), size=13)
                    )
                )

            cells.extend(
                [
                    ft.DataCell(
                        ft.Text(
                            item["nama_supir"],
                            size=13,
                            weight=ft.FontWeight.W_600,
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            item["nama_kenek"]
                            if item.get("nama_kenek")
                            else "-",
                            size=13,
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            rp(item["uang_jalan"]),
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=(
                                ft.Colors.RED_400
                                if is_dark
                                else ft.Colors.RED_700
                            ),
                        )
                    ),
                    ft.DataCell(
                        ft.Text(item["keterangan"] or "-", size=13)
                    ),
                    ft.DataCell(
                        ft.Text(
                            item.get("username") or "-",
                            size=12,
                            color=ft.Colors.GREY_500,
                        )
                    ),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.IconButton(
                                    ft.Icons.EDIT,
                                    icon_size=18,
                                    tooltip="Edit Catatan",
                                    on_click=(
                                        lambda e, selected=item: (
                                            open_edit_exp_dialog(selected)
                                        )
                                    ),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    icon_size=18,
                                    icon_color=ft.Colors.RED_400,
                                    tooltip="Hapus Catatan",
                                    on_click=(
                                        lambda e, selected=item: (
                                            open_delete_exp_dialog(selected)
                                        )
                                    ),
                                ),
                            ],
                            spacing=2,
                        )
                    ),
                ]
            )
            rows.append(ft.DataRow(cells=cells))

        return rows

    def refresh_table_content():
        try:
            items = get_pengeluaran_supir_kenek(
                cabang_id=filter_state["cabang_id"],
                start_date=filter_state["start_date"],
                end_date=filter_state["end_date"],
                personel_id=filter_state["personel_id"],
                search=filter_state["search"],
                sort_order=filter_state["sort_order"],
            )
        except Exception as error:
            items = []
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Error memuat data: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

        total_sum = sum(
            (item["uang_jalan"] for item in items),
            Decimal(0),
        )
        total_trips = len(items)
        average_sum = (
            total_sum / total_trips if total_trips > 0 else Decimal(0)
        )

        personel_list_all = get_personel_list(
            cabang_id=filter_state["cabang_id"]
        )
        active_personel_count = len(
            [person for person in personel_list_all if person.get("aktif")]
        )

        metric_total_card.content = metric_card(
            page,
            "Total Uang Jalan",
            rp(total_sum),
            light_color=ft.Colors.RED_50,
            light_text_color=ft.Colors.RED_900,
            dark_color=ft.Colors.RED_900,
            dark_text_color=ft.Colors.RED_100,
        )
        metric_trip_card.content = metric_card(
            page,
            "Total Perjalanan / Trip",
            f"{total_trips} Trip",
            light_color=ft.Colors.BLUE_50,
            light_text_color=ft.Colors.BLUE_900,
            dark_color=ft.Colors.BLUE_900,
            dark_text_color=ft.Colors.BLUE_100,
        )
        metric_avg_card.content = metric_card(
            page,
            "Rata-rata Uang Jalan",
            rp(average_sum),
            light_color=ft.Colors.ORANGE_50,
            light_text_color=ft.Colors.ORANGE_900,
            dark_color=ft.Colors.ORANGE_900,
            dark_text_color=ft.Colors.ORANGE_100,
        )
        metric_personel_card.content = metric_card(
            page,
            "Supir & Kenek Aktif",
            f"{active_personel_count} Orang",
            light_color=ft.Colors.GREEN_50,
            light_text_color=ft.Colors.GREEN_900,
            dark_color=ft.Colors.GREEN_900,
            dark_text_color=ft.Colors.GREEN_100,
        )

        state_border = ft.Border.all(
            0.5,
            ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
        )
        state_background = ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE

        if not items:
            table_exp_container.content = ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.LOCAL_SHIPPING_OUTLINED,
                            size=48,
                            color=ft.Colors.GREY_400,
                        ),
                        ft.Container(height=8),
                        ft.Text(
                            "Tidak ada data operasional mobil",
                            size=15,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Klik 'Catat Operasional' untuk menambahkan "
                            "perjalanan baru.",
                            size=12,
                            color=ft.Colors.GREY_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                padding=state_padding,
                border_radius=10,
                border=state_border,
                bgcolor=state_background,
            )
        else:
            columns = [
                ft.DataColumn(
                    ft.Text("Tanggal"),
                    on_sort=lambda e: on_sort_exp_tanggal(0, e.ascending),
                )
            ]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend(
                [
                    ft.DataColumn(ft.Text("Supir")),
                    ft.DataColumn(ft.Text("Kenek")),
                    ft.DataColumn(ft.Text("Uang Jalan")),
                    ft.DataColumn(ft.Text("Keterangan / Rute")),
                    ft.DataColumn(ft.Text("Diinput Oleh")),
                    ft.DataColumn(ft.Text("Aksi")),
                ]
            )

            data_table = ft.DataTable(
                sort_column_index=0,
                sort_ascending=filter_state["sort_order"] == "asc",
                columns=columns,
                rows=build_exp_table_rows(items),
                border=ft.Border.all(
                    0.5,
                    ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200,
                ),
                border_radius=10,
                heading_row_color=(
                    ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100
                ),
                show_bottom_border=True,
            )

            table_controls = []
            if mobile:
                table_controls.append(
                    ft.Text(
                        "Geser tabel ke samping untuk melihat kolom lainnya.",
                        size=11,
                        color=ft.Colors.GREY_500,
                    )
                )
            table_controls.append(
                ft.Row([data_table], scroll=ft.ScrollMode.AUTO)
            )
            table_exp_container.content = ft.Column(
                table_controls,
                spacing=6,
            )

        if page.views:
            page.update()

    def refresh_personel_table():
        try:
            personel_list = get_personel_list(
                cabang_id=None if is_pusat else actor.get("cabang_id")
            )
        except Exception:
            personel_list = []

        state_border = ft.Border.all(
            0.5,
            ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
        )
        state_background = ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE

        if not personel_list:
            table_personel_container.content = ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.PEOPLE_OUTLINE,
                            size=48,
                            color=ft.Colors.GREY_400,
                        ),
                        ft.Container(height=8),
                        ft.Text(
                            "Belum ada data master supir/kenek",
                            size=15,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Klik 'Tambah Supir/Kenek' untuk mendaftarkan "
                            "nama personel baru.",
                            size=12,
                            color=ft.Colors.GREY_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                padding=state_padding,
                border_radius=10,
                border=state_border,
                bgcolor=state_background,
            )
        else:
            rows = []
            for person in personel_list:
                is_active = person.get("aktif", True)
                registered_date = (
                    person["created_at"].strftime("%d-%m-%Y")
                    if person.get("created_at")
                    else "-"
                )

                cells = [
                    ft.DataCell(
                        ft.Text(
                            str(person["id"]),
                            size=12,
                            color=ft.Colors.GREY_500,
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            person["nama"],
                            size=13,
                            weight=ft.FontWeight.W_600,
                        )
                    ),
                ]
                if is_pusat:
                    cells.append(
                        ft.DataCell(
                            ft.Text(
                                person.get("nama_cabang", "-"),
                                size=13,
                            )
                        )
                    )

                cells.extend(
                    [
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    "Aktif" if is_active else "Nonaktif",
                                    size=11,
                                    weight=ft.FontWeight.W_500,
                                    color=(
                                        ft.Colors.GREEN_700
                                        if is_active
                                        else ft.Colors.GREY_600
                                    ),
                                ),
                                bgcolor=(
                                    ft.Colors.GREEN_50
                                    if is_active
                                    else ft.Colors.GREY_200
                                ),
                                padding=ft.Padding.symmetric(
                                    vertical=3,
                                    horizontal=8,
                                ),
                                border_radius=6,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                registered_date,
                                size=12,
                                color=ft.Colors.GREY_600,
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        ft.Icons.EDIT,
                                        icon_size=18,
                                        tooltip="Ubah Nama",
                                        on_click=(
                                            lambda e, selected=person: (
                                                open_edit_personel_dialog(
                                                    selected
                                                )
                                            )
                                        ),
                                    ),
                                    ft.IconButton(
                                        (
                                            ft.Icons.TOGGLE_ON
                                            if is_active
                                            else ft.Icons.TOGGLE_OFF
                                        ),
                                        icon_size=22,
                                        icon_color=(
                                            ft.Colors.GREEN_600
                                            if is_active
                                            else ft.Colors.GREY_400
                                        ),
                                        tooltip=(
                                            "Nonaktifkan"
                                            if is_active
                                            else "Aktifkan"
                                        ),
                                        on_click=(
                                            lambda e, selected=person: (
                                                toggle_personel_status(selected)
                                            )
                                        ),
                                    ),
                                ],
                                spacing=2,
                            )
                        ),
                    ]
                )
                rows.append(ft.DataRow(cells=cells))

            columns = [
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Nama Supir / Kenek")),
            ]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend(
                [
                    ft.DataColumn(ft.Text("Status")),
                    ft.DataColumn(ft.Text("Terdaftar")),
                    ft.DataColumn(ft.Text("Aksi")),
                ]
            )

            data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                border=ft.Border.all(
                    0.5,
                    ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200,
                ),
                border_radius=10,
                heading_row_color=(
                    ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100
                ),
                show_bottom_border=True,
            )

            table_controls = []
            if mobile:
                table_controls.append(
                    ft.Text(
                        "Geser tabel ke samping untuk melihat kolom lainnya.",
                        size=11,
                        color=ft.Colors.GREY_500,
                    )
                )
            table_controls.append(
                ft.Row([data_table], scroll=ft.ScrollMode.AUTO)
            )
            table_personel_container.content = ft.Column(
                table_controls,
                spacing=6,
            )

        if page.views:
            page.update()

    def get_filtered_data():
        return get_pengeluaran_supir_kenek(
            cabang_id=filter_state["cabang_id"],
            start_date=filter_state["start_date"],
            end_date=filter_state["end_date"],
            personel_id=filter_state["personel_id"],
            search=filter_state["search"],
            sort_order=filter_state["sort_order"],
        )

    # ---------------------------------------------------------------------
    # Ekspor PDF
    # ---------------------------------------------------------------------
    export_picker = ft.FilePicker()
    if export_picker not in page.services:
        page.services.append(export_picker)

    async def export_pdf(e):
        del e
        items = get_filtered_data()
        if not items:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(
                        "Tidak ada data operasional mobil untuk diexport."
                    ),
                    bgcolor=ft.Colors.RED_400,
                )
            )
            return

        cabang_name = "Semua Cabang"
        if filter_state["cabang_id"]:
            cabang_name = next(
                (
                    cabang[1]
                    for cabang in cabang_list
                    if cabang[0] == filter_state["cabang_id"]
                ),
                f"Cabang {filter_state['cabang_id']}",
            )
        elif not is_pusat:
            cabang_name = actor.get("nama_cabang", "Cabang")

        period = "Semua Periode"
        if filter_state["start_date"] and filter_state["end_date"]:
            period = (
                f"{filter_state['start_date'].strftime('%d-%m-%Y')} s/d "
                f"{filter_state['end_date'].strftime('%d-%m-%Y')}"
            )
        elif filter_state["start_date"]:
            period = (
                f"Mulai {filter_state['start_date'].strftime('%d-%m-%Y')}"
            )
        elif filter_state["end_date"]:
            period = (
                f"Sampai {filter_state['end_date'].strftime('%d-%m-%Y')}"
            )

        personel_name = "Semua Supir/Kenek"
        if filter_state["personel_id"]:
            all_personel = get_personel_list(
                cabang_id=filter_state["cabang_id"]
            )
            selected_personel = next(
                (
                    person
                    for person in all_personel
                    if person["id"] == filter_state["personel_id"]
                ),
                None,
            )
            if selected_personel:
                personel_name = selected_personel["nama"]

        filter_info = {
            "periode": period,
            "cabang": cabang_name,
            "extra": (
                f"Personel: {personel_name} | Total: {len(items)} Trip"
            ),
        }

        default_file_name = (
            f"Laporan_Operasional_Mobil_{today.strftime('%Y%m%d')}.pdf"
        )

        try:
            if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
                pdf_bytes = generate_supir_kenek_pdf(
                    items,
                    filter_info,
                    is_pusat=is_pusat,
                    output_path=None,
                )
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Operasional Mobil PDF",
                    file_name=default_file_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
                if not save_path:
                    return
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Operasional Mobil PDF",
                    file_name=default_file_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if not save_path:
                    return
                if not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                generate_supir_kenek_pdf(
                    items,
                    filter_info,
                    is_pusat=is_pusat,
                    output_path=save_path,
                )

            log_activity(
                actor.get("id"),
                actor.get("username", "user"),
                "CREATE",
                "export_pdf",
                filter_state.get("cabang_id") or 0,
                f"Export PDF Operasional Mobil ({period})",
                filter_state.get("cabang_id"),
            )
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"PDF berhasil disimpan: {save_path}"),
                    bgcolor=ft.Colors.GREEN_700,
                )
            )
        except Exception as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal export PDF: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    refresh_personel_dropdown()
    refresh_table_content()
    refresh_personel_table()

    # ---------------------------------------------------------------------
    # Tabs
    # ---------------------------------------------------------------------
    operational_tab = ft.Container(
        content=ft.Column(
            [
                ft.Container(height=8),
                filter_card,
                ft.Container(height=16),
                ft.Text(
                    "Daftar Catatan Operasional Mobil / Perjalanan",
                    size=16,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(height=8),
                table_exp_container,
            ],
            spacing=0,
        ),
        padding=ft.Padding.only(top=12),
    )

    master_title = ft.Container(
        content=ft.Text(
            "Daftar Master Supir & Kenek",
            size=16,
            weight=ft.FontWeight.W_500,
        ),
        col={"xs": 12, "sm": 6},
    )

    master_action = ft.Container(
        content=ft.Row(
            [
                ft.ElevatedButton(
                    "Tambah" if mobile else "Tambah Supir/Kenek",
                    icon=ft.Icons.PERSON_ADD,
                    on_click=open_add_personel_dialog,
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                )
            ],
            alignment=(
                ft.MainAxisAlignment.START
                if mobile
                else ft.MainAxisAlignment.END
            ),
        ),
        col={"xs": 12, "sm": 6},
    )

    master_tab = ft.Container(
        content=ft.Column(
            [
                ft.Container(height=8),
                ft.ResponsiveRow(
                    [master_title, master_action],
                    spacing=8,
                    run_spacing=8,
                ),
                ft.Container(height=8),
                table_personel_container,
            ],
            spacing=0,
        ),
        padding=ft.Padding.only(top=12),
    )

    tab_views = [operational_tab, master_tab]
    active_tab_container = ft.Container(content=tab_views[0])

    def on_tab_change(e):
        selected_index = int(e.data)
        active_tab_container.content = tab_views[selected_index]
        active_tab_container.update()

    tabs = ft.Tabs(
        length=2,
        selected_index=0,
        animation_duration=200,
        on_change=on_tab_change,
        content=ft.TabBar(
            tabs=[
                ft.Tab(
                    label=(
                        "Operasional"
                        if mobile
                        else "Catatan Pengeluaran Operasional"
                    ),
                    icon=ft.Icons.RECEIPT_LONG,
                ),
                ft.Tab(
                    label=(
                        "Master Personel"
                        if mobile
                        else "Daftar Supir & Kenek (Master)"
                    ),
                    icon=ft.Icons.BADGE_OUTLINED,
                ),
            ]
        ),
    )

    header_title = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Operasional Supir & Kenek",
                    size=22,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    "Pencatatan pengeluaran operasional mobil/trip, uang "
                    "jalan, supir, kenek, dan master supir/kenek.",
                    size=13,
                    color=ft.Colors.GREY_500,
                ),
            ],
            spacing=2,
        ),
        col={"xs": 12, "lg": 5},
    )

    header_actions = ft.Container(
        content=ft.Row(
            [
                ft.OutlinedButton(
                    "Export PDF" if mobile else "Export ke PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=export_pdf,
                ),
                ft.ElevatedButton(
                    "Catat" if mobile else "Catat Operasional",
                    icon=ft.Icons.ADD,
                    on_click=open_add_exp_dialog,
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                ),
                ft.OutlinedButton(
                    "Personel" if mobile else "Tambah Supir/Kenek",
                    icon=ft.Icons.PERSON_ADD,
                    on_click=open_add_personel_dialog,
                ),
                ft.IconButton(
                    ft.Icons.REFRESH,
                    tooltip="Segarkan Data",
                    on_click=lambda e: (
                        refresh_personel_dropdown(),
                        refresh_table_content(),
                        refresh_personel_table(),
                    ),
                ),
            ],
            wrap=True,
            spacing=8,
            run_spacing=8,
            alignment=(
                ft.MainAxisAlignment.START
                if mobile
                else ft.MainAxisAlignment.END
            ),
        ),
        col={"xs": 12, "lg": 7},
    )

    return ft.Column(
        [
            ft.ResponsiveRow(
                [header_title, header_actions],
                spacing=8,
                run_spacing=8,
            ),
            ft.Container(height=8),
            ft.ResponsiveRow(
                [
                    metric_total_card,
                    metric_trip_card,
                    metric_avg_card,
                    metric_personel_card,
                ],
                spacing=12,
                run_spacing=12,
            ),
            ft.Container(height=12),
            tabs,
            active_tab_container,
            ft.Container(height=24),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

