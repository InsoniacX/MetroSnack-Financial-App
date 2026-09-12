import flet as ft

from components.appbar import (
    build_appbar,
    build_navigation_drawer,
    can_access_operational_features,
    get_nav_config,
    is_mobile_layout,
    nav_rail,
)
from components.skeleton import build_page_skeleton
from components.navigation import navigate
from config import APP_TITLE
from db.folder_repo import get_invoice_ids
from db.http_client import ApiError
from state import app_state
from views import (
    activity_log_view,
    cabang_view,
    dashboard_view,
    folder_detail_view,
    invoice_detail_view,
    invoices_view,
    login_view,
    kas_navigation_view,
    pengambilan_balaraja_view,
    pengambilan_pabrik_view,
    rekap_bulanan_view,
    supir_kenek_view,
    users_view,
)


def _parse_positive_route_id(route, prefix):
    """Ambil satu ID positif dari route tanpa menerima segmen tambahan."""
    if not route.startswith(prefix):
        return None

    value = route[len(prefix):]
    if not value.isdigit():
        return None

    parsed = int(value)
    return parsed if parsed > 0 else None


def _get_route_title(route):
    if route == "/dashboard":
        return "Dashboard"
    if route == "/invoices" or route.startswith("/invoices/cabang/"):
        return "Daftar Invoice"
    if route.startswith("/invoices/"):
        return "Detail Folder"
    if route.startswith("/invoice/"):
        return "Detail Invoice"
    if route.startswith("/pendapatan-pengeluaran"):
        return "Pendapatan & Pengeluaran"
    if route.startswith("/supir-kenek"):
        return "Operasional Supir & Kenek"
    if route.startswith("/pengambilan-pabrik"):
        return "Pengambilan Pabrik"
    if route.startswith("/pengambilan-balaraja"):
        return "Pengambilan Balaraja"
    if route.startswith("/rekap-bulanan"):
        return "Rekap Bulanan Gabungan"
    if route == "/users":
        return "Kelola User"
    if route == "/activity-log":
        return "Log Aktivitas"
    if route == "/cabang":
        return "Kelola Cabang"
    return None


async def main(page: ft.Page):
    page.title = APP_TITLE

    if page.platform.is_mobile():
        await page.set_allowed_device_orientations(
            [
                ft.DeviceOrientation.LANDSCAPE_LEFT,
                ft.DeviceOrientation.LANDSCAPE_RIGHT,
            ]
        )

    page.window.width = 1100
    page.window.height = 750
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.icon = "METROSNACK_bgremoved.png"

    layout_state = {
        "mobile": is_mobile_layout(page)
    }

    def refresh_current_view():
        route_change(page.route)

    def get_selected_index(route):
        _, routes = get_nav_config()

        if route.startswith("/dashboard"):
            target = "/dashboard"
        elif (
            route.startswith("/invoices")
            or route.startswith("/invoice")
        ):
            target = "/invoices"
        elif route.startswith(
            "/pendapatan-pengeluaran"
        ):
            target = "/pendapatan-pengeluaran"
        elif route.startswith("/supir-kenek"):
            target = "/supir-kenek"
        elif route.startswith("/pengambilan-pabrik"):
            target = "/pengambilan-pabrik"
        elif route.startswith("/pengambilan-balaraja"):
            target = "/pengambilan-balaraja"
        elif route.startswith("/rekap-bulanan"):
            target = "/rekap-bulanan"
        elif route == "/users":
            target = "/users"
        elif route == "/activity-log":
            target = "/activity-log"
        elif route == "/cabang":
            target = "/cabang"
        else:
            return 0

        return (
            routes.index(target)
            if target in routes
            else 0
        )

    def create_view(route, title, body):
        mobile = is_mobile_layout(page)
        selected_index = get_selected_index(route)

        appbar = build_appbar(
            page,
            title,
            refresh_current_view,
            mobile=mobile,
        )

        body_container = ft.Container(
            content=body,
            padding=12 if mobile else 24,
            expand=True,
        )

        if mobile:
            controls = [body_container]

            drawer = build_navigation_drawer(
                page,
                selected_index,
            )

        else:
            controls = [
                ft.Row(
                    [
                        nav_rail(
                            page,
                            selected_index,
                            refresh_current_view,
                        ),
                        ft.VerticalDivider(width=1),
                        body_container,
                    ],
                    expand=True,
                    spacing=0,
                )
            ]

            drawer = None

        return ft.View(
            route=route,
            appbar=appbar,
            drawer=drawer,
            padding=0,
            controls=controls,
        )

    def build_route_error(
        title,
        message,
        back_route="/invoices",
    ):
        return ft.Column(
            [
                ft.Icon(
                    ft.Icons.CLOUD_OFF_OUTLINED,
                    size=40,
                    color=ft.Colors.RED_400,
                ),
                ft.Text(
                    title,
                    size=20,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    message,
                    size=13,
                    color=ft.Colors.GREY_600,
                ),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Kembali",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: navigate(
                                page,
                                back_route
                            ),
                        ),
                        ft.ElevatedButton(
                            "Coba Lagi",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda e: route_change(
                                page.route
                            ),
                        ),
                    ],
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                ),
            ],
            spacing=10,
        )

    def redirect_for_api_error(error):
        if error.status_code == 401:
            app_state.logout(session_expired=True)
            navigate(page, "/login")
            return True

        if error.status_code in (403, 404):
            navigate(page, "/invoices")
            return True

        return False

    def route_change(route):
        del route

        current_route = page.route

        if not app_state.is_logged_in():
            if current_route != "/login":
                navigate(page, "/login")
                return

            page.views.clear()
            page.views.append(
                login_view.build_view(page)
            )
            page.update()
            return

        if current_route == "/login":
            navigate(page, "/dashboard")
            return

        actor = app_state.user or {}

        is_admin = actor.get("role") == "admin"
        is_pusat = actor.get("cabang_id") is None
        show_ops = can_access_operational_features(
            actor
        )

        if (
            current_route.startswith(
                (
                    "/supir-kenek",
                    "/pengambilan-pabrik",
                    "/pengambilan-balaraja",
                    "/rekap-bulanan",
                )
            )
            and not show_ops
        ):
            navigate(page, "/dashboard")
            return

        if (
            current_route
            in ("/users", "/activity-log")
            and not is_admin
        ):
            navigate(page, "/dashboard")
            return

        if (
            current_route == "/cabang"
            and not (is_admin and is_pusat)
        ):
            navigate(page, "/dashboard")
            return

        if (
            current_route.startswith(
                "/invoices/cabang/"
            )
            and not is_pusat
        ):
            navigate(page, "/invoices")
            return

        if current_route == "/":
            navigate(page, "/dashboard")
            return

        loading_title = _get_route_title(current_route)
        if loading_title:
            page.views.clear()
            page.views.append(
                create_view(
                    current_route,
                    loading_title,
                    build_page_skeleton(page, current_route),
                )
            )
            page.update()

        if current_route == "/dashboard":
            body = dashboard_view.build_view(page)

            view = create_view(
                "/dashboard",
                "Dashboard",
                body,
            )

        elif current_route == "/invoices":
            body = invoices_view.build_view(page)

            view = create_view(
                "/invoices",
                "Daftar Invoice",
                body,
            )

        elif current_route.startswith(
            "/invoices/cabang/"
        ):
            cabang_id = _parse_positive_route_id(
                current_route,
                "/invoices/cabang/",
            )

            if cabang_id is None:
                navigate(page, "/invoices")
                return

            body = invoices_view.build_folder_list(
                page,
                cabang_id,
                current_route,
                show_back=True,
            )

            view = create_view(
                current_route,
                "Daftar Invoice",
                body,
            )

        elif current_route.startswith("/invoices/"):
            folder_id = _parse_positive_route_id(
                current_route,
                "/invoices/",
            )

            if folder_id is None:
                navigate(page, "/invoices")
                return

            invoice_ids = None
            load_error = None

            try:
                invoice_ids = get_invoice_ids(
                    folder_id
                )
            except Exception as ex:
                load_error = ex

            if isinstance(load_error, ApiError):
                if redirect_for_api_error(load_error):
                    return

            if load_error is not None:
                body = build_route_error(
                    "Folder gagal dimuat",
                    (
                        "Aplikasi tidak dapat mengambil data invoice. "
                        f"Periksa koneksi backend lalu coba lagi. Detail: {load_error}"
                    ),
                )

                view = create_view(
                    current_route,
                    "Detail Folder",
                    body,
                )

            elif len(invoice_ids) == 1:
                navigate(
                    page,
                    f"/invoice/{invoice_ids[0]}"
                )
                return

            else:
                body = folder_detail_view.build_view(
                    page,
                    folder_id,
                )

                view = create_view(
                    current_route,
                    "Detail Folder",
                    body,
                )

        elif current_route.startswith("/invoice/"):
            invoice_id = _parse_positive_route_id(
                current_route,
                "/invoice/",
            )

            if invoice_id is None:
                navigate(page, "/invoices")
                return

            try:
                body = invoice_detail_view.build_view(
                    page,
                    invoice_id,
                )
            except ApiError as ex:
                if redirect_for_api_error(ex):
                    return

                body = build_route_error(
                    "Invoice gagal dimuat",
                    (
                        "Aplikasi tidak dapat mengambil detail invoice. "
                        f"Periksa koneksi backend lalu coba lagi. Detail: {ex}"
                    ),
                )
            except Exception as ex:
                body = build_route_error(
                    "Invoice gagal dimuat",
                    (
                        "Aplikasi tidak dapat mengambil detail invoice. "
                        f"Periksa koneksi backend lalu coba lagi. Detail: {ex}"
                    ),
                )

            view = create_view(
                current_route,
                "Detail Invoice",
                body,
            )

        elif current_route.startswith(
            "/pendapatan-pengeluaran"
        ):
            body = (
                kas_navigation_view.build_view(
                    page
                )
            )

            view = create_view(
                current_route,
                "Pendapatan & Pengeluaran",
                body,
            )

        elif current_route.startswith(
            "/supir-kenek"
        ):
            body = supir_kenek_view.build_view(page)

            view = create_view(
                current_route,
                "Operasional Supir & Kenek",
                body,
            )

        elif current_route.startswith(
            "/pengambilan-pabrik"
        ):
            body = (
                pengambilan_pabrik_view.build_view(
                    page
                )
            )

            view = create_view(
                current_route,
                "Pengambilan Pabrik",
                body,
            )

        elif current_route.startswith(
            "/pengambilan-balaraja"
        ):
            body = (
                pengambilan_balaraja_view.build_view(
                    page
                )
            )

            view = create_view(
                current_route,
                "Pengambilan Balaraja",
                body,
            )

        elif current_route.startswith(
            "/rekap-bulanan"
        ):
            body = rekap_bulanan_view.build_view(page)

            view = create_view(
                current_route,
                "Rekap Bulanan Gabungan",
                body,
            )

        elif current_route == "/users":
            body = users_view.build_view(page)

            view = create_view(
                "/users",
                "Kelola User",
                body,
            )

        elif current_route == "/activity-log":
            body = activity_log_view.build_view(page)

            view = create_view(
                "/activity-log",
                "Log Aktivitas",
                body,
            )

        elif current_route == "/cabang":
            body = cabang_view.build_view(page)

            view = create_view(
                "/cabang",
                "Kelola Cabang",
                body,
            )

        else:
            navigate(page, "/dashboard")
            return

        if not app_state.is_logged_in():
            navigate(page, "/login")
            return

        page.views.clear()
        page.views.append(view)
        page.update()

    def handle_resize(e):
        del e

        mobile = is_mobile_layout(page)

        if mobile == layout_state["mobile"]:
            return

        layout_state["mobile"] = mobile
        route_change(page.route)

    def view_pop(view):
        del view

        if len(page.views) <= 1:
            return

        page.views.pop()
        navigate(page, page.views[-1].route)

    page.on_route_change = route_change
    page.on_resize = handle_resize
    page.on_view_pop = view_pop

    route_change(page.route)


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir="assets",
    )
