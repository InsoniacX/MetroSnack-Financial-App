import flet as ft
from database.db import query_all, execute
from utils.format import format_rupiah, format_month_year
from datetime import datetime


def build_invoice_list_view(page: ft.Page, on_open_folder) -> ft.Container:
    folders_column = ft.Column(spacing=16)

    def load_folders():
        rows = query_all(
            "SELECT * FROM v_month_folder_summary ORDER BY year DESC, month DESC"
        )
        folders_column.controls.clear()

        if not rows:
            folders_column.controls.append(
                ft.Text("Belum ada folder bulan. Klik 'Buat Folder Bulan Baru' untuk memulai.",
                         size=13, color="#94A3B8")
            )
        else:
            card_row = []
            for r in rows:
                card = ft.Container(
                    bgcolor="white",
                    border=ft.Border.all(1, "#E2E8F0"),
                    border_radius=16,
                    padding=18,
                    width=340,
                    content=ft.Column(
                        [
                            ft.Text(format_month_year(r["month"], r["year"]), size=15,
                                     weight=ft.FontWeight.BOLD, color="black"),
                            ft.Text(f"Status: {r['status']}", size=11, color="#94A3B8"),
                            ft.Container(height=10),
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text("TOTAL INVOICE", size=10, color="#94A3B8"),
                                            ft.Text(f"{r['total_invoice']} Lembar", size=14, weight=ft.FontWeight.BOLD, color="black"),
                                        ],
                                        spacing=2,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text("LABA BERSIH", size=10, color="#94A3B8"),
                                            ft.Text(format_rupiah(r["laba_bersih"]), size=14, weight=ft.FontWeight.BOLD, color="black"),
                                        ],
                                        spacing=2,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(height=12),
                            ft.ElevatedButton(
                                "Buka Folder",
                                bgcolor="#2563EB",
                                color="white",
                                width=300,
                                on_click=lambda e, year=r["year"], month=r["month"]: on_open_folder(year, month),
                            ),
                        ],
                        spacing=4,
                    ),
                )
                card_row.append(card)
            folders_column.controls.append(ft.Row(card_row, wrap=True, spacing=16, run_spacing=16))

        page.update()

    def create_folder(e):
        now = datetime.now()
        try:
            execute(
                "INSERT INTO month_folders (year, month) VALUES (?, ?)",
                (now.year, now.month),
            )
        except Exception as ex:
            print("Gagal buat folder (mungkin sudah ada):", ex)
        load_folders()

    load_folders()

    return ft.Container(
        padding=24,
        expand=True,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Daftar Invoice", size=22, weight=ft.FontWeight.BOLD, color="black"),
                                ft.Text("Kelola dokumen keuangan bulanan Anda.", size=13, color="#64748B"),
                            ],
                            spacing=2,
                        ),
                        ft.ElevatedButton(
                            "Buat Folder Bulan Baru",
                            bgcolor="#2563EB",
                            color="white",
                            on_click=create_folder,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=20),
                folders_column,
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
    )