import flet as ft
from database.db import query_one, query_all
from components.stat_card import stat_card

def build_dashboard_view() -> ft.Container:
    summary = query_one(
        """
        SELECT 
            COALESCE(SUM(total_amount), 0) AS pendapatan,
            COALESCE(SUM(hpp_amount + beban_amount), 0) AS modal_beban,
            COALESCE(SUM(total_amount - beban_amount), 0) AS laba_bersih
        FROM invoices
        """
    )
    pendapatan = summary["pendapatan"] if summary else 0
    modal_beban = summary["modal_beban"] if summary else 0
    laba_bersih = summary["laba_bersih"] if summary else 0

    activities = query_all("SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 5")

    activity_rows = []
    for a in activities:
        color = "#10B981" if a["direction"] == "masuk" else "#EF4444"
        sign = "+" if a["direction"] == "masuk" else "-"
        activity_rows.append(
            ft.Row(
                [
                    ft.Text(a["title"], size=13, color="black"),
                    ft.Text(
                        f"{sign} Rp {a['amount']:,.0f}".replace(",", "."),
                        size=13, color=color, weight=ft.FontWeight.W_500,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )
        )

    if not activity_rows:
        activity_rows.append(ft.Text("Belum ada Aktivitas", size=13, color="#94A3B8"))

    return ft.Container(
        padding=24,
        expand=True,
        content=ft.Column(
            [
                ft.Container(
                    padding=28,
                    border_radius=18,
                    gradient=ft.LinearGradient(colors=["#1D4ED8", "#2563EB"]),
                    content=ft.Column(
                        [
                            ft.Text("Selamat Datang Kembali!", size=22, weight=ft.FontWeight.BOLD, color="white"),
                            ft.Text("Kelola keuangan toko Anda dengan mudah.", size=14, color="#DBEAFE"),
                        ],
                    spacing=16,
                    )
                ),
                ft.Container(height=24),
                ft.Row(
                    [
                        stat_card(ft.Icons.TRENDING_UP, "Pendapatan", pendapatan, caption="Total omzet"),
                        stat_card(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, "Modal & Beban", modal_beban, caption="HPP dan biaya operasional"),
                        stat_card(ft.Icons.SAVINGS_OUTLINED, "Laba Bersih", laba_bersih, caption="Keuntungan bersih"),
                    ],
                    spacing=16,
                ),
                ft.Container(height=20),
                ft.Container(
                    bgcolor="white",
                    border_radius=16,
                    border=ft.Border.all(1, "#E2E8F0"),
                    padding=18,
                    content=ft.Column(
                        [
                            ft.Text("Aktivitas Terakhir", size=15, weight=ft.FontWeight.BOLD, color="black"),
                            ft.Container(height=8),
                            *activity_rows,
                        ],
                        spacing=10,
                    )
                )
            ],
            scroll=ft.ScrollMode.AUTO,
        )
    )