import flet as ft
from utils.format import format_rupiah

SLATE_400 = "#94A3B8"
SLATE_900 = "#0F172A"


def stat_card(icon: str, label: str, value: int, caption: str = "") -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(icon, size=18, color=SLATE_400),
                    bgcolor="#F1F5F9",
                    border_radius=10,
                    padding=8,
                ),
                ft.Container(height=12),
                ft.Text(label.upper(), size=11, weight=ft.FontWeight.W_500, color=SLATE_400),
                ft.Text(format_rupiah(value), size=22, weight=ft.FontWeight.BOLD, color=SLATE_900),
                ft.Text(caption, size=11, color=SLATE_400) if caption else ft.Container(),
            ],
            spacing=2,
        ),
        bgcolor="#FFFFFF",
        border_radius=16,
        border=ft.Border.all(1, "#E2E8F0"),
        padding=18,
        expand=True,
    )