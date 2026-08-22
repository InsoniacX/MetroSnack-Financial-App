import flet as ft
import flet_charts as fc
from config import MONTH
from components.appbar import build_appbar, nav_rail
from components.metric_card import metric_card
from utils.formatting import rp
from utils.hutang_style import hutang_style
from db.folder_repo import get_dashboard_summary, get_monthly_trend, get_cabang_breakdown
from state import app_state

PIE_COLORS = [
    ft.Colors.BLUE_400, ft.Colors.GREEN_400, ft.Colors.ORANGE_400, ft.Colors.PURPLE_400,
    ft.Colors.RED_400, ft.Colors.TEAL_400, ft.Colors.AMBER_400, ft.Colors.INDIGO_400,
    ft.Colors.PINK_400, ft.Colors.CYAN_400, ft.Colors.LIME_400, ft.Colors.BROWN_400,
]


def build_chart(trend_data):
    if not trend_data:
        return ft.Container(
            content=ft.Text("Belum ada data folder bulan untuk ditampilkan di grafik.", color=ft.Colors.GREY_600),
            padding=24, alignment=ft.Alignment.CENTER, height=200,
        )

    groups = []
    bottom_labels = []
    max_value = 0.0

    for idx, row in enumerate(trend_data):
        fid, nama_folder, bulan, tahun, omzet, laba = row
        omzet_f = float(omzet or 0)
        laba_f = float(laba or 0)
        max_value = max(max_value, omzet_f, laba_f)

        groups.append(fc.BarChartGroup(
            x=idx,
            rods=[
                fc.BarChartRod(from_y=0, to_y=omzet_f, width=14, color=ft.Colors.BLUE_400, border_radius=4, tooltip=f"Omset: {rp(omzet_f)}"),
                fc.BarChartRod(from_y=0, to_y=laba_f, width=14, color=ft.Colors.GREEN_400, border_radius=4, tooltip=f"Laba bersih: {rp(laba_f)}"),
            ],
        ))

        label_singkat = MONTH[bulan][:3]
        bottom_labels.append(fc.ChartAxisLabel(
            value=idx,
            label=ft.Text(f"{label_singkat} {str(tahun)[2:]}", size=10, color=ft.Colors.GREY_700),
        ))

    chart = fc.BarChart(
        groups=groups,
        bottom_axis=fc.ChartAxis(labels=bottom_labels, show_labels=True, label_size=32),
        max_y=max_value * 1.2 if max_value > 0 else 100,
        interactive=True,
        height=260,
        expand=True,
    )

    legend = ft.Row([
        ft.Row([ft.Container(width=10, height=10, bgcolor=ft.Colors.BLUE_400, border_radius=3), ft.Text("Omset", size=12)], spacing=4),
        ft.Row([ft.Container(width=10, height=10, bgcolor=ft.Colors.GREEN_400, border_radius=3), ft.Text("Laba Bersih", size=12)], spacing=4),
    ], spacing=16)

    return ft.Column([legend, ft.Container(height=8), chart])


def build_cabang_pie(cabang_breakdown, field, judul):
    """field: 'omzet' (pemasukan) atau 'barang' (pengeluaran)"""
    items = []
    total = 0.0
    for row in cabang_breakdown:
        cid, nama_cabang, total_omzet, total_barang = row
        v = float(total_omzet if field == "omzet" else total_barang)
        if v > 0:
            items.append((nama_cabang, v))
            total += v

    if total <= 0:
        return ft.Container(
            content=ft.Column([
                ft.Text(judul, size=14, weight=ft.FontWeight.W_500),
                ft.Container(height=8),
                ft.Text("Belum ada data.", color=ft.Colors.GREY_600, size=12),
            ]),
            padding=16, height=260,
        )

    sections = []
    legend_rows = []
    for idx, (nama_cabang, v) in enumerate(items):
        color = PIE_COLORS[idx % len(PIE_COLORS)]
        pct = (v / total) * 100
        sections.append(fc.PieChartSection(
            value=v,
            title=f"{pct:.0f}%",
            color=color,
            radius=55,
            title_style=ft.TextStyle(size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        ))
        legend_rows.append(
            ft.Row([
                ft.Container(width=10, height=10, bgcolor=color, border_radius=3),
                ft.Text(f"{nama_cabang} · {rp(v)}", size=12),
            ], spacing=6)
        )

    pie = fc.PieChart(sections=sections, sections_space=2, center_space_radius=28, height=180)

    return ft.Column([
        ft.Text(judul, size=14, weight=ft.FontWeight.W_500),
        ft.Container(height=8),
        pie,
        ft.Container(height=8),
        ft.Column(legend_rows, spacing=4),
    ])


def build_view(page: ft.Page):
    cabang_id = app_state.user.get("cabang_id")
    is_pusat = cabang_id is None
    scope_label = "Semua Cabang" if is_pusat else app_state.user.get("nama_cabang", "-")

    try:
        summary = get_dashboard_summary(cabang_id)
    except Exception:
        summary = {"omzet": 0, "barang": 0, "laba_bersih": 0, "sisa_hutang": 0}

    try:
        trend_data = get_monthly_trend(cabang_id, limit_months=6)
    except Exception:
        trend_data = []

    pie_section = None
    if is_pusat:
        try:
            cabang_breakdown = get_cabang_breakdown()
        except Exception:
            cabang_breakdown = []
        pie_section = ft.Column([
            ft.Text("Pemasukan & Pengeluaran per Cabang", size=16, weight=ft.FontWeight.W_500),
            ft.Container(height=8),
            ft.ResponsiveRow([
                ft.Container(
                    col={"xs": 12, "md": 6},
                    content=ft.Container(
                        content=build_cabang_pie(cabang_breakdown, "omzet", "Pemasukan (Omset)"),
                        bgcolor=ft.Colors.WHITE, border=ft.Border.all(0.5, ft.Colors.GREY_300),
                        border_radius=12, padding=16,
                    ),
                ),
                ft.Container(
                    col={"xs": 12, "md": 6},
                    content=ft.Container(
                        content=build_cabang_pie(cabang_breakdown, "barang", "Pengeluaran (Masuk Barang)"),
                        bgcolor=ft.Colors.WHITE, border=ft.Border.all(0.5, ft.Colors.GREY_300),
                        border_radius=12, padding=16,
                    ),
                ),
            ], spacing=12, run_spacing=12),
            ft.Container(height=24),
        ])

    # Card Total Hutang -- sekarang pakai data ASLI dari formula Sisa Hutang
    # yang sudah CONFIRMED di backend (dulu placeholder rp(0)).
    hutang_nilai, hutang_bg, hutang_text = hutang_style(summary.get("sisa_hutang", 0))
    hutang_label = "Total Hutang (Semua Toko)" if is_pusat else "Total Hutang Toko Ini"

    body_controls = [
        ft.Text("Selamat datang kembali", size=20, weight=ft.FontWeight.W_500),
        ft.Row([
            ft.Text("Menampilkan data:", size=13, color=ft.Colors.GREY_600),
            ft.Container(
                content=ft.Text(scope_label, size=12, color=ft.Colors.BLUE_900),
                bgcolor=ft.Colors.BLUE_50, padding=ft.Padding.symmetric(vertical=2, horizontal=8), border_radius=6,
            ),
        ], spacing=6),
        ft.Container(height=16),
        ft.Row([
            metric_card("Total omzet", rp(summary["omzet"])),
            metric_card("Total masuk barang", rp(summary["barang"])),
            metric_card(hutang_label, rp(hutang_nilai), color=hutang_bg, text_color=hutang_text),
            metric_card("Laba bersih", rp(summary["laba_bersih"]), color=ft.Colors.GREEN_50, text_color=ft.Colors.GREEN_900),
        ], spacing=12),
        ft.Container(height=24),
    ]

    if pie_section:
        body_controls.append(pie_section)

    body_controls.extend([
        ft.Text("Tren Omset & Laba Bersih (6 Bulan Terakhir)", size=16, weight=ft.FontWeight.W_500),
        ft.Container(height=8),
        ft.Container(
            content=build_chart(trend_data),
            bgcolor=ft.Colors.WHITE, border=ft.Border.all(0.5, ft.Colors.GREY_300),
            border_radius=12, padding=16,
        ),
        ft.Container(height=24),
        ft.ElevatedButton("Lihat daftar invoice", icon=ft.Icons.ARROW_FORWARD, on_click=lambda e: page.go("/invoices")),
    ])

    body = ft.Column(body_controls, spacing=6, expand=True, scroll=ft.ScrollMode.AUTO)

    return ft.View(
        route="/dashboard",
        controls=[
            build_appbar(page, "Dashboard"),
            ft.Row([
                nav_rail(page, 0),
                ft.VerticalDivider(width=1),
                ft.Container(content=body, padding=24, expand=True),
            ], expand=True),
        ],
        padding=0,
    )
