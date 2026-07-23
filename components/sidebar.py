import flet as ft

PRIMARY = "#2563EB"
SLATE_500 = "#64748B"


def build_sidebar(on_navigate) -> ft.Container:
    def nav_button(icon: str, label: str, route: str):
        return ft.TextButton(
            content=ft.Row(
                [
                    ft.Icon(icon, size=18, color=SLATE_500),
                    ft.Text(label, size=14, color=SLATE_500, weight=ft.FontWeight.W_500),
                ],
                spacing=12,
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            ),
            on_click=lambda e: on_navigate(route),
        )

    return ft.Container(
        width=250,
        bgcolor="#FFFFFF",
        border=ft.Border(right=ft.BorderSide(1, "#E2E8F0")),
        padding=ft.Padding.symmetric(vertical=20, horizontal=12),
        content=ft.Column(
            [
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=8, vertical=10),
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.SHOW_CHART, color="white", size=18),
                                bgcolor=PRIMARY,
                                border_radius=10,
                                padding=8,
                            ),
                            ft.Column(
                                [
                                    ft.Text("MetroSnack", size=14, weight=ft.FontWeight.BOLD, color="black"),
                                    ft.Text("MANAGEMENT", size=10, color="#94A3B8"),
                                ],
                                spacing=0,
                            ),
                        ],
                        spacing=10,
                    ),
                ),
                ft.Container(height=10),
                nav_button(ft.Icons.GRID_VIEW, "Dashboard", "/"),
                nav_button(ft.Icons.DESCRIPTION_OUTLINED, "Invoices", "/invoices"),
                ft.Container(expand=True),
                ft.Divider(color="#F1F5F9"),
                nav_button(ft.Icons.SETTINGS_OUTLINED, "Settings", "/settings"),
                nav_button(ft.Icons.HELP_OUTLINE, "Help & Support", "/help"),
                ft.TextButton(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.LOGOUT, size=18, color="#EF4444"),
                            ft.Text("Logout", size=14, color="#EF4444", weight=ft.FontWeight.W_500),
                        ],
                        spacing=12,
                    ),
                    style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=12, vertical=10)),
                ),
            ],
            expand=True,
        ),
    )