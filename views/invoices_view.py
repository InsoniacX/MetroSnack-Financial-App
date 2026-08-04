import flet as ft
from datetime import date
from config import MONTH
from components.appbar import build_appbar, nav_rail
from utils.formatting import rp
from db.folder_repo import get_folders, create_folder
from state import app_state


def build_view(page: ft.Page):
    try:
        folders = get_folders()
    except Exception as ex:
        folders = []
        page.snack_bar = ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400)
        page.snack_bar.open = True

    folder_cards = ft.ResponsiveRow(spacing=12, run_spacing=12)
    for f in folders:
        fid, nama_folder, bulan, tahun, total_invoice, laba_bersih = f
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
                    ft.ElevatedButton("Buka folder", icon=ft.Icons.FOLDER_OPEN, on_click=lambda e, fid=fid, nm=nama_folder: page.go(f"/invoices/{fid}?nama={nm}")),
                ], spacing=4),
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(0.5, ft.Colors.GREY_300),
                border_radius=12,
                padding=16,
            )
        )

    bulan_dd = ft.Dropdown(label="Bulan", width=180,
                            options=[ft.dropdown.Option(str(i), MONTH[i]) for i in range(1, 13)])
    tahun_field = ft.TextField(label="Tahun", width=120, value=str(date.today().year))

    def submit_folder(e):
        if not bulan_dd.value or not tahun_field.value:
            return
        try:
            create_folder(int(bulan_dd.value), int(tahun_field.value), app_state.user["id"])
            dlg.open = False
            page.update()
            page.go("/invoices")
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Gagal buat folder: {ex}"), bgcolor=ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("Buat folder bulan baru"),
        content=ft.Row([bulan_dd, tahun_field]),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: (setattr(dlg, "open", False), page.update())),
            ft.ElevatedButton("Simpan", on_click=submit_folder),
        ],
    )

    def open_dialog(e):
        page.dialog = dlg
        dlg.open = True
        page.update()

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
        "/invoices",
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