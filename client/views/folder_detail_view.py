import flet as ft
from decimal import Decimal
from datetime import date
from components.appbar import build_appbar, nav_rail
from utils.formatting import rp
from utils.validation import require_text, parse_date, parse_positive_decimal
from utils.pdf_export import generate_folder_pdf
from db.invoice_repo import get_invoices, create_invoice, update_invoice, delete_invoice
from db.folder_repo import get_folder_header
from db.transaksi_repo import get_transaksi
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

    # ---------- Dialog: edit invoice ----------
    edit_no_field = ft.TextField(label="No.", width=150)
    edit_tgl_dibuat_field = ft.TextField(label="Date (YYYY-MM-DD)", width=180)
    edit_tgl_laporan_field = ft.TextField(label="TGL Laporan (YYYY-MM-DD)", width=200)
    edit_invoice_bon_field = ft.TextField(label="Invoice / Bon (Rp)", width=200)
    edit_invoice_target = {"iid": None}

    def submit_edit_invoice(e):
        iid = edit_invoice_target["iid"]
        if not iid:
            return
        try:
            no_laporan = require_text("No.", edit_no_field.value, max_length=50)
            tgl_dibuat_val = parse_date("Date", edit_tgl_dibuat_field.value)
            tgl_laporan_val = parse_date("TGL Laporan", edit_tgl_laporan_field.value)
            invoice_bon_val = parse_positive_decimal("Invoice / Bon", edit_invoice_bon_field.value)
            update_invoice(iid, no_laporan, tgl_dibuat_val, tgl_laporan_val, invoice_bon_val)
            log_activity(actor["id"], actor["username"], "UPDATE", "invoice", iid, f"Mengubah invoice {no_laporan} di {nama_folder}", folder_cabang_id)
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal update: {ex}"), bgcolor=ft.Colors.RED_400))

    edit_invoice_dlg = ft.AlertDialog(
        title=ft.Text("Edit laporan invoice"),
        content=ft.Column([
            ft.Row([edit_no_field, edit_tgl_dibuat_field]),
            ft.Row([edit_tgl_laporan_field, edit_invoice_bon_field]),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan Perubahan", on_click=submit_edit_invoice),
        ],
    )

    def open_edit_invoice_dialog(iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon):
        edit_invoice_target["iid"] = iid
        edit_no_field.value = no_laporan or ""
        edit_tgl_dibuat_field.value = tgl_dibuat.isoformat() if tgl_dibuat else date.today().isoformat()
        edit_tgl_laporan_field.value = tgl_laporan.isoformat() if tgl_laporan else date.today().isoformat()
        edit_invoice_bon_field.value = str(invoice_bon or 0)
        page.show_dialog(edit_invoice_dlg)

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
                ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e, iid=iid, nl=no_laporan, td=tgl_dibuat, tl=tgl_laporan, ib=invoice_bon: open_edit_invoice_dialog(iid, nl, td, tl, ib)),
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
            page.update()
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
            # BARU: ambil detail transaksi harian tiap invoice, supaya PDF
            # folder juga menampilkan rincian per hari (bukan cuma ringkasan).
            invoices_with_transaksi = []
            for inv in invoices:
                iid = inv[0]
                try:
                    transaksi = get_transaksi(iid)
                except Exception:
                    transaksi = []
                invoices_with_transaksi.append({"header": inv, "transaksi": transaksi})

            generate_folder_pdf(nama_folder, invoices_with_transaksi, save_path)
            log_activity(actor["id"], actor["username"], "CREATE", "export_pdf", folder_id, f"Export PDF folder {nama_folder}", folder_cabang_id)
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    title_text = f"Invoice - {nama_folder}"
    if is_pusat:
        title_text += f" ({nama_cabang_folder})"
    back_route = f"/invoices/cabang/{folder_cabang_id}" if is_pusat else "/invoices"

    # Catatan: halaman ini SEHARUSNYA tidak muncul untuk folder normal --
    # main.py otomatis lompat ke /invoice/{id} kalau folder cuma punya
    # 1 invoice (kebijakan 1 folder = 1 invoice). Halaman ini cuma
    # kepakai untuk 2 kasus: folder ini belum punya invoice sama sekali
    # (misal auto-create invoice sempat gagal), atau folder lama yang
    # kebetulan masih punya >1 invoice dari sebelum kebijakan ini berlaku.
    info_banner = None
    if len(invoices) == 0:
        info_banner = ft.Container(
            content=ft.Text("Folder ini belum punya invoice. Buat 1 invoice untuk mulai input transaksi harian.", size=13, color=ft.Colors.ORANGE_900),
            bgcolor=ft.Colors.ORANGE_50, padding=12, border_radius=8,
        )
    elif len(invoices) > 1:
        info_banner = ft.Container(
            content=ft.Text("Folder ini punya lebih dari 1 invoice (data lama). Untuk folder baru, cukup 1 invoice per folder.", size=13, color=ft.Colors.BLUE_900),
            bgcolor=ft.Colors.BLUE_50, padding=12, border_radius=8,
        )

    body_controls = [
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go(back_route)),
            ft.Column([
                ft.Text(title_text, size=20, weight=ft.FontWeight.W_500),
                ft.Text("Daftar laporan invoice pada periode ini.", size=13, color=ft.Colors.GREY_600),
            ], expand=True),
            ft.OutlinedButton("Export ke PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_pdf),
            ft.ElevatedButton("Buat laporan baru", icon=ft.Icons.ADD, on_click=open_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]),
        ft.Container(height=16),
    ]
    if info_banner:
        body_controls.append(info_banner)
        body_controls.append(ft.Container(height=12))
    body_controls.append(
        ft.Row([table], scroll=ft.ScrollMode.AUTO) if invoices else ft.Text("Belum ada laporan invoice di folder ini.", color=ft.Colors.GREY_600)
    )

    body = ft.Column(body_controls, scroll=ft.ScrollMode.AUTO, expand=True)

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
