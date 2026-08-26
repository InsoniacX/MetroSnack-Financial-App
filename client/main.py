import flet as ft
from components.appbar import build_appbar, nav_rail
from state import app_state
from config import APP_TITLE
from db.folder_repo import get_invoice_ids
from views import (
    folder_cabang_view, login_view, dashboard_view, invoices_view, folder_detail_view,
    invoice_detail_view, users_view, activity_log_view, cabang_view,
)



def _loading_view(route):
    """Halaman transisi singkat, ditampilkan saat menunggu API sebelum
    redirect folder -> invoice (supaya tidak terasa seperti macet/nge-freeze)."""
    return ft.View(
        route=route,
        controls=[
            ft.Container(
                content=ft.Column(
                    [ft.ProgressRing(width=32, height=32), ft.Container(height=12), ft.Text("Memuat...", size=13, color=ft.Colors.GREY_600)],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )


def main(page: ft.Page):
    page.title = APP_TITLE
    page.window.width = 1100
    page.window.height = 750
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.icon = "METROSNACK_bgremoved.png"
    

    def refresh_current_view():
        route_change(page.route)

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
        appbar = build_appbar(page, title)

        navrail = nav_rail(
            page,
            get_selected_index(route),
            appbar,
            refresh_current_view,
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
            # invoice sama sekali. Tampilkan loading dulu supaya user
            # tidak lihat layar kosong/macet selagi request jalan.
            page.views.append(_loading_view(r))
            page.update()
            try:
                invoice_ids = get_invoice_ids(folder_id)
            except Exception:
                invoice_ids = []
            if len(invoice_ids) == 1:
                page.views.pop()
                page.go(f"/invoice/{invoice_ids[0]}")
                return
            page.views.pop()
            page.views.append(folder_detail_view.build_view(page, folder_id))
        elif r.startswith("/invoice/"):
            invoice_id = int(r.split("/")[2])
            body = invoice_detail_view.build_view(page, invoice_id)
            page.views.append(create_view(r, "Detail Invoice", body))
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
    ft.run(main, assets_dir="assets")

