import flet as ft

from components.appbar import is_mobile_layout
from components.navigation import navigate
from components.pagination import ClientPagination
from db.cabang_repo import (
    cabang_name_exist,
    create_cabang,
    get_all_cabang,
    set_cabang_aktif,
    update_cabang,
)
from db.http_client import ApiError
from state import app_state
from utils.validation import require_text


def build_view(page: ft.Page):
    mobile = is_mobile_layout(page)
    dialog_width = 300 if mobile else 620

    def close_dialog(e=None):
        del e
        page.pop_dialog()
        page.update()

    def format_error(action, error=None):
        if isinstance(error, ApiError) and str(error).strip():
            return f"{action}: {error}"
        if error is None:
            return action
        return f"{action}. Periksa koneksi backend lalu coba lagi."

    def show_error(action, error=None):
        page.show_dialog(
            ft.SnackBar(
                ft.Text(format_error(action, error)),
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
    is_pusat = bool(
        actor
        and actor.get("role") == "admin"
        and actor.get("cabang_id") is None
    )

    if not is_pusat:
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
                    "Halaman ini hanya bisa diakses oleh Admin Pusat.",
                    size=14,
                ),
                ft.TextButton(
                    "Kembali ke Dashboard",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate(page, "/dashboard"),
                ),
            ],
            spacing=8,
        )

    try:
        cabang_list = get_all_cabang()
        load_error = False
    except Exception:
        cabang_list = []
        load_error = True

    # ---------- Konfirmasi aktif/nonaktif ----------
    toggle_target = {
        "cid": None,
        "aktif": None,
        "nama": None,
    }
    toggle_message = ft.Text("")
    toggle_error = ft.Text(
        "",
        color=ft.Colors.RED_400,
        size=12,
        visible=False,
    )
    toggle_confirm_button = ft.ElevatedButton("Ya, Lanjutkan")

    def confirm_toggle(e):
        del e
        cid = toggle_target["cid"]
        current_aktif = toggle_target["aktif"]

        if (
            cid is None
            or current_aktif is None
            or toggle_confirm_button.disabled
        ):
            return

        toggle_error.visible = False
        set_button_busy(
            toggle_confirm_button,
            True,
            "Ya, Lanjutkan",
        )
        page.update()

        try:
            set_cabang_aktif(cid, not current_aktif)
            page.pop_dialog()
            refresh()
        except Exception as ex:
            set_button_busy(
                toggle_confirm_button,
                False,
                "Ya, Lanjutkan",
            )
            toggle_error.value = format_error(
                "Gagal mengubah status cabang",
                ex,
            )
            toggle_error.visible = True
            page.update()

    toggle_confirm_button.on_click = confirm_toggle

    toggle_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Konfirmasi Status Cabang"),
        content=ft.Container(
            width=300 if mobile else 460,
            content=ft.Column(
                [toggle_message, toggle_error],
                spacing=8,
                tight=True,
            ),
        ),
        inset_padding=12 if mobile else 40,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            toggle_confirm_button,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def request_toggle(
        cid,
        current_aktif,
        nama,
        total_user,
        total_folder,
    ):
        toggle_target.update(
            {
                "cid": cid,
                "aktif": current_aktif,
                "nama": nama,
            }
        )
        toggle_error.value = ""
        toggle_error.visible = False
        set_button_busy(
            toggle_confirm_button,
            False,
            "Ya, Lanjutkan",
        )

        if current_aktif:
            toggle_message.value = (
                f"Nonaktifkan cabang '{nama}'? Cabang tidak akan "
                "muncul pada pilihan cabang aktif. "
                f"Data lama tetap tersimpan ({total_user} user dan "
                f"{total_folder} folder)."
            )
        else:
            toggle_message.value = (
                f"Aktifkan kembali cabang '{nama}'? Cabang akan "
                "kembali muncul pada pilihan cabang aktif."
            )

        page.show_dialog(toggle_dialog)

    # ---------- Tambah cabang ----------
    new_nama = ft.TextField(
        label="Nama Cabang",
        col={"xs": 12, "md": 5},
    )
    new_alamat = ft.TextField(
        label="Alamat Cabang",
        multiline=True,
        min_lines=2,
        max_lines=3,
        col={"xs": 12, "md": 7},
    )
    add_form_error = ft.Text(
        "",
        color=ft.Colors.RED_400,
        size=12,
        visible=False,
        col={"xs": 12},
    )
    add_save_button = ft.ElevatedButton("Simpan")

    def submit_new_cabang(e):
        del e

        if add_save_button.disabled:
            return

        add_form_error.visible = False
        set_button_busy(add_save_button, True, "Simpan")
        page.update()

        try:
            nama_val = require_text(
                "Nama Cabang",
                new_nama.value,
                max_length=100,
            )
            alamat_val = (new_alamat.value or "").strip()

            if cabang_name_exist(nama_val):
                raise ValueError(f"Cabang '{nama_val}' sudah ada.")

            create_cabang(nama_val, alamat_val)
            page.pop_dialog()
            refresh()
        except ValueError as ex:
            set_button_busy(add_save_button, False, "Simpan")
            add_form_error.value = str(ex)
            add_form_error.visible = True
            page.update()
        except Exception as ex:
            set_button_busy(add_save_button, False, "Simpan")
            add_form_error.value = format_error(
                "Gagal menambah cabang",
                ex,
            )
            add_form_error.visible = True
            page.update()

    add_save_button.on_click = submit_new_cabang
    new_alamat.on_submit = submit_new_cabang

    add_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Tambah Cabang Baru"),
        content=ft.Container(
            width=dialog_width,
            content=ft.ResponsiveRow(
                [new_nama, new_alamat, add_form_error],
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
        new_nama.value = ""
        new_alamat.value = ""
        add_form_error.value = ""
        add_form_error.visible = False
        set_button_busy(add_save_button, False, "Simpan")
        page.show_dialog(add_dialog)

    # ---------- Edit cabang ----------
    edit_nama = ft.TextField(
        label="Nama Cabang",
        col={"xs": 12, "md": 5},
    )
    edit_alamat = ft.TextField(
        label="Alamat Cabang",
        multiline=True,
        min_lines=2,
        max_lines=3,
        col={"xs": 12, "md": 7},
    )
    edit_form_error = ft.Text(
        "",
        color=ft.Colors.RED_400,
        size=12,
        visible=False,
        col={"xs": 12},
    )
    edit_target = {"cid": None}
    edit_save_button = ft.ElevatedButton("Simpan")

    def submit_edit_cabang(e):
        del e
        cid = edit_target["cid"]

        if cid is None or edit_save_button.disabled:
            return

        edit_form_error.visible = False
        set_button_busy(edit_save_button, True, "Simpan")
        page.update()

        try:
            nama_val = require_text(
                "Nama Cabang",
                edit_nama.value,
                max_length=100,
            )
            alamat_val = (edit_alamat.value or "").strip()

            if cabang_name_exist(nama_val, exclude_id=cid):
                raise ValueError(
                    f"Cabang '{nama_val}' sudah dipakai cabang lain."
                )

            update_cabang(cid, nama_val, alamat_val)
            page.pop_dialog()
            refresh()
        except ValueError as ex:
            set_button_busy(edit_save_button, False, "Simpan")
            edit_form_error.value = str(ex)
            edit_form_error.visible = True
            page.update()
        except Exception as ex:
            set_button_busy(edit_save_button, False, "Simpan")
            edit_form_error.value = format_error(
                "Gagal memperbarui cabang",
                ex,
            )
            edit_form_error.visible = True
            page.update()

    edit_save_button.on_click = submit_edit_cabang
    edit_alamat.on_submit = submit_edit_cabang

    edit_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Cabang"),
        content=ft.Container(
            width=dialog_width,
            content=ft.ResponsiveRow(
                [edit_nama, edit_alamat, edit_form_error],
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

    def open_edit_dialog(cid, nama, alamat):
        edit_target["cid"] = cid
        edit_nama.value = nama
        edit_alamat.value = alamat or ""
        edit_form_error.value = ""
        edit_form_error.visible = False
        set_button_busy(edit_save_button, False, "Simpan")
        page.show_dialog(edit_dialog)

    # ---------- Tabel cabang ----------
    rows = []

    for cabang in cabang_list:
        (
            cid,
            nama_cabang,
            alamat,
            aktif,
            total_user,
            total_folder,
        ) = cabang
        current_aktif = bool(aktif)

        def edit_action(
            e,
            target_id=cid,
            target_name=nama_cabang,
            target_address=alamat,
        ):
            del e
            open_edit_dialog(
                target_id,
                target_name,
                target_address,
            )

        def toggle_action(
            e,
            target_id=cid,
            target_active=current_aktif,
            target_name=nama_cabang,
            target_users=total_user,
            target_folders=total_folder,
        ):
            del e
            request_toggle(
                target_id,
                target_active,
                target_name,
                target_users,
                target_folders,
            )

        if mobile:
            action_control = ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                tooltip=f"Aksi untuk {nama_cabang}",
                items=[
                    ft.PopupMenuItem(
                        "Edit",
                        icon=ft.Icons.EDIT,
                        on_click=edit_action,
                    ),
                    ft.PopupMenuItem(
                        (
                            "Nonaktifkan"
                            if current_aktif
                            else "Aktifkan"
                        ),
                        icon=(
                            ft.Icons.TOGGLE_OFF
                            if current_aktif
                            else ft.Icons.TOGGLE_ON
                        ),
                        on_click=toggle_action,
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
                        (
                            ft.Icons.TOGGLE_ON
                            if current_aktif
                            else ft.Icons.TOGGLE_OFF
                        ),
                        icon_color=(
                            ft.Colors.GREEN_700
                            if current_aktif
                            else ft.Colors.GREY_400
                        ),
                        tooltip=(
                            "Nonaktifkan"
                            if current_aktif
                            else "Aktifkan"
                        ),
                        on_click=toggle_action,
                    ),
                ],
                spacing=0,
            )

        status_text = "Aktif" if current_aktif else "Nonaktif"
        status_color = (
            ft.Colors.GREEN_700
            if current_aktif
            else ft.Colors.RED_700
        )
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(nama_cabang)),
                    ft.DataCell(ft.Text(alamat or "-")),
                    ft.DataCell(ft.Text(str(total_user))),
                    ft.DataCell(ft.Text(str(total_folder))),
                    ft.DataCell(
                        ft.Text(status_text, color=status_color)
                    ),
                    ft.DataCell(action_control),
                ]
            )
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Nama Cabang")),
            ft.DataColumn(ft.Text("Alamat")),
            ft.DataColumn(ft.Text("Jml User")),
            ft.DataColumn(ft.Text("Jml Folder")),
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Aksi")),
        ],
        rows=[],
    )

    def render_cabang_page():
        table.rows = cabang_pagination.paginate(rows)
        page.update()

    cabang_pagination = ClientPagination(render_cabang_page)
    table.rows = cabang_pagination.paginate(rows)

    header = ft.ResponsiveRow(
        [
            ft.Container(
                col={"xs": 12, "md": 8},
                content=ft.Column(
                    [
                        ft.Text(
                            "Kelola Cabang",
                            size=20,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            "Daftar cabang yang terdaftar di sistem.",
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
                                "Tambah cabang"
                                if mobile
                                else "Tambah cabang baru"
                            ),
                            icon=ft.Icons.ADD_BUSINESS,
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
                    "Data cabang gagal dimuat. Periksa koneksi backend."
                ),
                ft.OutlinedButton(
                    "Coba Lagi",
                    icon=ft.Icons.REFRESH,
                    on_click=lambda e: refresh(),
                ),
            ],
            spacing=8,
        )
    elif cabang_list:
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
        table_controls.append(cabang_pagination.control)
        data_content = ft.Column(table_controls, spacing=8)
    else:
        data_content = ft.Text(
            "Belum ada cabang.",
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
