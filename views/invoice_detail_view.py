import flet as ft
from database.db import query_all, query_one, execute
from utils.format import format_rupiah, format_month_year
from components.stat_box import stat_box


def build_invoice_detail_view(page: ft.Page, year: int, month: int, on_back) -> ft.Container:
    invoice_table_area = ft.Column(spacing=10)
    stat_row = ft.Row(spacing=16)

    def get_folder():
        return query_one(
            "SELECT * FROM v_month_folder_summary WHERE year = ? AND month = ?",
            (year, month),
        )

    def refresh():
        folder = get_folder()
        invoices = query_all(
            """
            SELECT i.*, s.name AS supplier_name
            FROM invoices i
            LEFT JOIN suppliers s ON s.id = i.supplier_id
            WHERE i.month_folder_id = ?
            ORDER BY i.invoice_date ASC
            """,
            (folder["month_folder_id"],) if folder else (0,),
        )

        stat_row.controls = [
            stat_box("Total Omzet", folder["total_omzet"] if folder else 0),
            stat_box("Total HPP", folder["total_hpp"] if folder else 0),
            stat_box("Laba Kotor", folder["laba_kotor"] if folder else 0),
            stat_box("Total Beban", folder["total_beban"] if folder else 0),
        ]

        rows = [
            ft.Row(
                [
                    ft.Text("Nota", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=120),
                    ft.Text("Tanggal", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=100),
                    ft.Text("Supplier", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=160),
                    ft.Text("Total", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("HPP", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("Laba", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("Beban", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                ],
            ),
            ft.Divider(color="#F1F5F9"),
        ]

        if not invoices:
            rows.append(ft.Text("Belum ada invoice di bulan ini.", size=13, color="#94A3B8"))
        else:
            for inv in invoices:
                rows.append(
                    ft.Row(
                        [
                            ft.Text(inv["nota_number"], size=13, color="#2563EB", width=120),
                            ft.Text(inv["invoice_date"], size=13, color="black", width=100),
                            ft.Text(inv["supplier_name"] or "-", size=13, color="black", width=160),
                            ft.Text(f"{inv['total_amount']:,.0f}".replace(",", "."), size=13, color="black", width=110),
                            ft.Text(f"{inv['hpp_amount']:,.0f}".replace(",", "."), size=13, color="#94A3B8", width=110),
                            ft.Text(f"{inv['laba_amount']:,.0f}".replace(",", "."), size=13, color="#10B981", width=110),
                            ft.Text(f"{inv['beban_amount']:,.0f}".replace(",", "."), size=13, color="#94A3B8", width=110),
                        ],
                    )
                )

        invoice_table_area.controls = rows
        page.update()

    nota_field = ft.TextField(label="Nomor Nota", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"))
    tanggal_field = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"), value=f"{year}-{month:02d}-01")
    total_field = ft.TextField(label="Total (Rp)", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"), value="0")
    hpp_field = ft.TextField(label="HPP (Rp)", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"), value="0")
    beban_field = ft.TextField(label="Beban (Rp)", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"), value="0")
    form_error = ft.Text("", color="#EF4444", size=12)

    def save_invoice(e):
        try:
            total = int(total_field.value or 0)
            hpp = int(hpp_field.value or 0)
            beban = int(beban_field.value or 0)
            laba = total - hpp - beban

            if not nota_field.value:
                form_error.value = "Nomor Nota Wajib diisi."
                page.update()
                return

            folder = get_folder()
            if not folder:
                execute("INSERT INTO month_folders (year, month) VALUES (?, ?)", (year, month))
                folder = get_folder()

            execute(
                """
                INSERT INTO invoices
                    (month_folder_id, nota_number, invoice_data, total_amount, hpp_amount, laba_amount, beban_amount)
                values(?, ?, ?, ?, ?, ?, ?)
                """,
                (folder["month_folder_id"], nota_field.value, tanggal_field.value, total, hpp, laba, beban),
            )

            form_error.value = ""
            close_dialog()
            nota_field.value = ""
            total_field.value = "0"
            hpp_field.value = "0"
            beban_field.value = "0"
            refresh()

        except ValueError:
            form_error.value = "Total, HPP, dan Beban harus berupa angka."
            page.update()

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor="white",
        title=ft.Text("Input Invoice Manual", color="black"),
        content=ft.Column(
            [nota_field, tanggal_field, total_field, hpp_field, beban_field, form_error],
            spacing=10,
            tight=True,
        ),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: close_dialog()),
            ft.ElevatedButton("Simpan", bgcolor="#2563EB", color="white", on_click=save_invoice),
        ],
    )

    def open_dialog(e):
        page.show_dialog(dialog)

    def close_dialog():
        page.pop_dialog()

    refresh()

    return ft.Container(
        padding=24,
        expand=True,
        content=ft.Column(
            [
                ft.TextButton(
                    content=ft.Row(
                        [
                        ft.Icon(ft.Icons.ARROW_BACK, size=14, color="#94A3B8"),
                        ft.Text("Kembali ke Daftar Bulan", size=12, color="#94A3B8")], spacing=6,),
                    on_click=lambda e: on_back(),
                ),
                ft.Row(
                    [
                        ft.Text(f"Invoice - {format_month_year(month, year)}", size=22, weight=ft.FontWeight.BOLD, color="black"),
                        ft.ElevatedButton("+ Input Manual", bgcolor="#2563EB", color="white", on_click=open_dialog),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=16),
                stat_row,
                ft.Container(height=20),
                ft.Container( bgcolor="white", border=ft.Border.all(1, "#E2E8F0"), border_radius=16, padding=18, content=ft.Column(
                        [
                            ft.Text("Daftar Invoice Terinput", size=14, weight=ft.FontWeight.BOLD, color="black"),
                            ft.Container(height=10),
                            invoice_table_area,
                        ],
                        spacing=10,
                    ),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
    )