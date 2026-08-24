import flet as ft

def metric_card(page, label, value, light_color=ft.Colors.BLUE_50, light_text_color=ft.Colors.BLUE_900, dark_color=ft.Colors.BLUE_900, dark_text_color=ft.Colors.BLUE_100):
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    return ft.Container(
        content=ft.Column([
            ft.Text(label, size=12, color=ft.Colors.GREY_300 if is_dark else ft.Colors.GREY_700),
            ft.Text(value, size=20, weight=ft.FontWeight.W_500, color=dark_text_color if is_dark else light_text_color),
        ], spacing=4),
        bgcolor=dark_color if is_dark else light_color,
        padding=16,
        border_radius=8,
        expand=True,
    )