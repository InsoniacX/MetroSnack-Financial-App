import flet as ft
from decimal import Decimal
from datetime import date
from components.appbar import build_appbar, nav_rail
from utils.formatting import rp
from db.invoice_repo import get_invoices, create_invoice, delete_invoice
from state import app_state


def build_view(page: ft.Page, folder_id: int, nama_folder: str):
    try:
        invoices = get_invoices(folder_id)
    except Exception:
        invoices = []

    def hapus_invoice(iid):
        try:
            delete_invoice(iid)
            page.go(f"/invoices/{folder_id}?nama={nama_folder}")
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Gagal hapus: {ex}"), bgcolor=ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()

    rows = []
    for inv in invoices:
        iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, total_omzet, total_barang = inv
        laba_bersih = total_omzet - total_barang
        sisa_hutang = (invoice_bon or 0) + total_barang - total_omzet
        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(no_laporan or "-")),
            ft.DataCell(ft.Text(tgl_laporan.strftime("%d-%m-%Y") if tgl_laporan else "-")),
            ft.DataCell(ft.Text(rp(invoice_bon))),
            ft.DataCell(ft.Text(rp(total_omzet))),
            ft.DataCell(ft.Text(rp(laba_bersih))),
            ft.DataCell(ft.Text(rp(sisa_hutang))),
            ft.DataCell(ft.Row([
                ft.IconButton(ft.Icons.VISIBILITY, tooltip="Detail transaksi", on_click=lambda e, iid=iid: page.go(f"/invoice/{iid}")),
                ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, tooltip="Hapus", on_click=lambda e, iid=iid: hapus_invoice(iid)),
            ])),
        ]))

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("No.")), ft.DataColumn(ft.Text("TGL Laporan")),
            ft.DataColumn(ft.Text("Invoice/Bon")), ft.DataColumn(ft.Text("Omset")),
            ft.DataColumn(ft.Text("Laba Bersih")), ft.DataColumn(ft.Text("Sisa Hutang")),
            ft.DataColumn(ft.Text("Aksi")),
        ],
        rows=rows,
    )

    no_field = ft.TextField(label="No.", width=150)
    tgl_dibuat_field = ft.TextField(label="Date (YYYY-MM-DD)", width=180, value=date.today().isoformat())
    tgl_laporan_field = ft.TextField(label="TGL Laporan (YYYY-MM-DD)", width=200, value=date.today().isoformat())
    invoice_bon_field = ft.TextField(label="Invoice / Bon (Rp)", width=200, value="0")

    def submit_invoice(e):
        try:
            iid = create_invoice(
                folder_id, no_field.value, tgl_dibuat_field.value, tgl_laporan_field.value,
                Decimal(invoice_bon_field.value or 0), app_state.user["id"],
            )
            dlg.open = False
            page.update()
            page.go(f"/invoice/{iid}")
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Gagal simpan: {ex}"), bgcolor=ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Buat laporan invoice baru"),
        content=ft.Column([
            ft.Row([no_field, tgl_dibuat_field]),
            ft.Row([tgl_laporan_field, invoice_bon_field]),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
            ft.ElevatedButton("Simpan & lanjut isi transaksi", on_click=submit_invoice),
        ],
    )

    def open_dialog(e):
        page.dialog = dlg
        dlg.open = True
        page.update()

    body = ft.Column([
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/invoices")),
            ft.Column([
                ft.Text(f"Invoice - {nama_folder}", size=20, weight=ft.FontWeight.W_500),
                ft.Text("Daftar laporan invoice pada periode ini.", size=13, color=ft.Colors.GREY_600),
            ], expand=True),
            ft.ElevatedButton("Buat laporan baru", icon=ft.Icons.ADD, on_click=open_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]),
        ft.Container(height=16),
        ft.Row([table], scroll=ft.ScrollMode.AUTO),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        f"/invoices/{folder_id}",
        controls=[
            build_appbar(page, "Detail folder"),
            ft.Row([
                nav_rail(page, 1),
                ft.VerticalDivider(width=1),
                ft.Container(content=body, padding=24, expand=True),
            ], expand=True),
        ],
        padding=0,
    )