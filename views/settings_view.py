import flet as ft
from database.db import query_all, execute, hash_password, query_one

def build_settings_view(page: ft.Page, current_user: dict) -> ft.Container:
    users_column = ft.Column(spacing=10)

    # Form Tambah User
    username_field = ft.TextField(label="Username", width=380, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"))
    fullname_field = ft.TextField(label="Nama Lengkap", width=380, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"))
    password_field = ft.TextField(label="Password", width=380, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"), password=True, can_reveal_password=True)
    role_dropdown = ft.Dropdown(
        label="Role",
        width=380,
        color="black",
        border_color="#CBD5E1",
        label_style=ft.TextStyle(color="#64748B"),
        options=[
            ft.dropdown.Option("admin", "Admin"),
            ft.dropdown.Option("superadmin", "Superadmin"),
        ],
        value="admin",
    )
    form_error = ft.Text("", color="#EF4444", size=12)

    def reset_form():
        username_field.value = ""
        fullname_field.value = ""
        password_field.value = ""
        role_dropdown.value = "admin"
        form_error.value = ""

    def save_user(e):
        username = (username_field.value or "").strip()
        full_name = (fullname_field.value or "").strip()
        password = (password_field.value or "").strip()

        if not username or not full_name or not password:
            form_error.value = "Semua field wajib diisi."
            page.update()
            return

        existing = query_one("SELECT id FROM users WHERE username = ?", (username,))
        if existing:
            form_error.value = f"Username '{username}' sudah dipakai."
            page.update()
            return

        password_hash, password_salt = hash_password(password)
        execute(
            """
            INSERT INTO users (username, full_name, password_hash, password_salt, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, full_name, password_hash, password_salt, role_dropdown.value),
        )

        close_dialog()
        reset_form()
        refresh()

    add_user_dialog = ft.AlertDialog(
        modal=True,
        bgcolor="white",
        title=ft.Text("Tambah User Baru", color="black"),
        content=ft.Column(
            [username_field, fullname_field, password_field, role_dropdown, form_error],
            spacing=10,
            tight=True,
        ),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: close_dialog()),
            ft.ElevatedButton("Simpan", bgcolor="#2563EB", color="white", on_click=save_user),
        ],
    )

    def open_add_dialog(e):
        reset_form()
        page.show_dialog(add_user_dialog)

    def close_dialog():
        page.pop_dialog()

    # Nonaktifkan / Aktifkan user
    def toggle_active(user_id: int, new_status: int):
        execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        refresh()

    # Refresh daftar user
    def refresh():
        users = query_all("SELECT * FROM users ORDER BY created_at ASC")
        rows = [
            ft.Row(
                [
                    ft.Text("Username", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=140),
                    ft.Text("Nama Lengkap", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=180),
                    ft.Text("Role", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("Status", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=90),
                    ft.Text("Aksi", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=100),
                ],
            ),
            ft.Divider(color="#F1F5F9"),
        ]

        for u in users:
            is_self = u["id"] == current_user["id"]
            status_text = "Aktif" if u["is_active"] else "Nonaktif"
            status_color = "#10B981" if u["is_active"] else "#EF4444"

            action_button = ft.Container(width=100)  # kosong kalau ini akun sendiri
            if not is_self:
                if u["is_active"]:
                    action_button = ft.TextButton(
                        "Nonaktifkan", style=ft.ButtonStyle(color="#EF4444"),
                        on_click=lambda e, uid=u["id"]: toggle_active(uid, 0),
                    )
                else:
                    action_button = ft.TextButton(
                        "Aktifkan", style=ft.ButtonStyle(color="#10B981"),
                        on_click=lambda e, uid=u["id"]: toggle_active(uid, 1),
                    )

            rows.append(
                ft.Row(
                    [
                        ft.Text(u["username"] + (" (Anda)" if is_self else ""), size=13, color="black", width=140),
                        ft.Text(u["full_name"], size=13, color="black", width=180),
                        ft.Text(u["role"], size=13, color="#64748B", width=110),
                        ft.Text(status_text, size=13, color=status_color, width=90),
                        action_button,
                    ],
                )
            )

        users_column.controls = rows
        page.update()

    refresh()

    return ft.Container(
        padding=24,
        expand=True,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Settings - Manajemen User", size=22, weight=ft.FontWeight.BOLD, color="black"),
                        ft.ElevatedButton("+ Tambah User", bgcolor="#2563EB", color="white", on_click=open_add_dialog),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=20),
                ft.Container(
                    bgcolor="white",
                    border=ft.Border.all(1, "#E2E8F0"),
                    border_radius=16,
                    padding=18,
                    content=users_column,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
    )