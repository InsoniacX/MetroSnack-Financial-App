import flet as ft
from database.db import query_one, verify_password

PRIMARY = "#2563EB"


def build_login_view(page: ft.Page, on_login_success) -> ft.Container:
    username_field = ft.TextField(label="Username", width=320, color="black", autofocus=True)
    password_field = ft.TextField(label="Password", width=320, color="black", password=True, can_reveal_password=True
    )
    error_text = ft.Text("", color="#EF4444", size=13)

    def handle_login(e):
        username = username_field.value.strip()
        password = password_field.value.strip()

        if not username or not password:
            error_text.value = "Username dan password wajib diisi."
            page.update()
            return

        user = query_one(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
        )

        if user is None or not verify_password(password, user["password_hash"], user["password_salt"]):
            error_text.value = "Username atau password salah."
            page.update()
            return

        error_text.value = ""
        on_login_success(dict(user))

    return ft.Container(
        alignment=ft.Alignment.CENTER,
        expand=True,
        bgcolor="#F8FAFC",
        content=ft.Column(
            [
                ft.Text("MetroSnack", size=26, color="black", weight=ft.FontWeight.BOLD),
                ft.Text("Masuk ke akun Anda", size=13, color="#64748B"),
                ft.Container(height=20),
                username_field,
                password_field,
                error_text,
                ft.Container(height=8),
                ft.ElevatedButton(
                    "Masuk",
                    width=320,
                    height=45,
                    bgcolor=PRIMARY,
                    color="white",
                    on_click=handle_login,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
    )