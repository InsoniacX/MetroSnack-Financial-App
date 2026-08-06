import flet as ft
from components.appbar import build_appbar, nav_rail
from components.metric_card import metric_card
from utils.formatting import rp
from db.folder_repo import get_dashboard_summary


def build_view(page: ft.Page):
    try:
        summary = get_dashboard_summary()
    except Exception:
        summary = {"omzet": 0, "barang": 0, "laba_bersih": 0}

    body = ft.Column([
        ft.Text("Selamat datang kembali", size=20, weight=ft.FontWeight.W_500),
        ft.Text("Ringkasan keuangan toko Anda secara keseluruhan.", size=13, color=ft.Colors.GREY_600),
        ft.Container(height=16),
        ft.Row([
            metric_card("Total omzet", rp(summary["omzet"])),
            metric_card("Total masuk barang", rp(summary["barang"])),
            metric_card("Laba bersih", rp(summary["laba_bersih"]), color=ft.Colors.GREEN_50, text_color=ft.Colors.GREEN_900),
        ], spacing=12),
        ft.Container(height=24),
        ft.ElevatedButton("Lihat daftar invoice", icon=ft.Icons.ARROW_FORWARD, on_click=lambda e: page.go("/invoices")),
    ], spacing=6, expand=True)

    return ft.View(
        route="/dashboard",
        controls=[
            build_appbar(page, "Dashboard"),
            ft.Row([
                nav_rail(page, 0),
                ft.VerticalDivider(width=1),
                ft.Container(content=body, padding=24, expand=True),
            ], expand=True),
        ],
        padding=0,
    )