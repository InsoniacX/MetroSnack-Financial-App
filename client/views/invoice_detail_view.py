import flet as ft
from decimal import Decimal
from datetime import date
from components.appbar import build_appbar, is_mobile_layout, nav_rail
from components.file_picker import get_file_picker
from components.metric_card import metric_card
from components.navigation import navigate
from components.pagination import ClientPagination
from utils.formatting import rp
from utils.validation import parse_date, parse_positive_decimal
from utils.hutang_style import hutang_style
from utils.pdf_export import generate_invoice_pdf
from db.invoice_repo import get_invoice_full, update_sisa_barang_manual
from db.transaksi_repo import add_transaksi, update_transaksi, delete_transaksi
from db.activity_repo import log_activity
from state import app_state


def build_view(page: ft.Page, invoice_id: int):
    mobile = is_mobile_layout(page)
    page_width = getattr(page, "width", None) or 1100
    dialog_content_width = min(520, max(260, page_width - 72))
    small_dialog_width = min(420, max(260, page_width - 72))

    def close_dialog(e=None):
        del e
        page.pop_dialog()
        page.update()

    def refresh():
        if page.views and page.views[-1].controls:
            root_control = page.views[-1].controls[0]
            replacement = build_view(page, invoice_id)

            if isinstance(root_control, ft.Container):
                root_control.content = replacement
                page.update()
                return

            if (
                isinstance(root_control, ft.Row)
                and len(root_control.controls) >= 3
                and isinstance(root_control.controls[2], ft.Container)
            ):
                root_control.controls[2].content = replacement
                page.update()
                return

        page.update()

    refresh_table = refresh

    def table_build(transaksi_data):
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Tanggal")), ft.DataColumn(ft.Text("Masuk Barang")),
                ft.DataColumn(ft.Text("Masuk Uang")), ft.DataColumn(ft.Text("Lebih / Kurang Uang")),
                ft.DataColumn(ft.Text("Nota")), ft.DataColumn(ft.Text("Aksi")),
            ],
            rows=build_rows(transaksi_data),
        )

    actor = app_state.user
    is_pusat = actor.get("cabang_id") is None
    is_dark = page.theme_mode == ft.ThemeMode.DARK

    try:
        header, transaksi, keuangan_folder = get_invoice_full(invoice_id, with_finance=True)
    except Exception as ex:
        return ft.Column([
            ft.Text("Data invoice dan saldo hutang gagal dimuat.", size=18),
            ft.Text(str(ex), color=ft.Colors.RED_400),
            ft.TextButton("Coba lagi", on_click=lambda e: refresh()),
        ])
    if header is None:
        return ft.View(route=f"/invoice/{invoice_id}", controls=[ft.Text("Invoice tidak ditemukan.")])
    iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, folder_id, invoice_cabang_id, sisa_barang_manual = header

    if not is_pusat and invoice_cabang_id != actor.get("cabang_id"):
        return ft.View(
            route=f"/invoice/{invoice_id}",
            controls=[
                build_appbar(page, "Akses Ditolak"),
                ft.Container(content=ft.Text("Anda tidak punya akses ke invoice cabang lain.", size=16), padding=24),
            ],
        )

    total_uang = sum([t[3] for t in transaksi]) if transaksi else Decimal(0)
    total_barang = sum([t[2] for t in transaksi]) if transaksi else Decimal(0)

    omset_penjualan = total_uang
    laba_bersih = total_uang - total_barang
    sisa_hutang_toko = keuangan_folder["sisa_hutang"]
    akumulasi_kurang_uang = sum([t[4] for t in transaksi if t[5] == "Kurang Uang"]) if transaksi else Decimal(0)
    akumulasi_lebih_uang = sum([t[4] for t in transaksi if t[5] == "Lebih Uang"]) if transaksi else Decimal(0)

    def parse_optional_note(value):
        note = (value or "").strip() or None
        if note and len(note) > 100:
            raise ValueError("Nota maksimal 100 karakter.")
        return note

    def hapus_baris(tid, tanggal_str):
        try:
            delete_transaksi(tid)
            log_activity(actor["id"], actor["username"], "DELETE", "transaksi_harian", tid, f"Menghapus transaksi {tanggal_str} di invoice {no_laporan or invoice_id}", invoice_cabang_id)
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal hapus baris: {ex}"), bgcolor=ft.Colors.RED_400))

    edit_tgl_field = ft.TextField(
        label="Tanggal (YYYY-MM-DD)",
        col={"xs": 12, "sm": 6},
    )
    edit_barang_field = ft.TextField(
        label="Masuk Barang (Rp)",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )
    edit_uang_field = ft.TextField(
        label="Masuk Uang (Rp)",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )
    edit_nota_field = ft.TextField(
        label="Nota (opsional)",
        max_length=100,
        col={"xs": 12, "sm": 6},
    )
    edit_transaksi_target = {"tid": None}

    def submit_edit_baris(e):
        tid = edit_transaksi_target["tid"]
        if not tid:
            return
        try:
            tanggal_val = parse_date("Tanggal", edit_tgl_field.value)
            barang_val = parse_positive_decimal("Masuk Barang", edit_barang_field.value)
            uang_val = parse_positive_decimal("Masuk Uang", edit_uang_field.value)
            nota_val = parse_optional_note(edit_nota_field.value)
            update_transaksi(tid, tanggal_val, barang_val, uang_val, nota_val)
            log_activity(actor["id"], actor["username"], "UPDATE", "transaksi_harian", tid, f"Mengubah transaksi {tanggal_val.strftime('%d-%m-%Y')} di invoice {no_laporan or invoice_id}", invoice_cabang_id)
            close_dialog(e)
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal update baris: {ex}"), bgcolor=ft.Colors.RED_400))

    edit_dlg = ft.AlertDialog(
        title=ft.Text("Edit baris transaksi harian"),
        content=ft.Container(
            content=ft.ResponsiveRow(
                [
                    edit_tgl_field,
                    edit_barang_field,
                    edit_uang_field,
                    edit_nota_field,
                ],
                spacing=10,
                run_spacing=10,
            ),
            width=dialog_content_width,
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
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan Perubahan", on_click=submit_edit_baris),
        ],
    )

    def open_edit_dialog(tid, ttgl, mbarang, muang, nota):
        edit_transaksi_target["tid"] = tid
        edit_tgl_field.value = ttgl.isoformat() if ttgl else date.today().isoformat()
        edit_barang_field.value = str(mbarang or 0)
        edit_uang_field.value = str(muang or 0)
        edit_nota_field.value = nota or ""
        page.show_dialog(edit_dlg)

    def build_rows(data_transaksi):
        rows = []
        for t in data_transaksi:
            tid, ttgl, mbarang, muang, lk, ket, nota = t
            warna = ft.Colors.GREEN_700 if ket == "Lebih Uang" else ft.Colors.RED_700
            dark_warna = ft.Colors.GREEN_50 if ket == "Lebih Uang" else ft.Colors.RED_50
            bg = ft.Colors.GREEN_50 if ket == "Lebih Uang" else ft.Colors.RED_50
            dark_bg = ft.Colors.GREEN_700 if ket == "Lebih Uang" else ft.Colors.RED_700
            tgl_str = ttgl.strftime("%d-%m-%Y") if ttgl else "-"
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(tgl_str)),
                ft.DataCell(ft.Text(rp(mbarang))),
                ft.DataCell(ft.Text(rp(muang))),
                ft.DataCell(ft.Container(
                    content=ft.Text(f"{rp(lk)}  ({ket})", size=12, color=dark_warna if is_dark else warna),
                    bgcolor=dark_bg if is_dark else bg, padding=ft.Padding.symmetric(vertical=4, horizontal=8), border_radius=6,
                )),
                ft.DataCell(ft.Text(nota or "-", size=12, color=ft.Colors.GREY_700)),
                ft.DataCell(ft.Row([
                    ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e, tid=tid, tt=ttgl, mb=mbarang, mu=muang, nt=nota: open_edit_dialog(tid, tt, mb, mu, nt)),
                    ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, tooltip="Hapus", on_click=lambda e, tid=tid, ts=tgl_str: hapus_baris(tid, ts)),
                ])),
            ]))
        return rows

    def render_transaction_page():
        table.rows = build_rows(transaction_pagination.paginate(transaksi))
        page.update()

    transaction_pagination = ClientPagination(render_transaction_page)
    table = table_build(transaction_pagination.paginate(transaksi))

    tgl_field = ft.TextField(
        label="Tanggal (YYYY-MM-DD)",
        value=date.today().isoformat(),
        col={"xs": 12, "sm": 6},
    )
    barang_field = ft.TextField(
        label="Masuk Barang (Rp)",
        value="0",
        hint_text="Contoh: 150000 atau 150.000",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )
    uang_field = ft.TextField(
        label="Masuk Uang (Rp)",
        value="0",
        hint_text="Contoh: 150000 atau 150.000",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )
    nota_field = ft.TextField(
        label="Nota (opsional)",
        max_length=100,
        col={"xs": 12, "sm": 6},
    )

    def submit_baris(e):
        try:
            tanggal_val = parse_date("Tanggal", tgl_field.value)
            barang_val = parse_positive_decimal("Masuk Barang", barang_field.value)
            uang_val = parse_positive_decimal("Masuk Uang", uang_field.value)
            nota_val = parse_optional_note(nota_field.value)
            add_transaksi(invoice_id, tanggal_val, barang_val, uang_val, nota_val)
            log_activity(actor["id"], actor["username"], "CREATE", "transaksi_harian", invoice_id, f"Tambah transaksi {tanggal_val.strftime('%d-%m-%Y')} di invoice {no_laporan or invoice_id}",
                         invoice_cabang_id)
            close_dialog(e)
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal simpan baris: {ex}"), bgcolor=ft.Colors.RED_400))

    dlg = ft.AlertDialog(
        title=ft.Text("Tambah baris transaksi harian"),
        content=ft.Container(
            content=ft.ResponsiveRow(
                [
                    tgl_field,
                    barang_field,
                    uang_field,
                    nota_field,
                ],
                spacing=10,
                run_spacing=10,
            ),
            width=dialog_content_width,
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
            ft.ElevatedButton("Simpan", on_click=submit_baris),
        ],
    )

    def open_tambah_dialog(e):
        tgl_field.value = date.today().isoformat()
        barang_field.value = "0"
        uang_field.value = "0"
        nota_field.value = ""
        page.show_dialog(dlg)

    sisa_barang_field = ft.TextField(
        label="Sisa Barang di Toko (Rp)",
        hint_text="Contoh: 150000 atau 150.000",
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    def submit_sisa_barang(e):
        try:
            nilai = parse_positive_decimal("Sisa Barang di Toko", sisa_barang_field.value)
            update_sisa_barang_manual(invoice_id, nilai)
            log_activity(actor["id"], actor["username"], "UPDATE", "invoice", invoice_id, f"Update Sisa Barang di Toko: {nilai}", invoice_cabang_id)
            close_dialog(e)
            refresh_table()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal update Sisa Barang: {ex}"), bgcolor=ft.Colors.RED_400))

    sisa_barang_dlg = ft.AlertDialog(
        title=ft.Text("Update Sisa Barang di Toko"),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Masukkan hasil cek fisik barang hari ini.",
                        size=12,
                        color=ft.Colors.GREY_600,
                    ),
                    sisa_barang_field,
                ],
                tight=True,
                spacing=10,
            ),
            width=small_dialog_width,
        ),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_sisa_barang),
        ],
    )

    def open_sisa_barang_dialog(e):
        sisa_barang_field.value = str(sisa_barang_manual) if sisa_barang_manual is not None else "0"
        page.show_dialog(sisa_barang_dlg)

    export_picker = get_file_picker(page, "invoice-detail")

    async def export_pdf(e):
        nama_file_default = f"Invoice_{(no_laporan or str(invoice_id)).replace(' ', '_')}.pdf"
        try:
            if page.platform == ft.PagePlatform.ANDROID or page.platform == ft.PagePlatform.IOS:
                fresh_header, fresh_transaksi, balance = get_invoice_full(invoice_id, with_finance=True)
                pdf_bytes = generate_invoice_pdf(fresh_header, fresh_transaksi, None, keuangan_folder=balance)
                save_path = await export_picker.save_file(
                    dialog_title="Simpan invoice PDF", 
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM, 
                    allowed_extensions=["pdf"], 
                    src_bytes=pdf_bytes)
                if not save_path:
                    return
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan invoice PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if not save_path:
                    return
                if not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                fresh_header, fresh_transaksi, balance = get_invoice_full(invoice_id, with_finance=True)
                generate_invoice_pdf(fresh_header, fresh_transaksi, save_path, keuangan_folder=balance)

            log_activity(actor["id"], actor["username"], "CREATE", "export_pdf", invoice_id, f"Export PDF invoice {no_laporan or invoice_id}", invoice_cabang_id)
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    def header_info_item(label, value):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        label,
                        size=11,
                        color=(
                            ft.Colors.WHITE
                            if is_dark
                            else ft.Colors.GREY_600
                        ),
                    ),
                    ft.Text(
                        value,
                        size=14,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
                spacing=2,
            ),
            col={"xs": 6, "sm": 3},
        )

    header_info = ft.ResponsiveRow(
        [
            header_info_item("No.", no_laporan or "-"),
            header_info_item(
                "Date",
                tgl_dibuat.strftime("%d-%m-%Y")
                if tgl_dibuat
                else "-",
            ),
            header_info_item(
                "TGL Laporan",
                tgl_laporan.strftime("%d-%m-%Y")
                if tgl_laporan
                else "-",
            ),
            header_info_item("Invoice / Bon", rp(invoice_bon)),
        ],
        spacing=12,
        run_spacing=12,
    )

    # PENTING: back_route TIDAK boleh ke /invoices/{folder_id} lagi --
    # sejak kebijakan 1 folder = 1 invoice, main.py auto-redirect route
    # itu BALIK ke /invoice/{id} ini (karena foldernya cuma 1 invoice),
    # jadi tombol back akan terasa "tidak berfungsi" (loop ke halaman
    # yang sama). Langsung ke daftar folder saja.
    if is_pusat:
        back_route = f"/invoices/cabang/{invoice_cabang_id}"
    else:
        back_route = "/invoices"

    sisa_hutang_nilai, light_sisa_hutang_bg, light_sisa_hutang_text,dark_sisa_hutang_bg, dark_sisa_hutang_text  = hutang_style(sisa_hutang_toko)
    sisa_barang_display = rp(sisa_barang_manual) if sisa_barang_manual is not None else "Belum diisi"

    header_title = ft.Container(
        content=ft.Row(
            [
                ft.IconButton(
                    ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate(page, back_route),
                ),
                ft.Text(
                    "Detail Laporan Invoice",
                    size=20,
                    weight=ft.FontWeight.W_500,
                    expand=True,
                ),
            ]
        ),
        col={"xs": 12, "md": 7},
    )
    header_action = ft.Container(
        content=ft.Row(
            [
                ft.OutlinedButton(
                    "Export PDF" if mobile else "Export ke PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=export_pdf,
                )
            ],
            alignment=(
                ft.MainAxisAlignment.START
                if mobile
                else ft.MainAxisAlignment.END
            ),
        ),
        col={"xs": 12, "md": 5},
    )

    transaction_title = ft.Container(
        content=ft.Text(
            "Transaksi Harian",
            size=16,
            weight=ft.FontWeight.W_500,
        ),
        col={"xs": 12, "sm": 6},
    )
    transaction_action = ft.Container(
        content=ft.Row(
            [
                ft.ElevatedButton(
                    "Tambah Transaksi"
                    if mobile
                    else "Tambah baris transaksi",
                    icon=ft.Icons.ADD,
                    on_click=open_tambah_dialog,
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
        ft.Row([table], scroll=ft.ScrollMode.AUTO)
    )
    table_controls.append(transaction_pagination.control)

    body = ft.Column([
        ft.ResponsiveRow(
            [header_title, header_action],
            spacing=8,
            run_spacing=8,
        ),
        ft.Container(height=8),
        ft.Container(header_info, padding=16, border_radius=10),
        ft.Text(
            f"Hutang bawaan bulan sebelumnya: {rp(keuangan_folder['hutang_bawaan'])}",
            size=14, weight=ft.FontWeight.W_500,
        ),
        ft.Text(
            "Sisa hutang dihitung untuk seluruh folder bulan ini, termasuk hutang bawaan. "
            "Buka ulang halaman setelah mengoreksi bulan sebelumnya.",
            size=12, color=ft.Colors.GREY_400 if is_dark else ft.Colors.GREY_600,
        ),
        ft.Container(height=20),
        ft.ResponsiveRow(
            [transaction_title, transaction_action],
            spacing=8,
            run_spacing=8,
        ),
        ft.Container(height=8),
        ft.Column(table_controls, spacing=6),
        ft.Container(height=12),
        ft.ResponsiveRow([
            ft.Container(
                col={"xs": 12, "sm": 6},
                content=metric_card(
                    page,
                    "Akumulasi Kurang Uang",
                    rp(akumulasi_kurang_uang * -1),
                    light_color=ft.Colors.RED_50,
                    light_text_color=ft.Colors.RED_900,
                    dark_color=ft.Colors.RED_900,
                    dark_text_color=ft.Colors.RED_100,
                ),
            ),
            ft.Container(
                col={"xs": 12, "sm": 6},
                content=metric_card(
                    page,
                    "Akumulasi Lebih Uang",
                    rp(akumulasi_lebih_uang),
                    light_color=ft.Colors.GREEN_50,
                    light_text_color=ft.Colors.GREEN_900,
                    dark_color=ft.Colors.GREEN_900,
                    dark_text_color=ft.Colors.GREEN_100,
                ),
            ),
        ], spacing=12),
        ft.Container(height=24),
        ft.Text("Ringkasan", size=16, weight=ft.FontWeight.W_500),
        ft.Container(height=8),
        ft.ResponsiveRow([
            ft.Container(col={"xs": 12, "sm": 6, "md": 3}, content=metric_card(page, "Sisa Hutang Toko", rp(sisa_hutang_nilai), light_sisa_hutang_bg, light_sisa_hutang_text, dark_sisa_hutang_bg, dark_sisa_hutang_text)),
            ft.Container(
                col={"xs": 12, "sm": 6, "md": 3},
                content=ft.Stack([
                    metric_card(page, "Sisa Barang di Toko", sisa_barang_display, ft.Colors.WHITE, ft.Colors.GREY_900, ft.Colors.GREY_900, ft.Colors.WHITE),
                    ft.Container(
                        content=ft.IconButton(ft.Icons.EDIT, icon_size=16, tooltip="Update sisa barang (cek fisik)", on_click=open_sisa_barang_dialog),
                        alignment=ft.Alignment.TOP_RIGHT,
                    ),
                ]),
            ),
            ft.Container(col={"xs": 12, "sm": 6, "md": 3}, content=metric_card(page, "Omset Penjualan", rp(omset_penjualan), ft.Colors.BLUE_50, ft.Colors.BLUE_900, ft.Colors.BLUE_900, ft.Colors.WHITE)),
            ft.Container(col={"xs": 12, "sm": 6, "md": 3}, content=metric_card(page, "Laba Bersih", rp(laba_bersih), ft.Colors.GREEN_50, ft.Colors.GREEN_900, ft.Colors.GREEN_900, ft.Colors.WHITE)),
        ], spacing=12),
    ], scroll=ft.ScrollMode.AUTO, expand=True)
    return body
    # return ft.View(
    #     route=f"/invoice/{invoice_id}",
    #     services=[export_picker],
    #     controls=[
    #         # build_appbar(page, "Detail Invoice"),
    #         ft.Row([
    #             # nav_rail(page, 1),
    #             ft.VerticalDivider(width=1),
    #             ft.Container(content=body, padding=24, expand=True),
    #         ], expand=True),
    #     ],
    #     padding=0,
    # )
