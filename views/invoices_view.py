import flet as ft
from datetime import date
from config import MONTH
from components.appbar import build_appbar, nav_rail
from utils.formatting import rp
from utils.validation import parse_year
from db.folder_repo import get_folders, create_folder, get_cabang_summary
from db.cabang_repo import get_cabang_name
from db.activity_repo import log_activity
from state import app_state


def build_view(page: ft.Page):
    """Entry point untuk tab 'Invoice'. Admin Pusat -> pilih cabang dulu. Selain itu -> langsung daftar folder miliknya."""
    actor = app_state.user
    cabang_id = actor.get("cabang_id")
    is_pusat = cabang_id is None

    if is_pusat:
        return build_cabang_hub(page)
    return build_folder_list(page, cabang_id, "/invoices", show_back=False)


def build_cabang_hub(page: ft.Page):
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

    return ft.View(
        route="/invoices",
        controls=[
            build_appbar(page, "Daftar Invoice"),
            ft.Row([
                nav_rail(page, 1),
                ft.VerticalDivider(width=1),
                ft.Container(content=body, padding=24, expand=True),
            ], expand=True),
        ],
        padding=0,
    )


def build_folder_list(page: ft.Page, cabang_id: int, route: str, show_back: bool):
    """Daftar folder MILIK 1 CABANG SPESIFIK. Dipakai baik untuk user cabang (route /invoices)
    maupun Admin Pusat yang sudah memilih 1 cabang (route /invoices/cabang/{id})."""
    actor = app_state.user
    is_pusat = actor.get("cabang_id") is None

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
    if show_back:
        try:
            nama_cabang_label = get_cabang_name(cabang_id)
        except Exception:
            nama_cabang_label = None

    try:
        folders = get_folders(cabang_id)
    except Exception as ex:
        folders = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400))

    folder_cards = ft.ResponsiveRow(spacing=12, run_spacing=12)
    for f in folders:
        fid, nama_folder, bulan, tahun, _nama_cabang, total_invoice, laba_bersih = f
        folder_cards.controls.append(
            ft.Container(
                col={"xs": 12, "sm": 6, "md": 4},
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE_700), ft.Text(nama_folder, weight=ft.FontWeight.W_500, size=16)]),
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

    def submit_folder(e):
        if not bulan_dd.value:
            page.show_dialog(ft.SnackBar(ft.Text("Bulan wajib dipilih."), bgcolor=ft.Colors.RED_400))
            return
        try:
            bulan_int = int(bulan_dd.value)
            tahun_int = parse_year("Tahun", tahun_field.value)
            fid = create_folder(bulan_int, tahun_int, cabang_id, actor["id"])
            nama_folder = f"{MONTH[bulan_int]} {tahun_int}"
            log_activity(actor["id"], actor["username"], "CREATE", "folder_bulan", fid, f"Membuat folder {nama_folder}", cabang_id)
            page.pop_dialog()
            page.update()
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal buat folder: {ex}"), bgcolor=ft.Colors.RED_400))

    dlg = ft.AlertDialog(
        title=ft.Text("Buat folder bulan baru"),
        content=ft.Row([bulan_dd, tahun_field]),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_folder),
        ],
    )

    def open_dialog(e):
        page.show_dialog(dlg)

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
        ft.ElevatedButton("Buat folder bulan baru", icon=ft.Icons.ADD, on_click=open_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
    )

    body = ft.Column([
        ft.Row(header_row_controls),
        ft.Container(height=16),
        folder_cards if folders else ft.Text("Belum ada folder bulan. Buat folder baru untuk mulai.", color=ft.Colors.GREY_600),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route=route,
        controls=[
            build_appbar(page, "Daftar invoice"),
            ft.Row([
                nav_rail(page, 1),
                ft.VerticalDivider(width=1),
                ft.Container(content=body, padding=24, expand=True),
            ], expand=True),
        ],
        padding=0,
    )