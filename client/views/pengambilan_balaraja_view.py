import flet as ft
from decimal import Decimal
from datetime import date, datetime
from config import MONTH
from components.metric_card import metric_card
from utils.formatting import rp
from utils.validation import require_text, parse_date, parse_positive_decimal
from utils.pdf_export import generate_pengambilan_balaraja_pdf
from db.activity_repo import log_activity
from db.pengambilan_balaraja_repo import (
    get_pengambilan_balaraja,
    add_pengambilan_balaraja,
    update_pengambilan_balaraja,
    delete_pengambilan_balaraja,
)
from db.cabang_repo import get_active_cabang
from state import app_state


def build_view(page: ft.Page):
    actor = app_state.user or {}
    is_pusat = actor.get("cabang_id") is None
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    today = date.today()

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
    if is_pusat:
        try:
            cabang_list = get_active_cabang()
        except Exception:
            cabang_list = [(1, "Cabang Utama"), (2, "Cabang Barat")]

    def close_dialog(e=None):
        page.pop_dialog()
        page.update()

    # =========================================================================
    # DIALOG TAMBAH & EDIT PENGAMBILAN BALARAJA
    # =========================================================================
    form_id_target = {"id": None}

    form_tanggal = ft.TextField(label="Tanggal (YYYY-MM-DD) *", width=180, value=today.isoformat())
    form_nominal = ft.TextField(label="Nominal Kas (Rp) *", width=220, value="0")
    form_keterangan = ft.TextField(
        label="Keterangan / Lokasi / Rincian *",
        width=480,
        multiline=True,
        min_lines=2,
        max_lines=3,
        hint_text="Contoh: Pengambilan Kas Gudang Balaraja - Pembelian Keripik & Repack",
    )

    form_cabang_dropdown = ft.Dropdown(
        label="Cabang Penerima",
        width=220,
        options=[ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value=str(cabang_list[0][0]) if cabang_list else "1",
    )

    def submit_form(e):
        try:
            tgl_val = parse_date("Tanggal", form_tanggal.value)
            nom_val = parse_positive_decimal("Nominal Kas", form_nominal.value)
            ket_val = require_text("Keterangan", form_keterangan.value, max_length=150)

            if is_pusat:
                sel_cid = int(form_cabang_dropdown.value or 1)
            else:
                sel_cid = actor.get("cabang_id", 1)

            is_edit = form_id_target["id"] is not None
            if not is_edit:
                add_pengambilan_balaraja(
                    tanggal=tgl_val,
                    keterangan=ket_val,
                    nominal=nom_val,
                    cabang_id=sel_cid,
                )
                success_msg = "Catatan pengambilan kas Balaraja berhasil disimpan!"
            else:
                update_pengambilan_balaraja(
                    entry_id=form_id_target["id"],
                    tanggal=tgl_val,
                    keterangan=ket_val,
                    nominal=nom_val,
                )
                success_msg = "Catatan pengambilan kas Balaraja berhasil diperbarui!"

            close_dialog()
            refresh_table_content()
            page.show_dialog(ft.SnackBar(ft.Text(success_msg), bgcolor=ft.Colors.GREEN_700))
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal simpan: {ex}"), bgcolor=ft.Colors.RED_400))

    form_dialog_title = ft.Text("Tambah Pengambilan Kas Balaraja", weight=ft.FontWeight.W_500)
    form_dialog = ft.AlertDialog(
        title=form_dialog_title,
        content=ft.Container(
            content=ft.Column([
                ft.Row([form_tanggal, form_nominal], spacing=10),
                form_keterangan,
                ft.Row([
                    form_cabang_dropdown if is_pusat else ft.Container(),
                ], spacing=10),
            ], tight=True, spacing=12),
            width=500,
        ),
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Simpan", on_click=submit_form, bgcolor=ft.Colors.INDIGO_700, color=ft.Colors.WHITE),
        ],
    )

    def open_add_dialog(e=None):
        form_id_target["id"] = None
        form_dialog_title.value = "Tambah Pengambilan Kas Balaraja"
        form_tanggal.value = date.today().isoformat()
        form_nominal.value = "0"
        form_keterangan.value = ""
        if is_pusat and cabang_list:
            form_cabang_dropdown.value = str(cabang_list[0][0])
        page.show_dialog(form_dialog)

    def open_edit_dialog(item):
        form_id_target["id"] = item["id"]
        form_dialog_title.value = f"Edit Pengambilan Kas Balaraja #{item['id']}"
        form_tanggal.value = item["tanggal"].isoformat() if hasattr(item["tanggal"], "isoformat") else str(item["tanggal"])
        form_nominal.value = str(item["nominal"])
        form_keterangan.value = item["keterangan"] or ""
        if is_pusat:
            form_cabang_dropdown.value = str(item["cabang_id"])
        page.show_dialog(form_dialog)

    # =========================================================================
    # DIALOG KONFIRMASI HAPUS
    # =========================================================================
    del_target_id = {"id": None}
    del_msg = ft.Text("")

    def confirm_delete(e):
        try:
            delete_pengambilan_balaraja(del_target_id["id"])
            close_dialog()
            refresh_table_content()
            page.show_dialog(ft.SnackBar(ft.Text("Data pengambilan Balaraja berhasil dihapus!"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal menghapus: {ex}"), bgcolor=ft.Colors.RED_400))

    delete_dialog = ft.AlertDialog(
        title=ft.Text("Konfirmasi Hapus Data"),
        content=del_msg,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Ya, Hapus", on_click=confirm_delete, bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
        ],
    )

    def open_delete_dialog(item):
        del_target_id["id"] = item["id"]
        del_msg.value = f"Apakah Anda yakin ingin menghapus data pengambilan Balaraja '{item['keterangan']}' senilai {rp(item['nominal'])}?"
        page.show_dialog(delete_dialog)

    # =========================================================================
    # FILTER CONTROLS
    # =========================================================================
    year_options = [ft.dropdown.Option("Semua", "Semua Tahun")] + [
        ft.dropdown.Option(str(y), str(y)) for y in range(today.year - 3, today.year + 4)
    ]
    if "2099" not in [opt.key for opt in year_options]:
        year_options.append(ft.dropdown.Option("2099", "2099"))

    filter_bulan_dropdown = ft.Dropdown(
        label="Bulan",
        width=150,
        options=[ft.dropdown.Option("Semua", "Semua Bulan")] + [ft.dropdown.Option(str(i), MONTH[i]) for i in range(1, 13)],
        value="Semua",
    )

    filter_tahun_dropdown = ft.Dropdown(
        label="Tahun",
        width=140,
        options=year_options,
        value="Semua",
    )

    filter_start_field = ft.TextField(label="Dari Tanggal (YYYY-MM-DD)", width=170)
    filter_end_field = ft.TextField(label="Sampai Tanggal (YYYY-MM-DD)", width=170)

    filter_sort_dropdown = ft.Dropdown(
        label="Urutan",
        width=140,
        options=[
            ft.dropdown.Option("desc", "Terbaru"),
            ft.dropdown.Option("asc", "Terlama"),
        ],
        value="desc",
    )

    search_field = ft.TextField(
        label="Cari Transaksi",
        hint_text="Keterangan, lokasi, user...",
        prefix_icon=ft.Icons.SEARCH,
        width=240,
        value=filter_state["search"],
    )

    def apply_filter(e=None):
        sel_b = filter_bulan_dropdown.value
        filter_state["bulan"] = None if sel_b == "Semua" or not sel_b else int(sel_b)
        sel_y = filter_tahun_dropdown.value
        filter_state["tahun"] = None if sel_y == "Semua" or not sel_y else int(sel_y)

        try:
            filter_state["start_date"] = parse_date("Dari Tanggal", filter_start_field.value) if filter_start_field.value else None
        except Exception:
            filter_state["start_date"] = None

        try:
            filter_state["end_date"] = parse_date("Sampai Tanggal", filter_end_field.value) if filter_end_field.value else None
        except Exception:
            filter_state["end_date"] = None

        filter_state["sort_order"] = filter_sort_dropdown.value or "desc"
        filter_state["search"] = search_field.value or ""
        refresh_table_content()

    def reset_filter(e=None):
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

    filter_controls = [
        filter_bulan_dropdown,
        filter_tahun_dropdown,
        filter_start_field,
        filter_end_field,
        filter_sort_dropdown,
        search_field,
    ]


    filter_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FILTER_LIST, size=20, color=ft.Colors.INDIGO_700),
                ft.Text("Filter Data Pengambilan Balaraja", weight=ft.FontWeight.W_500, size=15),
                ft.Container(expand=True),
                ft.TextButton("Reset Filter", icon=ft.Icons.RESTART_ALT, on_click=reset_filter),
                ft.ElevatedButton("Terapkan", icon=ft.Icons.CHECK, on_click=apply_filter, bgcolor=ft.Colors.INDIGO_700, color=ft.Colors.WHITE),
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
    metric_count_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_avg_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_max_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    table_container = ft.Container()

    def on_sort_tanggal(col_idx, ascending):
        filter_state["sort_order"] = "asc" if ascending else "desc"
        filter_sort_dropdown.value = filter_state["sort_order"]
        refresh_table_content()

    def build_table_rows(items):
        rows = []
        for it in items:
            tgl_str = it["tanggal"].strftime("%d-%m-%Y") if hasattr(it["tanggal"], "strftime") else str(it["tanggal"])

            cells = [
                ft.DataCell(ft.Text(tgl_str, size=13)),
            ]
            if is_pusat:
                cells.append(ft.DataCell(ft.Text(it.get("nama_cabang", "-"), size=13)))

            cells.extend([
                ft.DataCell(ft.Text(it["keterangan"] or "-", size=13, weight=ft.FontWeight.W_500)),
                ft.DataCell(
                    ft.Text(
                        rp(it["nominal"]),
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.INDIGO_400 if is_dark else ft.Colors.INDIGO_700,
                    )
                ),
                ft.DataCell(ft.Text(it.get("username") or "-", size=12, color=ft.Colors.GREY_500)),
                ft.DataCell(
                    ft.Row([
                        ft.IconButton(
                            ft.Icons.EDIT,
                            icon_size=18,
                            tooltip="Edit Catatan",
                            on_click=lambda e, item=it: open_edit_dialog(item),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_size=18,
                            icon_color=ft.Colors.RED_400,
                            tooltip="Hapus Catatan",
                            on_click=lambda e, item=it: open_delete_dialog(item),
                        ),
                    ], spacing=2)
                ),
            ])
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
        except Exception as ex:
            items = []
            page.show_dialog(ft.SnackBar(ft.Text(f"Error memuat data: {ex}"), bgcolor=ft.Colors.RED_400))

        total_sum = sum([it["nominal"] for it in items], Decimal(0))
        total_trx = len(items)
        avg_sum = (total_sum / total_trx) if total_trx > 0 else Decimal(0)
        max_sum = max([it["nominal"] for it in items], default=Decimal(0))

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
            f"{total_trx} Transaksi",
            light_color=ft.Colors.BLUE_50,
            light_text_color=ft.Colors.BLUE_900,
            dark_color=ft.Colors.BLUE_900,
            dark_text_color=ft.Colors.BLUE_100,
        )
        metric_avg_card.content = metric_card(
            page,
            "Rata-rata Transaksi",
            rp(avg_sum),
            light_color=ft.Colors.ORANGE_50,
            light_text_color=ft.Colors.ORANGE_900,
            dark_color=ft.Colors.ORANGE_900,
            dark_text_color=ft.Colors.ORANGE_100,
        )
        metric_max_card.content = metric_card(
            page,
            "Transaksi Terbesar",
            rp(max_sum),
            light_color=ft.Colors.TEAL_50,
            light_text_color=ft.Colors.TEAL_900,
            dark_color=ft.Colors.TEAL_900,
            dark_text_color=ft.Colors.TEAL_100,
        )

        if not items:
            table_container.content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.WAREHOUSE_OUTLINED, size=48, color=ft.Colors.GREY_400),
                    ft.Container(height=8),
                    ft.Text("Tidak ada data pengambilan kas Balaraja", size=15, weight=ft.FontWeight.W_500),
                    ft.Text("Klik 'Catat Pengambilan' untuk menambahkan data baru.", size=12, color=ft.Colors.GREY_500),
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
                    on_sort=lambda e: on_sort_tanggal(0, e.ascending),
                ),
            ]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend([
                ft.DataColumn(ft.Text("Keterangan / Rincian")),
                ft.DataColumn(ft.Text("Nominal Kas")),
                ft.DataColumn(ft.Text("Diinput Oleh")),
                ft.DataColumn(ft.Text("Aksi")),
            ])

            dt = ft.DataTable(
                sort_column_index=0,
                sort_ascending=(filter_state["sort_order"] == "asc"),
                columns=columns,
                rows=build_table_rows(items),
                border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200),
                border_radius=10,
                heading_row_color=ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100,
                show_bottom_border=True,
            )
            table_container.content = ft.Row([dt], scroll=ft.ScrollMode.AUTO)
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

    # Export PDF Picker & Handler
    export_picker = ft.FilePicker()
    if export_picker not in page.services:
        page.services.append(export_picker)

    async def export_pdf(e):
        items = get_filtered_data()
        if not items:
            page.show_dialog(ft.SnackBar(ft.Text("Tidak ada data untuk diexport."), bgcolor=ft.Colors.RED_400))
            return

        cbg_name = "Semua Cabang"
        if filter_state["cabang_id"]:
            cbg_name = next((c[1] for c in cabang_list if c[0] == filter_state["cabang_id"]), f"Cabang {filter_state['cabang_id']}")
        elif not is_pusat:
            cbg_name = actor.get("nama_cabang", "Cabang")

        if filter_state["start_date"] and filter_state["end_date"]:
            periode_str = f"{filter_state['start_date'].strftime('%d-%m-%Y')} s/d {filter_state['end_date'].strftime('%d-%m-%Y')}"
        elif filter_state["bulan"]:
            periode_str = f"{MONTH[filter_state['bulan']]} {filter_state['tahun']}"
        else:
            periode_str = f"Tahun {filter_state['tahun']}"

        total_sum = sum([it["nominal"] for it in items], Decimal(0))
        filter_info = {
            "periode": periode_str,
            "cabang": cbg_name,
            "extra": f"Total: {rp(total_sum)} | {len(items)} Transaksi",
        }

        nama_file_default = f"Laporan_Pengambilan_Balaraja_{today.strftime('%Y%m%d')}.pdf"
        try:
            if page.platform == ft.PagePlatform.ANDROID or page.platform == ft.PagePlatform.IOS:
                pdf_bytes = generate_pengambilan_balaraja_pdf(items, filter_info, is_pusat=is_pusat, output_path=None)
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Pengambilan Balaraja PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Pengambilan Balaraja PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if save_path and not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                if save_path:
                    generate_pengambilan_balaraja_pdf(items, filter_info, is_pusat=is_pusat, output_path=save_path)

            if save_path:
                log_activity(
                    actor.get("id"),
                    actor.get("username", "user"),
                    "CREATE",
                    "export_pdf",
                    filter_state.get("cabang_id") or 0,
                    f"Export PDF Pengambilan Kas Balaraja ({periode_str})",
                    filter_state.get("cabang_id"),
                )
                page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    # Initial data
    refresh_table_content()

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Pengambilan Kas Balaraja", size=22, weight=ft.FontWeight.W_600),
                ft.Text("Pencatatan pengambilan dana kas untuk operasional atau pengadaan barang Gudang Balaraja.", size=13, color=ft.Colors.GREY_500),
            ], expand=True),
            ft.OutlinedButton(
                "Export ke PDF",
                icon=ft.Icons.PICTURE_AS_PDF,
                on_click=export_pdf,
            ),
            ft.ElevatedButton(
                "Catat Pengambilan",
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
        ]),
        ft.Container(height=8),
        ft.ResponsiveRow([
            metric_total_card,
            metric_count_card,
            metric_avg_card,
            metric_max_card,
        ], spacing=12, run_spacing=12),
        ft.Container(height=12),
        filter_card,
        ft.Container(height=16),
        ft.Row([
            ft.Text("Daftar Catatan Pengambilan Kas Balaraja", size=16, weight=ft.FontWeight.W_500, expand=True),
        ]),
        ft.Container(height=8),
        table_container,
        ft.Container(height=24),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return body
