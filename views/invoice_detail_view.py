from utils.pdf_export import export_invoice_pdf
import os
import flet as ft
from database.db import query_all, query_one, execute
from utils.format import format_rupiah, format_month_year
from components.stat_box import stat_box


def build_invoice_detail_view(page: ft.Page, year: int, month: int, on_back, current_user: dict) -> ft.Container:
    invoice_table_area = ft.Column(spacing=10)
    stat_row = ft.Row(spacing=16)
    editing_id = {"value": None}

    def get_folder():
        return query_one(
            "SELECT * FROM v_month_folder_summary WHERE year = ? AND month = ?",
            (year, month),
        )

    # Form Input/Edit
    nota_field = ft.TextField(label="Nomor Nota", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"))
    tanggal_field = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"))
    total_field = ft.TextField(label="Total (Rp)", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"), value="0")
    hpp_field = ft.TextField(label="HPP (Rp)", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"), value="0")
    beban_field = ft.TextField(label="Beban (Rp)", width=400, color="black", border_color="#CBD5E1", label_style=ft.TextStyle(color="#64748B"), value="0")
    form_error = ft.Text("", color="#EF4444", size=12)
    dialog_title = ft.Text("Input Invoice Manual", color="black", size=16, weight=ft.FontWeight.BOLD)

    def reset_form():
        nota_field.value = ""
        tanggal_field.value = f"{year}-{month:02d}-01"
        total_field.value = "0"
        hpp_field.value = "0"
        beban_field.value = "0"
        form_error.value = ""

    def save_invoice(e):
        try:
            total = int(total_field.value or 0)
            hpp = int(hpp_field.value or 0)
            beban = int(beban_field.value or 0)
            laba = total - hpp - beban

            if not nota_field.value:
                form_error.value = "Nomor nota wajib diisi."
                page.update()
                return

            if editing_id["value"] is None:
                # Mode tambah baru
                folder = get_folder()
                if not folder:
                    execute("INSERT INTO month_folders (year, month) VALUES (?, ?)", (year, month))
                    folder = get_folder()

                execute(
                    """
                    INSERT INTO invoices
                        (month_folder_id, nota_number, invoice_date, total_amount, hpp_amount, laba_amount, beban_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (folder["month_folder_id"], nota_field.value, tanggal_field.value, total, hpp, laba, beban),
                )
            else:
                # Mode edit
                execute(
                    """
                    UPDATE invoices
                    SET nota_number = ?, invoice_date = ?, total_amount = ?, hpp_amount = ?, laba_amount = ?, beban_amount = ?
                    WHERE id = ?
                    """,
                    (nota_field.value, tanggal_field.value, total, hpp, laba, beban, editing_id["value"]),
                )

            close_dialog()
            reset_form()
            refresh()

        except ValueError:
            form_error.value = "Total, HPP, dan Beban harus berupa angka."
            page.update()

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor="white",
        title=dialog_title,
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

    def open_add_dialog(e):
        editing_id["value"] = None
        reset_form()
        dialog_title.value = "Input Invoice Manual"
        page.show_dialog(dialog)

    def open_edit_dialog(inv):
        editing_id["value"] = inv["id"]
        nota_field.value = inv["nota_number"]
        tanggal_field.value = inv["invoice_date"]
        total_field.value = str(inv["total_amount"])
        hpp_field.value = str(inv["hpp_amount"])
        beban_field.value = str(inv["beban_amount"])
        form_error.value = ""
        dialog_title.value = f"Edit Invoice - {inv['nota_number']}"
        page.show_dialog(dialog)

    def close_dialog():
        page.pop_dialog()

    delete_target = {"value": None}

    def confirm_delete(e):
        if delete_target["value"] is not None:
            execute("DELETE FROM invoices WHERE id = ?", (delete_target["value"],))
        page.pop_dialog()
        refresh()

    delete_dialog = ft.AlertDialog(
        modal=True,
        bgcolor="white",
        title=ft.Text("Hapus Invoice?", color="black"),
        content=ft.Text("Tindakan ini tidak bisa dibatalkan. Yakin ingin menghapus invoice ini?", color="#64748B"),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: page.pop_dialog()),
            ft.ElevatedButton("Hapus", bgcolor="#EF4444", color="white", on_click=confirm_delete),
        ],
    )

    def open_delete_dialog(inv):
        delete_target["value"] = inv["id"]
        page.show_dialog(delete_dialog)

    def refresh():
        folder = get_folder()
        invoices = query_all(
            "SELECT * FROM invoices WHERE month_folder_id = ? ORDER BY invoice_date ASC",
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
                    ft.Text("Nota", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("Tanggal", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=100),
                    ft.Text("Masuk Barang", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("Masuk Uang", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("Lebih Uang", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("Beban", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=110),
                    ft.Text("Aksi", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8", width=90),
                ],
            ),
            ft.Divider(color="#F1F5F9"),
        ]

        if not invoices:
            rows.append(ft.Text("Belum ada invoice di bulan ini.", size=13, color="#94A3B8"))
        else:
            for inv in invoices:
                inv_dict = dict(inv)
                rows.append(
                    ft.Row(
                        [
                            ft.Text(inv["nota_number"], size=13, color="#2563EB", width=110),
                            ft.Text(inv["invoice_date"], size=13, color="black", width=100),
                            ft.Text(f"{inv['total_amount']:,.0f}".replace(",", "."), size=13, color="black", width=110),
                            ft.Text(f"{inv['hpp_amount']:,.0f}".replace(",", "."), size=13, color="#94A3B8", width=110),
                            ft.Text(f"{inv['laba_amount']:,.0f}".replace(",", "."), size=13, color="#10B981", width=110),
                            ft.Text(f"{inv['beban_amount']:,.0f}".replace(",", "."), size=13, color="#94A3B8", width=110),
                            ft.Row(
                                [
                                    ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_size=16, icon_color="#64748B", on_click=lambda e, d=inv_dict: open_edit_dialog(d)),
                                    *([ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=16, icon_color="#EF4444", on_click=lambda e, d=inv_dict: open_delete_dialog(d))] if current_user["role"] == "superadmin" else []),
                                ],
                                spacing=0,
                                width=90,
                            ),
                        ],
                    )
                )

        invoice_table_area.controls = rows
        page.update()

    refresh()

    def download_pdf(e):
        filepath = export_invoice_pdf(year, month)
        os.startfile(filepath.parent)  # buka folder "exports" di File Explorer (Windows)
        page.open(
            ft.SnackBar(content=ft.Text(f"PDF berhasil dibuat: {filepath.name}"))
        ) if hasattr(page, "open") else None
        page.update()

    return ft.Container(
        padding=24,
        expand=True,
        content=ft.Column(
            [
                ft.TextButton(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.ARROW_BACK, size=14, color="#94A3B8"), ft.Text("Kembali ke Daftar Bulan", size=12, color="#94A3B8")],
                        spacing=6,
                    ),
                    on_click=lambda e: on_back(),
                ),
                ft.Row(
                    [
                        ft.Text(f"Invoice - {format_month_year(month, year)}", size=22, weight=ft.FontWeight.BOLD, color="black"),
                        ft.Row(
                            [
                                ft.OutlinedButton("Download Laporan PDF", on_click=lambda e: download_pdf(e)),
                                ft.ElevatedButton("+ Input Manual", bgcolor="#2563EB", color="white", on_click=open_add_dialog),
                            ],
                            spacing=10,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=16),
                stat_row,
                ft.Container(height=20),
                ft.Container(
                    bgcolor="white",
                    border=ft.Border.all(1, "#E2E8F0"),
                    border_radius=16,
                    padding=18,
                    content=ft.Column(
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