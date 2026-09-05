import flet as ft

from state import app_state
from components.appbar import is_mobile_layout
from db.http_client import ApiError
from db.user_repo import (
    get_all_users,
    create_user,
    update_user,
    reset_password,
    set_aktif,
    delete_user,
    username_exists,
)
from db.cabang_repo import get_active_cabang
from utils.validation import require_text, require_password


def build_view(page: ft.Page):
    mobile = is_mobile_layout(page)
    dialog_content_width = 300 if mobile else 620

    def close_dialog(e=None):
        del e
        page.pop_dialog()
        page.update()

    def format_error(action, error=None):
        if isinstance(error, ApiError) and str(error).strip():
            return f"{action}: {error}"
        elif error is None:
            return action
        return f"{action}. Periksa koneksi backend lalu coba lagi."

    def show_error(action, error=None):
        message = format_error(action, error)

        page.show_dialog(
            ft.SnackBar(
                ft.Text(message),
                bgcolor=ft.Colors.RED_400,
            )
        )

    def set_button_busy(button, busy, normal_text):
        button.disabled = busy
        button.content = "Memproses..." if busy else normal_text

    def refresh():
        if page.views and page.views[-1].controls:
            root_control = page.views[-1].controls[0]
            replacement = build_view(page)

            if isinstance(root_control, ft.Container):
                root_control.content = replacement
                page.update()
                return

            if (
                isinstance(root_control, ft.Row)
                and len(root_control.controls) >= 3
                and isinstance(root_control.controls[2], ft.Container)
            ):
                root_control.controls[2].content = replacement
                page.update()
                return

        page.update()

    actor = app_state.user

    if not actor or actor.get("role") != "admin":
        return ft.Column(
            [
                ft.Icon(
                    ft.Icons.LOCK_OUTLINE,
                    size=40,
                    color=ft.Colors.RED_400,
                ),
                ft.Text(
                    "Akses Ditolak",
                    size=20,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    "Halaman ini hanya bisa diakses oleh admin.",
                    size=14,
                ),
                ft.TextButton(
                    "Kembali ke Dashboard",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: page.go("/dashboard"),
                ),
            ],
            spacing=8,
        )

    is_pusat = actor.get("cabang_id") is None
    load_error = False

    try:
        users = get_all_users(
            None if is_pusat else actor["cabang_id"]
        )
    except Exception:
        users = []
        load_error = True

    def has_branch_access(target_cabang_id):
        if is_pusat:
            return True
        return target_cabang_id == actor.get("cabang_id")

    def can_manage_target(
        uid,
        target_role,
        target_cabang_id,
        action,
        destructive=False,
    ):
        if not has_branch_access(target_cabang_id):
            show_error("Anda tidak punya akses ke user cabang lain")
            return False

        if (
            not is_pusat
            and target_role == "admin"
            and uid != actor["id"]
        ):
            show_error(
                "Admin cabang tidak boleh mengelola akun admin lain"
            )
            return False

        if destructive and uid == actor["id"]:
            verb = (
                "menghapus"
                if action == "hapus"
                else "mengubah status"
            )
            show_error(
                f"Anda tidak bisa {verb} akun Anda sendiri"
            )
            return False

        return True

    # ---------- Konfirmasi aktif/nonaktif ----------
    toggle_target = {
        "uid": None,
        "current_aktif": None,
        "username": None,
        "role": None,
        "cabang_id": None,
    }
    toggle_message = ft.Text("")

    def confirm_toggle(e):
        del e
        uid = toggle_target["uid"]
        current_aktif = toggle_target["current_aktif"]

        if uid is None or current_aktif is None:
            return

        page.pop_dialog()

        try:
            set_aktif(uid, not current_aktif)
            refresh()
        except Exception as ex:
            show_error("Gagal mengubah status user", ex)

    toggle_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Konfirmasi Status User"),
        content=toggle_message,
        inset_padding=12 if mobile else 40,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Ya, Lanjutkan",
                on_click=confirm_toggle,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def request_toggle(
        uid,
        current_aktif,
        target_username,
        target_role,
        target_cabang_id,
    ):
        if not can_manage_target(
            uid,
            target_role,
            target_cabang_id,
            "status",
            destructive=True,
        ):
            return

        toggle_target.update(
            {
                "uid": uid,
                "current_aktif": current_aktif,
                "username": target_username,
                "role": target_role,
                "cabang_id": target_cabang_id,
            }
        )
        action_label = "menonaktifkan" if current_aktif else "mengaktifkan"
        toggle_message.value = (
            f"Anda yakin ingin {action_label} user "
            f"'{target_username}'?"
        )
        page.show_dialog(toggle_dialog)

    # ---------- Konfirmasi hapus ----------
    delete_target = {
        "uid": None,
        "username": None,
        "role": None,
        "cabang_id": None,
    }
    delete_message = ft.Text("")

    def confirm_delete(e):
        del e
        uid = delete_target["uid"]

        if uid is None:
            return

        page.pop_dialog()

        try:
            delete_user(uid)
            refresh()
        except Exception as ex:
            show_error("Gagal menghapus user", ex)

    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Hapus User?"),
        content=delete_message,
        inset_padding=12 if mobile else 40,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Ya, Hapus",
                on_click=confirm_delete,
                bgcolor=ft.Colors.RED_600,
                color=ft.Colors.WHITE,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def request_delete(
        uid,
        target_username,
        target_role,
        target_cabang_id,
    ):
        if not can_manage_target(
            uid,
            target_role,
            target_cabang_id,
            "hapus",
            destructive=True,
        ):
            return

        delete_target.update(
            {
                "uid": uid,
                "username": target_username,
                "role": target_role,
                "cabang_id": target_cabang_id,
            }
        )
        delete_message.value = (
            f"User '{target_username}' akan dihapus permanen. "
            "Jika user memiliki riwayat data, backend akan menolak "
            "penghapusan dan akun sebaiknya dinonaktifkan."
        )
        page.show_dialog(delete_dialog)

    # ---------- Tambah user ----------
    new_username = ft.TextField(
        label="Username",
        col={"xs": 12, "md": 6},
        autocorrect=False,
    )
    new_password = ft.TextField(
        label="Password",
        col={"xs": 12, "md": 6},
        password=True,
        can_reveal_password=True,
    )
    new_nama = ft.TextField(
        label="Nama Lengkap",
        col={"xs": 12, "md": 6},
    )

    if is_pusat:
        new_role = ft.Dropdown(
            label="Role",
            col={"xs": 12, "md": 6},
            value="karyawan",
            options=[
                ft.dropdown.Option("admin", "Admin"),
                ft.dropdown.Option("karyawan", "Karyawan"),
            ],
        )

        try:
            daftar_cabang = get_active_cabang()
            cabang_load_failed = False
        except Exception:
            daftar_cabang = []
            cabang_load_failed = True

        new_cabang_dd = ft.Dropdown(
            label="Cabang (kosongkan untuk Admin Pusat)",
            col={"xs": 12},
            options=[
                ft.dropdown.Option(str(cid), nama)
                for cid, nama in daftar_cabang
            ],
            helper_text=(
                "Daftar cabang gagal dimuat. Tutup dialog lalu coba lagi."
                if cabang_load_failed
                else None
            ),
        )
    else:
        new_role = ft.Dropdown(
            label="Role",
            col={"xs": 12, "md": 6},
            value="karyawan",
            options=[
                ft.dropdown.Option("karyawan", "Karyawan"),
            ],
            disabled=True,
        )
        new_cabang_dd = None

    add_save_button = ft.ElevatedButton("Simpan")
    add_form_error = ft.Text(
        "",
        color=ft.Colors.RED_400,
        size=12,
        visible=False,
        col={"xs": 12},
    )

    def submit_new_user(e):
        del e

        if add_save_button.disabled:
            return

        add_form_error.visible = False
        set_button_busy(add_save_button, True, "Simpan")
        page.update()

        try:
            username_val = require_text(
                "Username",
                new_username.value,
                max_length=50,
            )
            if " " in username_val:
                raise ValueError(
                    "Username tidak boleh mengandung spasi."
                )

            nama_val = require_text(
                "Nama Lengkap",
                new_nama.value,
                max_length=100,
            )
            password_val = require_password(new_password.value)

            if username_exists(username_val):
                raise ValueError(
                    f"Username '{username_val}' sudah digunakan, "
                    "pilih username lain."
                )

            if is_pusat:
                target_cabang_id = (
                    int(new_cabang_dd.value)
                    if new_cabang_dd.value
                    else None
                )
                role_val = new_role.value

                if role_val == "karyawan" and target_cabang_id is None:
                    raise ValueError(
                        "Karyawan wajib memiliki cabang, "
                        "tidak bisa dikosongkan."
                    )
            else:
                target_cabang_id = actor["cabang_id"]
                role_val = "karyawan"

            create_user(
                username_val,
                password_val,
                nama_val,
                role_val,
                target_cabang_id,
            )
            close_dialog()
            refresh()
        except ValueError as ex:
            set_button_busy(add_save_button, False, "Simpan")
            add_form_error.value = str(ex)
            add_form_error.visible = True
            page.update()
        except Exception as ex:
            set_button_busy(add_save_button, False, "Simpan")
            add_form_error.value = format_error(
                "Gagal menambah user baru",
                ex,
            )
            add_form_error.visible = True
            page.update()

    add_save_button.on_click = submit_new_user
    new_password.on_submit = submit_new_user

    add_dialog_controls = [
        new_username,
        new_password,
        new_nama,
        new_role,
    ]
    if new_cabang_dd is not None:
        add_dialog_controls.append(new_cabang_dd)
    add_dialog_controls.append(add_form_error)

    add_dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Tambah User Baru"),
        content=ft.Container(
            width=dialog_content_width,
            content=ft.ResponsiveRow(
                add_dialog_controls,
                spacing=10,
                run_spacing=10,
            ),
        ),
        content_padding=ft.Padding.only(
            left=16,
            right=16,
            top=8,
            bottom=8,
        ),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            add_save_button,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_add_dialog(e):
        del e
        new_username.value = ""
        new_password.value = ""
        new_nama.value = ""
        new_role.value = "karyawan"
        if new_cabang_dd is not None:
            new_cabang_dd.value = None
        add_form_error.value = ""
        add_form_error.visible = False
        set_button_busy(add_save_button, False, "Simpan")
        page.show_dialog(add_dlg)

    # ---------- Edit user ----------
    edit_nama = ft.TextField(
        label="Nama Lengkap",
        col={"xs": 12},
    )
    edit_role = ft.Dropdown(
        label="Role",
        col={"xs": 12},
        options=[
            ft.dropdown.Option("admin", "Admin"),
            ft.dropdown.Option("karyawan", "Karyawan"),
        ],
    )
    edit_target = {
        "uid": None,
        "username": None,
        "role": None,
        "cabang_id": None,
    }
    edit_save_button = ft.ElevatedButton("Simpan")
    edit_form_error = ft.Text(
        "",
        color=ft.Colors.RED_400,
        size=12,
        visible=False,
        col={"xs": 12},
    )

    def submit_edit_user(e):
        del e
        uid = edit_target["uid"]

        if uid is None or edit_save_button.disabled:
            return

        edit_form_error.visible = False
        set_button_busy(edit_save_button, True, "Simpan")
        page.update()

        try:
            nama_val = require_text(
                "Nama Lengkap",
                edit_nama.value,
                max_length=100,
            )
            role_val = edit_role.value or edit_target["role"]
            update_user(uid, nama_val, role_val)
            close_dialog()
            refresh()
        except ValueError as ex:
            set_button_busy(edit_save_button, False, "Simpan")
            edit_form_error.value = str(ex)
            edit_form_error.visible = True
            page.update()
        except Exception as ex:
            set_button_busy(edit_save_button, False, "Simpan")
            edit_form_error.value = format_error(
                "Gagal memperbarui user",
                ex,
            )
            edit_form_error.visible = True
            page.update()

    edit_save_button.on_click = submit_edit_user

    edit_dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit User"),
        content=ft.Container(
            width=300 if mobile else 420,
            content=ft.ResponsiveRow(
                [edit_nama, edit_role, edit_form_error],
                spacing=10,
                run_spacing=10,
            ),
        ),
        content_padding=ft.Padding.only(
            left=16,
            right=16,
            top=8,
            bottom=8,
        ),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            edit_save_button,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_edit_dialog(
        uid,
        username,
        nama,
        role,
        target_cabang_id,
    ):
        if not can_manage_target(
            uid,
            role,
            target_cabang_id,
            "edit",
        ):
            return

        edit_target.update(
            {
                "uid": uid,
                "username": username,
                "role": role,
                "cabang_id": target_cabang_id,
            }
        )
        edit_nama.value = nama
        edit_role.value = role
        edit_role.disabled = not is_pusat or uid == actor["id"]
        edit_form_error.value = ""
        edit_form_error.visible = False
        set_button_busy(edit_save_button, False, "Simpan")
        page.show_dialog(edit_dlg)

    # ---------- Reset password ----------
    reset_password_field = ft.TextField(
        label="Password Baru",
        password=True,
        can_reveal_password=True,
    )
    reset_target = {
        "uid": None,
        "username": None,
        "role": None,
        "cabang_id": None,
    }
    reset_save_button = ft.ElevatedButton("Simpan")
    reset_form_error = ft.Text(
        "",
        color=ft.Colors.RED_400,
        size=12,
        visible=False,
    )

    def submit_reset_password(e):
        del e
        uid = reset_target["uid"]

        if uid is None or reset_save_button.disabled:
            return

        reset_form_error.visible = False
        set_button_busy(reset_save_button, True, "Simpan")
        page.update()

        try:
            password_val = require_password(
                reset_password_field.value
            )
            reset_password(uid, password_val)
            reset_password_field.value = ""
            close_dialog()
            refresh()
        except ValueError as ex:
            set_button_busy(reset_save_button, False, "Simpan")
            reset_form_error.value = str(ex)
            reset_form_error.visible = True
            page.update()
        except Exception as ex:
            set_button_busy(reset_save_button, False, "Simpan")
            reset_form_error.value = format_error(
                "Gagal mereset password",
                ex,
            )
            reset_form_error.visible = True
            page.update()

    reset_save_button.on_click = submit_reset_password
    reset_password_field.on_submit = submit_reset_password

    reset_dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Reset Password User"),
        content=ft.Container(
            width=300 if mobile else 420,
            content=ft.Column(
                [reset_password_field, reset_form_error],
                spacing=8,
                tight=True,
            ),
        ),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            reset_save_button,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_reset_dialog(
        uid,
        username,
        role,
        target_cabang_id,
    ):
        if not can_manage_target(
            uid,
            role,
            target_cabang_id,
            "reset password",
        ):
            return

        reset_target.update(
            {
                "uid": uid,
                "username": username,
                "role": role,
                "cabang_id": target_cabang_id,
            }
        )
        reset_password_field.value = ""
        reset_form_error.value = ""
        reset_form_error.visible = False
        set_button_busy(reset_save_button, False, "Simpan")
        page.show_dialog(reset_dlg)

    # ---------- Tabel user ----------
    rows = []

    for user_row in users:
        (
            uid,
            username,
            nama,
            role,
            aktif,
            user_cabang_id,
            user_nama_cabang,
        ) = user_row

        status_text = "Aktif" if aktif else "Nonaktif"
        status_color = (
            ft.Colors.GREEN_700
            if aktif
            else ft.Colors.RED_700
        )
        cabang_display = user_nama_cabang or "Pusat"

        edit_action = lambda e, uid=uid, username=username, nama=nama, role=role, cid=user_cabang_id: open_edit_dialog(
            uid, username, nama, role, cid
        )
        reset_action = lambda e, uid=uid, username=username, role=role, cid=user_cabang_id: open_reset_dialog(
            uid, username, role, cid
        )
        toggle_action = lambda e, uid=uid, aktif=aktif, username=username, role=role, cid=user_cabang_id: request_toggle(
            uid, aktif, username, role, cid
        )
        delete_action = lambda e, uid=uid, username=username, role=role, cid=user_cabang_id: request_delete(
            uid, username, role, cid
        )

        if mobile:
            action_control = ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                tooltip=f"Aksi untuk {username}",
                items=[
                    ft.PopupMenuItem(
                        "Edit",
                        icon=ft.Icons.EDIT,
                        on_click=edit_action,
                    ),
                    ft.PopupMenuItem(
                        "Reset Password",
                        icon=ft.Icons.LOCK_RESET,
                        on_click=reset_action,
                    ),
                    ft.PopupMenuItem(
                        "Nonaktifkan" if aktif else "Aktifkan",
                        icon=(
                            ft.Icons.TOGGLE_OFF
                            if aktif
                            else ft.Icons.TOGGLE_ON
                        ),
                        on_click=toggle_action,
                    ),
                    ft.PopupMenuItem(
                        "Hapus",
                        icon=ft.Icons.DELETE,
                        on_click=delete_action,
                    ),
                ],
            )
        else:
            action_control = ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.EDIT,
                        tooltip="Edit",
                        on_click=edit_action,
                    ),
                    ft.IconButton(
                        ft.Icons.LOCK_RESET,
                        tooltip="Reset Password",
                        on_click=reset_action,
                    ),
                    ft.IconButton(
                        (
                            ft.Icons.TOGGLE_ON
                            if aktif
                            else ft.Icons.TOGGLE_OFF
                        ),
                        icon_color=(
                            ft.Colors.GREEN_700
                            if aktif
                            else ft.Colors.GREY_400
                        ),
                        tooltip=(
                            "Nonaktifkan"
                            if aktif
                            else "Aktifkan"
                        ),
                        on_click=toggle_action,
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Hapus",
                        on_click=delete_action,
                    ),
                ],
                spacing=0,
            )

        cells = [
            ft.DataCell(ft.Text(username)),
            ft.DataCell(ft.Text(nama)),
            ft.DataCell(ft.Text(role)),
        ]

        if is_pusat:
            cells.append(ft.DataCell(ft.Text(cabang_display)))

        cells.extend(
            [
                ft.DataCell(
                    ft.Text(status_text, color=status_color)
                ),
                ft.DataCell(action_control),
            ]
        )
        rows.append(ft.DataRow(cells=cells))

    columns = [
        ft.DataColumn(ft.Text("Username")),
        ft.DataColumn(ft.Text("Nama Lengkap")),
        ft.DataColumn(ft.Text("Role")),
    ]

    if is_pusat:
        columns.append(ft.DataColumn(ft.Text("Cabang")))

    columns.extend(
        [
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Aksi")),
        ]
    )

    table = ft.DataTable(columns=columns, rows=rows)

    subtitle = (
        "Tambah, edit, nonaktifkan, atau hapus akun pengguna aplikasi."
    )
    if not is_pusat:
        subtitle += f" Cabang: {actor.get('nama_cabang', '-')}"

    header = ft.ResponsiveRow(
        [
            ft.Container(
                col={"xs": 12, "md": 8},
                content=ft.Column(
                    [
                        ft.Text(
                            "Kelola User",
                            size=20,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            subtitle,
                            size=13,
                            color=ft.Colors.GREY_600,
                        ),
                    ],
                    spacing=4,
                ),
            ),
            ft.Container(
                col={"xs": 12, "md": 4},
                content=ft.Row(
                    [
                        ft.ElevatedButton(
                            (
                                "Tambah user"
                                if mobile
                                else "Tambah user baru"
                            ),
                            icon=ft.Icons.PERSON_ADD,
                            on_click=open_add_dialog,
                            bgcolor=ft.Colors.BLUE_700,
                            color=ft.Colors.WHITE,
                        )
                    ],
                    alignment=(
                        ft.MainAxisAlignment.START
                        if mobile
                        else ft.MainAxisAlignment.END
                    ),
                ),
            ),
        ],
        spacing=8,
        run_spacing=8,
    )

    if load_error:
        data_content = ft.Column(
            [
                ft.Icon(
                    ft.Icons.CLOUD_OFF_OUTLINED,
                    color=ft.Colors.RED_400,
                    size=32,
                ),
                ft.Text(
                    "Data user gagal dimuat. Periksa koneksi backend."
                ),
                ft.OutlinedButton(
                    "Coba Lagi",
                    icon=ft.Icons.REFRESH,
                    on_click=lambda e: refresh(),
                ),
            ],
            spacing=8,
        )
    elif users:
        table_controls = []
        if mobile:
            table_controls.append(
                ft.Text(
                    "Geser tabel ke samping untuk melihat semua kolom.",
                    size=12,
                    color=ft.Colors.GREY_600,
                )
            )
        table_controls.append(
            ft.Row([table], scroll=ft.ScrollMode.AUTO)
        )
        data_content = ft.Column(table_controls, spacing=8)
    else:
        data_content = ft.Text(
            "Belum ada user.",
            color=ft.Colors.GREY_600,
        )

    return ft.Column(
        [
            header,
            ft.Container(height=16),
            data_content,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
