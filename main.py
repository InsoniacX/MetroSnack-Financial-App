import flet as ft
from state import app_state
from config import APP_TITLE
from views import (
    login_view, dashboard_view, invoices_view, folder_detail_view,
    invoice_detail_view, users_view, activity_log_view, cabang_view,
)


def main(page: ft.Page):
    page.title = APP_TITLE
    page.window.width = 1100
    page.window.height = 750
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT

    def route_change(route):
        page.views.clear()
        r = page.route

        if not app_state.is_logged_in() and r != "/login":
            page.views.append(login_view.build_view(page))
            page.update()
            return

        if r in ("/login", "/"):
            page.views.append(login_view.build_view(page) if not app_state.is_logged_in() else dashboard_view.build_view(page))
        elif r == "/dashboard":
            page.views.append(dashboard_view.build_view(page))
        elif r == "/invoices":
            page.views.append(invoices_view.build_view(page))
        elif r.startswith("/invoices/"):
            folder_id = int(r.split("/")[2])
            page.views.append(folder_detail_view.build_view(page, folder_id))
        elif r.startswith("/invoice/"):
            invoice_id = int(r.split("/")[2])
            page.views.append(invoice_detail_view.build_view(page, invoice_id))
        elif r == "/users":
            page.views.append(users_view.build_view(page))
        elif r == "/activity-log":
            page.views.append(activity_log_view.build_view(page))
        elif r == "/cabang":
            page.views.append(cabang_view.build_view(page))
        else:
            page.views.append(login_view.build_view(page) if not app_state.is_logged_in() else dashboard_view.build_view(page))

        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route if page.route not in ("", "/") else "/login")


if __name__ == "__main__":
    ft.run(main)