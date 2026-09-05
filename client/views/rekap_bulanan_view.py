from datetime import date
from decimal import Decimal

import flet as ft
import flet_charts as fc

from components.appbar import is_mobile_layout
from components.metric_card import metric_card
from config import MONTH
from db.activity_repo import log_activity
from db.cabang_repo import get_active_cabang
from db.folder_repo import get_folders
from db.pengambilan_balaraja_repo import get_pengambilan_balaraja
from db.pengambilan_pabrik_repo import get_pengambilan_pabrik
from db.supir_kenek_repo import get_pengeluaran_supir_kenek
from state import app_state
from utils.formatting import rp
from utils.pdf_export import generate_rekap_bulanan_pdf


def get_rekap_available_years(cabang_id=None):
    """Mengambil daftar tahun yang tersedia melalui API."""
    years = set()

    try:
        for item in get_pengambilan_pabrik(cabang_id=cabang_id):
            tanggal = item.get("tanggal")
            if hasattr(tanggal, "year"):
                years.add(tanggal.year)
    except Exception:
        pass

    try:
        for item in get_pengambilan_balaraja(cabang_id=cabang_id):
            tanggal = item.get("tanggal")
            if hasattr(tanggal, "year"):
                years.add(tanggal.year)
    except Exception:
        pass

    try:
        for item in get_pengeluaran_supir_kenek(cabang_id=cabang_id):
            tanggal = item.get("tanggal")
            if hasattr(tanggal, "year"):
                years.add(tanggal.year)
    except Exception:
        pass

    try:
        folders = get_folders(cabang_id=cabang_id)
        for folder in folders:
            if len(folder) > 3 and folder[3]:
                years.add(int(folder[3]))
    except Exception:
        pass

    if not years:
        years.add(date.today().year)

    return sorted(years, reverse=True)


def build_view(page: ft.Page):
    actor = app_state.user or {}
    is_pusat = actor.get("cabang_id") is None
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    mobile = is_mobile_layout(page)
    today = date.today()
    card_padding = 12 if mobile else 16
    state_padding = 16 if mobile else 24

    initial_cabang_id = None if is_pusat else actor.get("cabang_id")
    available_years = get_rekap_available_years(initial_cabang_id)
    initial_year = available_years[0] if available_years else today.year

    filter_state = {
        "bulan": today.month,
        "tahun": initial_year,
        "cabang_id": initial_cabang_id,
    }

    cabang_list = []
    if is_pusat:
        try:
            cabang_list = get_active_cabang()
        except Exception:
            cabang_list = []

    # ---------------------------------------------------------------------
    # Filter periode
    # ---------------------------------------------------------------------
    filter_bulan_dropdown = ft.Dropdown(
        label="Pilih Bulan",
        options=[
            ft.dropdown.Option(str(month_number), MONTH[month_number])
            for month_number in range(1, 13)
        ],
        value=str(filter_state["bulan"]),
        col={"xs": 12, "sm": 5, "md": 3},
    )

    filter_tahun_dropdown = ft.Dropdown(
        label="Tahun",
        options=[
            ft.dropdown.Option(str(year), str(year))
            for year in available_years
        ],
        value=str(filter_state["tahun"]),
        col={"xs": 12, "sm": 3, "md": 2},
    )

    def apply_filter(e=None):
        del e
        filter_state["bulan"] = int(
            filter_bulan_dropdown.value or today.month
        )
        filter_state["tahun"] = int(
            filter_tahun_dropdown.value or today.year
        )
        refresh_rekap()

    filter_bulan_dropdown.on_change = apply_filter
    filter_tahun_dropdown.on_change = apply_filter

    filter_title = ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.CALENDAR_MONTH,
                    color=ft.Colors.INDIGO_700,
                    size=22,
                ),
                ft.Text(
                    "Periode Rekap Bulanan",
                    weight=ft.FontWeight.W_500,
                    size=15,
                ),
            ],
            spacing=8,
        ),
        col={"xs": 12, "md": 4},
    )

    filter_action = ft.Container(
        content=ft.Row(
            [
                ft.ElevatedButton(
                    "Segarkan",
                    icon=ft.Icons.REFRESH,
                    on_click=apply_filter,
                    bgcolor=ft.Colors.INDIGO_700,
                    color=ft.Colors.WHITE,
                )
            ],
            alignment=(
                ft.MainAxisAlignment.START
                if mobile
                else ft.MainAxisAlignment.END
            ),
        ),
        col={"xs": 12, "sm": 4, "md": 3},
    )

    filter_card = ft.Container(
        content=ft.ResponsiveRow(
            [
                filter_title,
                filter_bulan_dropdown,
                filter_tahun_dropdown,
                filter_action,
            ],
            spacing=10,
            run_spacing=10,
        ),
        bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
        border=ft.Border.all(
            0.5,
            ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
        ),
        border_radius=10,
        padding=card_padding,
    )

    # ---------------------------------------------------------------------
    # Kontainer dinamis
    # ---------------------------------------------------------------------
    metric_kenek_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_pabrik_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_balaraja_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_grand_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    chart_container = ft.Container()
    breakdown_table_container = ft.Container()
    detail_kenek_container = ft.Container()
    detail_pabrik_container = ft.Container()
    detail_balaraja_container = ft.Container()

    def table_with_horizontal_scroll(data_table):
        controls = []
        if mobile:
            controls.append(
                ft.Text(
                    "Geser tabel ke samping untuk melihat kolom lainnya.",
                    size=11,
                    color=ft.Colors.GREY_500,
                )
            )
        controls.append(
            ft.Row([data_table], scroll=ft.ScrollMode.AUTO)
        )
        return ft.Column(controls, spacing=6)

    def empty_detail(message):
        return ft.Container(
            content=ft.Text(
                message,
                color=ft.Colors.GREY_500,
                text_align=ft.TextAlign.CENTER,
            ),
            padding=state_padding,
            alignment=ft.Alignment.CENTER,
        )

    def build_comparison_chart(kenek_sum, pabrik_sum, balaraja_sum):
        kenek_value = float(kenek_sum)
        pabrik_value = float(pabrik_sum)
        balaraja_value = float(balaraja_sum)
        maximum_value = max(
            kenek_value,
            pabrik_value,
            balaraja_value,
            1000.0,
        )

        groups = [
            fc.BarChartGroup(
                x=0,
                rods=[
                    fc.BarChartRod(
                        from_y=0,
                        to_y=kenek_value,
                        width=28,
                        color=ft.Colors.RED_400,
                        border_radius=6,
                        tooltip=f"Operasional Mobil: {rp(kenek_value)}",
                    )
                ],
            ),
            fc.BarChartGroup(
                x=1,
                rods=[
                    fc.BarChartRod(
                        from_y=0,
                        to_y=pabrik_value,
                        width=28,
                        color=ft.Colors.INDIGO_400,
                        border_radius=6,
                        tooltip=f"Pengambilan Pabrik: {rp(pabrik_value)}",
                    )
                ],
            ),
            fc.BarChartGroup(
                x=2,
                rods=[
                    fc.BarChartRod(
                        from_y=0,
                        to_y=balaraja_value,
                        width=28,
                        color=ft.Colors.AMBER_400,
                        border_radius=6,
                        tooltip=(
                            f"Pengambilan Balaraja: {rp(balaraja_value)}"
                        ),
                    )
                ],
            ),
        ]

        label_color = (
            ft.Colors.GREY_300 if is_dark else ft.Colors.GREY_800
        )
        bottom_labels = [
            fc.ChartAxisLabel(
                value=0,
                label=ft.Text(
                    "Mobil" if mobile else "Operasional Mobil",
                    size=11,
                    weight=ft.FontWeight.W_500,
                    color=label_color,
                ),
            ),
            fc.ChartAxisLabel(
                value=1,
                label=ft.Text(
                    "Pabrik" if mobile else "Pengambilan Pabrik",
                    size=11,
                    weight=ft.FontWeight.W_500,
                    color=label_color,
                ),
            ),
            fc.ChartAxisLabel(
                value=2,
                label=ft.Text(
                    "Balaraja" if mobile else "Pengambilan Balaraja",
                    size=11,
                    weight=ft.FontWeight.W_500,
                    color=label_color,
                ),
            ),
        ]

        chart = fc.BarChart(
            groups=groups,
            bottom_axis=fc.ChartAxis(
                labels=bottom_labels,
                show_labels=True,
                label_size=32,
            ),
            max_y=maximum_value * 1.25,
            interactive=True,
            height=260,
            width=560 if mobile else None,
            expand=not mobile,
        )

        legend = ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=12,
                            height=12,
                            bgcolor=ft.Colors.RED_400,
                            border_radius=3,
                        ),
                        ft.Text("Operasional Mobil", size=12),
                    ],
                    spacing=6,
                ),
                ft.Row(
                    [
                        ft.Container(
                            width=12,
                            height=12,
                            bgcolor=ft.Colors.INDIGO_400,
                            border_radius=3,
                        ),
                        ft.Text("Pengambilan Pabrik", size=12),
                    ],
                    spacing=6,
                ),
                ft.Row(
                    [
                        ft.Container(
                            width=12,
                            height=12,
                            bgcolor=ft.Colors.AMBER_400,
                            border_radius=3,
                        ),
                        ft.Text("Pengambilan Balaraja", size=12),
                    ],
                    spacing=6,
                ),
            ],
            spacing=16,
            run_spacing=8,
            wrap=True,
        )

        chart_controls = []
        if mobile:
            chart_controls.append(
                ft.Text(
                    "Geser grafik ke samping untuk melihat seluruh bagian.",
                    size=11,
                    color=ft.Colors.GREY_500,
                )
            )
        chart_controls.append(
            ft.Row([chart], scroll=ft.ScrollMode.AUTO)
            if mobile
            else chart
        )

        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.BAR_CHART,
                            size=18,
                            color=ft.Colors.INDIGO_700,
                        ),
                        ft.Text(
                            "Grafik Komparasi Pengeluaran Bulanan",
                            size=15,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=4),
                legend,
                ft.Container(height=8),
                *chart_controls,
            ],
            spacing=6,
        )

    def refresh_rekap():
        month = filter_state["bulan"]
        year = filter_state["tahun"]
        cabang_id = filter_state["cabang_id"]
        month_name = MONTH[month]

        try:
            kenek_items = get_pengeluaran_supir_kenek(
                cabang_id=cabang_id,
                bulan=month,
                tahun=year,
                sort_order="desc",
            )
        except Exception:
            kenek_items = []
        kenek_sum = sum(
            (item["nominal"] for item in kenek_items),
            Decimal(0),
        )
        kenek_count = len(kenek_items)

        try:
            pabrik_items = get_pengambilan_pabrik(
                cabang_id=cabang_id,
                bulan=month,
                tahun=year,
                sort_order="desc",
            )
        except Exception:
            pabrik_items = []
        pabrik_sum = sum(
            (item["nominal"] for item in pabrik_items),
            Decimal(0),
        )
        pabrik_count = len(pabrik_items)

        try:
            balaraja_items = get_pengambilan_balaraja(
                cabang_id=cabang_id,
                bulan=month,
                tahun=year,
                sort_order="desc",
            )
        except Exception:
            balaraja_items = []
        balaraja_sum = sum(
            (item["nominal"] for item in balaraja_items),
            Decimal(0),
        )
        balaraja_count = len(balaraja_items)

        grand_total = kenek_sum + pabrik_sum + balaraja_sum
        total_transactions = kenek_count + pabrik_count + balaraja_count

        metric_kenek_card.content = metric_card(
            page,
            f"Operasional Mobil ({month_name})",
            rp(kenek_sum),
            light_color=ft.Colors.RED_50,
            light_text_color=ft.Colors.RED_900,
            dark_color=ft.Colors.RED_900,
            dark_text_color=ft.Colors.RED_100,
        )
        metric_pabrik_card.content = metric_card(
            page,
            f"Pengambilan Pabrik ({month_name})",
            rp(pabrik_sum),
            light_color=ft.Colors.INDIGO_50,
            light_text_color=ft.Colors.INDIGO_900,
            dark_color=ft.Colors.INDIGO_900,
            dark_text_color=ft.Colors.INDIGO_100,
        )
        metric_balaraja_card.content = metric_card(
            page,
            f"Pengambilan Balaraja ({month_name})",
            rp(balaraja_sum),
            light_color=ft.Colors.AMBER_50,
            light_text_color=ft.Colors.AMBER_900,
            dark_color=ft.Colors.AMBER_900,
            dark_text_color=ft.Colors.AMBER_100,
        )
        metric_grand_card.content = metric_card(
            page,
            "Grand Total Pengeluaran",
            rp(grand_total),
            light_color=ft.Colors.BLUE_50,
            light_text_color=ft.Colors.BLUE_900,
            dark_color=ft.Colors.BLUE_900,
            dark_text_color=ft.Colors.BLUE_100,
        )

        kenek_percentage = (
            kenek_sum / grand_total * 100
            if grand_total > 0
            else Decimal(0)
        )
        pabrik_percentage = (
            pabrik_sum / grand_total * 100
            if grand_total > 0
            else Decimal(0)
        )
        balaraja_percentage = (
            balaraja_sum / grand_total * 100
            if grand_total > 0
            else Decimal(0)
        )

        chart_container.content = ft.Container(
            content=build_comparison_chart(
                kenek_sum,
                pabrik_sum,
                balaraja_sum,
            ),
            bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
            border=ft.Border.all(
                0.5,
                ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
            ),
            border_radius=10,
            padding=card_padding,
        )

        breakdown_rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.Container(
                                    width=10,
                                    height=10,
                                    bgcolor=ft.Colors.RED_500,
                                    border_radius=2,
                                ),
                                ft.Text(
                                    "Operasional Mobil (Supir & Kenek)",
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=8,
                        )
                    ),
                    ft.DataCell(ft.Text(f"{kenek_count} Perjalanan")),
                    ft.DataCell(
                        ft.Text(rp(kenek_sum), weight=ft.FontWeight.W_600)
                    ),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.ProgressBar(
                                    value=float(kenek_percentage) / 100.0,
                                    color=ft.Colors.RED_500,
                                    width=100,
                                ),
                                ft.Text(
                                    f"{kenek_percentage:.1f}%",
                                    size=12,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=8,
                        )
                    ),
                ]
            ),
            ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.Container(
                                    width=10,
                                    height=10,
                                    bgcolor=ft.Colors.INDIGO_500,
                                    border_radius=2,
                                ),
                                ft.Text(
                                    "Pengambilan Kas Pabrik",
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=8,
                        )
                    ),
                    ft.DataCell(ft.Text(f"{pabrik_count} Transaksi")),
                    ft.DataCell(
                        ft.Text(rp(pabrik_sum), weight=ft.FontWeight.W_600)
                    ),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.ProgressBar(
                                    value=float(pabrik_percentage) / 100.0,
                                    color=ft.Colors.INDIGO_500,
                                    width=100,
                                ),
                                ft.Text(
                                    f"{pabrik_percentage:.1f}%",
                                    size=12,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=8,
                        )
                    ),
                ]
            ),
            ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.Container(
                                    width=10,
                                    height=10,
                                    bgcolor=ft.Colors.AMBER_600,
                                    border_radius=2,
                                ),
                                ft.Text(
                                    "Pengambilan Kas Balaraja",
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=8,
                        )
                    ),
                    ft.DataCell(ft.Text(f"{balaraja_count} Transaksi")),
                    ft.DataCell(
                        ft.Text(
                            rp(balaraja_sum),
                            weight=ft.FontWeight.W_600,
                        )
                    ),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.ProgressBar(
                                    value=float(balaraja_percentage) / 100.0,
                                    color=ft.Colors.AMBER_600,
                                    width=100,
                                ),
                                ft.Text(
                                    f"{balaraja_percentage:.1f}%",
                                    size=12,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            spacing=8,
                        )
                    ),
                ]
            ),
            ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Text(
                            "TOTAL KESELURUHAN",
                            weight=ft.FontWeight.BOLD,
                            color=(
                                ft.Colors.BLUE_300
                                if is_dark
                                else ft.Colors.BLUE_700
                            ),
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            f"{total_transactions} Transaksi",
                            weight=ft.FontWeight.BOLD,
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            rp(grand_total),
                            weight=ft.FontWeight.BOLD,
                            color=(
                                ft.Colors.BLUE_300
                                if is_dark
                                else ft.Colors.BLUE_700
                            ),
                        )
                    ),
                    ft.DataCell(
                        ft.Text("100.0%", weight=ft.FontWeight.BOLD)
                    ),
                ]
            ),
        ]

        breakdown_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Modul Rekapitulasi")),
                ft.DataColumn(ft.Text("Volume / Transaksi")),
                ft.DataColumn(ft.Text("Total Biaya (Rp)")),
                ft.DataColumn(ft.Text("Porsi (%)")),
            ],
            rows=breakdown_rows,
            border=ft.Border.all(
                0.5,
                ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200,
            ),
            border_radius=10,
            heading_row_color=(
                ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100
            ),
            show_bottom_border=True,
        )

        breakdown_table_container.content = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.PIE_CHART_OUTLINE,
                                size=18,
                                color=ft.Colors.INDIGO_700,
                            ),
                            ft.Text(
                                "Tabel Proporsi Pengeluaran Bulanan",
                                size=15,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=4),
                    table_with_horizontal_scroll(breakdown_table),
                ],
                spacing=6,
            ),
            bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
            border=ft.Border.all(
                0.5,
                ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300,
            ),
            border_radius=10,
            padding=card_padding,
        )

        # Rincian operasional mobil
        if not kenek_items:
            detail_kenek_container.content = empty_detail(
                "Tidak ada catatan operasional mobil pada bulan ini."
            )
        else:
            rows = []
            for item in kenek_items:
                tanggal = (
                    item["tanggal"].strftime("%d-%m-%Y")
                    if hasattr(item["tanggal"], "strftime")
                    else str(item["tanggal"])
                )
                cells = [ft.DataCell(ft.Text(tanggal))]
                if is_pusat:
                    cells.append(
                        ft.DataCell(
                            ft.Text(item.get("nama_cabang", "-"))
                        )
                    )
                cells.extend(
                    [
                        ft.DataCell(
                            ft.Text(
                                item.get("supir_nama") or "-",
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(item.get("kenek_nama") or "-")
                        ),
                        ft.DataCell(
                            ft.Text(item.get("keterangan") or "-")
                        ),
                        ft.DataCell(
                            ft.Text(
                                rp(item["nominal"]),
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.RED_600,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                item.get("username") or "-",
                                color=ft.Colors.GREY_500,
                            )
                        ),
                    ]
                )
                rows.append(ft.DataRow(cells=cells))

            columns = [ft.DataColumn(ft.Text("Tanggal"))]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend(
                [
                    ft.DataColumn(ft.Text("Supir")),
                    ft.DataColumn(ft.Text("Kenek")),
                    ft.DataColumn(ft.Text("Keterangan")),
                    ft.DataColumn(ft.Text("Uang Jalan")),
                    ft.DataColumn(ft.Text("Diinput Oleh")),
                ]
            )

            data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                border=ft.Border.all(
                    0.5,
                    ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200,
                ),
                border_radius=8,
                heading_row_color=(
                    ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100
                ),
            )
            detail_kenek_container.content = table_with_horizontal_scroll(
                data_table
            )

        # Rincian pengambilan pabrik
        if not pabrik_items:
            detail_pabrik_container.content = empty_detail(
                "Tidak ada data pengambilan pabrik pada bulan ini."
            )
        else:
            rows = []
            for item in pabrik_items:
                tanggal = (
                    item["tanggal"].strftime("%d-%m-%Y")
                    if hasattr(item["tanggal"], "strftime")
                    else str(item["tanggal"])
                )
                cells = [ft.DataCell(ft.Text(tanggal))]
                if is_pusat:
                    cells.append(
                        ft.DataCell(
                            ft.Text(item.get("nama_cabang", "-"))
                        )
                    )
                cells.extend(
                    [
                        ft.DataCell(
                            ft.Text(
                                item.get("keterangan") or "-",
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                rp(item["nominal"]),
                                weight=ft.FontWeight.W_600,
                                color=(
                                    ft.Colors.INDIGO_400
                                    if is_dark
                                    else ft.Colors.INDIGO_700
                                ),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                item.get("username") or "-",
                                color=ft.Colors.GREY_500,
                            )
                        ),
                    ]
                )
                rows.append(ft.DataRow(cells=cells))

            columns = [ft.DataColumn(ft.Text("Tanggal"))]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend(
                [
                    ft.DataColumn(ft.Text("Keterangan / Rincian")),
                    ft.DataColumn(ft.Text("Nominal Kas")),
                    ft.DataColumn(ft.Text("Diinput Oleh")),
                ]
            )

            data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                border=ft.Border.all(
                    0.5,
                    ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200,
                ),
                border_radius=8,
                heading_row_color=(
                    ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100
                ),
            )
            detail_pabrik_container.content = table_with_horizontal_scroll(
                data_table
            )

        # Rincian pengambilan Balaraja
        if not balaraja_items:
            detail_balaraja_container.content = empty_detail(
                "Tidak ada data pengambilan Balaraja pada bulan ini."
            )
        else:
            rows = []
            for item in balaraja_items:
                tanggal = (
                    item["tanggal"].strftime("%d-%m-%Y")
                    if hasattr(item["tanggal"], "strftime")
                    else str(item["tanggal"])
                )
                cells = [ft.DataCell(ft.Text(tanggal))]
                if is_pusat:
                    cells.append(
                        ft.DataCell(
                            ft.Text(item.get("nama_cabang", "-"))
                        )
                    )
                cells.extend(
                    [
                        ft.DataCell(
                            ft.Text(
                                item.get("keterangan") or "-",
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                rp(item["nominal"]),
                                weight=ft.FontWeight.W_600,
                                color=(
                                    ft.Colors.AMBER_400
                                    if is_dark
                                    else ft.Colors.AMBER_700
                                ),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                item.get("username") or "-",
                                color=ft.Colors.GREY_500,
                            )
                        ),
                    ]
                )
                rows.append(ft.DataRow(cells=cells))

            columns = [ft.DataColumn(ft.Text("Tanggal"))]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend(
                [
                    ft.DataColumn(ft.Text("Keterangan / Rincian")),
                    ft.DataColumn(ft.Text("Nominal Kas")),
                    ft.DataColumn(ft.Text("Diinput Oleh")),
                ]
            )

            data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                border=ft.Border.all(
                    0.5,
                    ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200,
                ),
                border_radius=8,
                heading_row_color=(
                    ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100
                ),
            )
            detail_balaraja_container.content = table_with_horizontal_scroll(
                data_table
            )

        if page.views:
            page.update()

    # ---------------------------------------------------------------------
    # Ekspor PDF
    # ---------------------------------------------------------------------
    export_picker = ft.FilePicker()
    if export_picker not in page.services:
        page.services.append(export_picker)

    async def export_pdf(e):
        del e
        month = filter_state["bulan"]
        year = filter_state["tahun"]
        cabang_id = filter_state["cabang_id"]
        month_name = MONTH[month]

        try:
            kenek_items = get_pengeluaran_supir_kenek(
                cabang_id=cabang_id,
                bulan=month,
                tahun=year,
                sort_order="desc",
            )
            pabrik_items = get_pengambilan_pabrik(
                cabang_id=cabang_id,
                bulan=month,
                tahun=year,
                sort_order="desc",
            )
            balaraja_items = get_pengambilan_balaraja(
                cabang_id=cabang_id,
                bulan=month,
                tahun=year,
                sort_order="desc",
            )
        except Exception:
            kenek_items = []
            pabrik_items = []
            balaraja_items = []

        if not kenek_items and not pabrik_items and not balaraja_items:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(
                        "Tidak ada data rekap bulanan pada periode ini "
                        "untuk diexport."
                    ),
                    bgcolor=ft.Colors.RED_400,
                )
            )
            return

        kenek_sum = sum(
            (item["nominal"] for item in kenek_items),
            Decimal(0),
        )
        pabrik_sum = sum(
            (item["nominal"] for item in pabrik_items),
            Decimal(0),
        )
        balaraja_sum = sum(
            (item["nominal"] for item in balaraja_items),
            Decimal(0),
        )
        grand_total = kenek_sum + pabrik_sum + balaraja_sum

        rekap_data = {
            "kenek": {"items": kenek_items, "total": kenek_sum},
            "pabrik": {"items": pabrik_items, "total": pabrik_sum},
            "balaraja": {
                "items": balaraja_items,
                "total": balaraja_sum,
            },
            "grand_total": grand_total,
        }

        cabang_name = "Semua Cabang"
        if filter_state["cabang_id"]:
            cabang_name = next(
                (
                    cabang[1]
                    for cabang in cabang_list
                    if cabang[0] == filter_state["cabang_id"]
                ),
                f"Cabang {filter_state['cabang_id']}",
            )
        elif not is_pusat:
            cabang_name = actor.get("nama_cabang", "Cabang")

        filter_info = {
            "periode": f"{month_name} {year}",
            "cabang": cabang_name,
            "extra": f"Grand Total: {rp(grand_total)}",
        }

        default_file_name = (
            f"Rekap_Bulanan_{year}_{month:02d}_"
            f"{cabang_name.replace(' ', '_')}.pdf"
        )
        try:
            if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
                pdf_bytes = generate_rekap_bulanan_pdf(
                    rekap_data,
                    filter_info,
                    is_pusat=is_pusat,
                    output_path=None,
                )
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Rekap Bulanan PDF",
                    file_name=default_file_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Rekap Bulanan PDF",
                    file_name=default_file_name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if save_path and not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                if save_path:
                    generate_rekap_bulanan_pdf(
                        rekap_data,
                        filter_info,
                        is_pusat=is_pusat,
                        output_path=save_path,
                    )

            if save_path:
                log_activity(
                    actor.get("id"),
                    actor.get("username", "user"),
                    "CREATE",
                    "export_pdf",
                    filter_state.get("cabang_id") or 0,
                    f"Export PDF Rekap Bulanan ({month_name} {year})",
                    filter_state.get("cabang_id"),
                )
                page.show_dialog(
                    ft.SnackBar(
                        ft.Text(f"PDF berhasil disimpan: {save_path}"),
                        bgcolor=ft.Colors.GREEN_700,
                    )
                )
        except Exception as error:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal export PDF: {error}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    refresh_rekap()

    # ---------------------------------------------------------------------
    # Tabs
    # ---------------------------------------------------------------------
    tab_views = [
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=12),
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=chart_container,
                                col={"xs": 12, "lg": 5},
                            ),
                            ft.Container(
                                content=breakdown_table_container,
                                col={"xs": 12, "lg": 7},
                            ),
                        ],
                        spacing=16,
                        run_spacing=16,
                    ),
                ]
            ),
            padding=ft.Padding.only(top=8),
        ),
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=12),
                    detail_kenek_container,
                ]
            ),
            padding=ft.Padding.only(top=8),
        ),
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=12),
                    detail_pabrik_container,
                ]
            ),
            padding=ft.Padding.only(top=8),
        ),
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=12),
                    detail_balaraja_container,
                ]
            ),
            padding=ft.Padding.only(top=8),
        ),
    ]

    active_tab_container = ft.Container(content=tab_views[0])

    def on_tab_change(e):
        selected_index = int(e.data)
        active_tab_container.content = tab_views[selected_index]
        active_tab_container.update()

    tabs = ft.Tabs(
        length=4,
        selected_index=0,
        animation_duration=200,
        on_change=on_tab_change,
        content=ft.TabBar(
            tabs=[
                ft.Tab(
                    label=(
                        "Ringkasan"
                        if mobile
                        else "Ringkasan & Komposisi"
                    ),
                    icon=ft.Icons.ANALYTICS,
                ),
                ft.Tab(
                    label=(
                        "Operasional"
                        if mobile
                        else "Rincian Operasional Mobil"
                    ),
                    icon=ft.Icons.LOCAL_SHIPPING,
                ),
                ft.Tab(
                    label=(
                        "Pabrik"
                        if mobile
                        else "Rincian Pengambilan Pabrik"
                    ),
                    icon=ft.Icons.FACTORY,
                ),
                ft.Tab(
                    label=(
                        "Balaraja"
                        if mobile
                        else "Rincian Pengambilan Balaraja"
                    ),
                    icon=ft.Icons.WAREHOUSE,
                ),
            ]
        ),
    )

    header_title = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Rekap Bulanan Gabungan",
                    size=22,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    "Konsolidasi bulanan operasional mobil (supir & kenek), "
                    "pengambilan kas pabrik, dan pengambilan kas Balaraja.",
                    size=13,
                    color=ft.Colors.GREY_500,
                ),
            ],
            spacing=2,
        ),
        col={"xs": 12, "md": 8},
    )

    header_actions = ft.Container(
        content=ft.Row(
            [
                ft.OutlinedButton(
                    "Export PDF" if mobile else "Export ke PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=export_pdf,
                ),
                ft.IconButton(
                    ft.Icons.REFRESH,
                    tooltip="Segarkan Rekap",
                    on_click=lambda e: refresh_rekap(),
                ),
            ],
            wrap=True,
            spacing=8,
            run_spacing=8,
            alignment=(
                ft.MainAxisAlignment.START
                if mobile
                else ft.MainAxisAlignment.END
            ),
        ),
        col={"xs": 12, "md": 4},
    )

    return ft.Column(
        [
            ft.ResponsiveRow(
                [header_title, header_actions],
                spacing=8,
                run_spacing=8,
            ),
            ft.Container(height=8),
            filter_card,
            ft.Container(height=12),
            ft.ResponsiveRow(
                [
                    metric_kenek_card,
                    metric_pabrik_card,
                    metric_balaraja_card,
                    metric_grand_card,
                ],
                spacing=12,
                run_spacing=12,
            ),
            ft.Container(height=12),
            tabs,
            active_tab_container,
            ft.Container(height=24),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
