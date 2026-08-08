import flet as ft
from decimal import Decimal
from datetime import date
from components.appbar import build_appbar, nav_rail
from components.metric_card import metric_card
from utils.formatting import rp
from utils.validation import parse_date, parse_positive_decimal
from db.invoice_repo import get_invoice_header
from db.transaksi_repo import get_transaksi, add_transaksi, update_transaksi, delete_transaksi
from db.activity_repo import log_activity
from state import app_state


def build_view(page: ft.Page, invoice_id: int):
    def refresh():
        page.views[-1] = build_view(page, invoice_id)
        page.update()

    actor = app_state.user
    is_pusat = actor.get("cabang_id") is None

    header = get_invoice_header(invoice_id)
    if header is None:
        return ft.View(route=f"/invoice/{invoice_id}", controls=[ft.Text("Invoice tidak ditemukan.")])
    iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, folder_id, invoice_cabang_id = header

    if not is_pusat and invoice_cabang_id != actor.get("cabang_id"):
        return ft.View(
            route=f"/invoice/{invoice_id}",
            controls=[
                build_appbar(page, "Akses Ditolak"),
                ft.Container(content=ft.Text("Anda tidak punya akses ke invoice cabang lain.", size=16), padding=24),
            ],
        )

    transaksi = get_transaksi(invoice_id)
    total_uang = sum([t[3] for t in transaksi]) if transaksi else Decimal(0)
    total_barang = sum([t[2] for t in transaksi]) if transaksi else Decimal(0)

    omset_penjualan = total_uang
    laba_bersih = total_uang - total_barang
    sisa_hutang_toko = (invoice_bon or 0) + total_barang - total_uang
    sisa_barang_toko = sisa_hutang_toko

    def hapus_baris(tid, tanggal_str):
        try:
            delete_transaksi(tid)
            log_activity(actor["id"], actor["username"], "DELETE", "transaksi_harian", tid, f"Menghapus transaksi {tanggal_str} di invoice {no_laporan or invoice_id}", invoice_cabang_id)
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal hapus baris: {ex}"), bgcolor=ft.Colors.RED_400))

    # ---------- Dialog: edit baris transaksi ----------
    edit_tgl_field = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=200)
    edit_barang_field = ft.TextField(label="Masuk Barang (Rp)", width=200)
    edit_uang_field = ft.TextField(label="Masuk Uang (Rp)", width=200)
    edit_transaksi_target = {"tid": None}

    def submit_edit_baris(e):
        tid = edit_transaksi_target["tid"]
        if not tid:
            return
        try:
            tanggal_val = parse_date("Tanggal", edit_tgl_field.value)
            barang_val = parse_positive_decimal("Masuk Barang", edit_barang_field.value)
            uang_val = parse_positive_decimal("Masuk Uang", edit_uang_field.value)
            update_transaksi(tid, tanggal_val, barang_val, uang_val)
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
        content=ft.Row([edit_tgl_field, edit_barang_field, edit_uang_field]),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan Perubahan", on_click=submit_edit_baris),
        ],
    )

    def open_edit_dialog(tid, ttgl, mbarang, muang):
        edit_transaksi_target["tid"] = tid
        edit_tgl_field.value = ttgl.isoformat() if ttgl else date.today().isoformat()
        edit_barang_field.value = str(mbarang or 0)
        edit_uang_field.value = str(muang or 0)
        page.show_dialog(edit_dlg)

    rows = []
    for t in transaksi:
        tid, ttgl, mbarang, muang, lk, ket = t
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
            ft.DataCell(ft.Row([
                ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e, tid=tid, tt=ttgl, mb=mbarang, mu=muang: open_edit_dialog(tid, tt, mb, mu)),
                ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, tooltip="Hapus", on_click=lambda e, tid=tid, ts=tgl_str: hapus_baris(tid, ts)),
            ])),
        ]))

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Tanggal")), ft.DataColumn(ft.Text("Masuk Barang")),
            ft.DataColumn(ft.Text("Masuk Uang")), ft.DataColumn(ft.Text("Lebih / Kurang Uang")),
            ft.DataColumn(ft.Text("Aksi")),
        ],
        rows=rows,
    )

    tgl_field = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=200, value=date.today().isoformat())
    barang_field = ft.TextField(label="Masuk Barang (Rp)", width=200, value="0")
    uang_field = ft.TextField(label="Masuk Uang (Rp)", width=200, value="0")

    def submit_baris(e):
        try:
            tanggal_val = parse_date("Tanggal", tgl_field.value)
            barang_val = parse_positive_decimal("Masuk Barang", barang_field.value)
            uang_val = parse_positive_decimal("Masuk Uang", uang_field.value)
            add_transaksi(invoice_id, tanggal_val, barang_val, uang_val)
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
        content=ft.Row([tgl_field, barang_field, uang_field]),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_baris),
        ],
    )

    def open_dialog(e):
        page.show_dialog(dlg)

    header_info = ft.Row([
        ft.Column([ft.Text("No.", size=11, color=ft.Colors.GREY_600), ft.Text(no_laporan or "-", size=14, weight=ft.FontWeight.W_500)]),
        ft.Column([ft.Text("Date", size=11, color=ft.Colors.GREY_600), ft.Text(tgl_dibuat.strftime("%d-%m-%Y") if tgl_dibuat else "-", size=14, weight=ft.FontWeight.W_500)]),
        ft.Column([ft.Text("TGL Laporan", size=11, color=ft.Colors.GREY_600), ft.Text(tgl_laporan.strftime("%d-%m-%Y") if tgl_laporan else "-", size=14, weight=ft.FontWeight.W_500)]),
        ft.Column([ft.Text("Invoice / Bon", size=11, color=ft.Colors.GREY_600), ft.Text(rp(invoice_bon), size=14, weight=ft.FontWeight.W_500)]),
    ], spacing=32)

    back_route = f"/invoices/{folder_id}" if folder_id else "/invoices"

    body = ft.Column([
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go(back_route)),
            ft.Text("Detail Laporan Invoice", size=20, weight=ft.FontWeight.W_500),
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
            ft.Container(col=3, content=metric_card("Sisa Hutang Toko", rp(sisa_hutang_toko))),
            ft.Container(col=3, content=metric_card("Sisa Barang di Toko", rp(sisa_barang_toko))),
            ft.Container(col=3, content=metric_card("Omset Penjualan", rp(omset_penjualan))),
            ft.Container(col=3, content=metric_card("Laba Bersih", rp(laba_bersih), color=ft.Colors.GREEN_50, text_color=ft.Colors.GREEN_900)),
        ], spacing=12),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route=f"/invoice/{invoice_id}",
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