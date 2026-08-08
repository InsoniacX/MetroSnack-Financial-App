import flet as ft
from state import app_state
from components.appbar import build_appbar, nav_rail
from db.user_repo import get_all_users, create_user, update_user, reset_password, set_aktif, delete_user, username_exists
from db.cabang_repo import get_active_cabang
from db.activity_repo import log_activity
from utils.validation import require_text, require_password


def build_view(page: ft.Page):
    actor = app_state.user
    if not actor or actor.get("role") != "admin":
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

    is_pusat = actor.get("cabang_id") is None

    def refresh():
        page.views[-1] = build_view(page)
        page.update()

    try:
        users = get_all_users(None if is_pusat else actor["cabang_id"])
    except Exception as ex:
        users = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400))

    def cek_akses_target(target_cabang_id):
        if is_pusat:
            return True
        return target_cabang_id == actor.get("cabang_id")

    def toggle_aktif(uid, current_aktif, target_username, target_cabang_id):
        if uid == actor["id"]:
            page.show_dialog(ft.SnackBar(ft.Text("Anda tidak bisa menonaktifkan akun Anda sendiri."), bgcolor=ft.Colors.RED_400))
            return
        if not cek_akses_target(target_cabang_id):
            page.show_dialog(ft.SnackBar(ft.Text("Anda tidak punya akses ke user cabang lain."), bgcolor=ft.Colors.RED_400))
            return
        try:
            set_aktif(uid, not current_aktif)
            aksi_teks = "Menonaktifkan" if current_aktif else "Mengaktifkan"
            log_activity(actor["id"], actor["username"], "UPDATE", "user", uid, f"{aksi_teks} user {target_username}", target_cabang_id)
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ubah status: {ex}"), bgcolor=ft.Colors.RED_400))

    def hapus_user(uid, target_username, target_cabang_id):
        if uid == actor["id"]:
            page.show_dialog(ft.SnackBar(ft.Text("Anda tidak bisa menghapus akun Anda sendiri."), bgcolor=ft.Colors.RED_400))
            return
        if not cek_akses_target(target_cabang_id):
            page.show_dialog(ft.SnackBar(ft.Text("Anda tidak punya akses ke user cabang lain."), bgcolor=ft.Colors.RED_400))
            return
        try:
            delete_user(uid)
            log_activity(actor["id"], actor["username"], "DELETE", "user", uid, f"Menghapus user {target_username}", target_cabang_id)
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal menghapus user: {ex}"), bgcolor=ft.Colors.RED_400))

    new_username = ft.TextField(label="Username", width=220)
    new_password = ft.TextField(label="Password", width=220, password=True, can_reveal_password=True)
    new_nama = ft.TextField(label="Nama Lengkap", width=220)

    if is_pusat:
        new_role = ft.Dropdown(label="Role", width=160, value="karyawan", options=[
            ft.dropdown.Option("admin", "Admin"), ft.dropdown.Option("karyawan", "Karyawan"),
        ])
        try:
            daftar_cabang = get_active_cabang()
        except Exception:
            daftar_cabang = []
        new_cabang_dd = ft.Dropdown(label="Cabang (kosongkan = Admin Pusat)", width=260, options=[ft.dropdown.Option(str(cid), nm) for cid, nm in daftar_cabang])
        new_user_row2 = ft.Row([new_nama, new_role, new_cabang_dd])
    else:
        new_role = ft.Dropdown(label="Role", width=160, value="karyawan", options=[
            ft.dropdown.Option("karyawan", "Karyawan"),
        ])
        new_cabang_dd = None
        new_user_row2 = ft.Row([new_nama, new_role])

    def submit_new_user(e):
        try:
            username_val = require_text("Username", new_username.value, max_length=50)
            if " " in username_val:
                raise ValueError("Username tidak boleh mengandung spasi.")
            nama_val = require_text("Nama Lengkap", new_nama.value, max_length=100)
            password_val = require_password(new_password.value)
            if username_exists(username_val):
                raise ValueError(f"Username '{username_val}' sudah digunakan, pilih username lain.")

            if is_pusat:
                target_cabang_id = int(new_cabang_dd.value) if new_cabang_dd.value else None
                role_val = new_role.value
                if role_val == "karyawan" and target_cabang_id is None:
                    raise ValueError("Karyawan wajib memiliki cabang, tidak bisa dikosongkan.")
            else:
                target_cabang_id = actor["cabang_id"]
                role_val = "karyawan"

            new_id = create_user(username_val, password_val, nama_val, role_val, target_cabang_id)
            log_activity(actor["id"], actor["username"], "CREATE", "user", new_id, f"Membuat user baru {username_val} (role: {role_val})", target_cabang_id)
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal tambah user baru: {ex}"), bgcolor=ft.Colors.RED_400))

    add_dlg = ft.AlertDialog(
        title=ft.Text("Tambah User Baru"),
        content=ft.Column([
            ft.Row([new_username, new_password]),
            new_user_row2,
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
    edit_target = {"uid": None, "username": None, "cabang_id": None}

    def submit_edit_user(e):
        uid = edit_target["uid"]
        if not uid:
            return
        try:
            nama_val = require_text("Nama Lengkap", edit_nama.value, max_length=100)
            update_user(uid, nama_val, edit_role.value)
            log_activity(actor["id"], actor["username"], "UPDATE", "user", uid, f"Mengubah data user {edit_target['username']} (nama: {nama_val}, role: {edit_role.value})", edit_target["cabang_id"])
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
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

    def open_edit_dialog(uid, username, nama, role, target_cabang_id):
        if not cek_akses_target(target_cabang_id):
            page.show_dialog(ft.SnackBar(ft.Text("Anda tidak punya akses ke user cabang lain."), bgcolor=ft.Colors.RED_400))
            return
        edit_target["uid"] = uid
        edit_target["username"] = username
        edit_target["cabang_id"] = target_cabang_id
        edit_nama.value = nama
        edit_role.value = role
        page.show_dialog(edit_dlg)

    reset_password_field = ft.TextField(label="Password Baru", width=250, password=True, can_reveal_password=True)
    reset_target = {"uid": None, "username": None, "cabang_id": None}

    def submit_reset_password(e):
        uid = reset_target["uid"]
        if not uid:
            return
        try:
            password_val = require_password(reset_password_field.value)
            reset_password(uid, password_val)
            log_activity(actor["id"], actor["username"], "UPDATE", "user", uid, f"Reset password user {reset_target['username']}", reset_target["cabang_id"])
            reset_password_field.value = ""
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
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

    def open_reset_dialog(uid, username, target_cabang_id):
        if not cek_akses_target(target_cabang_id):
            page.show_dialog(ft.SnackBar(ft.Text("Anda tidak punya akses ke user cabang lain."), bgcolor=ft.Colors.RED_400))
            return
        reset_target["uid"] = uid
        reset_target["username"] = username
        reset_target["cabang_id"] = target_cabang_id
        page.show_dialog(reset_dlg)

    rows = []
    for u in users:
        uid, username, nama, role, aktif, u_cabang_id, u_nama_cabang = u
        status_text = "Aktif" if aktif else "Nonaktif"
        status_color = ft.Colors.GREEN_700 if aktif else ft.Colors.RED_700
        cabang_display = u_nama_cabang if u_nama_cabang else "Pusat"
        cells = [
            ft.DataCell(ft.Text(username)),
            ft.DataCell(ft.Text(nama)),
            ft.DataCell(ft.Text(role)),
        ]
        if is_pusat:
            cells.append(ft.DataCell(ft.Text(cabang_display)))
        cells.append(ft.DataCell(ft.Text(status_text, color=status_color)))
        cells.append(ft.DataCell(ft.Row([
            ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e, uid=uid, username=username, nama=nama, role=role, cid=u_cabang_id: open_edit_dialog(uid, username, nama, role, cid)),
            ft.IconButton(
                ft.Icons.LOCK_RESET,
                tooltip="Reset Password",
                on_click=lambda e, uid=uid, username=username, cid=u_cabang_id: open_reset_dialog(uid, username, cid)
            ),
            ft.IconButton(
                ft.Icons.TOGGLE_ON if aktif else ft.Icons.TOGGLE_OFF,
                icon_color=ft.Colors.GREEN_700 if aktif else ft.Colors.GREY_400,
                tooltip="Nonaktifkan" if aktif else "Aktifkan",
                on_click=lambda e, uid=uid, aktif=aktif, username=username, cid=u_cabang_id: toggle_aktif(uid, aktif, username, cid),
            ),
            ft.IconButton(
                ft.Icons.DELETE,
                icon_color=ft.Colors.RED_400,
                tooltip="Hapus",
                on_click=lambda e, uid=uid, username=username, cid=u_cabang_id: hapus_user(uid, username, cid),
            )
        ])))
        rows.append(ft.DataRow(cells=cells))

    columns = [
        ft.DataColumn(ft.Text("Username")),
        ft.DataColumn(ft.Text("Nama Lengkap")),
        ft.DataColumn(ft.Text("Role")),
    ]
    if is_pusat:
        columns.append(ft.DataColumn(ft.Text("Cabang")))
    columns.append(ft.DataColumn(ft.Text("Status")))
    columns.append(ft.DataColumn(ft.Text("Aksi")))

    table = ft.DataTable(columns=columns, rows=rows)

    subtitle = "Tambah, Edit, Nonaktifkan, atau Hapus akun pengguna aplikasi."
    if not is_pusat:
        subtitle += f" (cabang: {actor.get('nama_cabang', '-')})"

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Kelola User", size=20, weight=ft.FontWeight.W_500),
                ft.Text(subtitle, size=13, color=ft.Colors.GREY_600),
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