import flet as ft
from components.appbar import build_appbar
from state import app_state

def build_view(page: ft.Page, id):
    cabang_id = id
    actor = app_state.user

    if not actor and actor.get("role") != "admin":
        return ft.View(
            route=f"/cabang/{id}",
            controls=[
                build_appbar(page, "Akses Ditolak"),
                ft.Container(
                    content = ft.Text("Halaman ini hanya bisa diakses oleh Admin dan Staff Pusat.", size=13),
                    padding=24,
                )
            ]
        )
