import flet as ft
from decimal import Decimal
from datetime import date, datetime
from config import MONTH
from components.metric_card import metric_card
from utils.formatting import rp
from utils.validation import require_text, parse_date, parse_positive_decimal
from utils.pdf_export import generate_pengambilan_pabrik_pdf
from db.activity_repo import log_activity
from db.pengambilan_pabrik_repo import (
    get_pengambilan_pabrik,
    add_pengambilan_pabrik,
    update_pengambilan_pabrik,
    delete_pengambilan_pabrik,
    get_akumulasi_bulanan_pabrik,
    DAFTAR_PABRIK_DEFAULT,
    SATUAN_BARANG_DEFAULT,
    KATEGORI_PRODUK_DEFAULT,
    STATUS_BAYAR_DEFAULT,
)
from db.cabang_repo import get_active_cabang
from state import app_state


def build_view(page: ft.Page):
    actor = app_state.user or {}
    is_pusat = actor.get("cabang_id") is None
    is_dark = page.theme_mode == ft.ThemeMode.DARK
    today = date.today()

    filter_state = {
        "bulan": today.month,
        "tahun": today.year,
        "start_date": None,
        "end_date": None,
        "nama_pabrik": "Semua",
        "kategori_barang": "Semua",
        "status_pembayaran": "Semua",
        "cabang_id": None if is_pusat else actor.get("cabang_id"),
        "search": "",
        "sort_order": "desc",
    }

    cabang_list = []
    if is_pusat:
        try:
            cabang_list = get_active_cabang()
        except Exception:
            cabang_list = [(1, "Cabang Utama"), (2, "Cabang Barat")]

    def close_dialog(e=None):
        page.pop_dialog()
        page.update()

    # =========================================================================
    # DIALOG TAMBAH & EDIT
    # =========================================================================
    form_id_target = {"id": None}

    form_tanggal = ft.TextField(label="Tanggal (YYYY-MM-DD)", width=180, value=today.isoformat())
    form_pabrik = ft.Dropdown(
        label="Nama Pabrik / Supplier",
        width=260,
        options=[ft.dropdown.Option(p, p) for p in DAFTAR_PABRIK_DEFAULT],
        value=DAFTAR_PABRIK_DEFAULT[0],
    )
    form_barang = ft.TextField(label="Nama Barang / Produk", width=260)
    form_kategori = ft.Dropdown(
        label="Kategori Produk",
        width=200,
        options=[ft.dropdown.Option(k, k) for k in KATEGORI_PRODUK_DEFAULT],
        value=KATEGORI_PRODUK_DEFAULT[0],
    )
    form_qty = ft.TextField(label="Jumlah / Qty", width=130, value="1")
    form_satuan = ft.Dropdown(
        label="Satuan",
        width=150,
        options=[ft.dropdown.Option(s, s) for s in SATUAN_BARANG_DEFAULT],
        value=SATUAN_BARANG_DEFAULT[0],
    )
    form_harga_satuan = ft.TextField(label="Harga Satuan (Rp)", width=180, value="0")
    form_total_preview = ft.Text("Total: Rp 0", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_700)
    form_sj = ft.TextField(label="No. Surat Jalan / DO (opsional)", width=220)
    form_status_bayar = ft.Dropdown(
        label="Status Pembayaran",
        width=200,
        options=[ft.dropdown.Option(s, s) for s in STATUS_BAYAR_DEFAULT],
        value=STATUS_BAYAR_DEFAULT[0],
    )
    form_keterangan = ft.TextField(label="Keterangan / Catatan", width=460, multiline=True, min_lines=2, max_lines=3)

    form_cabang_dropdown = ft.Dropdown(
        label="Cabang Penerima",
        width=220,
        options=[ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value=str(cabang_list[0][0]) if cabang_list else "1",
    )

    def calc_total_preview(e=None):
        try:
            q = float(form_qty.value or 0)
            hs = float(str(form_harga_satuan.value or 0).replace(",", "").strip())
            tot = q * hs
            form_total_preview.value = f"Total: {rp(tot)}"
        except Exception:
            form_total_preview.value = "Total: Rp 0"
        if e:
            page.update()

    form_qty.on_change = calc_total_preview
    form_harga_satuan.on_change = calc_total_preview

    def submit_form(e):
        try:
            tgl_val = parse_date("Tanggal", form_tanggal.value)
            pabrik_val = require_text("Nama Pabrik", form_pabrik.value, max_length=100)
            barang_val = require_text("Nama Barang", form_barang.value, max_length=100)
            kat_val = form_kategori.value or "Snack Ringan"
            qty_val = parse_positive_decimal("Jumlah Qty", form_qty.value)
            if qty_val <= 0:
                raise ValueError("Jumlah Qty harus lebih dari 0.")
            satuan_val = form_satuan.value or "Karton"
            hs_val = parse_positive_decimal("Harga Satuan", form_harga_satuan.value)
            sj_val = (form_sj.value or "").strip()
            status_val = form_status_bayar.value or "Lunas"
            ket_val = (form_keterangan.value or "").strip()

            if is_pusat:
                sel_cid = int(form_cabang_dropdown.value or 1)
                nama_cbg = next((c[1] for c in cabang_list if c[0] == sel_cid), "Cabang")
            else:
                sel_cid = actor.get("cabang_id", 1)
                nama_cbg = actor.get("nama_cabang", "Cabang")

            is_edit = form_id_target["id"] is not None
            if not is_edit:
                add_pengambilan_pabrik(
                    tanggal=tgl_val,
                    nama_pabrik=pabrik_val,
                    nama_barang=barang_val,
                    kategori_barang=kat_val,
                    qty=float(qty_val),
                    satuan=satuan_val,
                    harga_satuan=float(hs_val),
                    no_surat_jalan=sj_val,
                    status_pembayaran=status_val,
                    keterangan=ket_val,
                    cabang_id=sel_cid,
                    nama_cabang=nama_cbg,
                )
                success_msg = "Pengambilan pabrik berhasil dicatat!"
            else:
                update_pengambilan_pabrik(
                    pengambilan_id=form_id_target["id"],
                    tanggal=tgl_val,
                    nama_pabrik=pabrik_val,
                    nama_barang=barang_val,
                    kategori_barang=kat_val,
                    qty=float(qty_val),
                    satuan=satuan_val,
                    harga_satuan=float(hs_val),
                    no_surat_jalan=sj_val,
                    status_pembayaran=status_val,
                    keterangan=ket_val,
                    cabang_id=sel_cid,
                    nama_cabang=nama_cbg,
                )
                success_msg = "Data pengambilan pabrik berhasil diperbarui!"

            close_dialog()
            refresh_table_content()
            refresh_akumulasi_section()
            page.show_dialog(ft.SnackBar(ft.Text(success_msg), bgcolor=ft.Colors.GREEN_700))
        except ValueError as ve:
            page.show_dialog(ft.SnackBar(ft.Text(str(ve)), bgcolor=ft.Colors.RED_400))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal simpan data: {ex}"), bgcolor=ft.Colors.RED_400))

    form_dialog_title = ft.Text("Catat Pengambilan Barang Pabrik", weight=ft.FontWeight.W_500)
    form_dialog = ft.AlertDialog(
        title=form_dialog_title,
        content=ft.Container(
            content=ft.Column([
                ft.Row([form_tanggal, form_pabrik], spacing=10),
                ft.Row([form_barang, form_kategori], spacing=10),
                ft.Row([form_qty, form_satuan, form_harga_satuan], spacing=10),
                form_total_preview,
                ft.Row([form_sj, form_status_bayar], spacing=10),
                form_keterangan,
                form_cabang_dropdown if is_pusat else ft.Container(),
            ], tight=True, spacing=12),
            width=520,
        ),
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Simpan", on_click=submit_form, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ],
    )

    def open_add_dialog(e=None):
        form_id_target["id"] = None
        form_dialog_title.value = "Catat Pengambilan Barang Pabrik"
        form_tanggal.value = date.today().isoformat()
        form_pabrik.value = DAFTAR_PABRIK_DEFAULT[0]
        form_barang.value = ""
        form_kategori.value = KATEGORI_PRODUK_DEFAULT[0]
        form_qty.value = "1"
        form_satuan.value = SATUAN_BARANG_DEFAULT[0]
        form_harga_satuan.value = "0"
        form_sj.value = ""
        form_status_bayar.value = STATUS_BAYAR_DEFAULT[0]
        form_keterangan.value = ""
        if is_pusat and cabang_list:
            form_cabang_dropdown.value = str(cabang_list[0][0])
        calc_total_preview()
        page.show_dialog(form_dialog)

    def open_edit_dialog(item):
        form_id_target["id"] = item["id"]
        form_dialog_title.value = f"Edit Pengambilan Pabrik #{item['id']}"
        form_tanggal.value = item["tanggal"].isoformat() if hasattr(item["tanggal"], "isoformat") else str(item["tanggal"])
        form_pabrik.value = item["nama_pabrik"] if item["nama_pabrik"] in DAFTAR_PABRIK_DEFAULT else DAFTAR_PABRIK_DEFAULT[0]
        form_barang.value = item["nama_barang"]
        form_kategori.value = item["kategori_barang"] if item["kategori_barang"] in KATEGORI_PRODUK_DEFAULT else KATEGORI_PRODUK_DEFAULT[0]
        form_qty.value = str(int(item["qty"]) if item["qty"].is_integer() else item["qty"])
        form_satuan.value = item["satuan"] if item["satuan"] in SATUAN_BARANG_DEFAULT else SATUAN_BARANG_DEFAULT[0]
        form_harga_satuan.value = str(item["harga_satuan"])
        form_sj.value = item["no_surat_jalan"]
        form_status_bayar.value = item["status_pembayaran"] if item["status_pembayaran"] in STATUS_BAYAR_DEFAULT else STATUS_BAYAR_DEFAULT[0]
        form_keterangan.value = item["keterangan"]
        if is_pusat:
            form_cabang_dropdown.value = str(item["cabang_id"])
        calc_total_preview()
        page.show_dialog(form_dialog)

    # =========================================================================
    # DIALOG HAPUS
    # =========================================================================
    del_target = {"id": None}
    del_msg = ft.Text("")

    def confirm_delete(e):
        try:
            if del_target["id"]:
                delete_pengambilan_pabrik(del_target["id"])
                close_dialog()
                refresh_table_content()
                refresh_akumulasi_section()
                page.show_dialog(ft.SnackBar(ft.Text("Data pengambilan pabrik berhasil dihapus!"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal menghapus: {ex}"), bgcolor=ft.Colors.RED_400))

    delete_dialog = ft.AlertDialog(
        title=ft.Text("Konfirmasi Hapus Pengambilan Pabrik"),
        content=del_msg,
        actions=[
            ft.TextButton("Batal", on_click=close_dialog),
            ft.ElevatedButton("Ya, Hapus", on_click=confirm_delete, bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE),
        ],
    )

    def open_delete_dialog(item):
        del_target["id"] = item["id"]
        del_msg.value = f"Hapus catatan pengambilan '{item['nama_barang']}' ({item['qty']} {item['satuan']}) dari {item['nama_pabrik']} senilai {rp(item['total_harga'])}?"
        page.show_dialog(delete_dialog)

    # =========================================================================
    # FILTER CONTROLS
    # =========================================================================
    filter_bulan_dropdown = ft.Dropdown(
        label="Periode Bulan",
        width=175,
        options=[ft.dropdown.Option("Semua", "Semua Bulan")] + [
            ft.dropdown.Option(str(i), MONTH[i]) for i in range(1, 13)
        ],
        value=str(filter_state["bulan"]),
    )

    filter_tahun_dropdown = ft.Dropdown(
        label="Tahun",
        width=120,
        options=[ft.dropdown.Option(str(y), str(y)) for y in range(2024, 2030)],
        value=str(filter_state["tahun"]),
    )

    filter_start_field = ft.TextField(label="Dari Tanggal", hint_text="YYYY-MM-DD", width=160)
    filter_end_field = ft.TextField(label="Sampai Tanggal", hint_text="YYYY-MM-DD", width=160)

    filter_sort_dropdown = ft.Dropdown(
        label="Urutan Tanggal",
        width=170,
        options=[
            ft.dropdown.Option("desc", "Terbaru (Desc)"),
            ft.dropdown.Option("asc", "Terlama (Asc)"),
        ],
        value="desc",
    )

    filter_pabrik_dropdown = ft.Dropdown(
        label="Pabrik / Supplier",
        width=210,
        options=[ft.dropdown.Option("Semua", "Semua Pabrik")] + [
            ft.dropdown.Option(p, p) for p in DAFTAR_PABRIK_DEFAULT
        ],
        value="Semua",
    )

    filter_kategori_dropdown = ft.Dropdown(
        label="Kategori",
        width=180,
        options=[ft.dropdown.Option("Semua", "Semua Kategori")] + [
            ft.dropdown.Option(k, k) for k in KATEGORI_PRODUK_DEFAULT
        ],
        value="Semua",
    )

    filter_status_dropdown = ft.Dropdown(
        label="Status Bayar",
        width=160,
        options=[ft.dropdown.Option("Semua", "Semua Status")] + [
            ft.dropdown.Option(s, s) for s in STATUS_BAYAR_DEFAULT
        ],
        value="Semua",
    )

    filter_cabang_dropdown = ft.Dropdown(
        label="Cabang",
        width=180,
        options=[ft.dropdown.Option("Semua", "Semua Cabang")] + [ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value="Semua" if filter_state["cabang_id"] is None else str(filter_state["cabang_id"]),
    )

    search_field = ft.TextField(
        label="Cari Pengambilan",
        hint_text="Nama pabrik, barang, surat jalan...",
        prefix_icon=ft.Icons.SEARCH,
        width=230,
        value=filter_state["search"],
    )

    def apply_filter(e=None):
        sel_b = filter_bulan_dropdown.value
        filter_state["bulan"] = None if sel_b == "Semua" or not sel_b else int(sel_b)

        sel_t = filter_tahun_dropdown.value
        filter_state["tahun"] = int(sel_t) if sel_t else today.year

        try:
            filter_state["start_date"] = parse_date("Dari Tanggal", filter_start_field.value) if filter_start_field.value else None
        except Exception:
            filter_state["start_date"] = None

        try:
            filter_state["end_date"] = parse_date("Sampai Tanggal", filter_end_field.value) if filter_end_field.value else None
        except Exception:
            filter_state["end_date"] = None

        filter_state["sort_order"] = filter_sort_dropdown.value or "desc"
        filter_state["nama_pabrik"] = filter_pabrik_dropdown.value or "Semua"
        filter_state["kategori_barang"] = filter_kategori_dropdown.value or "Semua"
        filter_state["status_pembayaran"] = filter_status_dropdown.value or "Semua"

        if is_pusat:
            sel_cbg = filter_cabang_dropdown.value
            filter_state["cabang_id"] = None if sel_cbg == "Semua" else int(sel_cbg)

        filter_state["search"] = search_field.value or ""
        refresh_table_content()
        refresh_akumulasi_section()

    def reset_filter(e=None):
        filter_bulan_dropdown.value = str(today.month)
        filter_tahun_dropdown.value = str(today.year)
        filter_start_field.value = ""
        filter_end_field.value = ""
        filter_sort_dropdown.value = "desc"
        filter_pabrik_dropdown.value = "Semua"
        filter_kategori_dropdown.value = "Semua"
        filter_status_dropdown.value = "Semua"
        if is_pusat:
            filter_cabang_dropdown.value = "Semua"
        search_field.value = ""
        apply_filter()

    search_field.on_submit = apply_filter
    filter_bulan_dropdown.on_change = apply_filter
    filter_tahun_dropdown.on_change = apply_filter
    filter_sort_dropdown.on_change = apply_filter
    filter_pabrik_dropdown.on_change = apply_filter
    filter_kategori_dropdown.on_change = apply_filter
    filter_status_dropdown.on_change = apply_filter

    filter_controls = [
        filter_bulan_dropdown,
        filter_tahun_dropdown,
        filter_start_field,
        filter_end_field,
        filter_sort_dropdown,
        filter_pabrik_dropdown,
        filter_kategori_dropdown,
        filter_status_dropdown,
    ]
    if is_pusat:
        filter_controls.append(filter_cabang_dropdown)
    filter_controls.append(search_field)

    filter_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FILTER_LIST, size=20, color=ft.Colors.BLUE_700),
                ft.Text("Filter & Periode Pengambilan", weight=ft.FontWeight.W_500, size=15),
                ft.Container(expand=True),
                ft.TextButton("Reset Filter", icon=ft.Icons.RESTART_ALT, on_click=reset_filter),
                ft.ElevatedButton("Terapkan", icon=ft.Icons.CHECK, on_click=apply_filter, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
            ]),
            ft.Divider(height=1),
            ft.Row(filter_controls, wrap=True, spacing=10, run_spacing=10),
        ], spacing=10),
        bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
        border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
        border_radius=10,
        padding=16,
    )

    # =========================================================================
    # METRICS & AKUMULASI BULANAN CARDS
    # =========================================================================
    metric_akumulasi_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_qty_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_avg_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_trx_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    akumulasi_table_container = ft.Container()
    table_container = ft.Container()

    def on_sort_tanggal(col_idx, ascending):
        filter_state["sort_order"] = "asc" if ascending else "desc"
        filter_sort_dropdown.value = filter_state["sort_order"]
        refresh_table_content()

    def build_table_rows(items):
        rows = []
        for it in items:
            tgl_str = it["tanggal"].strftime("%d-%m-%Y") if hasattr(it["tanggal"], "strftime") else str(it["tanggal"])
            status_color = (
                ft.Colors.GREEN_700
                if it["status_pembayaran"] == "Lunas"
                else (ft.Colors.ORANGE_700 if it["status_pembayaran"] == "Transfer" else ft.Colors.RED_700)
            )
            status_bg = (
                ft.Colors.GREEN_50
                if it["status_pembayaran"] == "Lunas"
                else (ft.Colors.ORANGE_50 if it["status_pembayaran"] == "Transfer" else ft.Colors.RED_50)
            )
            if is_dark:
                status_color = (
                    ft.Colors.GREEN_300
                    if it["status_pembayaran"] == "Lunas"
                    else (ft.Colors.ORANGE_300 if it["status_pembayaran"] == "Transfer" else ft.Colors.RED_300)
                )
                status_bg = (
                    ft.Colors.GREEN_900
                    if it["status_pembayaran"] == "Lunas"
                    else (ft.Colors.ORANGE_900 if it["status_pembayaran"] == "Transfer" else ft.Colors.RED_900)
                )

            cells = [
                ft.DataCell(ft.Text(tgl_str, size=13)),
            ]
            if is_pusat:
                cells.append(ft.DataCell(ft.Text(it.get("nama_cabang", "-"), size=13)))

            qty_display = f"{int(it['qty']) if it['qty'].is_integer() else it['qty']} {it['satuan']}"

            cells.extend([
                ft.DataCell(ft.Text(it["nama_pabrik"], size=13, weight=ft.FontWeight.W_500)),
                ft.DataCell(
                    ft.Column([
                        ft.Text(it["nama_barang"], size=13, weight=ft.FontWeight.W_600),
                        ft.Text(it["kategori_barang"], size=11, color=ft.Colors.GREY_500),
                    ], spacing=1, alignment=ft.MainAxisAlignment.CENTER)
                ),
                ft.DataCell(ft.Text(qty_display, size=13, weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(rp(it["harga_satuan"]), size=13)),
                ft.DataCell(
                    ft.Text(
                        rp(it["total_harga"]),
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.BLUE_700 if not is_dark else ft.Colors.BLUE_300,
                    )
                ),
                ft.DataCell(ft.Text(it["no_surat_jalan"] or "-", size=12, color=ft.Colors.GREY_500)),
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(it["status_pembayaran"], size=11, weight=ft.FontWeight.W_500, color=status_color),
                        bgcolor=status_bg,
                        padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                        border_radius=6,
                    )
                ),
                ft.DataCell(
                    ft.Row([
                        ft.IconButton(
                            ft.Icons.EDIT,
                            icon_size=18,
                            tooltip="Edit Pengambilan",
                            on_click=lambda e, item=it: open_edit_dialog(item),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE,
                            icon_size=18,
                            icon_color=ft.Colors.RED_400,
                            tooltip="Hapus Pengambilan",
                            on_click=lambda e, item=it: open_delete_dialog(item),
                        ),
                    ], spacing=2)
                ),
            ])
            rows.append(ft.DataRow(cells=cells))
        return rows

    def refresh_table_content():
        items = get_pengambilan_pabrik(
            cabang_id=filter_state["cabang_id"],
            bulan=filter_state["bulan"],
            tahun=filter_state["tahun"],
            start_date=filter_state["start_date"],
            end_date=filter_state["end_date"],
            nama_pabrik=filter_state["nama_pabrik"],
            kategori_barang=filter_state["kategori_barang"],
            status_pembayaran=filter_state["status_pembayaran"],
            search=filter_state["search"],
            sort_order=filter_state["sort_order"],
        )

        total_nominal_sum = sum([it["total_harga"] for it in items])
        total_qty_sum = sum([it["qty"] for it in items])
        count_sum = len(items)
        avg_nominal = (total_nominal_sum / count_sum) if count_sum > 0 else Decimal(0)

        # Periode Label for header card
        periode_label = f"({MONTH[filter_state['bulan']]} {filter_state['tahun']})" if filter_state["bulan"] else f"(Tahun {filter_state['tahun']})"

        metric_akumulasi_card.content = metric_card(
            page,
            f"Akumulasi Total Bulan {periode_label}",
            rp(total_nominal_sum),
            light_color=ft.Colors.INDIGO_50,
            light_text_color=ft.Colors.INDIGO_900,
            dark_color=ft.Colors.INDIGO_900,
            dark_text_color=ft.Colors.INDIGO_100,
        )
        metric_qty_card.content = metric_card(
            page,
            f"Total Qty Barang {periode_label}",
            f"{int(total_qty_sum) if total_qty_sum.is_integer() else total_qty_sum:,.0f} Unit / Karton",
            light_color=ft.Colors.TEAL_50,
            light_text_color=ft.Colors.TEAL_900,
            dark_color=ft.Colors.TEAL_900,
            dark_text_color=ft.Colors.TEAL_100,
        )
        metric_avg_card.content = metric_card(
            page,
            "Rata-rata per Pengambilan",
            rp(avg_nominal),
            light_color=ft.Colors.BLUE_50,
            light_text_color=ft.Colors.BLUE_900,
            dark_color=ft.Colors.BLUE_900,
            dark_text_color=ft.Colors.BLUE_100,
        )
        metric_trx_card.content = metric_card(
            page,
            "Total Transaksi Pengambilan",
            f"{count_sum} Transaksi",
            light_color=ft.Colors.GREY_100,
            light_text_color=ft.Colors.GREY_900,
            dark_color=ft.Colors.GREY_800,
            dark_text_color=ft.Colors.WHITE,
        )

        if not items:
            table_container.content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.FACTORY_OUTLINED, size=48, color=ft.Colors.GREY_400),
                    ft.Container(height=8),
                    ft.Text("Tidak ada data pengambilan pabrik", size=15, weight=ft.FontWeight.W_500),
                    ft.Text("Klik tombol 'Catat Pengambilan' untuk menambah catatan baru atau sesuaikan filter periode.", size=12, color=ft.Colors.GREY_500),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment.CENTER,
                padding=40,
                border_radius=10,
                border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
                bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
            )
        else:
            columns = [
                ft.DataColumn(
                    ft.Text("Tanggal"),
                    on_sort=lambda e: on_sort_tanggal(0, e.ascending),
                ),
            ]
            if is_pusat:
                columns.append(ft.DataColumn(ft.Text("Cabang")))
            columns.extend([
                ft.DataColumn(ft.Text("Pabrik / Supplier")),
                ft.DataColumn(ft.Text("Nama Barang & Kategori")),
                ft.DataColumn(ft.Text("Qty")),
                ft.DataColumn(ft.Text("Harga Satuan")),
                ft.DataColumn(ft.Text("Total Harga")),
                ft.DataColumn(ft.Text("No. DO/SJ")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Aksi")),
            ])

            dt = ft.DataTable(
                sort_column_index=0,
                sort_ascending=(filter_state["sort_order"] == "asc"),
                columns=columns,
                rows=build_table_rows(items),
                border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200),
                border_radius=10,
                heading_row_color=ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100,
                show_bottom_border=True,
            )
            table_container.content = ft.Row([dt], scroll=ft.ScrollMode.AUTO)
        if page.views:
            page.update()

    def refresh_akumulasi_section():
        sel_year = filter_state["tahun"] or today.year
        akumulasi = get_akumulasi_bulanan_pabrik(
            tahun=sel_year,
            cabang_id=filter_state["cabang_id"],
        )
        
        # Build mini cards for active months
        month_chips = []
        for m_idx in range(1, 13):
            m_data = akumulasi["monthly"][m_idx]
            is_current_filter = filter_state["bulan"] == m_idx
            is_has_data = m_data["count"] > 0
            
            border_c = ft.Colors.BLUE_500 if is_current_filter else (ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300)
            bg_c = (
                (ft.Colors.BLUE_900 if is_dark else ft.Colors.BLUE_50)
                if is_current_filter
                else (ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE)
            )

            def select_month(e, m=m_idx):
                filter_bulan_dropdown.value = str(m)
                apply_filter()

            chip = ft.Container(
                content=ft.Column([
                    ft.Text(MONTH[m_idx][:3].upper(), size=11, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_700 if not is_dark else ft.Colors.BLUE_300),
                    ft.Text(rp(m_data["total_nominal"]), size=12, weight=ft.FontWeight.W_600),
                    ft.Text(f"{int(m_data['total_qty'])} Qty · {m_data['count']} Trx", size=10, color=ft.Colors.GREY_500),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=bg_c,
                border=ft.Border.all(1.5 if is_current_filter else 0.5, border_c),
                border_radius=8,
                padding=ft.Padding.symmetric(vertical=8, horizontal=12),
                ink=True,
                on_click=select_month,
            )
            month_chips.append(chip)

        akumulasi_table_container.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CALENDAR_MONTH, size=18, color=ft.Colors.INDIGO_700),
                    ft.Text(f"Ringkasan Akumulasi Bulanan Tahun {sel_year}", size=14, weight=ft.FontWeight.W_600),
                    ft.Container(expand=True),
                    ft.Text(f"Total Tahunan: {rp(akumulasi['grand_total_nominal'])} ({int(akumulasi['grand_total_qty']):,} Qty)", size=13, weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700),
                ]),
                ft.Divider(height=1),
                ft.Row(month_chips, wrap=True, spacing=8, run_spacing=8),
            ], spacing=8),
            bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.GREY_50,
            border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
            border_radius=10,
            padding=14,
        )
        if page.views:
            page.update()

    def get_filtered_data():
        return get_pengambilan_pabrik(
            cabang_id=filter_state["cabang_id"],
            bulan=filter_state["bulan"],
            tahun=filter_state["tahun"],
            start_date=filter_state["start_date"],
            end_date=filter_state["end_date"],
            nama_pabrik=filter_state["nama_pabrik"],
            kategori_barang=filter_state["kategori_barang"],
            status_pembayaran=filter_state["status_pembayaran"],
            search=filter_state["search"],
            sort_order=filter_state["sort_order"],
        )

    # Export PDF Picker & Handler
    export_picker = ft.FilePicker()
    if export_picker not in page.services:
        page.services.append(export_picker)

    async def export_pdf(e):
        items = get_filtered_data()
        if not items:
            page.show_dialog(ft.SnackBar(ft.Text("Tidak ada data pengambilan pabrik untuk diexport."), bgcolor=ft.Colors.RED_400))
            return

        cbg_name = "Semua Cabang"
        if filter_state["cabang_id"]:
            cbg_name = next((c[1] for c in cabang_list if c[0] == filter_state["cabang_id"]), f"Cabang {filter_state['cabang_id']}")
        elif not is_pusat:
            cbg_name = actor.get("nama_cabang", "Cabang")

        periode_str = f"{MONTH[filter_state['bulan']]} {filter_state['tahun']}" if filter_state.get("bulan") else f"Tahun {filter_state['tahun']}"
        if filter_state["start_date"] and filter_state["end_date"]:
            periode_str = f"{filter_state['start_date'].strftime('%d-%m-%Y')} s/d {filter_state['end_date'].strftime('%d-%m-%Y')}"

        pabrik_str = f"Pabrik: {filter_state['nama_pabrik']}" if filter_state.get("nama_pabrik") != "Semua" else "Semua Pabrik"
        status_str = f"Status: {filter_state['status_pembayaran']}" if filter_state.get("status_pembayaran") != "Semua" else "Semua Status"

        filter_info = {
            "periode": periode_str,
            "cabang": cbg_name,
            "extra": f"{pabrik_str} | {status_str} | Total: {len(items)} Trx",
        }

        nama_file_default = f"Laporan_Pabrik_{filter_state['tahun']}_{filter_state['bulan'] or 'All'}.pdf"
        try:
            if page.platform == ft.PagePlatform.ANDROID or page.platform == ft.PagePlatform.IOS:
                pdf_bytes = generate_pengambilan_pabrik_pdf(items, filter_info, is_pusat=is_pusat, output_path=None)
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Pengambilan Pabrik PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
                if not save_path:
                    return
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Pengambilan Pabrik PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if not save_path:
                    return
                if not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                generate_pengambilan_pabrik_pdf(items, filter_info, is_pusat=is_pusat, output_path=save_path)

            log_activity(
                actor.get("id"),
                actor.get("username", "user"),
                "CREATE",
                "export_pdf",
                filter_state.get("cabang_id") or 0,
                f"Export PDF Pengambilan Pabrik ({periode_str})",
                filter_state.get("cabang_id"),
            )
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    # Initial data
    refresh_table_content()
    refresh_akumulasi_section()

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Pengambilan Barang Pabrik", size=22, weight=ft.FontWeight.W_600),
                ft.Text("Pencatatan pengambilan stok dari pabrik, harga, dan akumulasi total bulanan.", size=13, color=ft.Colors.GREY_500),
            ], expand=True),
            ft.OutlinedButton(
                "Export ke PDF",
                icon=ft.Icons.PICTURE_AS_PDF,
                on_click=export_pdf,
            ),
            ft.ElevatedButton(
                "Catat Pengambilan",
                icon=ft.Icons.ADD,
                on_click=open_add_dialog,
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
            ft.IconButton(
                ft.Icons.REFRESH,
                tooltip="Segarkan Data",
                on_click=lambda e: (refresh_table_content(), refresh_akumulasi_section()),
            ),
        ]),
        ft.Container(height=8),
        ft.ResponsiveRow([
            metric_akumulasi_card,
            metric_qty_card,
            metric_avg_card,
            metric_trx_card,
        ], spacing=12, run_spacing=12),
        ft.Container(height=10),
        akumulasi_table_container,
        ft.Container(height=10),
        filter_card,
        ft.Container(height=16),
        ft.Row([
            ft.Text("Daftar Pengambilan Barang Pabrik", size=16, weight=ft.FontWeight.W_500, expand=True),
        ]),
        ft.Container(height=8),
        table_container,
        ft.Container(height=24),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return body
