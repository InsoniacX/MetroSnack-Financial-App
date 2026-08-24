import flet as ft
from state import app_state


def build_appbar(page, title):
    user = app_state.user
    nama = user.get("nama", "") if user else ""
    cabang_label = ""
    if user:
        cabang_label = " · Pusat" if user.get("cabang_id") is None else f" · {user.get('nama_cabang', '')}"

    is_dark = page.theme_mode == ft.ThemeMode.DARK

    def do_logout(e):
        app_state.logout()
        page.go("/login")

    return ft.AppBar(
        title=ft.Text(title, weight=ft.FontWeight.W_500),
        center_title=False,
        bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
        actions=[
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=18),
                    ft.Text(f"{nama}{cabang_label}", color=ft.Colors.WHITE, size=13),
                    ft.IconButton(ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, tooltip="Logout", on_click=do_logout),
                ], spacing=6),
                padding=ft.Padding.only(right=12),
            )
        ],
    )
    

def nav_rail(page, selected_index, appbar, refresh_current_view):
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    is_admin = app_state.user and app_state.user.get("role") == "admin"
    is_pusat = app_state.user and app_state.user.get("cabang_id") is None

    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            navrail.bgcolor = ft.Colors.BLACK
            theme_button.icon = ft.Icons.LIGHT_MODE_ROUNDED
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            navrail.bgcolor = ft.Colors.GREY_50
            theme_button.icon = ft.Icons.DARK_MODE_ROUNDED
        refresh_current_view()

    destinations = [
        ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_OUTLINED, selected_icon=ft.Icons.DASHBOARD, label="Dashboard"),
        ft.NavigationRailDestination(icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION, label="Invoice"),
    ]
    routes = ["/dashboard", "/invoices"]

    if is_admin:
        destinations.append(
            ft.NavigationRailDestination(icon=ft.Icons.PEOPLE_OUTLINE, selected_icon=ft.Icons.PEOPLE, label="User")
        )
        routes.append("/users")
        destinations.append(
            ft.NavigationRailDestination(icon=ft.Icons.HISTORY, selected_icon=ft.Icons.HISTORY, label="Log")
        )
        routes.append("/activity-log")

    if is_pusat:
        destinations.append(
            ft.NavigationRailDestination(icon=ft.Icons.STORE_OUTLINED, selected_icon=ft.Icons.STORE, label="Cabang")
        )
        routes.append("/cabang")

    theme_button = ft.IconButton(icon=(
        ft.Icons.LIGHT_MODE_ROUNDED
        if page.theme_mode == ft.ThemeMode.DARK
        else ft.Icons.DARK_MODE_ROUNDED
    ), tooltip="Darkmode", on_click=toggle_theme)
    
    navrail = ft.NavigationRail(
    selected_index=selected_index,
    label_type=ft.NavigationRailLabelType.ALL,
    min_width=90,
    bgcolor=ft.Colors.BLACK if is_dark else ft.Colors.GREY_50,
    destinations=destinations,
    trailing=theme_button,
    on_change=lambda e: page.go(routes[e.control.selected_index]),
    )
    return navrail
