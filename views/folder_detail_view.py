import flet as ft
from decimal import Decimal
from datetime import date
from components.appbar import build_appbar, nav_rail
from utils.formatting import rp
from utils.validation import require_text, parse_date, parse_positive_decimal
from utils.pdf_export import generate_folder_pdf
from db.invoice_repo import get_invoices, create_invoice, delete_invoice
from db.folder_repo import get_folder_header
from db.activity_repo import log_activity
from state import app_state


def build_view(page: ft.Page, folder_id: int):
    def refresh():
        page.views[-1] = build_view(page, folder_id)
        page.update()

    actor = app_state.user
    is_pusat = actor.get("cabang_id") is None

    header = get_folder_header(folder_id)
    if header is None:
        return ft.View(route=f"/invoices/{folder_id}", controls=[ft.Text("Folder tidak ditemukan.")])
    _, nama_folder, folder_cabang_id, nama_cabang_folder = header

    if not is_pusat and folder_cabang_id != actor.get("cabang_id"):
        return ft.View(
            route=f"/invoices/{folder_id}",
            controls=[
                build_appbar(page, "Akses Ditolak"),
                ft.Container(content=ft.Text("Anda tidak punya akses ke folder cabang lain.", size=16), padding=24),
            ],
        )

    try:
        invoices = get_invoices(folder_id)
    except Exception as ex:
        invoices = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400))

    def hapus_invoice(iid, no_laporan):
        try:
            delete_invoice(iid)
            log_activity(actor["id"], actor["username"], "DELETE", "invoice", iid, f"Menghapus invoice {no_laporan or iid} di {nama_folder}", folder_cabang_id)
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal hapus: {ex}"), bgcolor=ft.Colors.RED_400))

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
                ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, tooltip="Hapus", on_click=lambda e, iid=iid, nl=no_laporan: hapus_invoice(iid, nl)),
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
            no_laporan = require_text("No.", no_field.value, max_length=50)
            tgl_dibuat_val = parse_date("Date", tgl_dibuat_field.value)
            tgl_laporan_val = parse_date("TGL Laporan", tgl_laporan_field.value)
            invoice_bon_val = parse_positive_decimal("Invoice / Bon", invoice_bon_field.value)
            iid = create_invoice(
                folder_id, no_laporan, tgl_dibuat_val, tgl_laporan_val,
                invoice_bon_val, actor["id"],
            )
            log_activity(actor["id"], actor["username"], "CREATE", "invoice", iid, f"Membuat invoice {no_laporan} di {nama_folder}", folder_cabang_id)
            page.pop_dialog()
            page.go(f"/invoice/{iid}")
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal simpan: {ex}"), bgcolor=ft.Colors.RED_400))

    dlg = ft.AlertDialog(
        title=ft.Text("Buat laporan invoice baru"),
        content=ft.Column([
            ft.Row([no_field, tgl_dibuat_field]),
            ft.Row([tgl_laporan_field, invoice_bon_field]),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan & lanjut isi transaksi", on_click=submit_invoice),
        ],
    )

    def open_dialog(e):
        page.show_dialog(dlg)

    export_picker = ft.FilePicker()

    async def export_pdf(e):
        nama_file_default = f"Laporan_{nama_folder.replace(' ', '_')}.pdf"
        save_path = await export_picker.save_file(
            dialog_title="Simpan laporan PDF",
            file_name=nama_file_default,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"],
        )
        if not save_path:
            return
        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"
        try:
            generate_folder_pdf(nama_folder, invoices, save_path)
            log_activity(actor["id"], actor["username"], "CREATE", "export_pdf", folder_id, f"Export PDF folder {nama_folder}", folder_cabang_id)
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    title_text = f"Invoice - {nama_folder}"
    if is_pusat:
        title_text += f" ({nama_cabang_folder})"

    body = ft.Column([
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/invoices")),
            ft.Column([
                ft.Text(title_text, size=20, weight=ft.FontWeight.W_500),
                ft.Text("Daftar laporan invoice pada periode ini.", size=13, color=ft.Colors.GREY_600),
            ], expand=True),
            ft.OutlinedButton("Export ke PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_pdf),
            ft.ElevatedButton("Buat laporan baru", icon=ft.Icons.ADD, on_click=open_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]),
        ft.Container(height=16),
        ft.Row([table], scroll=ft.ScrollMode.AUTO) if invoices else ft.Text("Belum ada laporan invoice di folder ini.", color=ft.Colors.GREY_600),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route=f"/invoices/{folder_id}",
        services=[export_picker],
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