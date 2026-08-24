import flet as ft
from config import APP_TITLE
from state import app_state
from db.auth_repo import authenticate_user, AccountLockedError
from db.activity_repo import log_activity


def build_view(page: ft.Page):
    username_field = ft.TextField(label="Username", width=320, autofocus=True)
    password_field = ft.TextField(label="Password", width=320, password=True, can_reveal_password=True)
    error_text = ft.Text("", color=ft.Colors.RED_600, size=13)

    def do_login(e):
        error_text.value = ""
        if not username_field.value or not password_field.value:
            error_text.value = "Username dan password wajib diisi."
            page.update()
            return
        try:
            user = authenticate_user(username_field.value.strip(), password_field.value)
        except AccountLockedError as lock_err:
            error_text.value = (
                f"Akun terkunci karena terlalu banyak percobaan gagal. "
                f"Coba lagi setelah {lock_err.unlock_time.strftime('%H:%M')}."
            )
            page.update()
            return
        except Exception as ex:
            error_text.value = f"Gagal konek ke server: {ex}"
            page.update()
            return
        if user is None:
            error_text.value = "Username atau password salah."
            page.update()
            return
        app_state.login(user)
        try:
            log_activity(user["id"], user["username"], "LOGIN", "auth", user["id"], "Login berhasil", user.get("cabang_id"))
        except Exception:
            pass
        page.go("/dashboard")

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.STORE, size=48, color=ft.Colors.BLUE_700),
                        ft.Text(APP_TITLE, size=22, weight=ft.FontWeight.W_500),
                        ft.Text("Masuk untuk melanjutkan", size=13, color=ft.Colors.GREY_600),
                        ft.Container(height=16),
                        username_field,
                        password_field,
                        error_text,
                        ft.Container(height=8),
                        ft.ElevatedButton("Login", width=320, height=44, on_click=do_login, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
