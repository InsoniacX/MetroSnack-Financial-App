import flet as ft

from config import APP_TITLE
from state import app_state
from db.auth_repo import authenticate_user, AccountLockedError
from db.activity_repo import log_activity


def build_view(page: ft.Page):
    page_height = getattr(page, "height", None) or 750
    compact_height = page_height < 600

    logo_size = 96 if compact_height else 180
    vertical_padding = 8 if compact_height else 24
    form_spacing = 6 if compact_height else 10

    username_field = ft.TextField(
        label="Username",
        autofocus=not compact_height,
        autocorrect=False,
        dense=compact_height,
    )
    password_field = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        dense=compact_height,
    )
    error_text = ft.Text(
        "",
        color=ft.Colors.RED_600,
        size=13,
        text_align=ft.TextAlign.CENTER,
    )
    login_button = ft.ElevatedButton(
        "Login",
        height=42 if compact_height else 44,
        bgcolor=ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
    )

    def set_loading(is_loading):
        username_field.disabled = is_loading
        password_field.disabled = is_loading
        login_button.disabled = is_loading
        login_button.content = "Memproses..." if is_loading else "Login"

    def show_error(message):
        error_text.value = message
        set_loading(False)
        page.update()

    def do_login(e):
        del e

        if login_button.disabled:
            return

        error_text.value = ""
        username = (username_field.value or "").strip()
        password = password_field.value or ""

        if not username or not password:
            show_error("Username dan password wajib diisi.")
            return

        set_loading(True)
        page.update()

        try:
            user = authenticate_user(username, password)
        except AccountLockedError as lock_err:
            show_error(
                "Akun terkunci karena terlalu banyak percobaan gagal. "
                f"Coba lagi setelah {lock_err.unlock_time.strftime('%H:%M')}."
            )
            return
        except Exception:
            show_error(
                "Tidak dapat terhubung ke server. "
                "Pastikan backend berjalan dan periksa koneksi jaringan."
            )
            return

        if user is None:
            show_error("Username atau password salah.")
            return

        app_state.login(user)

        try:
            log_activity(
                user["id"],
                user["username"],
                "LOGIN",
                "auth",
                user["id"],
                "Login berhasil",
                user.get("cabang_id"),
            )
        except Exception:
            pass

        page.go("/dashboard")

    login_button.on_click = do_login
    password_field.on_submit = do_login

    form = ft.Container(
        col={"xs": 12, "sm": 8, "md": 5, "lg": 4},
        padding=ft.Padding.symmetric(
            horizontal=20,
            vertical=vertical_padding,
        ),
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Image(
                        src="METROSNACK_bgremoved.png",
                        width=logo_size,
                        height=logo_size,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    APP_TITLE,
                    size=20 if compact_height else 22,
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Masuk untuk melanjutkan",
                    size=12 if compact_height else 13,
                    color=ft.Colors.GREY_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    height=0 if compact_height else 12
                ),
                username_field,
                password_field,
                error_text,
                ft.Container(
                    height=0 if compact_height else 4
                ),
                login_button,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=form_spacing,
        ),
    )

    body = ft.Column(
        [
            ft.ResponsiveRow(
                [form],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.View(
        route="/login",
        controls=[body],
        padding=0,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
