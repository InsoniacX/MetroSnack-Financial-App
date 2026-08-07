import flet as ft
from datetime import date
from config import MONTH
from components.appbar import build_appbar, nav_rail
from utils.formatting import rp
from utils.validation import parse_year
from db.folder_repo import get_folders, create_folder
from db.cabang_repo import get_active_cabang
from db.activity_repo import log_activity
from state import app_state


def build_view(page: ft.Page):
    def refresh():
        page.views[-1] = build_view(page)
        page.update()

    actor = app_state.user
    cabang_id = actor.get("cabang_id")
    is_pusat = cabang_id is None

    try:
        folders = get_folders(cabang_id)
    except Exception as ex:
        folders = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400))

    folder_cards = ft.ResponsiveRow(spacing=12, run_spacing=12)
    for f in folders:
        fid, nama_folder, bulan, tahun, nama_cabang, total_invoice, laba_bersih = f
        header_row = [ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE_700), ft.Text(nama_folder, weight=ft.FontWeight.W_500, size=16)]
        if is_pusat:
            header_row.append(ft.Container(
                content=ft.Text(nama_cabang, size=11, color=ft.Colors.BLUE_900),
                bgcolor=ft.Colors.BLUE_50, padding=ft.Padding.symmetric(vertical=2, horizontal=8), border_radius=6,
            ))
        folder_cards.controls.append(
            ft.Container(
                col={"xs": 12, "sm": 6, "md": 4},
                content=ft.Column([
                    ft.Row(header_row, spacing=8),
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

    bulan_dd = ft.Dropdown(label="Bulan", width=180, options=[ft.dropdown.Option(str(i), MONTH[i]) for i in range(1, 13)])
    tahun_field = ft.TextField(label="Tahun", width=120, value=str(date.today().year))

    cabang_dd = None
    dialog_fields = [bulan_dd, tahun_field]
    if is_pusat:
        try:
            daftar_cabang = get_active_cabang()
        except Exception:
            daftar_cabang = []
        cabang_dd = ft.Dropdown(label="Cabang", width=200, options=[ft.dropdown.Option(str(cid), nm) for cid, nm in daftar_cabang])
        dialog_fields.append(cabang_dd)

    def submit_folder(e):
        if not bulan_dd.value:
            page.show_dialog(ft.SnackBar(ft.Text("Bulan wajib dipilih."), bgcolor=ft.Colors.RED_400))
            return
        if is_pusat and not cabang_dd.value:
            page.show_dialog(ft.SnackBar(ft.Text("Cabang wajib dipilih."), bgcolor=ft.Colors.RED_400))
            return
        try:
            bulan_int = int(bulan_dd.value)
            tahun_int = parse_year("Tahun", tahun_field.value)
            target_cabang_id = int(cabang_dd.value) if is_pusat else cabang_id
            fid = create_folder(bulan_int, tahun_int, target_cabang_id, actor["id"])
            nama_folder = f"{MONTH[bulan_int]} {tahun_int}"
            log_activity(actor["id"], actor["username"], "CREATE", "folder_bulan", fid, f"Membuat folder {nama_folder}", target_cabang_id)
            page.pop_dialog()
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal buat folder: {ex}"), bgcolor=ft.Colors.RED_400))

    dlg = ft.AlertDialog(
        title=ft.Text("Buat folder bulan baru"),
        content=ft.Row(dialog_fields),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_folder),
        ],
    )

    def open_dialog(e):
        page.show_dialog(dlg)

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Daftar invoice", size=20, weight=ft.FontWeight.W_500),
                ft.Text("Kelola dokumen keuangan bulanan Anda.", size=13, color=ft.Colors.GREY_600),
            ], expand=True),
            ft.ElevatedButton("Buat folder bulan baru", icon=ft.Icons.ADD, on_click=open_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]),
        ft.Container(height=16),
        folder_cards if folders else ft.Text("Belum ada folder bulan. Buat folder baru untuk mulai.", color=ft.Colors.GREY_600),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route="/invoices",
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