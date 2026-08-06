import flet as ft
from state import app_state


def build_appbar(page, title):
    user = app_state.user
    nama = user.get("nama", "") if user else ""

    def do_logout(e):
        app_state.logout()
        page.go("/login")

    return ft.AppBar(
        title=ft.Text(title, weight=ft.FontWeight.W_500),
        center_title=False,
        bgcolor=ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
        actions=[
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=18),
                    ft.Text(nama, color=ft.Colors.WHITE, size=13),
                    ft.IconButton(ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, tooltip="Logout", on_click=do_logout),
                ], spacing=6),
                padding=ft.Padding.only(right=12),
            )
        ],
    )


def nav_rail(page, selected_index):
    is_admin = app_state.user and app_state.user.get("role") == "admin"

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

    return ft.NavigationRail(
        selected_index=selected_index,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=90,
        bgcolor=ft.Colors.GREY_50,
        destinations=destinations,
        on_change=lambda e: page.go(routes[e.control.selected_index]),
    )