import flet as ft
from database.db import initialize_database
from components.sidebar import build_sidebar
from views.dashboard_view import build_dashboard_view
from views.login_view import build_login_view
from views.invoice_list_view import build_invoice_list_view


def main(page: ft.Page):
    page.title = "MetroSnack"
    page.bgcolor = "#F8FAFC"
    page.padding = 0
    page.window.width = 1280
    page.window.height = 820
    page.window.min_width = 1000
    page.window.min_height = 650

    root_container = ft.Container(expand=True)
    page.add(root_container)

    def show_app(current_user: dict):
        content_area = ft.Container(content=build_dashboard_view(), expand=True)

        def navigate(route: str):
            if route == "/":
                content_area.content = build_dashboard_view()
            elif route == "/invoices":
                content_area.content = build_invoice_list_view(page, on_open_folder=lambda y, m: print(f"Buka folder {m}/{y}"))
            else:
                content_area.content = ft.Container(
                    content=ft.Text(f"Halaman '{route}' belum dibuat.", size=16, color="#94A3B8"),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                )
            page.update()

        root_container.content = ft.Row(
            [
                build_sidebar(on_navigate=navigate),
                content_area,
            ],
            expand=True,
            spacing=0,
        )
        page.update()

    def show_login():
        root_container.content = build_login_view(page, on_login_success=show_app)
        page.update()

    show_login()


if __name__ == "__main__":
    initialize_database()
    ft.run(main)