import re
from datetime import date
from urllib.parse import urlsplit

import flet as ft

from components.appbar import is_mobile_layout
from components.navigation import navigate
from components.pagination import ClientPagination
from config import MONTH
from db.cabang_repo import get_active_cabang
from db.pendapatan_pengeluaran_repo import get_periode_kas
from state import app_state
from utils.formatting import rp
from views.pendapatan_pengeluaran_view import build_view as build_transactions


BASE_ROUTE = "/pendapatan-pengeluaran"


def _message(page, title, message, back_route=BASE_ROUTE):
    return ft.Column(
        [
            ft.Text(title, size=20, weight=ft.FontWeight.W_500, color=ft.Colors.RED_400),
            ft.Text(message, size=14),
            ft.TextButton(
                "Kembali",
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda event: navigate(page, back_route),
            ),
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def _metric(label, value, is_dark):
    return ft.Column(
        [
            ft.Text(
                label,
                size=11,
                color=ft.Colors.GREY_400 if is_dark else ft.Colors.GREY_600,
            ),
            ft.Text(str(value), size=16, weight=ft.FontWeight.W_500),
        ],
    )


def _card(content, is_dark, padding):
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 4},
        content=content,
        bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
        border=ft.Border.all(
            0.5,
            ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
        ),
        border_radius=12,
        padding=padding,
    )


def _branch_hub(page, branches):
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    summaries = {}
    branch_cards = ft.ResponsiveRow(spacing=12, run_spacing=12)

    def branch_card(cabang_id, nama_cabang):
        if cabang_id not in summaries:
            try:
                periods = get_periode_kas(cabang_id)
                summaries[cabang_id] = (
                    str(len(periods)),
                    rp(sum(period["saldo_bersih"] for period in periods)),
                    None,
                )
            except Exception:
                summaries[cabang_id] = (
                    "Tidak tersedia",
                    "Tidak tersedia",
                    "Ringkasan gagal dimuat. Buka cabang atau segarkan halaman.",
                )
        total_periods, cash_difference, error = summaries[cabang_id]
        content = [
            ft.Row(
                [
                    ft.Icon(ft.Icons.STORE, color=ft.Colors.BLUE_700, size=26),
                    ft.Text(nama_cabang, weight=ft.FontWeight.W_500, size=17, expand=True),
                ],
                spacing=10,
            ),
            ft.Container(height=12),
            ft.Row(
                [
                    _metric("Total folder", total_periods, is_dark),
                    _metric("Selisih kas", cash_difference, is_dark),
                ],
                spacing=24,
                wrap=True,
                run_spacing=8,
            ),
        ]
        if error:
            content.append(ft.Text(error, size=11, color=ft.Colors.RED_400))
        content.extend(
            [
                ft.Container(height=14),
                ft.Button(
                    "Lihat kas cabang ini",
                    icon=ft.Icons.ARROW_FORWARD,
                    on_click=lambda event: navigate(page, f"{BASE_ROUTE}/cabang/{cabang_id}"),
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                ),
            ]
        )
        return _card(ft.Column(content, spacing=4), is_dark, 20)

    def render_page():
        branch_cards.controls = [
            branch_card(cabang_id, nama_cabang)
            for cabang_id, nama_cabang in pagination.paginate(branches)
        ]

    def change_page():
        render_page()
        page.update()

    pagination = ClientPagination(change_page)
    render_page()
    return ft.Column(
        [
            ft.Text("Pilih cabang", size=20, weight=ft.FontWeight.W_500),
            ft.Text(
                "Klik salah satu cabang untuk melihat daftar kas bulanannya.",
                size=13,
                color=ft.Colors.GREY_400 if is_dark else ft.Colors.GREY_600,
            ),
            ft.Container(height=16),
            branch_cards if branches else ft.Text(
                "Belum ada cabang aktif. Tambahkan cabang lewat menu Cabang.",
                color=ft.Colors.GREY_400 if is_dark else ft.Colors.GREY_600,
            ),
            pagination.control,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def _period_card(page, cabang_id, period, is_dark):
    return _card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE_700),
                        ft.Text(
                            f"{MONTH[period['bulan']]} {period['tahun']}",
                            weight=ft.FontWeight.W_500,
                            size=16,
                            expand=True,
                        ),
                    ]
                ),
                ft.Container(height=8),
                ft.Row(
                    [
                        _metric("Total transaksi", period["jumlah_transaksi"], is_dark),
                        _metric("Selisih kas", rp(period["saldo_bersih"]), is_dark),
                    ],
                    spacing=24,
                    wrap=True,
                    run_spacing=8,
                ),
                ft.Container(height=8),
                ft.Button(
                    "Buka folder",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda event: navigate(
                        page,
                        f"{BASE_ROUTE}/cabang/{cabang_id}/{period['tahun']}/{period['bulan']}",
                    ),
                ),
            ],
            spacing=4,
        ),
        is_dark,
        16,
    )


def _period_list(page, cabang_id, nama_cabang, is_pusat):
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    mobile = is_mobile_layout(page)
    today = date.today()
    periods = get_periode_kas(cabang_id)
    folder_cards = ft.ResponsiveRow(spacing=12, run_spacing=12)
    empty_message = ft.Text(
        "Belum ada transaksi Kas. Buka bulan untuk mulai mencatat transaksi.",
        color=ft.Colors.GREY_400 if is_dark else ft.Colors.GREY_600,
    )

    def render_page():
        folder_cards.controls = [
            _period_card(page, cabang_id, period, is_dark)
            for period in pagination.paginate(periods)
        ]
        folder_cards.visible = bool(periods)
        empty_message.visible = not periods

    def change_page():
        render_page()
        page.update()

    def refresh_periods(event):
        nonlocal periods
        try:
            refreshed_periods = get_periode_kas(cabang_id)
        except Exception as error:
            page.show_dialog(
                ft.SnackBar(ft.Text(f"Gagal menyegarkan folder: {error}"), bgcolor=ft.Colors.RED_400)
            )
            return
        periods = refreshed_periods
        pagination.reset()
        change_page()

    pagination = ClientPagination(change_page)
    render_page()
    month_field = ft.Dropdown(
        label="Bulan",
        value=str(today.month),
        options=[ft.dropdown.Option(str(month), MONTH[month]) for month in range(1, 13)],
        col={"xs": 12, "sm": 6},
    )
    year_field = ft.TextField(
        label="Tahun",
        value=str(today.year),
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )

    def open_period(event):
        try:
            selected_month = int(month_field.value)
            selected_year = int(year_field.value)
            if not 1 <= selected_month <= 12 or not 2000 <= selected_year <= 2100:
                raise ValueError
        except (TypeError, ValueError):
            year_field.error_text = "Pilih bulan valid dan tahun antara 2000–2100."
            page.update()
            return
        year_field.error_text = None
        page.pop_dialog()
        navigate(page, f"{BASE_ROUTE}/cabang/{cabang_id}/{selected_year}/{selected_month}")

    dialog = ft.AlertDialog(
        title=ft.Text("Buka folder bulan"),
        content=ft.Container(
            ft.Column(
                [
                    ft.ResponsiveRow([month_field, year_field], spacing=10, run_spacing=10),
                    ft.Text(
                        "Pilih bulan yang ingin dibuka. Folder akan muncul dalam daftar "
                        "setelah transaksi pertama disimpan; tidak ada data baru saat membuka bulan kosong.",
                        size=12,
                    ),
                ],
                tight=True,
                spacing=12,
            ),
            width=min(520, max(260, (getattr(page, "width", None) or 1100) - 72)),
        ),
        content_padding=ft.Padding.only(left=16, right=16, top=8, bottom=8),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Batal", on_click=lambda event: page.pop_dialog()),
            ft.Button(
                "Buka & Lanjut" if mobile else "Buka & Mulai Input Transaksi",
                on_click=open_period,
            ),
        ],
    )

    def open_dialog(event):
        year_field.error_text = None
        page.show_dialog(dialog)

    title_controls = []
    if is_pusat:
        title_controls.append(
            ft.IconButton(
                ft.Icons.ARROW_BACK,
                tooltip="Kembali ke cabang",
                on_click=lambda event: navigate(page, BASE_ROUTE),
            )
        )
    title_controls.append(
        ft.Column(
            [
                ft.Text(f"Kas - {nama_cabang}", size=20, weight=ft.FontWeight.W_500),
                ft.Text("Kelola pendapatan dan pengeluaran bulanan Anda.", size=13, color=ft.Colors.GREY_600),
            ],
            expand=True,
        )
    )
    header_title = ft.Container(
        ft.Row(title_controls, vertical_alignment=ft.CrossAxisAlignment.START),
        col={"xs": 12, "md": 6},
    )
    header_actions = ft.Container(
        ft.Row(
            [
                ft.OutlinedButton("Segarkan", icon=ft.Icons.REFRESH, on_click=refresh_periods),
                ft.Button(
                    "Buka Bulan" if mobile else "Buka folder bulan",
                    icon=ft.Icons.ADD,
                    on_click=open_dialog,
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                ),
            ],
            wrap=True,
            spacing=8,
            run_spacing=8,
            alignment=ft.MainAxisAlignment.START if mobile else ft.MainAxisAlignment.END,
        ),
        col={"xs": 12, "md": 6},
    )
    return ft.Column(
        [
            ft.ResponsiveRow([header_title, header_actions], spacing=8, run_spacing=8),
            ft.Container(height=16),
            folder_cards,
            empty_message,
            pagination.control,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def build_view(page: ft.Page):
    actor = app_state.user or {}
    if not actor:
        return _message(page, "Sesi berakhir", "Silakan login kembali.", "/login")
    is_pusat = actor.get("role") == "admin" and actor.get("cabang_id") is None
    route = urlsplit(page.route or BASE_ROUTE).path.rstrip("/")
    selected_year = None
    selected_month = None
    if route == BASE_ROUTE:
        if is_pusat:
            try:
                return _branch_hub(page, get_active_cabang())
            except Exception as error:
                return _message(page, "Daftar cabang gagal dimuat", str(error))
        cabang_id = actor.get("cabang_id")
        if cabang_id is None:
            return _message(page, "Akses ditolak", "Akun belum terhubung ke cabang.")
        cabang_id = int(cabang_id)
    else:
        match = re.fullmatch(
            rf"{BASE_ROUTE}/cabang/([0-9]+)(?:/([0-9]{{4}})/([0-9]{{1,2}}))?", route
        )
        if match is None:
            return _message(page, "Halaman tidak ditemukan", "Alamat halaman Kas tidak valid.")
        cabang_id = int(match.group(1))
        if match.group(2) is not None:
            selected_year = int(match.group(2))
            selected_month = int(match.group(3))
            if not 2000 <= selected_year <= 2100 or not 1 <= selected_month <= 12:
                return _message(page, "Periode tidak valid", "Periksa kembali bulan dan tahun.")
    if cabang_id <= 0 or (not is_pusat and cabang_id != actor.get("cabang_id")):
        return _message(page, "Akses ditolak", "Anda hanya dapat membuka Kas cabang sendiri.")
    try:
        if is_pusat:
            branches = dict(get_active_cabang())
            if cabang_id not in branches:
                return _message(page, "Cabang tidak tersedia", "Cabang tidak ditemukan atau tidak aktif.")
            nama_cabang = branches[cabang_id]
        else:
            nama_cabang = actor.get("nama_cabang") or f"Cabang {cabang_id}"
        if selected_year is None:
            return _period_list(page, cabang_id, nama_cabang, is_pusat)
        return build_transactions(
            page, cabang_id=cabang_id, bulan=selected_month,
            tahun=selected_year, nama_cabang=nama_cabang,
        )
    except Exception as error:
        return _message(page, "Halaman Kas gagal dimuat", str(error))
