import flet as ft
from components.appbar import build_appbar, nav_rail
from db.activity_repo import log_activity
from db.cabang_repo import cabang_name_exist, create_cabang, get_all_cabang, set_cabang_aktif, update_cabang
from state import app_state
from utils.validation import require_text

def build_view(page: ft.Page):
    actor = app_state.user
    is_pusat = actor and actor.get("cabang_id") is None

    if not actor or actor.get("role") != "admin" or not is_pusat:
        return ft.View(
            route="/cabang",
            controls=[
                build_appbar(page, "Akses Ditolak"),
                ft.Container(
                    content = ft.Text("Halaman ini hanya bisa diakses oleh Admin Pusat.", size=16), 
                    padding=24
                ),
            ],
        )

    def refresh():
        page.views[-1] = build_view(page)
        page.update()

    try:
        cabang_list = get_all_cabang()
    except Exception as ex:
        cabang_list = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal mengambil data: \n {ex}"), bgcolor=ft.Colors.RED_400))

    def toggle_cabang_aktif(cid, current_aktif, nama):
        try:
            set_cabang_aktif(cid, not current_aktif)
            aksi = "Menonaktifkan" if current_aktif else "Mengaktifkan"
            log_activity(actor["id"], actor["username"], "UPDATE", "cabang", cid, f"{aksi} cabang {nama}", None)
            refresh()
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal mengubah status: \n {ex}"), bgcolor=ft.Color.RED_400))

    new_nama = ft.TextField(label="Nama Cabang", width=250)
    new_alamat = ft.TextField(label="Alamat Cabang", width=350)

    def submit_new_cabang(e):
        try:
            nama_val = require_text("Nama Cabang", new_nama.value, max_length=100)
            if cabang_name_exist(nama_val):
                raise ValueError(f"Cabang '{nama_val}' sudah ada.")
            cid = create_cabang(nama_val, (new_alamat.value or "").strip())
            log_activity(actor["id"], actor["username"], "CREATE", "cabang", cid, f"Membuat cabang {nama_val}", None)
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal tambah cabang: \n{ex}"), bgcolor=ft.Colors.RED_400))

    add_dlg = ft.AlertDialog(
        title=ft.Text("Tambah Cabang Baru"),
        content = ft.Column([new_nama, new_alamat], tight=True, spacing=10),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Simpan", on_click=submit_new_cabang),
        ],
    )

    def open_add_dialog(e):
        new_nama.value = ""
        new_alamat.value = ""
        page.show_dialog(add_dlg)

    edit_nama = ft.TextField(label = "Nama Cabang", width=250)
    edit_alamat = ft.TextField(label = "Alamat Cabang", width=350)
    edit_target = {"cid": None}

    def submit_edit_cabang(e):
        cid = edit_target["cid"]
        if not cid:
            return
        try:
            nama_val = require_text("Nama Cabang", edit_nama.value, max_length=100)
            if cabang_name_exist(nama_val, exclude_id=cid):
                raise ValueError(f"Cabang '{nama_val}' sudah dipakai cabang lain.")
            update_cabang(cid, nama_val, (edit_alamat.value or "").strip())
            log_activity(actor["id"], actor["username"], "UPDATE", "cabang", cid, f"Mengubah data cabang {nama_val}")
            page.pop_dialog()
            page.update()
            refresh()
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal update cabang: \n{ex}"), bgcolor=ft.Colors.RED_400))

    edit_dlg = ft.AlertDialog(
        title=ft.Text("Edit Cabang"),
        content=ft.Column(
            [edit_nama, edit_alamat],
            tight=True,
            spacing=10
        ),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Submit", on_click=submit_edit_cabang)
        ]
    )

    def open_edit_dialog(cid, nama, alamat):
        edit_target["cid"] = cid
        edit_nama.value = nama
        edit_alamat.value = alamat or ""
        page.show_dialog(edit_dlg)

    rows = []
    for c in cabang_list:
        cid, nama_cabang, alamat, aktif, total_user, total_folder = c
        status_text = "Aktif" if aktif else "Nonaktif"
        status_color = ft.Colors.GREEN_700 if aktif else ft.Colors.RED_700
        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(nama_cabang)),
            ft.DataCell(ft.Text(alamat or "-")),
            ft.DataCell(ft.Text(str(total_user))),
            ft.DataCell(ft.Text(str(total_folder))),
            ft.DataCell(ft.Text(status_text, color=status_color)),
            ft.DataCell(ft.Row([
                ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda e, cid=cid, nm=nama_cabang, al=alamat: open_edit_dialog(cid, nm, al)),
                ft.IconButton(
                    ft.Icons.TOGGLE_ON if aktif else ft.Icons.TOGGLE_OFF,
                    icon_color=ft.Colors.GREEN_700 if aktif else ft.Colors.GREY_400,
                    tooltip="Nonaktifkan" if aktif else "Aktifkan",
                    on_click=lambda e, cid=cid, aktif=aktif, nm=nama_cabang: toggle_cabang_aktif(cid, aktif, nm),
                ),
            ])),
        ]))

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Nama Cabang")), 
            ft.DataColumn(ft.Text("Alamat")),
            ft.DataColumn(ft.Text("Jml User")),
            ft.DataColumn(ft.Text("Jml Folder")),
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Aksi")),
        ],
        rows=rows,
    )

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Kelola Cabang", size=20, weight=ft.FontWeight.W_500),
                ft.Text("Daftar cabang yang terdaftar di sistem.", size=13, color=ft.Colors.GREY_600),
            ], expand=True),
            ft.ElevatedButton("Tambah cabang baru", icon=ft.Icons.ADD_BUSINESS, on_click=open_add_dialog, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]),
        ft.Container(height=16),
        ft.Row([table], scroll=ft.ScrollMode.AUTO) if cabang_list else ft.Text("Belum ada cabang.", color=ft.Colors.GREY_600),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route="/cabang",
        controls=[
            build_appbar(page, "Kelola Cabang"),
            ft.Row([
                nav_rail(page, 4),
                ft.VerticalDivider(width=1),
                ft.Container(content=body, padding=24, expand=True),
            ], expand=True),
        ],
        padding=0,
    )