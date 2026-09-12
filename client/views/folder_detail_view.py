import flet as ft
from datetime import date

from components.appbar import is_mobile_layout
from components.file_picker import get_file_picker
from components.navigation import navigate
from utils.formatting import rp
from utils.validation import require_text, parse_date, parse_positive_decimal
from utils.pdf_export import generate_folder_pdf
from db.invoice_repo import get_invoices, create_invoice, update_invoice, delete_invoice
from db.folder_repo import get_folder_header
from db.finance_repo import get_folder_balance
from db.transaksi_repo import get_transaksi
from db.activity_repo import log_activity
from state import app_state


def build_view(page: ft.Page, folder_id: int):
    mobile = is_mobile_layout(page)
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    page_width = getattr(page, "width", None) or 1100
    dialog_content_width = min(520, max(260, page_width - 72))
    small_dialog_width = min(420, max(260, page_width - 72))

    def close_dialog(e=None):
        del e
        page.pop_dialog()
        page.update()

    def refresh():
        if page.views and page.views[-1].controls:
            root_control = page.views[-1].controls[0]
            replacement = build_view(page, folder_id)

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

    actor = app_state.user or {}
    is_pusat = actor.get("cabang_id") is None

    try:
        header = get_folder_header(folder_id)
    except Exception as ex:
        return ft.Column(
            [
                ft.Text(
                    "Folder tidak dapat dimuat.",
                    size=20,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    f"Periksa koneksi lalu coba lagi. Detail: {ex}",
                    size=13,
                    color=ft.Colors.RED_400,
                ),
            ],
            spacing=8,
        )

    if header is None:
        return ft.Column(
            [
                ft.Text(
                    "Folder tidak ditemukan.",
                    size=20,
                    weight=ft.FontWeight.W_500,
                ),
                ft.TextButton(
                    "Kembali ke daftar invoice",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate(page, "/invoices"),
                ),
            ],
            spacing=8,
        )

    _, nama_folder, folder_cabang_id, nama_cabang_folder = header

    if not is_pusat and folder_cabang_id != actor.get("cabang_id"):
        return ft.Column(
            [
                ft.Text(
                    "Akses ditolak",
                    size=20,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.RED_400,
                ),
                ft.Text(
                    "Anda tidak punya akses ke folder cabang lain.",
                    size=14,
                ),
                ft.TextButton(
                    "Kembali ke daftar invoice",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate(page, "/invoices"),
                ),
            ],
            spacing=8,
        )

    try:
        invoices = get_invoices(folder_id)
        keuangan_folder = get_folder_balance(folder_id)
    except Exception as ex:
        return ft.Column([
            ft.Text("Invoice dan saldo hutang gagal dimuat.", size=18),
            ft.Text(str(ex), color=ft.Colors.RED_400),
            ft.TextButton("Coba lagi", on_click=lambda e: refresh()),
        ])

    # ---------- Dialog: konfirmasi hapus invoice ----------
    delete_target = {"iid": None, "no_laporan": None}

    def confirm_delete_invoice(e):
        del e
        iid = delete_target["iid"]
        if not iid:
            return

        try:
            delete_invoice(iid)
            log_activity(
                actor["id"],
                actor["username"],
                "DELETE",
                "invoice",
                iid,
                (
                    f"Menghapus invoice "
                    f"{delete_target['no_laporan'] or iid} di {nama_folder}"
                ),
                folder_cabang_id,
            )
            close_dialog()
            refresh()
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal hapus: {ex}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    delete_invoice_dlg = ft.AlertDialog(
        title=ft.Text("Hapus invoice ini?"),
        content=ft.Container(
            content=ft.Text("", size=13),
            width=small_dialog_width,
        ),
        inset_padding=12 if mobile else 40,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Ya, Hapus Permanen",
                on_click=confirm_delete_invoice,
                bgcolor=ft.Colors.RED_600,
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def open_delete_invoice_dialog(iid, no_laporan):
        delete_target["iid"] = iid
        delete_target["no_laporan"] = no_laporan
        delete_invoice_dlg.content.content.value = (
            f"Invoice '{no_laporan or iid}' beserta seluruh transaksi "
            "hariannya akan dihapus permanen. Tindakan ini tidak dapat "
            "dibatalkan."
        )
        page.show_dialog(delete_invoice_dlg)

    # ---------- Dialog: edit invoice ----------
    edit_no_field = ft.TextField(
        label="No.",
        max_length=50,
        col={"xs": 12, "sm": 6},
    )
    edit_tgl_dibuat_field = ft.TextField(
        label="Date (YYYY-MM-DD)",
        col={"xs": 12, "sm": 6},
    )
    edit_tgl_laporan_field = ft.TextField(
        label="TGL Laporan (YYYY-MM-DD)",
        col={"xs": 12, "sm": 6},
    )
    edit_invoice_bon_field = ft.TextField(
        label="Invoice / Bon (Rp)",
        hint_text="Contoh: 150000 atau 150.000",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )
    edit_invoice_target = {"iid": None}

    def submit_edit_invoice(e):
        del e
        iid = edit_invoice_target["iid"]
        if not iid:
            return

        try:
            no_laporan = require_text(
                "No.",
                edit_no_field.value,
                max_length=50,
            )
            tgl_dibuat_val = parse_date(
                "Date",
                edit_tgl_dibuat_field.value,
            )
            tgl_laporan_val = parse_date(
                "TGL Laporan",
                edit_tgl_laporan_field.value,
            )
            invoice_bon_val = parse_positive_decimal(
                "Invoice / Bon",
                edit_invoice_bon_field.value,
            )
            update_invoice(
                iid,
                no_laporan,
                tgl_dibuat_val,
                tgl_laporan_val,
                invoice_bon_val,
            )
            log_activity(
                actor["id"],
                actor["username"],
                "UPDATE",
                "invoice",
                iid,
                f"Mengubah invoice {no_laporan} di {nama_folder}",
                folder_cabang_id,
            )
            close_dialog()
            refresh()
        except ValueError as ve:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(str(ve)),
                    bgcolor=ft.Colors.RED_400,
                )
            )
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal update: {ex}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    edit_invoice_dlg = ft.AlertDialog(
        title=ft.Text("Edit laporan invoice"),
        content=ft.Container(
            content=ft.ResponsiveRow(
                [
                    edit_no_field,
                    edit_tgl_dibuat_field,
                    edit_tgl_laporan_field,
                    edit_invoice_bon_field,
                ],
                spacing=10,
                run_spacing=10,
            ),
            width=dialog_content_width,
        ),
        content_padding=ft.Padding.only(
            left=16,
            right=16,
            top=8,
            bottom=8,
        ),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                "Simpan Perubahan",
                on_click=submit_edit_invoice,
            ),
        ],
    )

    def open_edit_invoice_dialog(
        iid,
        no_laporan,
        tgl_dibuat,
        tgl_laporan,
        invoice_bon,
    ):
        edit_invoice_target["iid"] = iid
        edit_no_field.value = no_laporan or ""
        edit_tgl_dibuat_field.value = (
            tgl_dibuat.isoformat()
            if tgl_dibuat
            else date.today().isoformat()
        )
        edit_tgl_laporan_field.value = (
            tgl_laporan.isoformat()
            if tgl_laporan
            else date.today().isoformat()
        )
        edit_invoice_bon_field.value = str(invoice_bon or 0)
        page.show_dialog(edit_invoice_dlg)

    rows = []
    for inv in invoices:
        (
            iid,
            no_laporan,
            tgl_dibuat,
            tgl_laporan,
            invoice_bon,
            total_omzet,
            total_barang,
        ) = inv
        laba_bersih = total_omzet - total_barang
        sisa_hutang = (invoice_bon or 0) + total_barang - total_omzet

        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(no_laporan or "-")),
                    ft.DataCell(
                        ft.Text(
                            tgl_laporan.strftime("%d-%m-%Y")
                            if tgl_laporan
                            else "-"
                        )
                    ),
                    ft.DataCell(ft.Text(rp(invoice_bon))),
                    ft.DataCell(ft.Text(rp(total_omzet))),
                    ft.DataCell(ft.Text(rp(laba_bersih))),
                    ft.DataCell(ft.Text(rp(sisa_hutang))),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.IconButton(
                                    ft.Icons.VISIBILITY,
                                    tooltip="Detail transaksi",
                                    on_click=lambda e, iid=iid: navigate(
                                        page,
                                        f"/invoice/{iid}"
                                    ),
                                ),
                                ft.IconButton(
                                    ft.Icons.EDIT,
                                    tooltip="Edit",
                                    on_click=lambda e,
                                    iid=iid,
                                    nl=no_laporan,
                                    td=tgl_dibuat,
                                    tl=tgl_laporan,
                                    ib=invoice_bon: open_edit_invoice_dialog(
                                        iid,
                                        nl,
                                        td,
                                        tl,
                                        ib,
                                    ),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED_400,
                                    tooltip="Hapus",
                                    on_click=lambda e,
                                    iid=iid,
                                    nl=no_laporan: open_delete_invoice_dialog(
                                        iid,
                                        nl,
                                    ),
                                ),
                            ],
                            spacing=0,
                        )
                    ),
                ]
            )
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("No.")),
            ft.DataColumn(ft.Text("TGL Laporan")),
            ft.DataColumn(ft.Text("Invoice/Bon")),
            ft.DataColumn(ft.Text("Omset")),
            ft.DataColumn(ft.Text("Laba Bersih")),
            ft.DataColumn(ft.Text("Sisa Hutang")),
            ft.DataColumn(ft.Text("Aksi")),
        ],
        rows=rows,
    )

    # ---------- Dialog: buat invoice ----------
    no_field = ft.TextField(
        label="No.",
        max_length=50,
        col={"xs": 12, "sm": 6},
    )
    tgl_dibuat_field = ft.TextField(
        label="Date (YYYY-MM-DD)",
        value=date.today().isoformat(),
        col={"xs": 12, "sm": 6},
    )
    tgl_laporan_field = ft.TextField(
        label="TGL Laporan (YYYY-MM-DD)",
        value=date.today().isoformat(),
        col={"xs": 12, "sm": 6},
    )
    invoice_bon_field = ft.TextField(
        label="Invoice / Bon (Rp)",
        value="0",
        hint_text="Contoh: 150000 atau 150.000",
        keyboard_type=ft.KeyboardType.NUMBER,
        col={"xs": 12, "sm": 6},
    )

    def submit_invoice(e):
        del e
        try:
            no_laporan = require_text(
                "No.",
                no_field.value,
                max_length=50,
            )
            tgl_dibuat_val = parse_date(
                "Date",
                tgl_dibuat_field.value,
            )
            tgl_laporan_val = parse_date(
                "TGL Laporan",
                tgl_laporan_field.value,
            )
            invoice_bon_val = parse_positive_decimal(
                "Invoice / Bon",
                invoice_bon_field.value,
            )
            iid = create_invoice(
                folder_id,
                no_laporan,
                tgl_dibuat_val,
                tgl_laporan_val,
                invoice_bon_val,
                actor["id"],
            )
            log_activity(
                actor["id"],
                actor["username"],
                "CREATE",
                "invoice",
                iid,
                f"Membuat invoice {no_laporan} di {nama_folder}",
                folder_cabang_id,
            )
            close_dialog()
            navigate(page, f"/invoice/{iid}")
        except ValueError as ve:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(str(ve)),
                    bgcolor=ft.Colors.RED_400,
                )
            )
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal simpan: {ex}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    create_invoice_dlg = ft.AlertDialog(
        title=ft.Text("Buat laporan invoice baru"),
        content=ft.Container(
            content=ft.ResponsiveRow(
                [
                    no_field,
                    tgl_dibuat_field,
                    tgl_laporan_field,
                    invoice_bon_field,
                ],
                spacing=10,
                run_spacing=10,
            ),
            width=dialog_content_width,
        ),
        content_padding=ft.Padding.only(
            left=16,
            right=16,
            top=8,
            bottom=8,
        ),
        inset_padding=12 if mobile else 40,
        scrollable=True,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton(
                (
                    "Simpan & Lanjut"
                    if mobile
                    else "Simpan & lanjut isi transaksi"
                ),
                on_click=submit_invoice,
            ),
        ],
    )

    def open_dialog(e):
        del e
        page.show_dialog(create_invoice_dlg)

    export_picker = get_file_picker(page, "invoice-folder")

    async def export_pdf(e):
        del e
        nama_file_default = f"Laporan_{nama_folder.replace(' ', '_')}.pdf"

        try:
            balance = get_folder_balance(folder_id)
            invoices_with_transaksi = []
            for inv in get_invoices(folder_id):
                iid = inv[0]
                transaksi = get_transaksi(iid)
                invoices_with_transaksi.append(
                    {"header": inv, "transaksi": transaksi}
                )

            if page.platform in (
                ft.PagePlatform.ANDROID,
                ft.PagePlatform.IOS,
            ):
                pdf_bytes = generate_folder_pdf(
                    nama_folder,
                    invoices_with_transaksi,
                    None,
                    keuangan_folder=balance,
                )
                save_path = await export_picker.save_file(
                    dialog_title="Simpan laporan PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan laporan PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if not save_path:
                    return
                if not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                generate_folder_pdf(
                    nama_folder,
                    invoices_with_transaksi,
                    save_path,
                    keuangan_folder=balance,
                )

            if not save_path:
                return

            log_activity(
                actor["id"],
                actor["username"],
                "CREATE",
                "export_pdf",
                folder_id,
                f"Export PDF folder {nama_folder}",
                folder_cabang_id,
            )
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"PDF berhasil disimpan: {save_path}"),
                    bgcolor=ft.Colors.GREEN_700,
                )
            )
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Gagal export PDF: {ex}"),
                    bgcolor=ft.Colors.RED_400,
                )
            )

    title_text = f"Invoice - {nama_folder}"
    if is_pusat:
        title_text += f" ({nama_cabang_folder})"

    back_route = (
        f"/invoices/cabang/{folder_cabang_id}"
        if is_pusat
        else "/invoices"
    )

    info_banner = None
    if len(invoices) == 0:
        info_banner = ft.Container(
            content=ft.Text(
                "Folder ini belum punya invoice. Buat 1 invoice untuk "
                "mulai input transaksi harian.",
                size=13,
                color=(
                    ft.Colors.ORANGE_200
                    if is_dark
                    else ft.Colors.ORANGE_900
                ),
            ),
            bgcolor=(
                ft.Colors.with_opacity(0.18, ft.Colors.ORANGE_400)
                if is_dark
                else ft.Colors.ORANGE_50
            ),
            padding=12,
            border_radius=8,
        )
    elif len(invoices) > 1:
        info_banner = ft.Container(
            content=ft.Text(
                "Folder ini punya lebih dari 1 invoice (data lama). "
                "Untuk folder baru, cukup 1 invoice per folder.",
                size=13,
                color=(
                    ft.Colors.BLUE_200
                    if is_dark
                    else ft.Colors.BLUE_900
                ),
            ),
            bgcolor=(
                ft.Colors.with_opacity(0.18, ft.Colors.BLUE_400)
                if is_dark
                else ft.Colors.BLUE_50
            ),
            padding=12,
            border_radius=8,
        )

    header_title = ft.Container(
        content=ft.Row(
            [
                ft.IconButton(
                    ft.Icons.ARROW_BACK,
                    tooltip="Kembali",
                    on_click=lambda e: navigate(page, back_route),
                ),
                ft.Column(
                    [
                        ft.Text(
                            title_text,
                            size=20,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            "Daftar laporan invoice pada periode ini.",
                            size=13,
                            color=(
                                ft.Colors.GREY_400
                                if is_dark
                                else ft.Colors.GREY_600
                            ),
                        ),
                    ],
                    expand=True,
                    spacing=2,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        col={"xs": 12, "md": 6},
    )

    header_actions = ft.Container(
        content=ft.Row(
            [
                ft.OutlinedButton(
                    "Export PDF" if mobile else "Export ke PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=export_pdf,
                ),
                ft.ElevatedButton(
                    "Buat Laporan" if mobile else "Buat laporan baru",
                    icon=ft.Icons.ADD,
                    on_click=open_dialog,
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
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
        col={"xs": 12, "md": 6},
    )

    body_controls = [
        ft.Text(
            f"Hutang bawaan: {rp(keuangan_folder['hutang_bawaan'])}  |  "
            f"Sisa hutang akhir bulan: {rp(keuangan_folder['sisa_hutang'])}",
            size=14, weight=ft.FontWeight.W_500,
        ),
        ft.Text("Saldo pada tabel hanya per invoice, belum termasuk hutang bawaan bulan sebelumnya.", size=12),
        ft.ResponsiveRow(
            [header_title, header_actions],
            spacing=8,
            run_spacing=8,
        ),
        ft.Container(height=16),
    ]

    if info_banner:
        body_controls.extend(
            [
                info_banner,
                ft.Container(height=12),
            ]
        )

    if invoices:
        if mobile:
            body_controls.append(
                ft.Text(
                    "Geser tabel ke samping untuk melihat kolom lainnya.",
                    size=12,
                    color=(
                        ft.Colors.GREY_400
                        if is_dark
                        else ft.Colors.GREY_600
                    ),
                )
            )
        body_controls.append(
            ft.Row(
                [table],
                scroll=ft.ScrollMode.AUTO,
            )
        )
    else:
        body_controls.append(
            ft.Text(
                "Belum ada laporan invoice di folder ini.",
                color=(
                    ft.Colors.GREY_400
                    if is_dark
                    else ft.Colors.GREY_600
                ),
            )
        )

    return ft.Column(
        body_controls,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
