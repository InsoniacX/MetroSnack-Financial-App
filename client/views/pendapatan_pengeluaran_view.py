from datetime import date
from decimal import Decimal

import flet as ft

from components.appbar import is_mobile_layout
from components.metric_card import metric_card
from db.activity_repo import log_activity
from db.cabang_repo import get_active_cabang
from db.pendapatan_pengeluaran_repo import (
    DEFAULT_KATEGORI_PENDAPATAN,
    DEFAULT_KATEGORI_PENGELUARAN,
    add_transaksi_kas,
    delete_transaksi_kas,
    get_transaksi_kas,
    update_transaksi_kas,
)
from state import app_state
from utils.formatting import rp
from utils.pdf_export import generate_pendapatan_pengeluaran_pdf
from utils.validation import parse_date, parse_positive_decimal, require_text


def build_view(page: ft.Page):
    actor = app_state.user or {}
    is_pusat = actor.get("cabang_id") is None
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    mobile = is_mobile_layout(page)
    today = date.today()

    page_width = getattr(page, "width", None) or 1100
    form_content_width = min(500, max(260, page_width - 72))
    card_padding = 12 if mobile else 16
    state_padding = 24 if mobile else 40

    filter_state = {
        "start_date": None,
        "end_date": None,
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

    def get_filtered_data():
        return get_transaksi_kas(
            cabang_id=filter_state["cabang_id"],
            start_date=filter_state["start_date"],
            end_date=filter_state["end_date"],
            search=filter_state["search"],
            sort_order=filter_state["sort_order"],
        )

    def close_dialog(e=None):
        del e
        page.pop_dialog()
        page.update()

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

    # ---------------------------------------------------------------------
    # Dialog tambah dan edit
    # ---------------------------------------------------------------------
    form_id_target = {"id": None}

    form_jenis = ft.Dropdown(
        label="Jenis Transaksi",
        options=[
            ft.dropdown.Option("Pendapatan", "Pendapatan (Pemasukan)"),
            ft.dropdown.Option("Pengeluaran", "Pengeluaran (Biaya)"),
        ],
        value="Pendapatan",
        col={"xs": 12, "sm": 6},
    )

    form_tanggal = ft.TextField(
        label="Tanggal (YYYY-MM-DD)",
        value=today.isoformat(),
        col={"xs": 12, "sm": 6},
    )

    form_kategori = ft.Dropdown(
        label="Kategori",
        col={"xs": 12, "sm": 6},
    )

    form_nominal = ft.TextField(
        label="Nominal (Rp) *",
        value="",
        hint_text="Contoh: 150000 atau 150.000",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )

    form_keterangan = ft.TextField(
        label="Keterangan / Deskripsi",
        multiline=True,
        min_lines=2,
        max_lines=3,
        col={"xs": 12},
    )

    form_nota = ft.TextField(
        label="No. Nota / Bukti (opsional)",
        col={"xs": 12, "sm": 6},
    )

    form_cabang_dropdown = ft.Dropdown(
        label="Cabang",
        options=[ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value=None,
        col={"xs": 12, "sm": 6},
    )

    def update_kategori_options(e=None):
        kategori_options = (
            DEFAULT_KATEGORI_PENDAPATAN
            if form_jenis.value == "Pendapatan"
            else DEFAULT_KATEGORI_PENGELUARAN
        )
        form_kategori.options = [
            ft.dropdown.Option(kategori, kategori)
            for kategori in kategori_options
        ]
        form_kategori.value = kategori_options[0] if kategori_options else ""
        if e:
            page.update()

    form_jenis.on_change = update_kategori_options
    update_kategori_options()

    def submit_form(e):
        del e
        try:
            tanggal = parse_date("Tanggal", form_tanggal.value)
            nominal = parse_positive_decimal(
                "Nominal",
                form_nominal.value,
                allow_zero=False,
                max_digits=14,
                decimal_places=2,
            )
            keterangan = require_text(
                "Keterangan",
                form_keterangan.value,
                max_length=200,
            )
            kategori = form_kategori.value or "Lain-lain"
            jenis = form_jenis.value
            nota = (form_nota.value or "").strip()

            cabang_id = resolve_cabang_id(form_cabang_dropdown)

            nama_cabang = next(
                (
                    cabang[1]
                    for cabang in cabang_list
                    if int(cabang[0]) == cabang_id
                ),
                actor.get("nama_cabang") or f"Cabang {cabang_id}",
            )

            is_edit = form_id_target["id"] is not None
            if is_edit:
                update_transaksi_kas(
                    transaksi_id=form_id_target["id"],
                    tanggal=tanggal,
                    jenis=jenis,
                    kategori=kategori,
                    nominal=nominal,
                    keterangan=keterangan,
                    nota=nota,
                    cabang_id=cabang_id,
                    nama_cabang=nama_cabang,
                )
                success_message = "Transaksi berhasil diperbarui!"
            else:
                add_transaksi_kas(
                    cabang_id=cabang_id,
                    nama_cabang=nama_cabang,
                    tanggal=tanggal,
                    jenis=jenis,
                    kategori=kategori,
                    nominal=nominal,
                    keterangan=keterangan,
                    nota=nota,
                )
                success_message = "Transaksi berhasil ditambahkan!"

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
                    ft.Text(f"Gagal simpan transaksi: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    form_controls = [
        form_jenis,
        form_tanggal,
        form_kategori,
        form_nominal,
        form_keterangan,
        form_nota,
    ]
    if is_pusat:
        form_controls.append(form_cabang_dropdown)

    form_dialog_title = ft.Text(
        "Tambah Transaksi Baru",
        weight=ft.FontWeight.W_500,
    )

    form_dialog = ft.AlertDialog(
        modal=True,
        title=form_dialog_title,
        content=ft.Container(
            content=ft.ResponsiveRow(
                form_controls,
                spacing=10,
                run_spacing=10,
            ),
            width=form_content_width,
        ),
        content_padding=ft.Padding.only(left=16, right=16, top=8, bottom=8),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Simpan",
                on_click=submit_form,
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def open_add_dialog(e=None):
        del e
        form_id_target["id"] = None
        form_dialog_title.value = "Tambah Transaksi Baru"
        form_jenis.value = "Pendapatan"
        update_kategori_options()
        form_tanggal.value = date.today().isoformat()
        form_nominal.value = ""
        form_keterangan.value = ""
        form_nota.value = ""
        if is_pusat:
            form_cabang_dropdown.value = None
        page.show_dialog(form_dialog)

    def open_edit_dialog(item):
        form_id_target["id"] = item["id"]
        form_dialog_title.value = f"Edit Transaksi #{item['id']}"
        form_jenis.value = item["jenis"]
        update_kategori_options()
        form_kategori.value = item["kategori"]
        form_tanggal.value = (
            item["tanggal"].isoformat()
            if hasattr(item["tanggal"], "isoformat")
            else str(item["tanggal"])
        )
        form_nominal.value = str(item["nominal"])
        form_keterangan.value = item["keterangan"]
        form_nota.value = item["nota"]
        if is_pusat:
            form_cabang_dropdown.value = str(item["cabang_id"])
        page.show_dialog(form_dialog)

    # ---------------------------------------------------------------------
    # Dialog hapus
    # ---------------------------------------------------------------------
    delete_target = {"id": None, "ket": ""}
    delete_message = ft.Text("")

    def confirm_delete(e):
        del e
        try:
            transaksi_id = delete_target["id"]
            if transaksi_id:
                delete_transaksi_kas(transaksi_id)
                close_dialog()
                refresh_table_content()
                page.show_dialog(
                    ft.SnackBar(
                        ft.Text("Transaksi berhasil dihapus!"),
                        bgcolor=ft.Colors.GREEN_700,
                    )
                )
        except Exception as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal menghapus transaksi: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Konfirmasi Hapus Transaksi"),
        content=delete_message,
        inset_padding=12 if mobile else 40,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Ya, Hapus",
                on_click=confirm_delete,
                bgcolor=ft.Colors.RED_600,
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def open_delete_dialog(item):
        delete_target["id"] = item["id"]
        delete_target["ket"] = item["keterangan"]
        delete_message.value = (
            "Apakah Anda yakin ingin menghapus transaksi "
            f"'{item['keterangan']}' senilai {rp(item['nominal'])}?"
        )
        page.show_dialog(delete_dialog)

    # ---------------------------------------------------------------------
    # Filter
    # ---------------------------------------------------------------------
    filter_start_field = ft.TextField(
        label="Dari Tanggal (YYYY-MM-DD)",
        hint_text="YYYY-MM-DD",
        value="",
        col={"xs": 12, "sm": 6, "lg": 3},
    )

    filter_end_field = ft.TextField(
        label="Sampai Tanggal (YYYY-MM-DD)",
        hint_text="YYYY-MM-DD",
        value="",
        col={"xs": 12, "sm": 6, "lg": 3},
    )

    filter_sort_dropdown = ft.Dropdown(
        label="Urutan Tanggal",
        options=[
            ft.dropdown.Option("desc", "Terbaru (Desc)"),
            ft.dropdown.Option("asc", "Terlama (Asc)"),
        ],
        value=filter_state["sort_order"],
        col={"xs": 12, "sm": 6, "lg": 3},
    )

    search_field = ft.TextField(
        label="Cari Transaksi",
        hint_text="Keterangan, nota, kategori...",
        prefix_icon=ft.Icons.SEARCH,
        value=filter_state["search"],
        col={"xs": 12, "sm": 6, "lg": 3},
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
        filter_state["search"] = search_field.value or ""
        refresh_table_content()

    def reset_filter(e=None):
        del e
        filter_start_field.value = ""
        filter_end_field.value = ""
        filter_sort_dropdown.value = "desc"
        search_field.value = ""
        apply_filter()

    search_field.on_submit = apply_filter
    filter_sort_dropdown.on_change = apply_filter

    filter_title = ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.FILTER_LIST,
                    size=20,
                    color=ft.Colors.BLUE_700,
                ),
                ft.Text(
                    "Filter Data",
                    weight=ft.FontWeight.W_500,
                    size=15,
                ),
            ],
            spacing=8,
        ),
        col={"xs": 12, "sm": 5},
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
        col={"xs": 12, "sm": 7},
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
    # Tabel dan metrik
    # ---------------------------------------------------------------------
    table_container = ft.Container()

    def on_sort_tanggal(column_index, ascending):
        del column_index
        filter_state["sort_order"] = "asc" if ascending else "desc"
        filter_sort_dropdown.value = filter_state["sort_order"]
        refresh_table_content()

    def build_table_rows(items):
        rows = []

        for item in items:
            is_pendapatan = item["jenis"] == "Pendapatan"
            jenis_color = (
                ft.Colors.GREEN_700 if is_pendapatan else ft.Colors.RED_700
            )
            jenis_dark_color = (
                ft.Colors.GREEN_400 if is_pendapatan else ft.Colors.RED_400
            )
            jenis_background = (
                ft.Colors.GREEN_50 if is_pendapatan else ft.Colors.RED_50
            )
            jenis_dark_background = (
                ft.Colors.GREEN_800 if is_pendapatan else ft.Colors.RED_800
            )

            tanggal_text = (
                item["tanggal"].strftime("%d-%m-%Y")
                if hasattr(item["tanggal"], "strftime")
                else str(item["tanggal"])
            )
            nominal_prefix = "+ " if is_pendapatan else "- "

            cells = [ft.DataCell(ft.Text(tanggal_text, size=13))]

            if is_pusat:
                cells.append(
                    ft.DataCell(ft.Text(item.get("nama_cabang", "-"), size=13))
                )

            cells.extend(
                [
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(
                                item["jenis"],
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=(
                                    ft.Colors.WHITE if is_dark else jenis_color
                                ),
                            ),
                            bgcolor=(
                                jenis_dark_background
                                if is_dark
                                else jenis_background
                            ),
                            padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                            border_radius=6,
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            item["kategori"],
                            size=13,
                            weight=ft.FontWeight.W_500,
                        )
                    ),
                    ft.DataCell(ft.Text(item["keterangan"] or "-", size=13)),
                    ft.DataCell(
                        ft.Text(
                            f"{nominal_prefix}{rp(item['nominal'])}",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=(
                                jenis_dark_color if is_dark else jenis_color
                            ),
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            item["nota"] or "-",
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
                                    tooltip="Edit Transaksi",
                                    on_click=(
                                        lambda e, selected=item: open_edit_dialog(
                                            selected
                                        )
                                    ),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    icon_size=18,
                                    icon_color=ft.Colors.RED_400,
                                    tooltip="Hapus Transaksi",
                                    on_click=(
                                        lambda e, selected=item: open_delete_dialog(
                                            selected
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

    metric_pendapatan_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_pengeluaran_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_saldo_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_count_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    def refresh_table_content():
        error_message = None
        try:
            items = get_filtered_data()
        except Exception as error:
            items = []
            error_message = str(error)

        pendapatan_total = sum(
            (item["nominal"] for item in items if item["jenis"] == "Pendapatan"),
            Decimal(0),
        )
        pengeluaran_total = sum(
            (item["nominal"] for item in items if item["jenis"] == "Pengeluaran"),
            Decimal(0),
        )
        saldo_total = pendapatan_total - pengeluaran_total

        metric_pendapatan_card.content = metric_card(
            page,
            "Total Pendapatan",
            rp(pendapatan_total),
            light_color=ft.Colors.GREEN_50,
            light_text_color=ft.Colors.GREEN_900,
            dark_color=ft.Colors.GREEN_900,
            dark_text_color=ft.Colors.GREEN_100,
        )
        metric_pengeluaran_card.content = metric_card(
            page,
            "Total Pengeluaran",
            rp(pengeluaran_total),
            light_color=ft.Colors.RED_50,
            light_text_color=ft.Colors.RED_900,
            dark_color=ft.Colors.RED_900,
            dark_text_color=ft.Colors.RED_100,
        )
        metric_saldo_card.content = metric_card(
            page,
            "Saldo Kas Bersih",
            rp(saldo_total),
            light_color=(
                ft.Colors.BLUE_50 if saldo_total >= 0 else ft.Colors.RED_50
            ),
            light_text_color=(
                ft.Colors.BLUE_900 if saldo_total >= 0 else ft.Colors.RED_900
            ),
            dark_color=(
                ft.Colors.BLUE_900 if saldo_total >= 0 else ft.Colors.RED_900
            ),
            dark_text_color=(
                ft.Colors.BLUE_100 if saldo_total >= 0 else ft.Colors.RED_100
            ),
        )
        metric_count_card.content = metric_card(
            page,
            "Jumlah Transaksi",
            f"{len(items)} Transaksi",
            light_color=ft.Colors.GREY_100,
            light_text_color=ft.Colors.GREY_900,
            dark_color=ft.Colors.GREY_800,
            dark_text_color=ft.Colors.WHITE,
        )

        state_border = ft.Border.all(
            0.5,
            ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
        )
        state_background = ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE

        if error_message:
            table_container.content = ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.WARNING_AMBER_ROUNDED,
                            size=48,
                            color=ft.Colors.ORANGE_400,
                        ),
                        ft.Text(
                            "Tidak dapat memuat data transaksi",
                            size=15,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            error_message,
                            size=12,
                            color=ft.Colors.GREY_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                alignment=ft.Alignment.CENTER,
                padding=state_padding,
                border_radius=10,
                border=state_border,
                bgcolor=state_background,
            )
        elif not items:
            table_container.content = ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.RECEIPT_LONG_OUTLINED,
                            size=48,
                            color=ft.Colors.GREY_400,
                        ),
                        ft.Text(
                            "Tidak ada data transaksi",
                            size=15,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Gunakan tombol 'Tambah Transaksi' untuk memasukkan "
                            "catatan kas baru atau sesuaikan filter.",
                            size=12,
                            color=ft.Colors.GREY_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
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
                    on_sort=lambda e: on_sort_tanggal(0, e.ascending),
                )
            ]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend(
                [
                    ft.DataColumn(ft.Text("Jenis")),
                    ft.DataColumn(ft.Text("Kategori")),
                    ft.DataColumn(ft.Text("Keterangan")),
                    ft.DataColumn(ft.Text("Nominal")),
                    ft.DataColumn(ft.Text("Nota")),
                    ft.DataColumn(ft.Text("Aksi")),
                ]
            )

            data_table = ft.DataTable(
                sort_column_index=0,
                sort_ascending=filter_state["sort_order"] == "asc",
                columns=columns,
                rows=build_table_rows(items),
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
            table_container.content = ft.Column(
                table_controls,
                spacing=6,
            )

        if page.views:
            page.update()

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
                    ft.Text("Tidak ada data transaksi untuk diexport."),
                    bgcolor=ft.Colors.RED_400,
                )
            )
            return

        cabang_name = "Semua Cabang"
        if filter_state["cabang_id"]:
            cabang_name = next(
                (
                    c[1]
                    for c in cabang_list
                    if c[0] == filter_state["cabang_id"]
                ),
                f"Cabang {filter_state['cabang_id']}",
            )
        elif not is_pusat:
            cabang_name = actor.get("nama_cabang", "Cabang")

        periode = "Semua Periode"
        if filter_state["start_date"] and filter_state["end_date"]:
            periode = (
                f"{filter_state['start_date'].strftime('%d-%m-%Y')} s/d "
                f"{filter_state['end_date'].strftime('%d-%m-%Y')}"
            )
        elif filter_state["start_date"]:
            periode = f"Mulai {filter_state['start_date'].strftime('%d-%m-%Y')}"
        elif filter_state["end_date"]:
            periode = f"Sampai {filter_state['end_date'].strftime('%d-%m-%Y')}"

        filter_info = {
            "periode": periode,
            "cabang": cabang_name,
            "extra": f"Total: {len(items)} Transaksi",
        }
        default_file_name = f"Laporan_Kas_{today.strftime('%Y%m%d')}.pdf"

        try:
            if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
                pdf_bytes = generate_pendapatan_pengeluaran_pdf(
                    items,
                    filter_info,
                    is_pusat=is_pusat,
                    output_path=None,
                )
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Kas PDF",
                    file_name=default_file_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
                if not save_path:
                    return
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Kas PDF",
                    file_name=default_file_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if not save_path:
                    return
                if not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                generate_pendapatan_pengeluaran_pdf(
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
                f"Export PDF Laporan Kas ({periode})",
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

    refresh_table_content()

    header_title = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Pendapatan & Pengeluaran",
                    size=22,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    "Kelola dan pantau seluruh transaksi kas masuk & keluar.",
                    size=13,
                    color=ft.Colors.GREY_500,
                ),
            ],
            spacing=2,
        ),
        col={"xs": 12, "md": 6},
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
                    "Tambah" if mobile else "Tambah Transaksi",
                    icon=ft.Icons.ADD,
                    on_click=open_add_dialog,
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                ),
                ft.IconButton(
                    ft.Icons.REFRESH,
                    tooltip="Segarkan Data",
                    on_click=lambda e: refresh_table_content(),
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
        col={"xs": 12, "md": 6},
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
                    metric_pendapatan_card,
                    metric_pengeluaran_card,
                    metric_saldo_card,
                    metric_count_card,
                ],
                spacing=12,
                run_spacing=12,
            ),
            ft.Container(height=12),
            filter_card,
            ft.Container(height=16),
            ft.Text(
                "Daftar Transaksi Kas",
                size=16,
                weight=ft.FontWeight.W_500,
            ),
            ft.Container(height=8),
            table_container,
            ft.Container(height=24),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
