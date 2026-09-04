import flet as ft
from state import app_state


def build_appbar(page, title, refresh_current_view=None):
    user = app_state.user
    nama = user.get("nama", "") if user else ""
    cabang_label = ""
    if user:
        cabang_label = " · Pusat" if user.get("cabang_id") is None else f" · {user.get('nama_cabang', '')}"

    is_dark = page.theme_mode == ft.ThemeMode.DARK

    def do_logout(e):
        app_state.logout()
        page.go("/login")

    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
        if refresh_current_view:
            refresh_current_view()
        else:
            page.update()

    theme_button = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE_ROUNDED if is_dark else ft.Icons.DARK_MODE_ROUNDED,
        icon_color=ft.Colors.WHITE,
        tooltip="Mode Terang" if is_dark else "Mode Gelap",
        on_click=toggle_theme,
    )

    return ft.AppBar(
        title=ft.Text(title, weight=ft.FontWeight.W_500),
        center_title=False,
        bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
        actions=[
            ft.Container(
                content=ft.Row([
                    theme_button,
                    ft.VerticalDivider(width=1, color=ft.Colors.WHITE24),
                    ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=18),
                    ft.Text(f"{nama}{cabang_label}", color=ft.Colors.WHITE, size=13),
                    ft.IconButton(ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, tooltip="Logout", on_click=do_logout),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding.only(right=12),
            )
        ],
    )


def get_nav_config(user=None):
    if user is None:
        user = app_state.user or {}
    is_admin = user.get("role") == "admin"
    is_pusat = user.get("cabang_id") is None
    nama_cabang = str(user.get("nama_cabang") or "").strip().lower()
    is_zebor = "zebor" in nama_cabang

    show_ops = is_admin or is_zebor

    destinations = [
        ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_OUTLINED, selected_icon=ft.Icons.DASHBOARD, label="Dashboard"),
        ft.NavigationRailDestination(icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION, label="Invoice"),
        ft.NavigationRailDestination(icon=ft.Icons.SWAP_HORIZ_OUTLINED, selected_icon=ft.Icons.SWAP_HORIZ, label="Kas"),
    ]
    routes = [
        "/dashboard",
        "/invoices",
        "/pendapatan-pengeluaran",
    ]

    if show_ops:
        destinations.extend([
            ft.NavigationRailDestination(icon=ft.Icons.LOCAL_SHIPPING_OUTLINED, selected_icon=ft.Icons.LOCAL_SHIPPING, label="Supir/Kenek"),
            ft.NavigationRailDestination(icon=ft.Icons.FACTORY_OUTLINED, selected_icon=ft.Icons.FACTORY, label="Pabrik"),
            ft.NavigationRailDestination(icon=ft.Icons.WAREHOUSE_OUTLINED, selected_icon=ft.Icons.WAREHOUSE, label="Balaraja"),
        ])
        routes.extend([
            "/supir-kenek",
            "/pengambilan-pabrik",
            "/pengambilan-balaraja",
        ])

    destinations.append(
        ft.NavigationRailDestination(icon=ft.Icons.ASSESSMENT_OUTLINED, selected_icon=ft.Icons.ASSESSMENT, label="Rekap")
    )
    routes.append("/rekap-bulanan")

    if is_admin:
        destinations.append(
            ft.NavigationRailDestination(icon=ft.Icons.PEOPLE_OUTLINE, selected_icon=ft.Icons.PEOPLE, label="User")
        )
        routes.append("/users")
        destinations.append(
            ft.NavigationRailDestination(icon=ft.Icons.HISTORY, selected_icon=ft.Icons.HISTORY, label="Log")
        )
        routes.append("/activity-log")

    if is_admin and is_pusat:
        destinations.append(
            ft.NavigationRailDestination(icon=ft.Icons.STORE_OUTLINED, selected_icon=ft.Icons.STORE, label="Cabang")
        )
        routes.append("/cabang")

    return destinations, routes


def nav_rail(page, selected_index, refresh_current_view=None):
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    destinations, routes = get_nav_config()

    rail_height = max(550, len(destinations) * 62 + 20)
    navrail = ft.NavigationRail(
        selected_index=selected_index if 0 <= selected_index < len(destinations) else 0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=90,
        bgcolor=ft.Colors.BLACK if is_dark else ft.Colors.GREY_50,
        destinations=destinations,
        on_change=lambda e: page.go(routes[e.control.selected_index]),
        height=rail_height,
    )

    return ft.Container(
        content=ft.Column(
            [navrail],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        ),
        width=90,
        bgcolor=ft.Colors.BLACK if is_dark else ft.Colors.GREY_50,
    )


