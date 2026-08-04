import flet as ft

def metric_card(label, value, color=ft.Colors.BLUE_50, text_color=ft.Colors.BLUE_900):
    return ft.Container(
        content=ft.Column([
            ft.Text(label, size=12, color=ft.Colors.GREY_700),
            ft.Text(value, size=20, weight=ft.FontWeight.W_500, color=text_color),
        ], spacing=4),
        bgcolor=color,
        padding=16,
        border_radius=8,
        expand=True,
    )