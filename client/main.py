import flet as ft
from components.appbar import build_appbar, nav_rail
from state import app_state
from config import APP_TITLE
from db.invoice_repo import get_invoices
from views import (
    folder_cabang_view, login_view, dashboard_view, invoices_view, folder_detail_view,
    invoice_detail_view, users_view, activity_log_view, cabang_view,
)

def main(page: ft.Page):
    page.title = APP_TITLE
    page.window.width = 1100
    page.window.height = 750
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    appbar = build_appbar(page, "")

    def get_selected_index(route):
        if route.startswith("/dashboard"):
            return 0
        elif route.startswith("/invoices") or route.startswith("/invoice"):
            return 1
        elif route == "/users":
            return 2
        elif route == "/activity-log":
            return 3
        elif route == "/cabang":
            return 4
        return 0

    def create_view(route, title, body):
        appbar.title = ft.Text(title)

        navrail = nav_rail(
            page,
            get_selected_index(route),
            appbar
        )

        return ft.View(
            route=route,
            appbar=appbar,
            padding=0,
            controls=[
                ft.Row(
                    [
                        navrail,
                        ft.VerticalDivider(width=1),
                        ft.Container(
                            content=body,
                            padding=24,
                            expand=True,
                        ),
                    ],
                    expand=True,
                )
            ],
        )

    def route_change(route):
        page.views.clear()
        r = page.route

        if not app_state.is_logged_in() and r != "/login":
            page.views.append(login_view.build_view(page))
            page.update()
            return

        if r == "/login":
            page.views.append(login_view.build_view(page))
            page.update()
            return

        if r == "/":
            page.go("/dashboard")
            return

        elif r == "/dashboard":
            body = dashboard_view.build_view(page)
            page.views.append(create_view("/dashboard", "Dashboard", body))
        elif r == "/invoices":
            body = invoices_view.build_view(page)
            page.views.append(create_view("/invoices", "Daftar Invoice", body))
        elif r.startswith("/invoices/cabang/"):
            cabang_id = int(r.split("/")[3])
            body = invoices_view.build_folder_list(page, cabang_id, r, show_back=True)
            page.views.append(create_view(r, "Daftar Invoice", body))
        elif r.startswith("/invoices/"):
            folder_id = int(r.split("/")[2])
            # 1 folder = 1 invoice (kebijakan baru): kalau folder ini
            # sudah punya PERSIS 1 invoice, langsung lompat ke halaman
            # transaksi harian invoice itu -- lewati halaman daftar
            # invoice sama sekali. folder_detail_view.py (daftar invoice)
            # cuma dipakai sebagai fallback untuk 2 kasus khusus:
            #   - folder belum punya invoice sama sekali (harusnya jarang,
            #     misal auto-create invoice gagal saat folder dibuat)
            #   - folder lama yang kebetulan masih punya >1 invoice
            #     (data sebelum kebijakan ini berlaku)
            try:
                invoices = get_invoices(folder_id)
            except Exception:
                invoices = []
            if len(invoices) == 1:
                page.go(f"/invoice/{invoices[0][0]}")
                appbar.title = ft.Text("Detail Invoice")
                view = folder_detail_view.build_view(page, folder_id)
                view.appbar = appbar
                page.views.append(view)
        elif r.startswith("/invoice/"):
            invoice_id = int(r.split("/")[2])
            appbar.title = ft.Text("Detail Invoice")
            view = invoice_detail_view.build_view(page, invoice_id)
            view.appbar = appbar
            page.views.append(view)
        elif r == "/users":
            body = users_view.build_view(page)
            page.views.append(create_view("/users", "Kelola User", body))
        elif r == "/activity-log":
            body = activity_log_view.build_view(page)
            page.views.append(create_view("/activity-log", "Log Aktivitas", body))
        elif r == "/cabang":
            body = cabang_view.build_view(page)
            page.views.append(create_view("/cabang", "Kelola Cabang", body))
        else:
            body = login_view.build_view(page) if not app_state.is_logged_in() else dashboard_view.build_view(page)
            page.views.append(create_view(page.route, "Dashboard", body))
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
