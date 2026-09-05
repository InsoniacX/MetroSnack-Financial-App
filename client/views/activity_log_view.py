import flet as ft

from components.appbar import is_mobile_layout
from db.activity_repo import get_recent_activities
from state import app_state


AKSI_WARNA = {
    "CREATE": ft.Colors.GREEN_700,
    "UPDATE": ft.Colors.ORANGE_700,
    "DELETE": ft.Colors.RED_700,
    "LOGIN": ft.Colors.BLUE_700,
}


def build_view(page: ft.Page):
    mobile = is_mobile_layout(page)

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

    try:
        # Backend menentukan cakupan cabang dari access token.
        activities = get_recent_activities(limit=200)
        load_error = False
    except Exception:
        activities = []
        load_error = True

    rows = []

    for activity in activities:
        (
            _activity_id,
            username,
            action,
            entity,
            _entity_id,
            description,
            created_at,
            nama_cabang,
        ) = activity

        action_text = str(action or "-").upper()
        action_color = AKSI_WARNA.get(
            action_text,
            ft.Colors.GREY_700,
        )

        if created_at and hasattr(created_at, "strftime"):
            time_format = (
                "%d-%m-%Y\n%H:%M"
                if mobile
                else "%d-%m-%Y %H:%M"
            )
            created_at_text = created_at.strftime(time_format)
        elif created_at:
            created_at_text = str(created_at)
        else:
            created_at_text = "-"

        cells = [
            ft.DataCell(ft.Text(created_at_text)),
            ft.DataCell(ft.Text(username or "-")),
        ]

        if is_pusat:
            cells.append(
                ft.DataCell(ft.Text(nama_cabang or "Pusat"))
            )

        cells.extend(
            [
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(
                            action_text,
                            size=12,
                            color=ft.Colors.WHITE,
                        ),
                        bgcolor=action_color,
                        padding=ft.Padding.symmetric(
                            vertical=2,
                            horizontal=8,
                        ),
                        border_radius=6,
                    )
                ),
                ft.DataCell(ft.Text(entity or "-")),
                ft.DataCell(ft.Text(description or "-")),
            ]
        )
        rows.append(ft.DataRow(cells=cells))

    columns = [
        ft.DataColumn(ft.Text("Waktu")),
        ft.DataColumn(ft.Text("User")),
    ]

    if is_pusat:
        columns.append(ft.DataColumn(ft.Text("Cabang")))

    columns.extend(
        [
            ft.DataColumn(ft.Text("Aksi")),
            ft.DataColumn(ft.Text("Entitas")),
            ft.DataColumn(ft.Text("Keterangan")),
        ]
    )

    table = ft.DataTable(columns=columns, rows=rows)

    header = ft.ResponsiveRow(
        [
            ft.Container(
                col={"xs": 12, "md": 8},
                content=ft.Column(
                    [
                        ft.Text(
                            "Log Aktivitas",
                            size=20,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            "Riwayat 200 aktivitas terbaru.",
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
                        ft.OutlinedButton(
                            "Muat ulang",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda e: refresh(),
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
                    "Log aktivitas gagal dimuat. Periksa koneksi backend."
                ),
                ft.OutlinedButton(
                    "Coba Lagi",
                    icon=ft.Icons.REFRESH,
                    on_click=lambda e: refresh(),
                ),
            ],
            spacing=8,
        )
    elif activities:
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
            "Belum ada aktivitas tercatat.",
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
