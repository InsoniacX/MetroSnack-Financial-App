import flet as ft
from state import app_state
from components.appbar import build_appbar, nav_rail
from db.user_repo import get_all_users, create_user, update_user, reset_password, set_aktif, delete_user
from db.activity_repo import log_activity


def build_view(page: ft.Page):
    if not app_state.user or app_state.user.get("role") != "admin":
        return ft.View(
            route="/users",
            controls=[
                build_appbar(page, "Akses Ditolak!"),
                ft.Container(
                    content=ft.Text("Halaman ini hanya bisa diakses oleh admin.", size=16),
                    padding=24,
                ),
            ],
        )

    def refresh():
        page.views[-1] = build_view(page)
        page.update()

    try:
        users = get_all_users()
    except Exception as ex:
        users = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400))

    def toggle_aktif(uid, current_aktif, target_username):
        try:
            set_aktif(uid, not current_aktif)
            aksi_teks = "Menonaktifkan" if current_aktif else "Mengaktifkan"
            log_activity(app_state.user["id"], app_state.user["username"], "UPDATE", "user", uid, f"{aksi_teks} user {target_username}")
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ubah status: {ex}"), bgcolor=ft.Colors.RED_400))

    def hapus_user(uid, target_username):
        try:
            delete_user(uid)
            log_activity(app_state.user["id"], app_state.user["username"], "DELETE", "user", uid, f"Menghapus user {target_username}")
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal menghapus user: {ex}"), bgcolor=ft.Colors.RED_400))

    new_username = ft.TextField(label="Username", width=220)
    new_password = ft.TextField(label="Password", width=220, password=True, can_reveal_password=True)
    new_nama = ft.TextField(label="Nama Lengkap", width=220)
    new_role = ft.Dropdown(label="Role", width=180, value="karyawan", options=[
        ft.dropdown.Option("admin", "Admin"), ft.dropdown.Option("karyawan", "Karyawan")
    ])

    def submit_new_user(e):
        if not new_username.value or not new_password.value or not new_nama.value:
            return
        try:
            new_id = create_user(new_username.value.strip(), new_password.value, new_nama.value.strip(), new_role.value)
            log_activity(app_state.user["id"], app_state.user["username"], "CREATE", "user", new_id, f"Membuat user baru {new_username.value.strip()} (role: {new_role.value})")
            page.pop_dialog()
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal tambah user baru: {ex}"), bgcolor=ft.Colors.RED_400))

    add_dlg = ft.AlertDialog(
        title=ft.Text("Tambah User Baru"),
        content=ft.Column([
            ft.Row([new_username, new_password]),
            ft.Row([new_nama, new_role]),
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_new_user),
        ]
    )

    def open_add_dialog(e):
        page.show_dialog(add_dlg)

    edit_nama = ft.TextField(label="Nama Lengkap", width=220)
    edit_role = ft.Dropdown(label="Role", width=180, options=[
        ft.dropdown.Option("admin", "Admin"), ft.dropdown.Option("karyawan", "Karyawan"),
    ])
    edit_target = {"uid": None, "username": None}

    def submit_edit_user(e):
        uid = edit_target["uid"]
        if not uid or not edit_nama.value:
            return
        try:
            update_user(uid, edit_nama.value.strip(), edit_role.value)
            log_activity(app_state.user["id"], app_state.user["username"], "UPDATE", "user", uid, f"Mengubah data user {edit_target['username']} (nama: {edit_nama.value.strip()}, role: {edit_role.value})")
            page.pop_dialog()
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal update user: {ex}"), bgcolor=ft.Colors.RED_400))

    edit_dlg = ft.AlertDialog(
        title=ft.Text("Edit User"),
        content=ft.Column([edit_nama, edit_role], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_edit_user),
        ],
    )

    def open_edit_dialog(uid, username, nama, role):
        edit_target["uid"] = uid
        edit_target["username"] = username
        edit_nama.value = nama
        edit_role.value = role
        page.show_dialog(edit_dlg)

    reset_password_field = ft.TextField(label="Password Baru", width=250, password=True, can_reveal_password=True)
    reset_target = {"uid": None, "username": None}

    def submit_reset_password(e):
        uid = reset_target["uid"]
        if not uid or not reset_password_field.value:
            return
        try:
            reset_password(uid, reset_password_field.value)
            log_activity(app_state.user["id"], app_state.user["username"], "UPDATE", "user", uid, f"Reset password user {reset_target['username']}")
            reset_password_field.value = ""
            page.pop_dialog()
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal reset password: {ex}"), bgcolor=ft.Colors.RED_400))

    reset_dlg = ft.AlertDialog(
        title=ft.Text("Reset Password user"),
        content=reset_password_field,
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_reset_password),
        ],
    )

    def open_reset_dialog(uid, username):
        reset_target["uid"] = uid
        reset_target["username"] = username
        page.show_dialog(reset_dlg)

    rows = []
    for u in users:
        uid, username, nama, role, aktif = u
        status_text = "Aktif" if aktif else "Nonaktif"
        status_color = ft.Colors.GREEN_700 if aktif else ft.Colors.RED_700
        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(username)),
            ft.DataCell(ft.Text(nama)),
            ft.DataCell(ft.Text(role)),
            ft.DataCell(ft.Text(status_text, color=status_color)),
            ft.DataCell(ft.Row([
                ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e, uid=uid, username=username, nama=nama, role=role: open_edit_dialog(uid, username, nama, role)),
                ft.IconButton(
                    ft.Icons.LOCK_RESET,
                    tooltip="Reset Password",
                    on_click=lambda e, uid=uid, username=username: open_reset_dialog(uid, username)
                ),
                ft.IconButton(
                    ft.Icons.TOGGLE_ON if aktif else ft.Icons.TOGGLE_OFF,
                    icon_color=ft.Colors.GREEN_700 if aktif else ft.Colors.GREY_400,
                    tooltip="Nonaktifkan" if aktif else "Aktifkan",
                    on_click=lambda e, uid=uid, aktif=aktif, username=username: toggle_aktif(uid, aktif, username),
                ),
                ft.IconButton(
                    ft.Icons.DELETE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Hapus",
                    on_click=lambda e, uid=uid, username=username: hapus_user(uid, username),
                )
            ])),
        ]))

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Username")),
            ft.DataColumn(ft.Text("Nama Lengkap")),
            ft.DataColumn(ft.Text("Role")),
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Aksi")),
        ],
        rows=rows,
    )

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Kelola User", size=20, weight=ft.FontWeight.W_500),
                ft.Text("Tambah, Edit, Nonaktifkan, atau Hapus akun pengguna aplikasi.", size=13, color=ft.Colors.GREY_600),
            ], expand=True),
            ft.ElevatedButton("Tambah user baru", icon=ft.Icons.PERSON_ADD, on_click=open_add_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]),
        ft.Container(height=16),
        ft.Row([table], scroll=ft.ScrollMode.AUTO) if users else ft.Text("Belum ada user.", color=ft.Colors.GREY_600),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route="/users",
        controls=[
            build_appbar(page, "Kelola User"),
            ft.Row([
                nav_rail(page, 2),
                ft.VerticalDivider(width=1),
                ft.Container(content=body, padding=24, expand=True),
            ], expand=True)
        ],
        padding=0
    )