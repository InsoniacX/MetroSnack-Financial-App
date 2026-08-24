import flet as ft
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
        elif r.startswith("/invoices/cabang/"):
            cabang_id = int(r.split("/")[3])
            page.views.append(invoices_view.build_folder_list(page, cabang_id, r, show_back=True))
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

