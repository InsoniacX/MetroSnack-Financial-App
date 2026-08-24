import flet as ft
from datetime import date
from config import MONTH
from components.appbar import build_appbar, nav_rail
from utils.formatting import rp
from utils.validation import parse_year, require_text, parse_date, parse_positive_decimal
from utils.pdf_export import generate_cabang_pdf
from db.folder_repo import get_folders, create_folder, delete_folder, get_cabang_summary
from db.cabang_repo import get_cabang_name
from db.invoice_repo import get_invoices, create_invoice
from db.transaksi_repo import get_transaksi
from db.activity_repo import log_activity
from state import app_state


def build_view(page: ft.Page)-> ft.Control:
    """Entry point untuk tab 'Invoice'. Admin Pusat -> pilih cabang dulu. Selain itu -> langsung daftar folder miliknya."""
    actor = app_state.user
    cabang_id = actor.get("cabang_id")
    is_pusat = cabang_id is None

    if is_pusat:
        return build_cabang_hub(page)
    return build_folder_list(page, cabang_id, "/invoices", show_back=False)


def build_cabang_hub(page: ft.Page)-> ft.Control:
    """Halaman 'Pilih Cabang' - hanya untuk Admin Pusat."""

    try:
        cabang_summary = get_cabang_summary()
    except Exception as ex:
        cabang_summary = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400))

    cabang_cards = ft.ResponsiveRow(spacing=12, run_spacing=12)
    for c in cabang_summary:
        cid, nama_cabang, total_folder, laba_bersih = c
        cabang_cards.controls.append(
            ft.Container(
                col={"xs": 12, "sm": 6, "md": 4},
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.STORE, color=ft.Colors.BLUE_700, size=26),
                            ft.Text(nama_cabang, weight=ft.FontWeight.W_500, size=17)], spacing=10),
                    ft.Container(height=12),
                    ft.Row([
                        ft.Column([ft.Text("Total folder", size=11, color=ft.Colors.GREY_600), ft.Text(str(total_folder), size=16, weight=ft.FontWeight.W_500)]),
                        ft.Column([ft.Text("Laba bersih", size=11, color=ft.Colors.GREY_600), ft.Text(rp(laba_bersih), size=16, weight=ft.FontWeight.W_500)]),
                    ], spacing=24),
                    ft.Container(height=14),
                    ft.ElevatedButton("Lihat invoice cabang ini", icon=ft.Icons.ARROW_FORWARD, on_click=lambda e, cid=cid: page.go(f"/invoices/cabang/{cid}"), bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                ], spacing=4),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(0.5, ft.Colors.GREY_300),
                border_radius=12,
                padding=20,
            )
        )

    body = ft.Column([
        ft.Text("Pilih cabang", size=20, weight=ft.FontWeight.W_500),
        ft.Text("Klik salah satu cabang untuk melihat daftar invoicenya.", size=13, color=ft.Colors.GREY_600),
        ft.Container(height=16),
        cabang_cards if cabang_summary else ft.Text("Belum ada cabang aktif. Tambahkan cabang lewat menu Cabang.", color=ft.Colors.GREY_600),
    ], scroll=ft.ScrollMode.AUTO, expand=True)
    return body
    # return ft.View(
    #     route="/invoices",
    #     controls=[
    #         build_appbar(page, "Daftar Invoice"),
    #         ft.Row([
    #             nav_rail(page, 1),
    #             ft.VerticalDivider(width=1),
    #             ft.Container(content=body, padding=24, expand=True),
    #         ], expand=True),
    #     ],
    #     padding=0,
    # )


def build_folder_list(page: ft.Page, cabang_id: int, route: str, show_back: bool)-> ft.Control:
    """Daftar folder MILIK 1 CABANG SPESIFIK. Dipakai baik untuk user cabang (route /invoices)
    maupun Admin Pusat yang sudah memilih 1 cabang (route /invoices/cabang/{id})."""
    actor = app_state.user
    is_pusat = actor.get("cabang_id") is None
    is_admin = actor.get("role") == "admin"

    if not is_pusat and cabang_id != actor.get("cabang_id"):
        return ft.View(
            route=route,
            controls=[
                build_appbar(page, "Akses Ditolak"),
                ft.Container(content=ft.Text("Anda tidak punya akses ke cabang lain.", size=16), padding=24),
            ],
        )

    def refresh():
        page.views[-1] = build_folder_list(page, cabang_id, route, show_back)
        page.update()

    nama_cabang_label = None
    try:
        nama_cabang_label = get_cabang_name(cabang_id)
    except Exception:
        nama_cabang_label = None

    try:
        folders = get_folders(cabang_id)
    except Exception as ex:
        folders = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400))

    # ---------- Dialog: konfirmasi hapus folder (khusus admin/owner) ----------
    delete_target = {"fid": None, "nama": None, "total_invoice": 0}

    def confirm_delete_folder(e):
        if not is_admin:
            page.show_dialog(ft.SnackBar(ft.Text("Hanya admin/owner yang bisa menghapus folder."), bgcolor=ft.Colors.RED_400))
            return
        fid = delete_target["fid"]
        if not fid:
            return
        try:
            delete_folder(fid)
            log_activity(actor["id"], actor["username"], "DELETE", "folder_bulan", fid, f"Menghapus folder {delete_target['nama']} beserta {delete_target['total_invoice']} invoice di dalamnya", cabang_id)
            page.pop_dialog()
            page.update()
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal hapus folder: {ex}"), bgcolor=ft.Colors.RED_400))

    delete_folder_dlg = ft.AlertDialog(
        title=ft.Text("Hapus folder ini?"),
        content=ft.Text(""),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Ya, Hapus Permanen", on_click=confirm_delete_folder, bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
        ],
    )

    def open_delete_folder_dialog(fid, nama_folder, total_invoice):
        delete_target["fid"] = fid
        delete_target["nama"] = nama_folder
        delete_target["total_invoice"] = total_invoice
        if total_invoice > 0:
            pesan = (
                f"Folder '{nama_folder}' berisi {total_invoice} invoice. "
                f"Semua invoice beserta transaksi harian di dalamnya akan ikut terhapus permanen. "
                f"Tindakan ini tidak bisa dibatalkan."
            )
        else:
            pesan = f"Folder '{nama_folder}' masih kosong. Hapus folder ini?"
        delete_folder_dlg.content = ft.Text(pesan, size=13)
        page.show_dialog(delete_folder_dlg)

    folder_cards = ft.ResponsiveRow(spacing=12, run_spacing=12)
    for f in folders:
        fid, nama_folder, bulan, tahun, _nama_cabang, total_invoice, laba_bersih = f

        header_controls = [
            ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE_700),
            ft.Text(nama_folder, weight=ft.FontWeight.W_500, size=16, expand=True),
        ]
        if is_admin:
            header_controls.append(
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400, tooltip="Hapus folder", on_click=lambda e, fid=fid, nm=nama_folder, ti=total_invoice: open_delete_folder_dialog(fid, nm, ti))
            )

        folder_cards.controls.append(
            ft.Container(
                col={"xs": 12, "sm": 6, "md": 4},
                content=ft.Column([
                    ft.Row(header_controls),
                    ft.Container(height=8),
                    ft.Row([
                        ft.Column([ft.Text("Total invoice", size=11, color=ft.Colors.GREY_600), ft.Text(str(total_invoice), size=16, weight=ft.FontWeight.W_500)]),
                        ft.Column([ft.Text("Laba bersih", size=11, color=ft.Colors.GREY_600), ft.Text(rp(laba_bersih), size=16, weight=ft.FontWeight.W_500)]),
                    ], spacing=24),
                    ft.Container(height=8),
                    ft.ElevatedButton("Buka folder", icon=ft.Icons.FOLDER_OPEN, on_click=lambda e, fid=fid: page.go(f"/invoices/{fid}")),
                ], spacing=4),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(0.5, ft.Colors.GREY_300),
                border_radius=12,
                padding=16,
            )
        )

    bulan_dd = ft.Dropdown(label="Bulan", width=180,
                            options=[ft.dropdown.Option(str(i), MONTH[i]) for i in range(1, 13)])
    tahun_field = ft.TextField(label="Tahun", width=120, value=str(date.today().year))
    # BARU: sesuai kebijakan 1 folder = 1 invoice, field invoice langsung
    # ditanya di sini juga -- tidak perlu lagi buka folder lalu buat
    # invoice terpisah.
    inv_no_field = ft.TextField(label="No. Laporan", width=150)
    inv_tgl_dibuat_field = ft.TextField(label="Date (YYYY-MM-DD)", width=180, value=date.today().isoformat())
    inv_tgl_laporan_field = ft.TextField(label="TGL Laporan (YYYY-MM-DD)", width=200, value=date.today().isoformat())
    inv_bon_field = ft.TextField(label="Invoice / Bon / Modal (Rp)", width=200, value="0")

    def submit_folder(e):
        if not bulan_dd.value:
            page.show_dialog(ft.SnackBar(ft.Text("Bulan wajib dipilih."), bgcolor=ft.Colors.RED_400))
            return
        try:
            bulan_int = int(bulan_dd.value)
            tahun_int = parse_year("Tahun", tahun_field.value)
            no_laporan = require_text("No. Laporan", inv_no_field.value, max_length=50)
            tgl_dibuat_val = parse_date("Date", inv_tgl_dibuat_field.value)
            tgl_laporan_val = parse_date("TGL Laporan", inv_tgl_laporan_field.value)
            invoice_bon_val = parse_positive_decimal("Invoice / Bon", inv_bon_field.value)
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
            return

        try:
            fid = create_folder(bulan_int, tahun_int, cabang_id, actor["id"])
            nama_folder = f"{MONTH[bulan_int]} {tahun_int}"
            log_activity(actor["id"], actor["username"], "CREATE", "folder_bulan", fid, f"Membuat folder {nama_folder}", cabang_id)
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal buat folder: {ex}"), bgcolor=ft.Colors.RED_400))
            return

        try:
            iid = create_invoice(fid, no_laporan, tgl_dibuat_val, tgl_laporan_val, invoice_bon_val, actor["id"])
            log_activity(actor["id"], actor["username"], "CREATE", "invoice", iid, f"Membuat invoice {no_laporan} di {nama_folder}", cabang_id)
            page.pop_dialog()
            page.update()
            page.go(f"/invoice/{iid}")
        except Exception as ex:
            # Folder sudah terlanjur dibuat, tapi invoice gagal -- folder
            # ini sementara jadi 0-invoice, tetap bisa diakses lewat
            # halaman fallback (folder_detail_view) untuk coba buat lagi.
            page.show_dialog(ft.SnackBar(
                ft.Text(f"Folder berhasil dibuat, tapi gagal membuat invoice: {ex}. Buka folder ini lagi untuk coba buat invoice."),
                bgcolor=ft.Colors.RED_400,
            ))
            page.pop_dialog()
            page.update()
            refresh()

    dlg = ft.AlertDialog(
        title=ft.Text("Buat folder bulan baru"),
        content=ft.Column([
            ft.Row([bulan_dd, tahun_field]),
            ft.Row([inv_no_field, inv_tgl_dibuat_field]),
            ft.Row([inv_tgl_laporan_field, inv_bon_field]),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan & Mulai Input Transaksi", on_click=submit_folder),
        ],
    )

    def open_dialog(e):
        page.show_dialog(dlg)

    # ---------- Export PDF Cabang (BARU): rekap semua folder/bulan sekaligus ----------
    export_picker = ft.FilePicker()

    async def export_cabang_pdf(e):
        if not folders:
            page.show_dialog(ft.SnackBar(ft.Text("Belum ada folder untuk diexport."), bgcolor=ft.Colors.RED_400))
            return

        label_cabang = nama_cabang_label or "Cabang"
        nama_file_default = f"Laporan_Cabang_{label_cabang.replace(' ', '_')}.pdf"
        save_path = await export_picker.save_file(
            dialog_title="Simpan laporan PDF cabang",
            file_name=nama_file_default,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"],
        )
        if not save_path:
            return
        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"

        try:
            # Urutkan folder dari yang lama ke baru supaya laporan runtut
            # (get_folders() mengembalikan urutan terbaru dulu).
            folders_sorted = sorted(folders, key=lambda f: (f[3], f[2]))  # (tahun, bulan) ascending

            folders_data = []
            for f in folders_sorted:
                fid, nama_folder = f[0], f[1]
                invoices = get_invoices(fid)
                invoices_with_transaksi = []
                for inv in invoices:
                    iid = inv[0]
                    try:
                        transaksi = get_transaksi(iid)
                    except Exception:
                        transaksi = []
                    invoices_with_transaksi.append({"header": inv, "transaksi": transaksi})
                folders_data.append({"nama_folder": nama_folder, "invoices_with_transaksi": invoices_with_transaksi})

            generate_cabang_pdf(label_cabang, folders_data, save_path)
            log_activity(actor["id"], actor["username"], "CREATE", "export_pdf", cabang_id, f"Export PDF cabang {label_cabang}", cabang_id)
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF cabang: {ex}"), bgcolor=ft.Colors.RED_400))

    title_text = f"Invoice - {nama_cabang_label}" if show_back and nama_cabang_label else "Daftar invoice"

    header_row_controls = []
    if show_back:
        header_row_controls.append(ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/invoices")))
    header_row_controls.append(
        ft.Column([
            ft.Text(title_text, size=20, weight=ft.FontWeight.W_500),
            ft.Text("Kelola dokumen keuangan bulanan Anda.", size=13, color=ft.Colors.GREY_600),
        ], expand=True)
    )
    header_row_controls.append(
        ft.OutlinedButton("Export PDF Cabang", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_cabang_pdf)
    )
    header_row_controls.append(
        ft.ElevatedButton("Buat folder bulan baru", icon=ft.Icons.ADD, on_click=open_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
    )

    body = ft.Column([
        ft.Row(header_row_controls),
        ft.Container(height=16),
        folder_cards if folders else ft.Text("Belum ada folder bulan. Buat folder baru untuk mulai.", color=ft.Colors.GREY_600),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return body
    # return ft.View(
    #     route=route,
    #     services=[export_picker],
    #     controls=[
             # build_appbar(page, "Daftar invoice"),
    #         ft.Row([
                 # nav_rail(page, 1),
    #             ft.VerticalDivider(width=1),
    #             ft.Container(content=body, padding=24, expand=True),
    #         ], expand=True),
    #     ],
    #     padding=0,
    # )
