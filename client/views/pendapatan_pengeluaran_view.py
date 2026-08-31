import flet as ft
from decimal import Decimal
from datetime import date, datetime
from components.appbar import build_appbar
from components.metric_card import metric_card
from utils.formatting import rp
from utils.validation import require_text, parse_date, parse_positive_decimal
from utils.pdf_export import generate_pendapatan_pengeluaran_pdf
from db.activity_repo import log_activity
from db.pendapatan_pengeluaran_repo import (
    get_transaksi_kas,
    add_transaksi_kas,
    update_transaksi_kas,
    delete_transaksi_kas,
    DEFAULT_KATEGORI_PENDAPATAN,
    DEFAULT_KATEGORI_PENGELUARAN,
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

    def get_filtered_data():
        return get_transaksi_kas(
            cabang_id=filter_state["cabang_id"],
            start_date=filter_state["start_date"],
            end_date=filter_state["end_date"],
            search=filter_state["search"],
            sort_order=filter_state["sort_order"],
        )

    def close_dialog(e=None):
        page.pop_dialog()
        page.update()

    # ==========================
    # DIALOG TAMBAH & EDIT
    # ==========================
    form_id_target = {"id": None}
    form_jenis = ft.Dropdown(
        label="Jenis Transaksi",
        width=200,
        options=[
            ft.dropdown.Option("Pendapatan", "Pendapatan (Pemasukan)"),
            ft.dropdown.Option("Pengeluaran", "Pengeluaran (Biaya)"),
        ],
        value="Pendapatan",
    )
    form_tanggal = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=200, value=today.isoformat())
    form_kategori = ft.Dropdown(label="Kategori", width=250)
    form_nominal = ft.TextField(label="Nominal (Rp)", width=250, value="0")
    form_keterangan = ft.TextField(label="Keterangan / Deskripsi", width=460, multiline=True, min_lines=2, max_lines=3)
    form_nota = ft.TextField(label="No. Nota / Bukti (opsional)", width=200)

    form_cabang_dropdown = ft.Dropdown(
        label="Cabang",
        width=250,
        options=[ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value=str(cabang_list[0][0]) if cabang_list else "1",
    )

    def update_kategori_options(e=None):
        jenis_val = form_jenis.value
        kategori_options = (
            DEFAULT_KATEGORI_PENDAPATAN if jenis_val == "Pendapatan" else DEFAULT_KATEGORI_PENGELUARAN
        )
        form_kategori.options = [ft.dropdown.Option(k, k) for k in kategori_options]
        form_kategori.value = kategori_options[0] if kategori_options else ""
        if e:
            page.update()

    form_jenis.on_change = update_kategori_options
    update_kategori_options()

    def submit_form(e):
        try:
            tgl_val = parse_date("Tanggal", form_tanggal.value)
            nom_val = parse_positive_decimal("Nominal", form_nominal.value)
            ket_val = require_text("Keterangan", form_keterangan.value, max_length=200)
            kat_val = form_kategori.value or "Lain-lain"
            jns_val = form_jenis.value
            nota_val = (form_nota.value or "").strip()

            if is_pusat:
                sel_cid = int(form_cabang_dropdown.value or 1)
                nama_cbg = next((c[1] for c in cabang_list if c[0] == sel_cid), "Cabang")
            else:
                sel_cid = actor.get("cabang_id", 1)
                nama_cbg = actor.get("nama_cabang", "Cabang")

            is_edit = form_id_target["id"] is not None
            if not is_edit:
                add_transaksi_kas(
                    cabang_id=sel_cid,
                    nama_cabang=nama_cbg,
                    tanggal=tgl_val,
                    jenis=jns_val,
                    kategori=kat_val,
                    nominal=nom_val,
                    keterangan=ket_val,
                    nota=nota_val,
                )
                success_msg = "Transaksi berhasil ditambahkan!"
            else:
                update_transaksi_kas(
                    transaksi_id=form_id_target["id"],
                    tanggal=tgl_val,
                    jenis=jns_val,
                    kategori=kat_val,
                    nominal=nom_val,
                    keterangan=ket_val,
                    nota=nota_val,
                    cabang_id=sel_cid,
                    nama_cabang=nama_cbg,
                )
                success_msg = "Transaksi berhasil diperbarui!"

            # Tutup dialog terlebih dahulu
            close_dialog()
            # Segarkan tabel & metrik
            refresh_table_content()
            # Tampilkan notifikasi snackbar
            page.show_dialog(ft.SnackBar(ft.Text(success_msg), bgcolor=ft.Colors.GREEN_700))
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal simpan transaksi: {ex}"), bgcolor=ft.Colors.RED_400))

    form_dialog_title = ft.Text("Tambah Transaksi Baru", weight=ft.FontWeight.W_500)
    form_dialog = ft.AlertDialog(
        title=form_dialog_title,
        content=ft.Container(
            content=ft.Column([
                ft.Row([form_jenis, form_tanggal], spacing=10),
                ft.Row([form_kategori, form_nominal], spacing=10),
                form_keterangan,
                ft.Row([
                    form_nota,
                    form_cabang_dropdown if is_pusat else ft.Container(),
                ], spacing=10),
            ], tight=True, spacing=12),
            width=500,
        ),
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Simpan", on_click=submit_form, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ],
    )

    def open_add_dialog(e=None):
        form_id_target["id"] = None
        form_dialog_title.value = "Tambah Transaksi Baru"
        form_jenis.value = "Pendapatan"
        update_kategori_options()
        form_tanggal.value = date.today().isoformat()
        form_nominal.value = "0"
        form_keterangan.value = ""
        form_nota.value = ""
        if is_pusat and cabang_list:
            form_cabang_dropdown.value = str(cabang_list[0][0])
        page.show_dialog(form_dialog)

    def open_edit_dialog(item):
        form_id_target["id"] = item["id"]
        form_dialog_title.value = f"Edit Transaksi #{item['id']}"
        form_jenis.value = item["jenis"]
        update_kategori_options()
        form_kategori.value = item["kategori"]
        form_tanggal.value = item["tanggal"].isoformat() if hasattr(item["tanggal"], "isoformat") else str(item["tanggal"])
        form_nominal.value = str(item["nominal"])
        form_keterangan.value = item["keterangan"]
        form_nota.value = item["nota"]
        if is_pusat:
            form_cabang_dropdown.value = str(item["cabang_id"])
        page.show_dialog(form_dialog)

    # ==========================
    # DIALOG HAPUS
    # ==========================
    delete_target = {"id": None, "ket": ""}
    delete_msg = ft.Text("")

    def confirm_delete(e):
        try:
            tid = delete_target["id"]
            if tid:
                delete_transaksi_kas(tid)
                close_dialog()
                refresh_table_content()
                page.show_dialog(ft.SnackBar(ft.Text("Transaksi berhasil dihapus!"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal menghapus transaksi: {ex}"), bgcolor=ft.Colors.RED_400))

    delete_dialog = ft.AlertDialog(
        title=ft.Text("Konfirmasi Hapus Transaksi"),
        content=delete_msg,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Ya, Hapus", on_click=confirm_delete, bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
        ],
    )

    def open_delete_dialog(item):
        delete_target["id"] = item["id"]
        delete_target["ket"] = item["keterangan"]
        delete_msg.value = f"Apakah Anda yakin ingin menghapus transaksi '{item['keterangan']}' senilai {rp(item['nominal'])}?"
        page.show_dialog(delete_dialog)

    # ==========================
    # KOMPONEN FILTER (HANYA DARI TANGGAL / RENTANG & CABANG PUSAT)
    # ==========================
    filter_start_field = ft.TextField(
        label="Dari Tanggal (YYYY-MM-DD)",
        hint_text="YYYY-MM-DD",
        width=190,
        value="",
    )

    filter_end_field = ft.TextField(
        label="Sampai Tanggal (YYYY-MM-DD)",
        hint_text="YYYY-MM-DD",
        width=190,
        value="",
    )

    filter_sort_dropdown = ft.Dropdown(
        label="Urutan Tanggal",
        width=190,
        options=[
            ft.dropdown.Option("desc", "Terbaru (Desc)"),
            ft.dropdown.Option("asc", "Terlama (Asc)"),
        ],
        value=filter_state["sort_order"],
    )

    filter_cabang_dropdown = ft.Dropdown(
        label="Cabang",
        width=200,
        options=[ft.dropdown.Option("Semua", "Semua Cabang")] + [ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value="Semua" if filter_state["cabang_id"] is None else str(filter_state["cabang_id"]),
    )

    search_field = ft.TextField(
        label="Cari Transaksi",
        hint_text="Keterangan, nota, kategori...",
        prefix_icon=ft.Icons.SEARCH,
        width=240,
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

        if is_pusat:
            sel_cbg = filter_cabang_dropdown.value
            filter_state["cabang_id"] = None if sel_cbg == "Semua" else int(sel_cbg)

        filter_state["search"] = search_field.value or ""
        refresh_table_content()

    def reset_filter(e=None):
        filter_start_field.value = ""
        filter_end_field.value = ""
        filter_sort_dropdown.value = "desc"
        if is_pusat:
            filter_cabang_dropdown.value = "Semua"
        search_field.value = ""
        apply_filter()

    search_field.on_submit = apply_filter
    filter_sort_dropdown.on_change = apply_filter

    filter_controls = [
        filter_start_field,
        filter_end_field,
        filter_sort_dropdown,
    ]
    if is_pusat:
        filter_controls.append(filter_cabang_dropdown)
    filter_controls.append(search_field)

    filter_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FILTER_LIST, size=20, color=ft.Colors.BLUE_700),
                ft.Text("Filter Data", weight=ft.FontWeight.W_500, size=15),
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

    # ==========================
    # TABEL DAFTAR TRANSAKSI
    # ==========================
    table_container = ft.Container()

    def on_sort_tanggal(col_idx, ascending):
        filter_state["sort_order"] = "asc" if ascending else "desc"
        filter_sort_dropdown.value = filter_state["sort_order"]
        refresh_table_content()

    def build_table_rows(items):
        rows = []
        for it in items:
            is_pendapatan = it["jenis"] == "Pendapatan"
            jenis_color = ft.Colors.GREEN_700 if is_pendapatan else ft.Colors.RED_700
            jenis_dark_color = ft.Colors.GREEN_400 if is_pendapatan else ft.Colors.RED_400
            jenis_bg = ft.Colors.GREEN_50 if is_pendapatan else ft.Colors.RED_50
            jenis_dark_bg = ft.Colors.GREEN_900 if is_pendapatan else ft.Colors.RED_900

            tgl_str = it["tanggal"].strftime("%d-%m-%Y") if hasattr(it["tanggal"], "strftime") else str(it["tanggal"])
            nom_prefix = "+ " if is_pendapatan else "- "

            cells = [
                ft.DataCell(ft.Text(tgl_str, size=13)),
            ]

            if is_pusat:
                cells.append(ft.DataCell(ft.Text(it.get("nama_cabang", "-"), size=13)))

            cells.extend([
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(
                            it["jenis"],
                            size=11,
                            weight=ft.FontWeight.W_500,
                            color=jenis_dark_color if is_dark else jenis_color,
                        ),
                        bgcolor=jenis_dark_bg if is_dark else jenis_bg,
                        padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                        border_radius=6,
                    )
                ),
                ft.DataCell(ft.Text(it["kategori"], size=13, weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(it["keterangan"] or "-", size=13)),
                ft.DataCell(
                    ft.Text(
                        f"{nom_prefix}{rp(it['nominal'])}",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=jenis_dark_color if is_dark else jenis_color,
                    )
                ),
                ft.DataCell(ft.Text(it["nota"] or "-", size=12, color=ft.Colors.GREY_500)),
                ft.DataCell(
                    ft.Row([
                        ft.IconButton(
                            ft.Icons.EDIT,
                            icon_size=18,
                            tooltip="Edit Transaksi",
                            on_click=lambda e, item=it: open_edit_dialog(item),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_size=18,
                            icon_color=ft.Colors.RED_400,
                            tooltip="Hapus Transaksi",
                            on_click=lambda e, item=it: open_delete_dialog(item),
                        ),
                    ], spacing=2)
                ),
            ])

            rows.append(ft.DataRow(cells=cells))
        return rows

    # Cards Metrik
    metric_pendapatan_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_pengeluaran_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_saldo_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_count_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    def refresh_table_content():
        items = get_filtered_data()

        pendapatan_sum = sum([it["nominal"] for it in items if it["jenis"] == "Pendapatan"])
        pengeluaran_sum = sum([it["nominal"] for it in items if it["jenis"] == "Pengeluaran"])
        saldo_sum = pendapatan_sum - pengeluaran_sum
        count_sum = len(items)

        metric_pendapatan_card.content = metric_card(
            page,
            "Total Pendapatan",
            rp(pendapatan_sum),
            light_color=ft.Colors.GREEN_50,
            light_text_color=ft.Colors.GREEN_900,
            dark_color=ft.Colors.GREEN_900,
            dark_text_color=ft.Colors.GREEN_100,
        )
        metric_pengeluaran_card.content = metric_card(
            page,
            "Total Pengeluaran",
            rp(pengeluaran_sum),
            light_color=ft.Colors.RED_50,
            light_text_color=ft.Colors.RED_900,
            dark_color=ft.Colors.RED_900,
            dark_text_color=ft.Colors.RED_100,
        )
        metric_saldo_card.content = metric_card(
            page,
            "Saldo Kas Bersih",
            rp(saldo_sum),
            light_color=ft.Colors.BLUE_50 if saldo_sum >= 0 else ft.Colors.RED_50,
            light_text_color=ft.Colors.BLUE_900 if saldo_sum >= 0 else ft.Colors.RED_900,
            dark_color=ft.Colors.BLUE_900 if saldo_sum >= 0 else ft.Colors.RED_900,
            dark_text_color=ft.Colors.BLUE_100 if saldo_sum >= 0 else ft.Colors.RED_100,
        )
        metric_count_card.content = metric_card(
            page,
            "Jumlah Transaksi",
            f"{count_sum} Transaksi",
            light_color=ft.Colors.GREY_100,
            light_text_color=ft.Colors.GREY_900,
            dark_color=ft.Colors.GREY_800,
            dark_text_color=ft.Colors.WHITE,
        )

        if not items:
            table_container.content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=48, color=ft.Colors.GREY_400),
                    ft.Container(height=8),
                    ft.Text("Tidak ada data transaksi", size=15, weight=ft.FontWeight.W_500),
                    ft.Text("Gunakan tombol 'Tambah Transaksi' untuk memasukkan catatan kas baru atau sesuaikan filter.", size=12, color=ft.Colors.GREY_500),
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
                ft.DataColumn(ft.Text("Jenis")),
                ft.DataColumn(ft.Text("Kategori")),
                ft.DataColumn(ft.Text("Keterangan")),
                ft.DataColumn(ft.Text("Nominal")),
                ft.DataColumn(ft.Text("Nota")),
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

    # Export PDF Picker & Handler
    export_picker = ft.FilePicker()
    if export_picker not in page.services:
        page.services.append(export_picker)

    async def export_pdf(e):
        items = get_filtered_data()
        if not items:
            page.show_dialog(ft.SnackBar(ft.Text("Tidak ada data transaksi untuk diexport."), bgcolor=ft.Colors.RED_400))
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

        filter_info = {
            "periode": periode_str,
            "cabang": cbg_name,
            "extra": f"Total: {len(items)} Transaksi",
        }

        nama_file_default = f"Laporan_Kas_{today.strftime('%Y%m%d')}.pdf"
        try:
            if page.platform == ft.PagePlatform.ANDROID or page.platform == ft.PagePlatform.IOS:
                pdf_bytes = generate_pendapatan_pengeluaran_pdf(items, filter_info, is_pusat=is_pusat, output_path=None)
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Kas PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
                if not save_path:
                    return
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Kas PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if not save_path:
                    return
                if not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                generate_pendapatan_pengeluaran_pdf(items, filter_info, is_pusat=is_pusat, output_path=save_path)

            log_activity(
                actor.get("id"),
                actor.get("username", "user"),
                "CREATE",
                "export_pdf",
                filter_state.get("cabang_id") or 0,
                f"Export PDF Laporan Kas ({periode_str})",
                filter_state.get("cabang_id"),
            )
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    # Initial population
    refresh_table_content()

    # Layout Utama
    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Pendapatan & Pengeluaran", size=22, weight=ft.FontWeight.W_600),
                ft.Text("Kelola dan pantau seluruh transaksi kas masuk & keluar.", size=13, color=ft.Colors.GREY_500),
            ], expand=True),
            ft.OutlinedButton(
                "Export ke PDF",
                icon=ft.Icons.PICTURE_AS_PDF,
                on_click=export_pdf,
            ),
            ft.ElevatedButton(
                "Tambah Transaksi",
                icon=ft.Icons.ADD,
                on_click=open_add_dialog,
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
            ft.IconButton(ft.Icons.REFRESH, tooltip="Segarkan Data", on_click=lambda e: refresh_table_content()),
        ]),
        ft.Container(height=8),
        ft.ResponsiveRow([
            metric_pendapatan_card,
            metric_pengeluaran_card,
            metric_saldo_card,
            metric_count_card,
        ], spacing=12, run_spacing=12),
        ft.Container(height=12),
        filter_card,
        ft.Container(height=16),
        ft.Row([
            ft.Text("Daftar Transaksi Kas", size=16, weight=ft.FontWeight.W_500, expand=True),
        ]),
        ft.Container(height=8),
        table_container,
        ft.Container(height=24),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return body
