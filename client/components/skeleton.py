import flet as ft

from components.appbar import is_mobile_layout


def _block(
    color,
    *,
    height,
    width=None,
    expand=None,
    col=None,
    radius=8,
):
    return ft.Container(
        height=height,
        width=width,
        expand=expand,
        col=col,
        bgcolor=color,
        border_radius=radius,
    )


def _loading_header(base_color, accent_color, mobile):
    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Memuat data...",
                        size=12,
                        color=accent_color,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.ProgressRing(
                        width=16,
                        height=16,
                        stroke_width=2,
                        color=accent_color,
                    ),
                ],
                spacing=8,
            ),
            _block(
                base_color,
                height=24,
                width=190 if mobile else 260,
            ),
            _block(
                base_color,
                height=12,
                width=250 if mobile else 380,
                radius=6,
            ),
        ],
        spacing=9,
    )


def _metric_skeleton(base_color):
    return ft.ResponsiveRow(
        [
            ft.Container(
                content=ft.Column(
                    [
                        _block(base_color, height=11, width=105, radius=5),
                        _block(base_color, height=22, width=145, radius=6),
                    ],
                    spacing=12,
                ),
                height=86,
                padding=14,
                border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.28, base_color),
                col={"xs": 12, "sm": 6, "md": 3},
            )
            for _ in range(4)
        ],
        spacing=12,
        run_spacing=12,
    )


def _table_skeleton(base_color, mobile):
    columns = 3 if mobile else 5
    rows = 5 if mobile else 7

    table_rows = []
    for row_index in range(rows):
        row_color = (
            ft.Colors.with_opacity(0.82, base_color)
            if row_index == 0
            else ft.Colors.with_opacity(0.55, base_color)
        )
        table_rows.append(
            ft.Row(
                [
                    _block(
                        row_color,
                        height=14 if row_index == 0 else 12,
                        expand=True,
                        radius=5,
                    )
                    for _ in range(columns)
                ],
                spacing=12,
            )
        )

    return ft.Container(
        content=ft.Column(table_rows, spacing=16),
        padding=16,
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.22, base_color),
    )


def _card_grid_skeleton(base_color):
    return ft.ResponsiveRow(
        [
            ft.Container(
                content=ft.Column(
                    [
                        _block(base_color, height=18, width=150, radius=6),
                        _block(base_color, height=12, width=105, radius=5),
                        _block(base_color, height=32, width=130, radius=7),
                    ],
                    spacing=14,
                ),
                height=132,
                padding=16,
                border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.25, base_color),
                col={"xs": 12, "sm": 6, "md": 4},
            )
            for _ in range(6)
        ],
        spacing=12,
        run_spacing=12,
    )


def build_page_skeleton(page, route):
    """Bangun placeholder ringan yang mengikuti bentuk halaman tujuan."""
    mobile = is_mobile_layout(page)
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    base_color = ft.Colors.BLUE_GREY_700 if is_dark else ft.Colors.BLUE_GREY_100
    accent_color = ft.Colors.BLUE_300 if is_dark else ft.Colors.BLUE_700

    controls = [
        ft.ProgressBar(
            height=3,
            color=accent_color,
            bgcolor=ft.Colors.with_opacity(0.25, base_color),
        ),
        _loading_header(base_color, accent_color, mobile),
        ft.Container(height=4),
    ]

    if route == "/dashboard":
        controls.extend(
            [
                _metric_skeleton(base_color),
                ft.ResponsiveRow(
                    [
                        _block(
                            ft.Colors.with_opacity(0.45, base_color),
                            height=220,
                            col={"xs": 12, "lg": 7},
                            radius=10,
                        ),
                        _block(
                            ft.Colors.with_opacity(0.45, base_color),
                            height=220,
                            col={"xs": 12, "lg": 5},
                            radius=10,
                        ),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
            ]
        )
    elif route == "/invoices" or route.startswith("/invoices/cabang/"):
        controls.append(_card_grid_skeleton(base_color))
    else:
        controls.extend(
            [
                ft.ResponsiveRow(
                    [
                        _block(
                            base_color,
                            height=48,
                            col={"xs": 12, "sm": 4},
                        )
                        for _ in range(3)
                    ],
                    spacing=10,
                    run_spacing=10,
                ),
                _metric_skeleton(base_color),
                _table_skeleton(base_color, mobile),
            ]
        )

    return ft.Column(
        controls,
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
