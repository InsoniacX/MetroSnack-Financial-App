import flet as ft
import flet_charts as fc
from config import MONTH
from components.appbar import build_appbar, nav_rail
from components.metric_card import metric_card
from utils.formatting import rp
from db.folder_repo import get_dashboard_summary, get_monthly_trend
from state import app_state


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
                fc.BarChartRod(from_y=0, to_y=omzet_f, width=14, color=ft.Colors.BLUE_400,
                                border_radius=4, tooltip=f"Omset: {rp(omzet_f)}"),
                fc.BarChartRod(from_y=0, to_y=laba_f, width=14, color=ft.Colors.GREEN_400,
                                border_radius=4, tooltip=f"Laba bersih: {rp(laba_f)}"),
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


def build_view(page: ft.Page):
    cabang_id = app_state.user.get("cabang_id")
    is_pusat = cabang_id is None
    scope_label = "Semua Cabang" if is_pusat else app_state.user.get("nama_cabang", "-")

    try:
        summary = get_dashboard_summary(cabang_id)
    except Exception:
        summary = {"omzet": 0, "barang": 0, "laba_bersih": 0}

    try:
        trend_data = get_monthly_trend(cabang_id, limit_months=6)
    except Exception:
        trend_data = []

    body = ft.Column([
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
            metric_card("Laba bersih", rp(summary["laba_bersih"]), color=ft.Colors.GREEN_50, text_color=ft.Colors.GREEN_900),
        ], spacing=12),
        ft.Container(height=24),
        ft.Text("Tren Omset & Laba Bersih (6 Bulan Terakhir)", size=16, weight=ft.FontWeight.W_500),
        ft.Container(height=8),
        ft.Container(
            content=build_chart(trend_data),
            bgcolor=ft.Colors.WHITE, border=ft.Border.all(0.5, ft.Colors.GREY_300),
            border_radius=12, padding=16,
        ),
        ft.Container(height=24),
        ft.ElevatedButton("Lihat daftar invoice", icon=ft.Icons.ARROW_FORWARD, on_click=lambda e: page.go("/invoices")),
    ], spacing=6, expand=True, scroll=ft.ScrollMode.AUTO)

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