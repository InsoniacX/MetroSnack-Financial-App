import flet as ft

from components.navigation import navigate
from state import app_state


MOBILE_BREAKPOINT = 960
MOBILE_SHORTEST_SIDE_BREAKPOINT = 600
_ZEBOR_CABANG_NAME = "Toko Zebor"


def is_mobile_layout(page):
    """Deteksi layout ringkas, termasuk ponsel yang diputar landscape."""
    width = getattr(page, "width", None)
    height = getattr(page, "height", None)

    if width is None:
        width = 1100
    if height is None:
        height = 750

    shortest_side = min(width, height)
    return (
        width <= MOBILE_BREAKPOINT
        or shortest_side < MOBILE_SHORTEST_SIDE_BREAKPOINT
    )


def can_access_operational_features(user=None):
    """Samakan akses fitur operasional dengan aturan backend."""
    if user is None:
        user = app_state.user or {}

    is_admin = user.get("role") == "admin"
    cabang_id = user.get("cabang_id")
    is_pusat_admin = is_admin and cabang_id is None

    nama_cabang = str(
        user.get("nama_cabang") or ""
    ).strip().casefold()

    is_zebor_user = (
        cabang_id is not None
        and nama_cabang == _ZEBOR_CABANG_NAME.casefold()
    )

    return is_pusat_admin or is_zebor_user


def _get_nav_items(user=None):
    if user is None:
        user = app_state.user or {}

    is_admin = user.get("role") == "admin"
    is_pusat = user.get("cabang_id") is None
    show_ops = can_access_operational_features(user)

    items = [
        (
            "/dashboard",
            "Dashboard",
            ft.Icons.DASHBOARD_OUTLINED,
            ft.Icons.DASHBOARD,
        ),
        (
            "/invoices",
            "Invoice",
            ft.Icons.DESCRIPTION_OUTLINED,
            ft.Icons.DESCRIPTION,
        ),
        (
            "/pendapatan-pengeluaran",
            "Kas",
            ft.Icons.SWAP_HORIZ_OUTLINED,
            ft.Icons.SWAP_HORIZ,
        ),
    ]

    if show_ops:
        items.extend(
            [
                (
                    "/supir-kenek",
                    "Supir/Kenek",
                    ft.Icons.LOCAL_SHIPPING_OUTLINED,
                    ft.Icons.LOCAL_SHIPPING,
                ),
                (
                    "/pengambilan-pabrik",
                    "Pabrik",
                    ft.Icons.FACTORY_OUTLINED,
                    ft.Icons.FACTORY,
                ),
                (
                    "/pengambilan-balaraja",
                    "Balaraja",
                    ft.Icons.WAREHOUSE_OUTLINED,
                    ft.Icons.WAREHOUSE,
                ),
                (
                    "/rekap-bulanan",
                    "Rekap",
                    ft.Icons.ASSESSMENT_OUTLINED,
                    ft.Icons.ASSESSMENT,
                ),
            ]
        )

    if is_admin:
        items.extend(
            [
                (
                    "/users",
                    "User",
                    ft.Icons.PEOPLE_OUTLINE,
                    ft.Icons.PEOPLE,
                ),
                (
                    "/activity-log",
                    "Log",
                    ft.Icons.HISTORY,
                    ft.Icons.HISTORY,
                ),
            ]
        )

    if is_admin and is_pusat:
        items.append(
            (
                "/cabang",
                "Cabang",
                ft.Icons.STORE_OUTLINED,
                ft.Icons.STORE,
            )
        )

    return items


def get_nav_config(user=None):
    items = _get_nav_items(user)

    destinations = [
        ft.NavigationRailDestination(
            icon=icon,
            selected_icon=selected_icon,
            label=label,
        )
        for _, label, icon, selected_icon in items
    ]

    routes = [route for route, _, _, _ in items]

    return destinations, routes


def build_appbar(
    page,
    title,
    refresh_current_view=None,
    mobile=False,
):
    user = app_state.user or {}

    nama = str(
        user.get("nama")
        or user.get("username")
        or "Pengguna"
    )

    cabang_label = (
        "Pusat"
        if user.get("cabang_id") is None
        else str(user.get("nama_cabang") or "Cabang")
    )

    is_dark = page.theme_mode == ft.ThemeMode.DARK

    def do_logout(e):
        app_state.logout()
        navigate(page, "/login")

    def toggle_theme(e):
        page.theme_mode = (
            ft.ThemeMode.DARK
            if page.theme_mode == ft.ThemeMode.LIGHT
            else ft.ThemeMode.LIGHT
        )

        if refresh_current_view:
            refresh_current_view()
        else:
            page.update()

    async def open_navigation(e):
        await page.show_drawer()

    theme_button = ft.IconButton(
        icon=(
            ft.Icons.LIGHT_MODE_ROUNDED
            if is_dark
            else ft.Icons.DARK_MODE_ROUNDED
        ),
        icon_color=ft.Colors.WHITE,
        tooltip="Mode Terang" if is_dark else "Mode Gelap",
        on_click=toggle_theme,
    )

    logout_button = ft.IconButton(
        icon=ft.Icons.LOGOUT,
        icon_color=ft.Colors.WHITE,
        tooltip="Logout",
        on_click=do_logout,
    )

    if mobile:
        actions = [
            theme_button,
            logout_button,
        ]

        leading = ft.IconButton(
            icon=ft.Icons.MENU,
            icon_color=ft.Colors.WHITE,
            tooltip="Buka navigasi",
            on_click=open_navigation,
        )

    else:
        actions = [
            ft.Container(
                content=ft.Row(
                    [
                        theme_button,
                        ft.VerticalDivider(
                            width=1,
                            color=ft.Colors.WHITE_24,
                        ),
                        ft.Icon(
                            ft.Icons.PERSON,
                            color=ft.Colors.WHITE,
                            size=18,
                        ),
                        ft.Text(
                            f"{nama} · {cabang_label}",
                            color=ft.Colors.WHITE,
                            size=13,
                        ),
                        logout_button,
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.only(right=12),
            )
        ]

        leading = None

    return ft.AppBar(
        leading=leading,
        leading_width=48 if mobile else None,
        automatically_imply_leading=False,
        title=ft.Text(
            title,
            weight=ft.FontWeight.W_500,
            size=18 if mobile else None,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
        title_spacing=0 if mobile else 16,
        center_title=False,
        bgcolor=(
            ft.Colors.GREY_900
            if is_dark
            else ft.Colors.BLUE_700
        ),
        color=ft.Colors.WHITE,
        actions=actions,
        actions_padding=ft.Padding.only(
            right=4 if mobile else 0
        ),
    )


def nav_rail(
    page,
    selected_index,
    refresh_current_view=None,
):
    del refresh_current_view

    is_dark = page.theme_mode == ft.ThemeMode.DARK
    destinations, routes = get_nav_config()

    safe_index = (
        selected_index
        if 0 <= selected_index < len(destinations)
        else 0
    )

    navigation_rail = ft.NavigationRail(
        selected_index=safe_index,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=90,
        bgcolor=(
            ft.Colors.BLACK
            if is_dark
            else ft.Colors.GREY_50
        ),
        destinations=destinations,
        on_change=lambda e: navigate(
            page,
            routes[e.control.selected_index]
        ),
        height=max(
            550,
            len(destinations) * 62 + 20,
        ),
    )

    return ft.Container(
        content=ft.Column(
            [navigation_rail],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        ),
        width=90,
        bgcolor=(
            ft.Colors.BLACK
            if is_dark
            else ft.Colors.GREY_50
        ),
    )


def build_navigation_drawer(page, selected_index):
    user = app_state.user or {}

    items = _get_nav_items(user)
    routes = [route for route, _, _, _ in items]

    safe_index = (
        selected_index
        if 0 <= selected_index < len(items)
        else 0
    )

    is_dark = page.theme_mode == ft.ThemeMode.DARK

    def navigate(e):
        index = e.control.selected_index

        if 0 <= index < len(routes):
            navigate(page, routes[index])

    cabang_label = (
        "Pusat"
        if user.get("cabang_id") is None
        else str(user.get("nama_cabang") or "Cabang")
    )

    nama = str(
        user.get("nama")
        or user.get("username")
        or "Pengguna"
    )

    drawer_destinations = [
        ft.NavigationDrawerDestination(
            label=label,
            icon=icon,
            selected_icon=selected_icon,
        )
        for _, label, icon, selected_icon in items
    ]

    return ft.NavigationDrawer(
        selected_index=safe_index,
        width=280,
        bgcolor=(
            ft.Colors.GREY_900
            if is_dark
            else ft.Colors.WHITE
        ),
        on_change=navigate,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "MetroSnack",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            nama,
                            size=14,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            cabang_label,
                            size=12,
                            color=ft.Colors.GREY_500,
                        ),
                    ],
                    spacing=2,
                ),
                padding=ft.Padding.only(
                    left=28,
                    right=16,
                    top=24,
                    bottom=16,
                ),
            ),
            ft.Divider(height=1),
            *drawer_destinations,
        ],
    )
