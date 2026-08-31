import flet as ft
import flet_charts as fc
from decimal import Decimal
from datetime import date, datetime
from config import MONTH
from components.metric_card import metric_card
from utils.formatting import rp
from utils.pdf_export import generate_rekap_bulanan_pdf
from db.activity_repo import log_activity
from db.supir_kenek_repo import get_pengeluaran_supir_kenek, get_rekap_supir_kenek_bulanan
from db.pengambilan_pabrik_repo import get_pengambilan_pabrik
from db.pengambilan_balaraja_repo import get_pengambilan_balaraja
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
        "cabang_id": None if is_pusat else actor.get("cabang_id"),
    }

    cabang_list = []
    if is_pusat:
        try:
            cabang_list = get_active_cabang()
        except Exception:
            cabang_list = [(1, "Cabang Utama"), (2, "Cabang Barat")]

    # Controls
    filter_bulan_dropdown = ft.Dropdown(
        label="Pilih Bulan",
        width=180,
        options=[ft.dropdown.Option(str(i), MONTH[i]) for i in range(1, 13)],
        value=str(filter_state["bulan"]),
    )

    filter_tahun_dropdown = ft.Dropdown(
        label="Tahun",
        width=130,
        options=[ft.dropdown.Option(str(y), str(y)) for y in range(2024, 2030)],
        value=str(filter_state["tahun"]),
    )

    filter_cabang_dropdown = ft.Dropdown(
        label="Cabang",
        width=200,
        options=[ft.dropdown.Option("Semua", "Semua Cabang")] + [ft.dropdown.Option(str(c[0]), c[1]) for c in cabang_list],
        value="Semua" if filter_state["cabang_id"] is None else str(filter_state["cabang_id"]),
    )

    def apply_filter(e=None):
        filter_state["bulan"] = int(filter_bulan_dropdown.value or today.month)
        filter_state["tahun"] = int(filter_tahun_dropdown.value or today.year)
        if is_pusat:
            sel_cbg = filter_cabang_dropdown.value
            filter_state["cabang_id"] = None if sel_cbg == "Semua" else int(sel_cbg)
        refresh_rekap()

    filter_bulan_dropdown.on_change = apply_filter
    filter_tahun_dropdown.on_change = apply_filter
    filter_cabang_dropdown.on_change = apply_filter

    filter_card = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.CALENDAR_MONTH, color=ft.Colors.BLUE_700, size=22),
            ft.Text("Periode Rekap Bulanan:", weight=ft.FontWeight.W_500, size=15),
            filter_bulan_dropdown,
            filter_tahun_dropdown,
            filter_cabang_dropdown if is_pusat else ft.Container(),
            ft.ElevatedButton("Segarkan", icon=ft.Icons.REFRESH, on_click=apply_filter, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ], wrap=True, spacing=12, alignment=ft.MainAxisAlignment.START),
        bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
        border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
        border_radius=10,
        padding=16,
    )

    # Top Metric Cards
    metric_kenek_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_pabrik_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_balaraja_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})
    metric_grand_card = ft.Container(col={"xs": 12, "sm": 6, "md": 3})

    # Containers for dynamic sections
    chart_container = ft.Container()
    breakdown_table_container = ft.Container()
    detail_kenek_container = ft.Container()
    detail_pabrik_container = ft.Container()
    detail_balaraja_container = ft.Container()

    def build_comparison_chart(kenek_sum, pabrik_sum, balaraja_sum):
        k_val = float(kenek_sum)
        p_val = float(pabrik_sum)
        b_val = float(balaraja_sum)
        max_val = max(k_val, p_val, b_val, 1000.0)

        groups = [
            fc.BarChartGroup(
                x=0,
                rods=[
                    fc.BarChartRod(from_y=0, to_y=k_val, width=28, color=ft.Colors.RED_400, border_radius=6, tooltip=f"Operasional Kenek/Supir: {rp(k_val)}"),
                ],
            ),
            fc.BarChartGroup(
                x=1,
                rods=[
                    fc.BarChartRod(from_y=0, to_y=p_val, width=28, color=ft.Colors.INDIGO_400, border_radius=6, tooltip=f"Pengambilan Pabrik: {rp(p_val)}"),
                ],
            ),
            fc.BarChartGroup(
                x=2,
                rods=[
                    fc.BarChartRod(from_y=0, to_y=b_val, width=28, color=ft.Colors.AMBER_400, border_radius=6, tooltip=f"Pengambilan Balaraja: {rp(b_val)}"),
                ],
            ),
        ]

        bottom_labels = [
            fc.ChartAxisLabel(value=0, label=ft.Text("Kenek/Supir", size=11, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_300 if is_dark else ft.Colors.GREY_800)),
            fc.ChartAxisLabel(value=1, label=ft.Text("Pabrik", size=11, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_300 if is_dark else ft.Colors.GREY_800)),
            fc.ChartAxisLabel(value=2, label=ft.Text("Balaraja", size=11, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_300 if is_dark else ft.Colors.GREY_800)),
        ]

        chart = fc.BarChart(
            groups=groups,
            bottom_axis=fc.ChartAxis(labels=bottom_labels, show_labels=True, label_size=32),
            max_y=max_val * 1.25,
            interactive=True,
            height=260,
            expand=True,
        )

        legend = ft.Row([
            ft.Row([ft.Container(width=12, height=12, bgcolor=ft.Colors.RED_400, border_radius=3), ft.Text("Operasional Kenek & Supir", size=12)], spacing=6),
            ft.Row([ft.Container(width=12, height=12, bgcolor=ft.Colors.INDIGO_400, border_radius=3), ft.Text("Pengambilan Pabrik", size=12)], spacing=6),
            ft.Row([ft.Container(width=12, height=12, bgcolor=ft.Colors.AMBER_400, border_radius=3), ft.Text("Pengambilan Balaraja", size=12)], spacing=6),
        ], spacing=16, wrap=True)

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.BAR_CHART, size=18, color=ft.Colors.BLUE_700),
                ft.Text("Grafik Komparasi Pengeluaran Bulanan", size=15, weight=ft.FontWeight.W_600),
            ]),
            ft.Container(height=4),
            legend,
            ft.Container(height=8),
            chart,
        ], spacing=6)

    def refresh_rekap():
        bulan = filter_state["bulan"]
        tahun = filter_state["tahun"]
        cabang_id = filter_state["cabang_id"]
        bulan_nama = MONTH[bulan]

        # 1. Kenek & Supir Data
        kenek_items = get_pengeluaran_supir_kenek(cabang_id=cabang_id, bulan=bulan, tahun=tahun, sort_order="desc")
        kenek_sum = sum(it["nominal"] for it in kenek_items)
        kenek_count = len(kenek_items)

        # 2. Pengambilan Pabrik Data
        pabrik_items = get_pengambilan_pabrik(cabang_id=cabang_id, bulan=bulan, tahun=tahun, sort_order="desc")
        pabrik_sum = sum(it["total_harga"] for it in pabrik_items)
        pabrik_count = len(pabrik_items)
        pabrik_qty = sum(it["qty"] for it in pabrik_items)

        # 3. Pengambilan Balaraja Data
        balaraja_items = get_pengambilan_balaraja(cabang_id=cabang_id, bulan=bulan, tahun=tahun, sort_order="desc")
        balaraja_sum = sum(it["total_harga"] for it in balaraja_items)
        balaraja_count = len(balaraja_items)
        balaraja_qty = sum(it["qty"] for it in balaraja_items)

        # Grand Total
        grand_total = kenek_sum + pabrik_sum + balaraja_sum
        total_trx = kenek_count + pabrik_count + balaraja_count

        # Update Top Metric Cards
        metric_kenek_card.content = metric_card(
            page,
            f"Operasional Kenek/Supir ({bulan_nama})",
            rp(kenek_sum),
            light_color=ft.Colors.RED_50,
            light_text_color=ft.Colors.RED_900,
            dark_color=ft.Colors.RED_900,
            dark_text_color=ft.Colors.RED_100,
        )
        metric_pabrik_card.content = metric_card(
            page,
            f"Pengambilan Pabrik ({bulan_nama})",
            rp(pabrik_sum),
            light_color=ft.Colors.INDIGO_50,
            light_text_color=ft.Colors.INDIGO_900,
            dark_color=ft.Colors.INDIGO_900,
            dark_text_color=ft.Colors.INDIGO_100,
        )
        metric_balaraja_card.content = metric_card(
            page,
            f"Pengambilan Balaraja ({bulan_nama})",
            rp(balaraja_sum),
            light_color=ft.Colors.AMBER_50,
            light_text_color=ft.Colors.AMBER_900,
            dark_color=ft.Colors.AMBER_900,
            dark_text_color=ft.Colors.AMBER_100,
        )
        metric_grand_card.content = metric_card(
            page,
            f"Grand Total Pengeluaran & Stok",
            rp(grand_total),
            light_color=ft.Colors.BLUE_50,
            light_text_color=ft.Colors.BLUE_900,
            dark_color=ft.Colors.BLUE_900,
            dark_text_color=ft.Colors.BLUE_100,
        )

        # Percentages
        pct_kenek = (kenek_sum / grand_total * 100) if grand_total > 0 else Decimal(0)
        pct_pabrik = (pabrik_sum / grand_total * 100) if grand_total > 0 else Decimal(0)
        pct_balaraja = (balaraja_sum / grand_total * 100) if grand_total > 0 else Decimal(0)

        # Chart
        chart_container.content = ft.Container(
            content=build_comparison_chart(kenek_sum, pabrik_sum, balaraja_sum),
            bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
            border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
            border_radius=10,
            padding=16,
        )

        # Breakdown Table
        breakdown_rows = [
            ft.DataRow(cells=[
                ft.DataCell(
                    ft.Row([
                        ft.Container(width=10, height=10, bgcolor=ft.Colors.RED_500, border_radius=2),
                        ft.Text("Operasional Kenek & Supir", weight=ft.FontWeight.W_600),
                    ], spacing=8)
                ),
                ft.DataCell(ft.Text(f"{kenek_count} Transaksi")),
                ft.DataCell(ft.Text(rp(kenek_sum), weight=ft.FontWeight.W_600)),
                ft.DataCell(
                    ft.Row([
                        ft.ProgressBar(value=float(pct_kenek) / 100.0, color=ft.Colors.RED_500, width=100),
                        ft.Text(f"{pct_kenek:.1f}%", size=12, weight=ft.FontWeight.W_500),
                    ], spacing=8)
                ),
            ]),
            ft.DataRow(cells=[
                ft.DataCell(
                    ft.Row([
                        ft.Container(width=10, height=10, bgcolor=ft.Colors.INDIGO_500, border_radius=2),
                        ft.Text("Pengambilan Barang Pabrik", weight=ft.FontWeight.W_600),
                    ], spacing=8)
                ),
                ft.DataCell(ft.Text(f"{pabrik_count} Trx ({int(pabrik_qty)} Unit)")),
                ft.DataCell(ft.Text(rp(pabrik_sum), weight=ft.FontWeight.W_600)),
                ft.DataCell(
                    ft.Row([
                        ft.ProgressBar(value=float(pct_pabrik) / 100.0, color=ft.Colors.INDIGO_500, width=100),
                        ft.Text(f"{pct_pabrik:.1f}%", size=12, weight=ft.FontWeight.W_500),
                    ], spacing=8)
                ),
            ]),
            ft.DataRow(cells=[
                ft.DataCell(
                    ft.Row([
                        ft.Container(width=10, height=10, bgcolor=ft.Colors.AMBER_600, border_radius=2),
                        ft.Text("Pengambilan Barang Balaraja", weight=ft.FontWeight.W_600),
                    ], spacing=8)
                ),
                ft.DataCell(ft.Text(f"{balaraja_count} Trx ({int(balaraja_qty)} Unit)")),
                ft.DataCell(ft.Text(rp(balaraja_sum), weight=ft.FontWeight.W_600)),
                ft.DataCell(
                    ft.Row([
                        ft.ProgressBar(value=float(pct_balaraja) / 100.0, color=ft.Colors.AMBER_600, width=100),
                        ft.Text(f"{pct_balaraja:.1f}%", size=12, weight=ft.FontWeight.W_500),
                    ], spacing=8)
                ),
            ]),
            ft.DataRow(cells=[
                ft.DataCell(ft.Text("TOTAL KESELURUHAN", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700 if not is_dark else ft.Colors.BLUE_300)),
                ft.DataCell(ft.Text(f"{total_trx} Transaksi", weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(rp(grand_total), weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700 if not is_dark else ft.Colors.BLUE_300)),
                ft.DataCell(ft.Text("100.0%", weight=ft.FontWeight.BOLD)),
            ]),
        ]

        breakdown_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Modul Rekapitulasi")),
                ft.DataColumn(ft.Text("Volume / Transaksi")),
                ft.DataColumn(ft.Text("Total Biaya (Rp)")),
                ft.DataColumn(ft.Text("Porsi (%)")),
            ],
            rows=breakdown_rows,
            border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200),
            border_radius=10,
            heading_row_color=ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100,
            show_bottom_border=True,
        )

        breakdown_table_container.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.PIE_CHART_OUTLINE, size=18, color=ft.Colors.BLUE_700),
                    ft.Text("Tabel Proporsi Pengeluaran & Pengadaan", size=15, weight=ft.FontWeight.W_600),
                ]),
                ft.Container(height=4),
                ft.Row([breakdown_table], scroll=ft.ScrollMode.AUTO),
            ], spacing=6),
            bgcolor=ft.Colors.GREY_900 if is_dark else ft.Colors.WHITE,
            border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_300),
            border_radius=10,
            padding=16,
        )

        # Tab Rincian 1: Kenek Table
        if not kenek_items:
            detail_kenek_container.content = ft.Container(
                content=ft.Text("Tidak ada catatan pengeluaran supir/kenek pada bulan ini.", color=ft.Colors.GREY_500),
                padding=24, alignment=ft.Alignment.CENTER,
            )
        else:
            k_rows = []
            for it in kenek_items:
                tgl = it["tanggal"].strftime("%d-%m-%Y") if hasattr(it["tanggal"], "strftime") else str(it["tanggal"])
                cells = [
                    ft.DataCell(ft.Text(tgl)),
                ]
                if is_pusat:
                    cells.append(ft.DataCell(ft.Text(it.get("nama_cabang", "-"))))
                cells.extend([
                    ft.DataCell(ft.Text(it["nama_personel"], weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(it["peran"])),
                    ft.DataCell(ft.Text(it["kategori_biaya"])),
                    ft.DataCell(ft.Text(it["keterangan"] or "-")),
                    ft.DataCell(ft.Text(rp(it["nominal"]), weight=ft.FontWeight.W_600, color=ft.Colors.RED_600)),
                    ft.DataCell(ft.Text(it["nota"] or "-")),
                ])
                k_rows.append(ft.DataRow(cells=cells))

            k_cols = [ft.DataColumn(ft.Text("Tanggal"))]
            if is_pusat:
                k_cols.append(ft.DataColumn(ft.Text("Cabang")))
            k_cols.extend([
                ft.DataColumn(ft.Text("Nama Personel")),
                ft.DataColumn(ft.Text("Peran")),
                ft.DataColumn(ft.Text("Kategori")),
                ft.DataColumn(ft.Text("Keterangan")),
                ft.DataColumn(ft.Text("Nominal")),
                ft.DataColumn(ft.Text("Nota")),
            ])
            detail_kenek_container.content = ft.Row([
                ft.DataTable(columns=k_cols, rows=k_rows, border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200), border_radius=8, heading_row_color=ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100)
            ], scroll=ft.ScrollMode.AUTO)

        # Tab Rincian 2: Pabrik Table
        if not pabrik_items:
            detail_pabrik_container.content = ft.Container(
                content=ft.Text("Tidak ada data pengambilan pabrik pada bulan ini.", color=ft.Colors.GREY_500),
                padding=24, alignment=ft.Alignment.CENTER,
            )
        else:
            p_rows = []
            for it in pabrik_items:
                tgl = it["tanggal"].strftime("%d-%m-%Y") if hasattr(it["tanggal"], "strftime") else str(it["tanggal"])
                qty_txt = f"{int(it['qty']) if it['qty'].is_integer() else it['qty']} {it['satuan']}"
                cells = [
                    ft.DataCell(ft.Text(tgl)),
                ]
                if is_pusat:
                    cells.append(ft.DataCell(ft.Text(it.get("nama_cabang", "-"))))
                cells.extend([
                    ft.DataCell(ft.Text(it["nama_pabrik"], weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(it["nama_barang"])),
                    ft.DataCell(ft.Text(qty_txt)),
                    ft.DataCell(ft.Text(rp(it["harga_satuan"]))),
                    ft.DataCell(ft.Text(rp(it["total_harga"]), weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_700 if not is_dark else ft.Colors.BLUE_300)),
                    ft.DataCell(ft.Text(it["no_surat_jalan"] or "-")),
                    ft.DataCell(ft.Text(it["status_pembayaran"])),
                ])
                p_rows.append(ft.DataRow(cells=cells))

            p_cols = [ft.DataColumn(ft.Text("Tanggal"))]
            if is_pusat:
                p_cols.append(ft.DataColumn(ft.Text("Cabang")))
            p_cols.extend([
                ft.DataColumn(ft.Text("Pabrik")),
                ft.DataColumn(ft.Text("Nama Barang")),
                ft.DataColumn(ft.Text("Qty")),
                ft.DataColumn(ft.Text("Harga Satuan")),
                ft.DataColumn(ft.Text("Total")),
                ft.DataColumn(ft.Text("No. DO/SJ")),
                ft.DataColumn(ft.Text("Status")),
            ])
            detail_pabrik_container.content = ft.Row([
                ft.DataTable(columns=p_cols, rows=p_rows, border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200), border_radius=8, heading_row_color=ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100)
            ], scroll=ft.ScrollMode.AUTO)

        # Tab Rincian 3: Balaraja Table
        if not balaraja_items:
            detail_balaraja_container.content = ft.Container(
                content=ft.Text("Tidak ada data pengambilan Balaraja pada bulan ini.", color=ft.Colors.GREY_500),
                padding=24, alignment=ft.Alignment.CENTER,
            )
        else:
            b_rows = []
            for it in balaraja_items:
                tgl = it["tanggal"].strftime("%d-%m-%Y") if hasattr(it["tanggal"], "strftime") else str(it["tanggal"])
                qty_txt = f"{int(it['qty']) if it['qty'].is_integer() else it['qty']} {it['satuan']}"
                cells = [
                    ft.DataCell(ft.Text(tgl)),
                ]
                if is_pusat:
                    cells.append(ft.DataCell(ft.Text(it.get("nama_cabang", "-"))))
                cells.extend([
                    ft.DataCell(ft.Text(it["lokasi_gudang"], weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(it["nama_barang"])),
                    ft.DataCell(ft.Text(qty_txt)),
                    ft.DataCell(ft.Text(rp(it["harga_satuan"]))),
                    ft.DataCell(ft.Text(rp(it["total_harga"]), weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_700 if not is_dark else ft.Colors.BLUE_300)),
                    ft.DataCell(ft.Text(it["no_surat_jalan"] or "-")),
                    ft.DataCell(ft.Text(it["driver"] or "-")),
                ])
                b_rows.append(ft.DataRow(cells=cells))

            b_cols = [ft.DataColumn(ft.Text("Tanggal"))]
            if is_pusat:
                b_cols.append(ft.DataColumn(ft.Text("Cabang")))
            b_cols.extend([
                ft.DataColumn(ft.Text("Lokasi Gudang")),
                ft.DataColumn(ft.Text("Nama Barang")),
                ft.DataColumn(ft.Text("Qty")),
                ft.DataColumn(ft.Text("Harga Satuan")),
                ft.DataColumn(ft.Text("Total")),
                ft.DataColumn(ft.Text("No. Surat Jalan")),
                ft.DataColumn(ft.Text("Driver")),
            ])
            detail_balaraja_container.content = ft.Row([
                ft.DataTable(columns=b_cols, rows=b_rows, border=ft.Border.all(0.5, ft.Colors.GREY_700 if is_dark else ft.Colors.GREY_200), border_radius=8, heading_row_color=ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_100)
            ], scroll=ft.ScrollMode.AUTO)

        if page.views:
            page.update()

    # Export PDF Picker & Handler
    export_picker = ft.FilePicker()
    if export_picker not in page.services:
        page.services.append(export_picker)

    async def export_pdf(e):
        bulan = filter_state["bulan"]
        tahun = filter_state["tahun"]
        cabang_id = filter_state["cabang_id"]
        bulan_nama = MONTH[bulan]

        kenek_items = get_pengeluaran_supir_kenek(cabang_id=cabang_id, bulan=bulan, tahun=tahun, sort_order="desc")
        pabrik_items = get_pengambilan_pabrik(cabang_id=cabang_id, bulan=bulan, tahun=tahun, sort_order="desc")
        balaraja_items = get_pengambilan_balaraja(cabang_id=cabang_id, bulan=bulan, tahun=tahun, sort_order="desc")

        if not kenek_items and not pabrik_items and not balaraja_items:
            page.show_dialog(ft.SnackBar(ft.Text("Tidak ada data rekap bulanan pada periode ini untuk diexport."), bgcolor=ft.Colors.RED_400))
            return

        kenek_sum = sum(it["nominal"] for it in kenek_items)
        pabrik_sum = sum(it["total_harga"] for it in pabrik_items)
        pabrik_qty = sum(it["qty"] for it in pabrik_items)
        balaraja_sum = sum(it["total_harga"] for it in balaraja_items)
        balaraja_qty = sum(it["qty"] for it in balaraja_items)
        grand_total = kenek_sum + pabrik_sum + balaraja_sum

        rekap_data = {
            "kenek": {"items": kenek_items, "total": kenek_sum},
            "pabrik": {"items": pabrik_items, "total": pabrik_sum, "qty": pabrik_qty},
            "balaraja": {"items": balaraja_items, "total": balaraja_sum, "qty": balaraja_qty},
            "grand_total": grand_total,
        }

        cbg_name = "Semua Cabang"
        if filter_state["cabang_id"]:
            cbg_name = next((c[1] for c in cabang_list if c[0] == filter_state["cabang_id"]), f"Cabang {filter_state['cabang_id']}")
        elif not is_pusat:
            cbg_name = actor.get("nama_cabang", "Cabang")

        filter_info = {
            "periode": f"{bulan_nama} {tahun}",
            "cabang": cbg_name,
            "extra": f"Grand Total: {rp(grand_total)}",
        }

        nama_file_default = f"Rekap_Bulanan_{tahun}_{bulan:02d}_{cbg_name.replace(' ', '_')}.pdf"
        try:
            if page.platform == ft.PagePlatform.ANDROID or page.platform == ft.PagePlatform.IOS:
                pdf_bytes = generate_rekap_bulanan_pdf(rekap_data, filter_info, is_pusat=is_pusat, output_path=None)
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Rekap Bulanan PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
                if not save_path:
                    return
            else:
                save_path = await export_picker.save_file(
                    dialog_title="Simpan Laporan Rekap Bulanan PDF",
                    file_name=nama_file_default,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                )
                if not save_path:
                    return
                if not save_path.lower().endswith(".pdf"):
                    save_path += ".pdf"
                generate_rekap_bulanan_pdf(rekap_data, filter_info, is_pusat=is_pusat, output_path=save_path)

            log_activity(
                actor.get("id"),
                actor.get("username", "user"),
                "CREATE",
                "export_pdf",
                filter_state.get("cabang_id") or 0,
                f"Export PDF Rekap Bulanan ({bulan_nama} {tahun})",
                filter_state.get("cabang_id"),
            )
            page.show_dialog(ft.SnackBar(ft.Text(f"PDF berhasil disimpan: {save_path}"), bgcolor=ft.Colors.GREEN_700))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(ft.Text(f"Gagal export PDF: {ex}"), bgcolor=ft.Colors.RED_400))

    # Initial calculation
    refresh_rekap()

    tab_views = [
        ft.Container(
            content=ft.Column([
                ft.Container(height=12),
                ft.ResponsiveRow([
                    ft.Container(content=chart_container, col={"xs": 12, "md": 5}),
                    ft.Container(content=breakdown_table_container, col={"xs": 12, "md": 7}),
                ], spacing=16, run_spacing=16),
            ]),
            padding=ft.Padding.only(top=8),
        ),
        ft.Container(
            content=ft.Column([
                ft.Container(height=12),
                detail_kenek_container,
            ]),
            padding=ft.Padding.only(top=8),
        ),
        ft.Container(
            content=ft.Column([
                ft.Container(height=12),
                detail_pabrik_container,
            ]),
            padding=ft.Padding.only(top=8),
        ),
        ft.Container(
            content=ft.Column([
                ft.Container(height=12),
                detail_balaraja_container,
            ]),
            padding=ft.Padding.only(top=8),
        ),
    ]

    active_tab_container = ft.Container(content=tab_views[0])

    def on_tab_change(e):
        idx = int(e.data)
        active_tab_container.content = tab_views[idx]
        active_tab_container.update()

    tabs = ft.Tabs(
        length=4,
        selected_index=0,
        animation_duration=200,
        on_change=on_tab_change,
        content=ft.TabBar(
            tabs=[
                ft.Tab(label="Ringkasan & Komposisi", icon=ft.Icons.ANALYTICS),
                ft.Tab(label="Rincian Operasional Kenek/Supir", icon=ft.Icons.LOCAL_SHIPPING),
                ft.Tab(label="Rincian Pengambilan Pabrik", icon=ft.Icons.FACTORY),
                ft.Tab(label="Rincian Pengambilan Balaraja", icon=ft.Icons.WAREHOUSE),
            ]
        ),
    )

    body = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Rekap Bulanan Gabungan", size=22, weight=ft.FontWeight.W_600),
                ft.Text("Konsolidasi bulanan operasional kenek/supir, pengambilan pabrik, dan pengambilan Balaraja.", size=13, color=ft.Colors.GREY_500),
            ], expand=True),
            ft.OutlinedButton(
                "Export ke PDF",
                icon=ft.Icons.PICTURE_AS_PDF,
                on_click=export_pdf,
            ),
            ft.IconButton(
                ft.Icons.REFRESH,
                tooltip="Segarkan Rekap",
                on_click=lambda e: refresh_rekap(),
            ),
        ]),
        ft.Container(height=8),
        filter_card,
        ft.Container(height=12),
        ft.ResponsiveRow([
            metric_kenek_card,
            metric_pabrik_card,
            metric_balaraja_card,
            metric_grand_card,
        ], spacing=12, run_spacing=12),
        ft.Container(height=12),
        tabs,
        active_tab_container,
        ft.Container(height=24),
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    return body
