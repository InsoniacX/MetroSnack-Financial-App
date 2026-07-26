import flet as ft
from utils.format import format_rupiah

def stat_box(label: str, value: int) -> ft.Container:
    return ft.Container(
        bgcolor="white",
        border=ft.Border.all(1, "#E2E8F0"),
        border_radius=14,
        padding=16,
        expand=True,
        content=ft.Column(
            [
                ft.Text(label.upper(), size=10, color="#94A3B8"),
                ft.Text(format_rupiah(value), size=17, weight=ft.FontWeight.BOLD, color="black"),
            ],
            spacing=4,
        ),
    )