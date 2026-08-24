import flet as ft
from components.appbar import build_appbar, nav_rail
from state import app_state
from db.activity_repo import get_recent_activities

AKSI_WARNA = {
    "CREATE": ft.Colors.GREEN_700,
    "UPDATE": ft.Colors.ORANGE_700,
    "DELETE": ft.Colors.RED_700,
    "LOGIN": ft.Colors.BLUE_700,
}


def build_view(page: ft.Page):
    actor = app_state.user
    if not actor or actor.get("role") != "admin":
        return ft.View(
            route="/activity-log",
            controls=[
                build_appbar(page, "Akses Ditolak"),
                ft.Container(
                    content=ft.Text("Halaman ini hanya bisa diakses oleh admin.", size=16),
                    padding=24,
                ),
            ],
        )

    is_pusat = actor.get("cabang_id") is None

    try:
        activities = get_recent_activities(None if is_pusat else actor["cabang_id"])
    except Exception as ex:
        activities = []
        page.show_dialog(ft.SnackBar(ft.Text(f"Gagal ambil data: {ex}"), bgcolor=ft.Colors.RED_400))

    rows = []
    for a in activities:
        aid, username, action, entity, entity_id, description, created_at, nama_cabang = a
        warna = AKSI_WARNA.get(action, ft.Colors.GREY_700)
        cells = [
            ft.DataCell(ft.Text(created_at.strftime("%d-%m-%Y %H:%M") if created_at else "-")),
            ft.DataCell(ft.Text(username or "-")),
        ]
        if is_pusat:
            cells.append(ft.DataCell(ft.Text(nama_cabang or "Pusat")))
        cells.extend([
            ft.DataCell(ft.Container(
                content=ft.Text(action, size=12, color=ft.Colors.WHITE),
                bgcolor=warna, padding=ft.Padding.symmetric(vertical=2, horizontal=8), border_radius=6,
            )),
            ft.DataCell(ft.Text(entity)),
            ft.DataCell(ft.Text(description or "-")),
        ])
        rows.append(ft.DataRow(cells=cells))

    columns = [ft.DataColumn(ft.Text("Waktu")), ft.DataColumn(ft.Text("User"))]
    if is_pusat:
        columns.append(ft.DataColumn(ft.Text("Cabang")))
    columns.extend([
        ft.DataColumn(ft.Text("Aksi")), ft.DataColumn(ft.Text("Entitas")), ft.DataColumn(ft.Text("Keterangan")),
    ])

    table = ft.DataTable(columns=columns, rows=rows)

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Log Aktivitas", size=20, weight=ft.FontWeight.W_500),
                ft.Text("Riwayat 200 aktivitas terbaru.", size=13, color=ft.Colors.GREY_600),
            ], expand=True),
        ]),
        ft.Container(height=16),
        ft.Row([table], scroll=ft.ScrollMode.AUTO) if activities else ft.Text("Belum ada aktivitas tercatat.", color=ft.Colors.GREY_600),
    ], scroll=ft.ScrollMode.AUTO, expand=True)
    return body
    # return ft.View(
    #     route="/activity-log",
    #     controls=[
    #         # build_appbar(page, "Log Aktivitas"),
    #         ft.Row([
    #             # nav_rail(page, 3),
    #             ft.VerticalDivider(width=1),
    #             ft.Container(content=body, padding=24, expand=True),
    #         ], expand=True),
    #     ],
    #     padding=0,
    # )