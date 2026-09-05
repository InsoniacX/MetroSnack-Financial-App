from datetime import date
from decimal import Decimal

import flet as ft

from components.appbar import is_mobile_layout
from components.metric_card import metric_card
from config import MONTH
from db.activity_repo import log_activity
from db.cabang_repo import get_active_cabang
from db.pengambilan_balaraja_repo import (
    add_pengambilan_balaraja,
    delete_pengambilan_balaraja,
    get_pengambilan_balaraja,
    update_pengambilan_balaraja,
)
from state import app_state
from utils.formatting import rp
from utils.pdf_export import generate_pengambilan_balaraja_pdf
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
        "bulan": None,
        "tahun": None,
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
    # Dialog tambah dan edit pengambilan Balaraja
    # ---------------------------------------------------------------------
    form_id_target = {"id": None}

    form_tanggal = ft.TextField(
        label="Tanggal (YYYY-MM-DD) *",
        value=today.isoformat(),
        col={"xs": 12, "sm": 6},
    )

    form_nominal = ft.TextField(
        label="Nominal Kas (Rp) *",
        value="",
        hint_text="Contoh: 150000 atau 150.000",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )

    form_keterangan = ft.TextField(
        label="Keterangan / Lokasi / Rincian *",
        multiline=True,
        min_lines=2,
        max_lines=3,
        hint_text=(
            "Contoh: Pengambilan Kas Gudang Balaraja - Pembelian Keripik "
            "& Repack"
        ),
        col={"xs": 12},
    )

    form_cabang_dropdown = ft.Dropdown(
        label="Cabang Penerima",
        options=[
            ft.dropdown.Option(str(cabang[0]), cabang[1])
            for cabang in cabang_list
        ],
        value=None,
        col={"xs": 12, "sm": 6},
    )

    def submit_form(e):
        del e
        try:
            tanggal = parse_date("Tanggal", form_tanggal.value)
            nominal = parse_positive_decimal(
                "Nominal Kas",
                form_nominal.value,
                allow_zero=False,
                max_digits=14,
                decimal_places=2,
            )
            keterangan = require_text(
                "Keterangan",
                form_keterangan.value,
                max_length=150,
            )

            cabang_id = resolve_cabang_id(form_cabang_dropdown)

            is_edit = form_id_target["id"] is not None
            if is_edit:
                update_pengambilan_balaraja(
                    entry_id=form_id_target["id"],
                    tanggal=tanggal,
                    keterangan=keterangan,
                    nominal=nominal,
                )
                success_message = (
                    "Catatan pengambilan kas Balaraja berhasil diperbarui!"
                )
            else:
                add_pengambilan_balaraja(
                    tanggal=tanggal,
                    keterangan=keterangan,
                    nominal=nominal,
                    cabang_id=cabang_id,
                )
                success_message = (
                    "Catatan pengambilan kas Balaraja berhasil disimpan!"
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

    form_controls = [
        form_tanggal,
        form_nominal,
        form_keterangan,
    ]
    if is_pusat:
        form_controls.append(form_cabang_dropdown)

    form_dialog_title = ft.Text(
        "Tambah Pengambilan Kas Balaraja",
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
                on_click=submit_form,
                bgcolor=ft.Colors.INDIGO_700,
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def open_add_dialog(e=None):
        del e
        form_id_target["id"] = None
        form_dialog_title.value = "Tambah Pengambilan Kas Balaraja"
        form_tanggal.value = date.today().isoformat()
        form_nominal.value = ""
        form_keterangan.value = ""
        if is_pusat:
            form_cabang_dropdown.value = None
        page.show_dialog(form_dialog)

    def open_edit_dialog(item):
        form_id_target["id"] = item["id"]
        form_dialog_title.value = (
            f"Edit Pengambilan Kas Balaraja #{item['id']}"
        )
        form_tanggal.value = (
            item["tanggal"].isoformat()
            if hasattr(item["tanggal"], "isoformat")
            else str(item["tanggal"])
        )
        form_nominal.value = str(item["nominal"])
        form_keterangan.value = item["keterangan"] or ""
        if is_pusat:
            form_cabang_dropdown.value = str(item["cabang_id"])
        page.show_dialog(form_dialog)

    # ---------------------------------------------------------------------
    # Dialog konfirmasi hapus
    # ---------------------------------------------------------------------
    delete_target = {"id": None}
    delete_message = ft.Text("")

    def confirm_delete(e):
        del e
        try:
            delete_pengambilan_balaraja(delete_target["id"])
            close_dialog()
            refresh_table_content()
            page.show_dialog(
                ft.SnackBar(
                    ft.Text("Data pengambilan Balaraja berhasil dihapus!"),
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
                on_click=confirm_delete,
                bgcolor=ft.Colors.RED_600,
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def open_delete_dialog(item):
        delete_target["id"] = item["id"]
        delete_message.value = (
            "Apakah Anda yakin ingin menghapus data pengambilan Balaraja "
            f"'{item['keterangan']}' senilai {rp(item['nominal'])}?"
        )
        page.show_dialog(delete_dialog)

    # ---------------------------------------------------------------------
    # Filter
    # ---------------------------------------------------------------------
    year_options = [ft.dropdown.Option("Semua", "Semua Tahun")] + [
        ft.dropdown.Option(str(year), str(year))
        for year in range(today.year - 3, today.year + 4)
    ]
    if "2099" not in [option.key for option in year_options]:
        year_options.append(ft.dropdown.Option("2099", "2099"))

    filter_bulan_dropdown = ft.Dropdown(
        label="Bulan",
        options=[ft.dropdown.Option("Semua", "Semua Bulan")]
        + [
            ft.dropdown.Option(str(month_number), MONTH[month_number])
            for month_number in range(1, 13)
        ],
        value="Semua",
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    filter_tahun_dropdown = ft.Dropdown(
        label="Tahun",
        options=year_options,
        value="Semua",
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    filter_start_field = ft.TextField(
        label="Dari Tanggal (YYYY-MM-DD)",
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    filter_end_field = ft.TextField(
        label="Sampai Tanggal (YYYY-MM-DD)",
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    filter_sort_dropdown = ft.Dropdown(
        label="Urutan",
        options=[
            ft.dropdown.Option("desc", "Terbaru"),
            ft.dropdown.Option("asc", "Terlama"),
        ],
        value="desc",
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    search_field = ft.TextField(
        label="Cari Transaksi",
        hint_text="Keterangan, lokasi, user...",
        prefix_icon=ft.Icons.SEARCH,
        value=filter_state["search"],
        col={"xs": 12, "sm": 6, "lg": 2},
    )

    def apply_filter(e=None):
        del e
        selected_month = filter_bulan_dropdown.value
        filter_state["bulan"] = (
            None
            if selected_month == "Semua" or not selected_month
            else int(selected_month)
        )

        selected_year = filter_tahun_dropdown.value
        filter_state["tahun"] = (
            None
            if selected_year == "Semua" or not selected_year
            else int(selected_year)
        )

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
        filter_bulan_dropdown.value = "Semua"
        filter_tahun_dropdown.value = "Semua"
        filter_start_field.value = ""
        filter_end_field.value = ""
        filter_sort_dropdown.value = "desc"
        search_field.value = ""
        apply_filter()

    search_field.on_submit = apply_filter
    filter_bulan_dropdown.on_change = apply_filter
    filter_tahun_dropdown.on_change = apply_filter
    filter_sort_dropdown.on_change = apply_filter

    filter_title = ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.FILTER_LIST,
                    size=20,
                    color=ft.Colors.INDIGO_700,
                ),
                ft.Text(
                    "Filter Data Pengambilan Balaraja",
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
                    bgcolor=ft.Colors.INDIGO_700,
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
                        filter_bulan_dropdown,
                        filter_tahun_dropdown,
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
    # Metrik dan tabel
    # ---------------------------------------------------------------------
    metric_total_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_count_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_avg_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_max_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    table_container = ft.Container()

    def on_sort_tanggal(column_index, ascending):
        del column_index
        filter_state["sort_order"] = "asc" if ascending else "desc"
        filter_sort_dropdown.value = filter_state["sort_order"]
        refresh_table_content()

    def build_table_rows(items):
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
                            item["keterangan"] or "-",
                            size=13,
                            weight=ft.FontWeight.W_500,
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            rp(item["nominal"]),
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=(
                                ft.Colors.INDIGO_400
                                if is_dark
                                else ft.Colors.INDIGO_700
                            ),
                        )
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
                                            open_edit_dialog(selected)
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
                                            open_delete_dialog(selected)
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
            items = get_pengambilan_balaraja(
                cabang_id=filter_state["cabang_id"],
                bulan=filter_state["bulan"],
                tahun=filter_state["tahun"],
                start_date=filter_state["start_date"],
                end_date=filter_state["end_date"],
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
            (item["nominal"] for item in items),
            Decimal(0),
        )
        total_transactions = len(items)
        average_sum = (
            total_sum / total_transactions
            if total_transactions > 0
            else Decimal(0)
        )
        maximum_sum = max(
            (item["nominal"] for item in items),
            default=Decimal(0),
        )

        metric_total_card.content = metric_card(
            page,
            "Total Pengambilan Balaraja",
            rp(total_sum),
            light_color=ft.Colors.INDIGO_50,
            light_text_color=ft.Colors.INDIGO_900,
            dark_color=ft.Colors.INDIGO_900,
            dark_text_color=ft.Colors.INDIGO_100,
        )
        metric_count_card.content = metric_card(
            page,
            "Jumlah Transaksi",
            f"{total_transactions} Transaksi",
            light_color=ft.Colors.BLUE_50,
            light_text_color=ft.Colors.BLUE_900,
            dark_color=ft.Colors.BLUE_900,
            dark_text_color=ft.Colors.BLUE_100,
        )
        metric_avg_card.content = metric_card(
            page,
            "Rata-rata Transaksi",
            rp(average_sum),
            light_color=ft.Colors.ORANGE_50,
            light_text_color=ft.Colors.ORANGE_900,
            dark_color=ft.Colors.ORANGE_900,
            dark_text_color=ft.Colors.ORANGE_100,
        )
        metric_max_card.content = metric_card(
            page,
            "Transaksi Terbesar",
            rp(maximum_sum),
            light_color=ft.Colors.TEAL_50,
            light_text_color=ft.Colors.TEAL_900,
            dark_color=ft.Colors.TEAL_900,
            dark_text_color=ft.Colors.TEAL_100,
        )

        state_border = ft.Border.all(
            0.5,
            ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
        )
        state_background = ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE

        if not items:
            table_container.content = ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.WAREHOUSE_OUTLINED,
                            size=48,
                            color=ft.Colors.GREY_400,
                        ),
                        ft.Container(height=8),
                        ft.Text(
                            "Tidak ada data pengambilan kas Balaraja",
                            size=15,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Klik 'Catat Pengambilan' untuk menambahkan "
                            "data baru.",
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
                    on_sort=lambda e: on_sort_tanggal(0, e.ascending),
                )
            ]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend(
                [
                    ft.DataColumn(ft.Text("Keterangan / Rincian")),
                    ft.DataColumn(ft.Text("Nominal Kas")),
                    ft.DataColumn(ft.Text("Diinput Oleh")),
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

    def get_filtered_data():
        return get_pengambilan_balaraja(
            cabang_id=filter_state["cabang_id"],
            bulan=filter_state["bulan"],
            tahun=filter_state["tahun"],
            start_date=filter_state["start_date"],
            end_date=filter_state["end_date"],
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
                    ft.Text("Tidak ada data untuk diexport."),
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

        if filter_state["start_date"] and filter_state["end_date"]:
            period = (
                f"{filter_state['start_date'].strftime('%d-%m-%Y')} s/d "
                f"{filter_state['end_date'].strftime('%d-%m-%Y')}"
            )
        elif filter_state["bulan"]:
            period = (
                f"{MONTH[filter_state['bulan']]} "
                f"{filter_state['tahun']}"
            )
        else:
            period = f"Tahun {filter_state['tahun']}"

        total_sum = sum(
            (item["nominal"] for item in items),
            Decimal(0),
        )
        filter_info = {
            "periode": period,
            "cabang": cabang_name,
            "extra": f"Total: {rp(total_sum)} | {len(items)} Transaksi",
        }

        default_file_name = (
            f"Laporan_Pengambilan_Balaraja_{today.strftime('%Y%m%d')}.pdf"
        )
        try:
            if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
                pdf_bytes = generate_pengambilan_balaraja_pdf(
                    items,
                    filter_info,
                    is_pusat=is_pusat,
                    output_path=None,
                )
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Pengambilan Balaraja PDF",
                    file_name=default_file_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Pengambilan Balaraja PDF",
                    file_name=default_file_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if save_path and not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                if save_path:
                    generate_pengambilan_balaraja_pdf(
                        items,
                        filter_info,
                        is_pusat=is_pusat,
                        output_path=save_path,
                    )

            if save_path:
                log_activity(
                    actor.get("id"),
                    actor.get("username", "user"),
                    "CREATE",
                    "export_pdf",
                    filter_state.get("cabang_id") or 0,
                    f"Export PDF Pengambilan Kas Balaraja ({period})",
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
                    "Pengambilan Kas Balaraja",
                    size=22,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    "Pencatatan pengambilan dana kas untuk operasional atau "
                    "pengadaan barang Gudang Balaraja.",
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
                    "Catat" if mobile else "Catat Pengambilan",
                    icon=ft.Icons.ADD,
                    on_click=open_add_dialog,
                    bgcolor=ft.Colors.INDIGO_700,
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
                    metric_total_card,
                    metric_count_card,
                    metric_avg_card,
                    metric_max_card,
                ],
                spacing=12,
                run_spacing=12,
            ),
            ft.Container(height=12),
            filter_card,
            ft.Container(height=16),
            ft.Text(
                "Daftar Catatan Pengambilan Kas Balaraja",
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
