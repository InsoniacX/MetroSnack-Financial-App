import flet as ft
from decimal import Decimal
from datetime import date
from components.appbar import build_appbar, nav_rail
from components.metric_card import metric_card
from utils.formatting import rp
from utils.validation import parse_date, parse_positive_decimal
from utils.hutang_style import hutang_style
from utils.pdf_export import generate_invoice_pdf
from db.invoice_repo import get_invoice_full, update_sisa_barang_manual
from db.transaksi_repo import add_transaksi, update_transaksi, delete_transaksi
from db.activity_repo import log_activity
from state import app_state


def build_view(page: ft.Page, invoice_id: int):
    def refresh():
        page.views[-1] = build_view(page, invoice_id)
        page.update()

    actor = app_state.user
    is_pusat = actor.get("cabang_id") is None

    header, transaksi = get_invoice_full(invoice_id)
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
    sisa_hutang_toko = (invoice_bon or 0) + total_barang - total_uang

    def hapus_baris(tid, tanggal_str):
        try:
            delete_transaksi(tid)
            log_activity(actor["id"], actor["username"], "DELETE", "transaksi_harian", tid, f"Menghapus transaksi {tanggal_str} di invoice {no_laporan or invoice_id}", invoice_cabang_id)
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal hapus baris: {ex}"), bgcolor=ft.Colors.RED_400))

    edit_tgl_field = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=200)
    edit_barang_field = ft.TextField(label="Masuk Barang (Rp)", width=200)
    edit_uang_field = ft.TextField(label="Masuk Uang (Rp)", width=200)
    edit_nota_field = ft.TextField(label="Nota (opsional)", width=200)
    edit_transaksi_target = {"tid": None}

    def submit_edit_baris(e):
        tid = edit_transaksi_target["tid"]
        if not tid:
            return
        try:
            tanggal_val = parse_date("Tanggal", edit_tgl_field.value)
            barang_val = parse_positive_decimal("Masuk Barang", edit_barang_field.value)
            uang_val = parse_positive_decimal("Masuk Uang", edit_uang_field.value)
            nota_val = (edit_nota_field.value or "").strip() or None
            update_transaksi(tid, tanggal_val, barang_val, uang_val, nota_val)
            log_activity(actor["id"], actor["username"], "UPDATE", "transaksi_harian", tid, f"Mengubah transaksi {tanggal_val.strftime('%d-%m-%Y')} di invoice {no_laporan or invoice_id}", invoice_cabang_id)
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal update baris: {ex}"), bgcolor=ft.Colors.RED_400))

    edit_dlg = ft.AlertDialog(
        title=ft.Text("Edit baris transaksi harian"),
        content=ft.Column([
            ft.Row([edit_tgl_field, edit_barang_field]),
            ft.Row([edit_uang_field, edit_nota_field]),
        ], tight=True, spacing=10),
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

    rows = []
    for t in transaksi:
        tid, ttgl, mbarang, muang, lk, ket, nota = t
        warna = ft.Colors.GREEN_700 if ket == "Lebih Uang" else ft.Colors.RED_700
        bg = ft.Colors.GREEN_50 if ket == "Lebih Uang" else ft.Colors.RED_50
        tgl_str = ttgl.strftime("%d-%m-%Y")
        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(tgl_str)),
            ft.DataCell(ft.Text(rp(mbarang))),
            ft.DataCell(ft.Text(rp(muang))),
            ft.DataCell(ft.Container(
                content=ft.Text(f"{rp(lk)}  ({ket})", size=12, color=warna),
                bgcolor=bg, padding=ft.Padding.symmetric(vertical=4, horizontal=8), border_radius=6,
            )),
            ft.DataCell(ft.Text(nota or "-", size=12, color=ft.Colors.GREY_700)),
            ft.DataCell(ft.Row([
                ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e, tid=tid, tt=ttgl, mb=mbarang, mu=muang, nt=nota: open_edit_dialog(tid, tt, mb, mu, nt)),
                ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, tooltip="Hapus", on_click=lambda e, tid=tid, ts=tgl_str: hapus_baris(tid, ts)),
            ])),
        ]))

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Tanggal")), ft.DataColumn(ft.Text("Masuk Barang")),
            ft.DataColumn(ft.Text("Masuk Uang")), ft.DataColumn(ft.Text("Lebih / Kurang Uang")),
            ft.DataColumn(ft.Text("Nota")), ft.DataColumn(ft.Text("Aksi")),
        ],
        rows=rows,
    )

    tgl_field = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=200, value=date.today().isoformat())
    barang_field = ft.TextField(label="Masuk Barang (Rp)", width=200, value="0")
    uang_field = ft.TextField(label="Masuk Uang (Rp)", width=200, value="0")
    nota_field = ft.TextField(label="Nota (opsional)", width=200)

    def submit_baris(e):
        try:
            tanggal_val = parse_date("Tanggal", tgl_field.value)
            barang_val = parse_positive_decimal("Masuk Barang", barang_field.value)
            uang_val = parse_positive_decimal("Masuk Uang", uang_field.value)
            nota_val = (nota_field.value or "").strip() or None
            add_transaksi(invoice_id, tanggal_val, barang_val, uang_val, nota_val)
            log_activity(actor["id"], actor["username"], "CREATE", "transaksi_harian", invoice_id, f"Tambah transaksi {tanggal_val.strftime('%d-%m-%Y')} di invoice {no_laporan or invoice_id}",
                         invoice_cabang_id)
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal simpan baris: {ex}"), bgcolor=ft.Colors.RED_400))

    dlg = ft.AlertDialog(
        title=ft.Text("Tambah baris transaksi harian"),
        content=ft.Column([
            ft.Row([tgl_field, barang_field]),
            ft.Row([uang_field, nota_field]),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_baris),
        ],
    )

    def open_dialog(e):
        page.show_dialog(dlg)

    sisa_barang_field = ft.TextField(label="Sisa Barang di Toko (Rp)", width=220)

    def submit_sisa_barang(e):
        try:
            nilai = parse_positive_decimal("Sisa Barang di Toko", sisa_barang_field.value)
            update_sisa_barang_manual(invoice_id, nilai)
            log_activity(actor["id"], actor["username"], "UPDATE", "invoice", invoice_id, f"Update Sisa Barang di Toko: {nilai}", invoice_cabang_id)
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal update Sisa Barang: {ex}"), bgcolor=ft.Colors.RED_400))

    sisa_barang_dlg = ft.AlertDialog(
        title=ft.Text("Update Sisa Barang di Toko"),
        content=ft.Column([
            ft.Text("Masukkan hasil cek fisik barang hari ini.", size=12, color=ft.Colors.GREY_600),
            sisa_barang_field,
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_sisa_barang),
        ],
    )

    def open_sisa_barang_dialog(e):
        sisa_barang_field.value = str(sisa_barang_manual) if sisa_barang_manual is not None else "0"
        page.show_dialog(sisa_barang_dlg)

    export_picker = ft.FilePicker()

    async def export_pdf(e):
        nama_file_default = f"Invoice_{(no_laporan or str(invoice_id)).replace(' ', '_')}.pdf"
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
        try:
            generate_invoice_pdf(header, transaksi, save_path)
            log_activity(actor["id"], actor["username"], "CREATE", "export_pdf", invoice_id, f"Export PDF invoice {no_laporan or invoice_id}", invoice_cabang_id)
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    header_info = ft.Row([
        ft.Column([ft.Text("No.", size=11, color=ft.Colors.GREY_600), ft.Text(no_laporan or "-", size=14, weight=ft.FontWeight.W_500)]),
        ft.Column([ft.Text("Date", size=11, color=ft.Colors.GREY_600), ft.Text(tgl_dibuat.strftime("%d-%m-%Y") if tgl_dibuat else "-", size=14, weight=ft.FontWeight.W_500)]),
        ft.Column([ft.Text("TGL Laporan", size=11, color=ft.Colors.GREY_600), ft.Text(tgl_laporan.strftime("%d-%m-%Y") if tgl_laporan else "-", size=14, weight=ft.FontWeight.W_500)]),
        ft.Column([ft.Text("Invoice / Bon", size=11, color=ft.Colors.GREY_600), ft.Text(rp(invoice_bon), size=14, weight=ft.FontWeight.W_500)]),
    ], spacing=32)

    # PENTING: back_route TIDAK boleh ke /invoices/{folder_id} lagi --
    # sejak kebijakan 1 folder = 1 invoice, main.py auto-redirect route
    # itu BALIK ke /invoice/{id} ini (karena foldernya cuma 1 invoice),
    # jadi tombol back akan terasa "tidak berfungsi" (loop ke halaman
    # yang sama). Langsung ke daftar folder saja.
    if is_pusat:
        back_route = f"/invoices/cabang/{invoice_cabang_id}"
    else:
        back_route = "/invoices"

    sisa_hutang_nilai, sisa_hutang_bg, sisa_hutang_text = hutang_style(sisa_hutang_toko)
    sisa_barang_display = rp(sisa_barang_manual) if sisa_barang_manual is not None else "Belum diisi"

    body = ft.Column([
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go(back_route)),
            ft.Text("Detail Laporan Invoice", size=20, weight=ft.FontWeight.W_500, expand=True),
            ft.OutlinedButton("Export ke PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_pdf),
        ]),
        ft.Container(height=8),
        ft.Container(header_info, bgcolor=ft.Colors.GREY_50, padding=16, border_radius=10),
        ft.Container(height=20),
        ft.Row([
            ft.Text("Transaksi Harian", size=16, weight=ft.FontWeight.W_500, expand=True),
            ft.ElevatedButton("Tambah baris transaksi", icon=ft.Icons.ADD, on_click=open_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]),
        ft.Container(height=8),
        ft.Row([table], scroll=ft.ScrollMode.AUTO),
        ft.Container(height=24),
        ft.Text("Ringkasan", size=16, weight=ft.FontWeight.W_500),
        ft.Container(height=8),
        ft.ResponsiveRow([
            ft.Container(col=3, content=metric_card("Sisa Hutang Toko", rp(sisa_hutang_nilai), color=sisa_hutang_bg, text_color=sisa_hutang_text)),
            ft.Container(
                col=3,
                content=ft.Stack([
                    metric_card("Sisa Barang di Toko", sisa_barang_display),
                    ft.Container(
                        content=ft.IconButton(ft.Icons.EDIT, icon_size=16, tooltip="Update sisa barang (cek fisik)", on_click=open_sisa_barang_dialog),
                        alignment=ft.Alignment.TOP_RIGHT,
                    ),
                ]),
            ),
            ft.Container(col=3, content=metric_card("Omset Penjualan", rp(omset_penjualan))),
            ft.Container(col=3, content=metric_card("Laba Bersih", rp(laba_bersih), color=ft.Colors.GREEN_50, text_color=ft.Colors.GREEN_900)),
        ], spacing=12),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route=f"/invoice/{invoice_id}",
        services=[export_picker],
        controls=[
            build_appbar(page, "Detail Invoice"),
            ft.Row([
                nav_rail(page, 1),
                ft.VerticalDivider(width=1),
                ft.Container(content=body, padding=24, expand=True),
            ], expand=True),
        ],
        padding=0,
    )
