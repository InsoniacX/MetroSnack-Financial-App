from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from utils.formatting import rp
from utils.hutang_calc import hutang_amount
from io import BytesIO
from datetime import datetime, date
from decimal import Decimal

_styles = getSampleStyleSheet()

# --- Legacy Styles (for Invoice & Cabang existing reports) ---
_style_invoice_title = ParagraphStyle(
    "InvoiceTitle", parent=_styles["Heading3"], textColor=colors.HexColor("#1565C0"), spaceBefore=14
)
_style_small = ParagraphStyle("SmallGrey", parent=_styles["Normal"], textColor=colors.grey, fontSize=9)

# --- Standard Report Typography ---
_style_title = ParagraphStyle(
    "ReportTitle",
    parent=_styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=18,
    textColor=colors.HexColor("#1A237E"),
    alignment=0,
    spaceAfter=3,
)

_style_subtitle = ParagraphStyle(
    "ReportSubtitle",
    parent=_styles["Normal"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=12,
    textColor=colors.HexColor("#455A64"),
    spaceAfter=8,
)

_style_section_heading = ParagraphStyle(
    "ReportSectionHeading",
    parent=_styles["Heading3"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=13,
    textColor=colors.HexColor("#0D47A1"),
    spaceBefore=8,
    spaceAfter=4,
)

_style_th = ParagraphStyle(
    "TableHead",
    parent=_styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    textColor=colors.white,
    alignment=1,
)

_style_cell_left = ParagraphStyle(
    "CellLeft",
    parent=_styles["Normal"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=9.5,
    alignment=0,
)

_style_cell_center = ParagraphStyle(
    "CellCenter",
    parent=_styles["Normal"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=9.5,
    alignment=1,
)

_style_cell_right = ParagraphStyle(
    "CellRight",
    parent=_styles["Normal"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=9.5,
    alignment=2,
)

_style_cell_bold_left = ParagraphStyle(
    "CellBoldLeft",
    parent=_styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=7.5,
    leading=9.5,
    alignment=0,
)

_style_cell_bold_center = ParagraphStyle(
    "CellBoldCenter",
    parent=_styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=7.5,
    leading=9.5,
    alignment=1,
)

_style_cell_bold_right = ParagraphStyle(
    "CellBoldRight",
    parent=_styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=7.5,
    leading=9.5,
    alignment=2,
)


def _format_date_val(d):
    if not d:
        return "-"
    if hasattr(d, "strftime"):
        return d.strftime("%d-%m-%Y")
    if isinstance(d, str):
        try:
            return datetime.strptime(d[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
        except Exception:
            return d
    return str(d)


def _build_kpi_table(cards, total_width_cm=27.3):
    """
    Membuat kartu metrik horizontal.
    cards: list of tuple (title, value, text_color_hex, bg_color_hex)
    """
    if not cards:
        return Spacer(1, 1)
    col_w = (total_width_cm * cm) / len(cards)
    headers = []
    vals = []
    for c in cards:
        title, val, text_c, _ = c
        headers.append(Paragraph(f"<font size='7' color='#546E7A'><b>{title.upper()}</b></font>", _style_cell_center))
        vals.append(Paragraph(f"<font size='9.5' color='{text_c}'><b>{val}</b></font>", _style_cell_center))

    t = Table([headers, vals], colWidths=[col_w] * len(cards))
    t_style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD8DC")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for idx, c in enumerate(cards):
        bg_c = c[3]
        t_style.append(("BACKGROUND", (idx, 0), (idx, 1), colors.HexColor(bg_c)))
    t.setStyle(TableStyle(t_style))
    return t


def _build_header_elements(title, filter_info, is_landscape=False):
    """Membangun header judul dan ringkasan filter/metadata."""
    now_str = datetime.now().strftime("%d-%m-%Y %H:%M")
    elements = [
        Paragraph(title, _style_title),
    ]
    meta_parts = []
    if filter_info.get("periode"):
        meta_parts.append(f"<b>Periode:</b> {filter_info['periode']}")
    if filter_info.get("cabang"):
        meta_parts.append(f"<b>Cabang:</b> {filter_info['cabang']}")
    if filter_info.get("extra"):
        meta_parts.append(filter_info["extra"])
    meta_parts.append(f"<b>Dicetak:</b> {now_str}")

    elements.append(Paragraph(" &nbsp;|&nbsp; ".join(meta_parts), _style_subtitle))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#B0BEC5"), spaceAfter=8))
    return elements


# =========================================================================
# 1. INVOICE & FOLDER & CABANG (EXISTING IMPLEMENTATION)
# =========================================================================

def _transaksi_table(transaksi):
    """Table detail transaksi harian (Tanggal, Masuk Barang, Masuk Uang, Lebih/Kurang, Keterangan, Nota).
    transaksi: list tuple (id, tanggal, masuk_barang, masuk_uang, lebih_kurang, keterangan, nota)
    -> hasil dari db.transaksi_repo.get_transaksi()"""
    data = [["Tanggal", "Masuk Barang", "Masuk Uang", "Lebih/Kurang", "Ket.", "Nota"]]
    for t in transaksi:
        _, tgl, mbarang, muang, lk, ket, nota = t
        data.append([
            tgl.strftime("%d-%m-%Y") if tgl else "-",
            rp(mbarang), rp(muang), rp(lk), ket or "-", nota or "-",
        ])

    table = Table(data, colWidths=[2.3 * cm, 2.8 * cm, 2.8 * cm, 2.8 * cm, 2.3 * cm, 3.3 * cm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#455A64")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 1), (3, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
    ]
    for i, t in enumerate(transaksi, start=1):
        ket = t[5]
        bg = colors.HexColor("#E8F5E9") if ket == "Lebih Uang" else colors.HexColor("#FFEBEE")
        style.append(("BACKGROUND", (0, i), (-1, i), bg))
    table.setStyle(TableStyle(style))
    return table


def _ringkasan_paragraph(sisa_hutang, omset, laba_bersih):
    nilai, is_lunas = hutang_amount(sisa_hutang)
    warna_hex = "#2E7D32" if is_lunas else "#C62828"
    label = "Lunas" if is_lunas else "Masih Ada Hutang"
    return Paragraph(
        f"<b>Sisa Hutang Toko:</b> <font color='{warna_hex}'>{rp(nilai)} ({label})</font> &nbsp;&nbsp; "
        f"<b>Omset:</b> {rp(omset)} &nbsp;&nbsp; <b>Laba Bersih:</b> {rp(laba_bersih)}",
        _styles["Normal"],
    )


def generate_invoice_pdf(invoice_header, transaksi, output_path=None):
    """
    invoice_header: tuple (id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, folder_bulan_id, cabang_id, sisa_barang_manual)
    -> hasil dari db.invoice_repo.get_invoice_header() / get_invoice_full()
    transaksi: list tuple (id, tanggal, masuk_barang, masuk_uang, lebih_kurang, keterangan, nota)
    -> hasil dari db.transaksi_repo.get_transaksi()
    """
    iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, _folder_id, _cabang_id, sisa_barang_manual = invoice_header

    total_uang = sum(t[3] for t in transaksi) if transaksi else 0
    total_barang = sum(t[2] for t in transaksi) if transaksi else 0
    laba_bersih = total_uang - total_barang
    sisa_hutang = (invoice_bon or 0) + total_barang - total_uang
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer

    doc = SimpleDocTemplate(target, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    elements = [
        Paragraph(f"Detail Invoice - {no_laporan or f'#{iid}'}", _styles["Title"]),
        Paragraph(
            f"Date: {tgl_dibuat.strftime('%d-%m-%Y') if tgl_dibuat else '-'} &nbsp;&nbsp; "
            f"TGL Laporan: {tgl_laporan.strftime('%d-%m-%Y') if tgl_laporan else '-'} &nbsp;&nbsp; "
            f"Invoice/Bon: {rp(invoice_bon)}",
            _style_small,
        ),
        Spacer(1, 14),
        Paragraph("Transaksi Harian", _style_invoice_title),
        Spacer(1, 6),
        _transaksi_table(transaksi) if transaksi else Paragraph("Belum ada transaksi.", _style_small),
        Spacer(1, 16),
        _ringkasan_paragraph(sisa_hutang, total_uang, laba_bersih),
    ]
    doc.build(elements)

    if output_path is None:
        return buffer.getvalue()


def _folder_section_elements(nama_folder, invoices_with_transaksi, heading_style):
    elements = []
    elements.append(Paragraph(nama_folder, heading_style))
    elements.append(Spacer(1, 8))

    data = [["No.", "TGL Laporan", "Invoice/Bon", "Omset", "Laba Bersih", "Sisa Hutang"]]
    total_omzet_all = 0
    total_laba_all = 0
    total_hutang_all = 0

    for item in invoices_with_transaksi:
        iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, total_omzet, total_barang = item["header"]
        laba_bersih = total_omzet - total_barang
        sisa_hutang = (invoice_bon or 0) + total_barang - total_omzet
        data.append([
            no_laporan or "-",
            tgl_laporan.strftime("%d-%m-%Y") if tgl_laporan else "-",
            rp(invoice_bon), rp(total_omzet), rp(laba_bersih), rp(sisa_hutang),
        ])
        total_omzet_all += total_omzet
        total_laba_all += laba_bersih
        total_hutang_all += sisa_hutang

    data.append(["TOTAL", "", "", rp(total_omzet_all), rp(total_laba_all), rp(total_hutang_all)])

    table = Table(data, colWidths=[2.5 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E3F2FD")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Detail Transaksi per Invoice", _styles["Heading3"]))

    for item in invoices_with_transaksi:
        iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, total_omzet, total_barang = item["header"]
        transaksi = item.get("transaksi", [])
        laba_bersih = total_omzet - total_barang
        sisa_hutang = (invoice_bon or 0) + total_barang - total_omzet

        elements.append(Paragraph(
            f"Invoice {no_laporan or f'#{iid}'} — TGL Laporan: "
            f"{tgl_laporan.strftime('%d-%m-%Y') if tgl_laporan else '-'} — Invoice/Bon: {rp(invoice_bon)}",
            _style_invoice_title,
        ))
        elements.append(Spacer(1, 4))
        if transaksi:
            elements.append(_transaksi_table(transaksi))
        else:
            elements.append(Paragraph("Belum ada transaksi pada invoice ini.", _style_small))
        elements.append(Spacer(1, 6))
        elements.append(_ringkasan_paragraph(sisa_hutang, total_omzet, laba_bersih))
        elements.append(Spacer(1, 10))

    return elements, total_omzet_all, total_laba_all, total_hutang_all


def generate_folder_pdf(nama_folder, invoices_with_transaksi, output_path=None):
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(target, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    elements = [Paragraph(f"Laporan Keuangan - {nama_folder}", _styles["Title"]), Spacer(1, 12)]

    section_elements, _, _, _ = _folder_section_elements(nama_folder, invoices_with_transaksi, _styles["Heading2"])
    elements.extend(section_elements[2:] if len(section_elements) > 2 else section_elements)

    doc.build(elements)
    if output_path is None:
        return buffer.getvalue()


def generate_cabang_pdf(nama_cabang, folders_data, output_path=None):
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(target, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    elements = [Paragraph(f"Laporan Keuangan Cabang - {nama_cabang}", _styles["Title"]), Spacer(1, 4)]

    grand_omzet = 0
    grand_laba = 0
    grand_hutang = 0
    all_sections = []

    for f in folders_data:
        section_elements, omzet_all, laba_all, hutang_all = _folder_section_elements(
            f["nama_folder"], f["invoices_with_transaksi"], _styles["Heading2"],
        )
        all_sections.append(section_elements)
        grand_omzet += omzet_all
        grand_laba += laba_all
        grand_hutang += hutang_all

    elements.append(Paragraph(
        f"<b>Total {len(folders_data)} periode:</b> Omset {rp(grand_omzet)} &nbsp;&nbsp; "
        f"Laba Bersih {rp(grand_laba)} &nbsp;&nbsp; Sisa Hutang {rp(grand_hutang)}",
        _styles["Normal"],
    ))
    elements.append(Spacer(1, 16))

    for idx, section_elements in enumerate(all_sections):
        if idx > 0:
            elements.append(PageBreak())
        elements.extend(section_elements)

    doc.build(elements)
    if output_path is None:
        return buffer.getvalue()


# =========================================================================
# 2. PENDAPATAN & PENGELUARAN KAS PDF EXPORT
# =========================================================================

def generate_pendapatan_pengeluaran_pdf(items, filter_info, is_pusat=False, output_path=None):
    """
    items: list of dict -> hasil dari db.pendapatan_pengeluaran_repo.get_transaksi_kas()
    filter_info: dict {"periode": str, "cabang": str, "extra": str}
    """
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(
        target,
        pagesize=A4,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
    )

    elements = _build_header_elements("Laporan Pendapatan & Pengeluaran Kas", filter_info)

    # Hitung Metrik
    total_pendapatan = sum([it["nominal"] for it in items if it.get("jenis") == "Pendapatan"])
    total_pengeluaran = sum([it["nominal"] for it in items if it.get("jenis") == "Pengeluaran"])
    saldo_bersih = total_pendapatan - total_pengeluaran
    count_trx = len(items)

    kpi_cards = [
        ("Total Pendapatan", rp(total_pendapatan), "#2E7D32", "#E8F5E9"),
        ("Total Pengeluaran", rp(total_pengeluaran), "#C62828", "#FFEBEE"),
        ("Saldo Kas Bersih", rp(saldo_bersih), "#1565C0" if saldo_bersih >= 0 else "#C62828", "#E3F2FD" if saldo_bersih >= 0 else "#FFEBEE"),
        ("Jumlah Transaksi", f"{count_trx} Transaksi", "#37474F", "#ECEFF1"),
    ]
    elements.append(_build_kpi_table(kpi_cards, total_width_cm=18.6))
    elements.append(Spacer(1, 10))

    # Build Table
    if is_pusat:
        headers = ["No", "Tanggal", "Cabang", "Jenis", "Kategori", "Keterangan", "Nota", "Nominal"]
        col_widths = [0.9 * cm, 2.1 * cm, 2.4 * cm, 2.2 * cm, 2.8 * cm, 3.8 * cm, 1.8 * cm, 2.6 * cm]
    else:
        headers = ["No", "Tanggal", "Jenis", "Kategori", "Keterangan", "Nota", "Nominal"]
        col_widths = [1.0 * cm, 2.3 * cm, 2.4 * cm, 3.2 * cm, 4.6 * cm, 2.2 * cm, 2.9 * cm]

    header_row = [Paragraph(f"<b>{h}</b>", _style_th) for h in headers]
    data = [header_row]

    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]

    for idx, it in enumerate(items, start=1):
        tgl_str = _format_date_val(it.get("tanggal"))
        jenis = it.get("jenis", "Pendapatan")
        is_in = (jenis == "Pendapatan")
        nom_prefix = "+" if is_in else "-"
        nom_color = "#2E7D32" if is_in else "#C62828"
        bg_row = "#F9FBE7" if is_in else "#FFF9C4" if idx % 2 == 0 else "#FFFFFF"

        if is_pusat:
            row = [
                Paragraph(str(idx), _style_cell_center),
                Paragraph(tgl_str, _style_cell_center),
                Paragraph(it.get("nama_cabang", "-"), _style_cell_left),
                Paragraph(f"<font color='{nom_color}'><b>{jenis}</b></font>", _style_cell_center),
                Paragraph(it.get("kategori", "-"), _style_cell_left),
                Paragraph(it.get("keterangan", "-") or "-", _style_cell_left),
                Paragraph(it.get("nota", "-") or "-", _style_cell_center),
                Paragraph(f"<font color='{nom_color}'><b>{nom_prefix}{rp(it['nominal'])}</b></font>", _style_cell_right),
            ]
        else:
            row = [
                Paragraph(str(idx), _style_cell_center),
                Paragraph(tgl_str, _style_cell_center),
                Paragraph(f"<font color='{nom_color}'><b>{jenis}</b></font>", _style_cell_center),
                Paragraph(it.get("kategori", "-"), _style_cell_left),
                Paragraph(it.get("keterangan", "-") or "-", _style_cell_left),
                Paragraph(it.get("nota", "-") or "-", _style_cell_center),
                Paragraph(f"<font color='{nom_color}'><b>{nom_prefix}{rp(it['nominal'])}</b></font>", _style_cell_right),
            ]

        data.append(row)
        if is_in:
            table_style.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#F1F8E9" if idx % 2 == 0 else "#FFFFFF")))
        else:
            table_style.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#FFEBEE" if idx % 2 == 0 else "#FFFFFF")))

    # Summary Row
    span_col = len(headers) - 2
    summary_row = [
        Paragraph("<b>SALDO KAS BERSIH</b>", _style_cell_bold_left),
    ] + [Paragraph("", _style_cell_left)] * (span_col - 1) + [
        Paragraph("", _style_cell_left),
        Paragraph(f"<b>{rp(saldo_bersih)}</b>", _style_cell_bold_right),
    ]
    data.append(summary_row)
    last_row_idx = len(data) - 1
    table_style.extend([
        ("SPAN", (0, last_row_idx), (span_col, last_row_idx)),
        ("BACKGROUND", (0, last_row_idx), (-1, last_row_idx), colors.HexColor("#E3F2FD")),
        ("TOPPADDING", (0, last_row_idx), (-1, last_row_idx), 5),
        ("BOTTOMPADDING", (0, last_row_idx), (-1, last_row_idx), 5),
    ])

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(table_style))
    elements.append(table)

    doc.build(elements)
    if output_path is None:
        return buffer.getvalue()


# =========================================================================
# 3. PENGAMBILAN BALARAJA PDF EXPORT
# =========================================================================

def generate_pengambilan_balaraja_pdf(items, filter_info, is_pusat=False, output_path=None):
    """
    items: list of dict -> hasil dari db.pengambilan_balaraja_repo.get_pengambilan_balaraja()
    filter_info: dict {"periode": str, "cabang": str, "extra": str}
    """
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(
        target,
        pagesize=landscape(A4),
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
    )

    elements = _build_header_elements("Laporan Pengambilan Barang Balaraja", filter_info, is_landscape=True)

    # Metrik
    total_nominal = sum([it.get("total_harga", 0) for it in items])
    total_qty = sum([it.get("qty", 0) for it in items])
    count_trx = len(items)
    avg_per_trx = (total_nominal / count_trx) if count_trx > 0 else 0

    kpi_cards = [
        ("Total Biaya Pengambilan", rp(total_nominal), "#E65100", "#FFF3E0"),
        ("Total Volume / Qty", f"{total_qty:,.0f} Item", "#0277BD", "#E1F5FE"),
        ("Rata-Rata per Transaksi", rp(avg_per_trx), "#455A64", "#ECEFF1"),
        ("Jumlah Transaksi", f"{count_trx} Transaksi", "#37474F", "#ECEFF1"),
    ]
    elements.append(_build_kpi_table(kpi_cards, total_width_cm=27.3))
    elements.append(Spacer(1, 10))

    if is_pusat:
        headers = ["No", "Tanggal", "Cabang", "Lokasi Gudang", "Nama Barang & Kategori", "Qty", "Harga Satuan", "Total Harga", "No. SJ", "Driver / Armada"]
        col_widths = [0.9 * cm, 2.2 * cm, 2.6 * cm, 3.2 * cm, 4.8 * cm, 2.0 * cm, 2.6 * cm, 3.0 * cm, 2.8 * cm, 3.2 * cm]
    else:
        headers = ["No", "Tanggal", "Lokasi Gudang", "Nama Barang & Kategori", "Qty", "Harga Satuan", "Total Harga", "No. SJ", "Driver / Armada"]
        col_widths = [1.0 * cm, 2.3 * cm, 3.6 * cm, 5.4 * cm, 2.2 * cm, 2.8 * cm, 3.2 * cm, 3.2 * cm, 3.6 * cm]

    header_row = [Paragraph(f"<b>{h}</b>", _style_th) for h in headers]
    data = [header_row]

    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D84315")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]

    for idx, it in enumerate(items, start=1):
        tgl_str = _format_date_val(it.get("tanggal"))
        bg_row = colors.HexColor("#FFF8E1" if idx % 2 == 0 else "#FFFFFF")
        table_style.append(("BACKGROUND", (0, idx), (-1, idx), bg_row))

        barang_info = f"<b>{it.get('nama_barang', '-')}</b><br/><font size='6.5' color='#78909C'>{it.get('kategori_barang', '-')}</font>"
        qty_str = f"{it.get('qty', 0):,.0f} {it.get('satuan', '')}"

        if is_pusat:
            row = [
                Paragraph(str(idx), _style_cell_center),
                Paragraph(tgl_str, _style_cell_center),
                Paragraph(it.get("nama_cabang", "-"), _style_cell_left),
                Paragraph(it.get("lokasi_gudang", "-"), _style_cell_left),
                Paragraph(barang_info, _style_cell_left),
                Paragraph(qty_str, _style_cell_center),
                Paragraph(rp(it.get("harga_satuan", 0)), _style_cell_right),
                Paragraph(f"<b>{rp(it.get('total_harga', 0))}</b>", _style_cell_right),
                Paragraph(it.get("no_surat_jalan", "-") or "-", _style_cell_center),
                Paragraph(it.get("driver", "-") or "-", _style_cell_left),
            ]
        else:
            row = [
                Paragraph(str(idx), _style_cell_center),
                Paragraph(tgl_str, _style_cell_center),
                Paragraph(it.get("lokasi_gudang", "-"), _style_cell_left),
                Paragraph(barang_info, _style_cell_left),
                Paragraph(qty_str, _style_cell_center),
                Paragraph(rp(it.get("harga_satuan", 0)), _style_cell_right),
                Paragraph(f"<b>{rp(it.get('total_harga', 0))}</b>", _style_cell_right),
                Paragraph(it.get("no_surat_jalan", "-") or "-", _style_cell_center),
                Paragraph(it.get("driver", "-") or "-", _style_cell_left),
            ]
        data.append(row)

    # Footer Total
    span_col = 4 if is_pusat else 3
    footer_row = [
        Paragraph("<b>TOTAL KESELURUHAN</b>", _style_cell_bold_left),
    ] + [Paragraph("", _style_cell_left)] * span_col + [
        Paragraph(f"<b>{total_qty:,.0f} Qty</b>", _style_cell_bold_center),
        Paragraph("", _style_cell_left),
        Paragraph(f"<b>{rp(total_nominal)}</b>", _style_cell_bold_right),
        Paragraph("", _style_cell_left),
        Paragraph("", _style_cell_left),
    ]
    data.append(footer_row)
    last_row_idx = len(data) - 1
    table_style.extend([
        ("SPAN", (0, last_row_idx), (span_col, last_row_idx)),
        ("BACKGROUND", (0, last_row_idx), (-1, last_row_idx), colors.HexColor("#FFE082")),
        ("TOPPADDING", (0, last_row_idx), (-1, last_row_idx), 4.5),
        ("BOTTOMPADDING", (0, last_row_idx), (-1, last_row_idx), 4.5),
    ])

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(table_style))
    elements.append(table)

    doc.build(elements)
    if output_path is None:
        return buffer.getvalue()


# =========================================================================
# 4. PENGAMBILAN PABRIK PDF EXPORT
# =========================================================================

def generate_pengambilan_pabrik_pdf(items, filter_info, is_pusat=False, output_path=None):
    """
    items: list of dict -> hasil dari db.pengambilan_pabrik_repo.get_pengambilan_pabrik()
    filter_info: dict {"periode": str, "cabang": str, "extra": str}
    """
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(
        target,
        pagesize=landscape(A4),
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
    )

    elements = _build_header_elements("Laporan Pengambilan Barang Pabrik", filter_info, is_landscape=True)

    # Metrik
    total_nominal = sum([it.get("total_harga", 0) for it in items])
    total_qty = sum([it.get("qty", 0) for it in items])
    total_lunas = sum([it.get("total_harga", 0) for it in items if it.get("status_pembayaran") == "Lunas"])
    total_tempo = sum([it.get("total_harga", 0) for it in items if it.get("status_pembayaran") != "Lunas"])

    kpi_cards = [
        ("Total Pembelian Pabrik", rp(total_nominal), "#1A237E", "#E8EAF6"),
        ("Total Volume / Qty", f"{total_qty:,.0f} Item", "#00695C", "#E0F2F1"),
        ("Status Lunas", rp(total_lunas), "#2E7D32", "#E8F5E9"),
        ("Status Hutang / Tempo", rp(total_tempo), "#C62828", "#FFEBEE"),
    ]
    elements.append(_build_kpi_table(kpi_cards, total_width_cm=27.3))
    elements.append(Spacer(1, 10))

    if is_pusat:
        headers = ["No", "Tanggal", "Cabang", "Pabrik / Supplier", "Nama Barang & Kategori", "Qty", "Harga Satuan", "Total Harga", "No. DO/SJ", "Status Bayar"]
        col_widths = [0.9 * cm, 2.2 * cm, 2.6 * cm, 3.6 * cm, 4.8 * cm, 2.0 * cm, 2.6 * cm, 3.0 * cm, 2.8 * cm, 2.8 * cm]
    else:
        headers = ["No", "Tanggal", "Pabrik / Supplier", "Nama Barang & Kategori", "Qty", "Harga Satuan", "Total Harga", "No. DO/SJ", "Status Bayar"]
        col_widths = [1.0 * cm, 2.4 * cm, 4.0 * cm, 5.4 * cm, 2.2 * cm, 2.8 * cm, 3.2 * cm, 3.1 * cm, 3.2 * cm]

    header_row = [Paragraph(f"<b>{h}</b>", _style_th) for h in headers]
    data = [header_row]

    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#283593")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]

    for idx, it in enumerate(items, start=1):
        tgl_str = _format_date_val(it.get("tanggal"))
        bg_row = colors.HexColor("#E8EAF6" if idx % 2 == 0 else "#FFFFFF")
        table_style.append(("BACKGROUND", (0, idx), (-1, idx), bg_row))

        barang_info = f"<b>{it.get('nama_barang', '-')}</b><br/><font size='6.5' color='#78909C'>{it.get('kategori_barang', '-')}</font>"
        qty_str = f"{it.get('qty', 0):,.0f} {it.get('satuan', '')}"
        st_bayar = it.get("status_pembayaran", "Lunas")
        st_color = "#2E7D32" if st_bayar == "Lunas" else "#C62828"

        if is_pusat:
            row = [
                Paragraph(str(idx), _style_cell_center),
                Paragraph(tgl_str, _style_cell_center),
                Paragraph(it.get("nama_cabang", "-"), _style_cell_left),
                Paragraph(it.get("nama_pabrik", "-"), _style_cell_left),
                Paragraph(barang_info, _style_cell_left),
                Paragraph(qty_str, _style_cell_center),
                Paragraph(rp(it.get("harga_satuan", 0)), _style_cell_right),
                Paragraph(f"<b>{rp(it.get('total_harga', 0))}</b>", _style_cell_right),
                Paragraph(it.get("no_surat_jalan", "-") or "-", _style_cell_center),
                Paragraph(f"<font color='{st_color}'><b>{st_bayar}</b></font>", _style_cell_center),
            ]
        else:
            row = [
                Paragraph(str(idx), _style_cell_center),
                Paragraph(tgl_str, _style_cell_center),
                Paragraph(it.get("nama_pabrik", "-"), _style_cell_left),
                Paragraph(barang_info, _style_cell_left),
                Paragraph(qty_str, _style_cell_center),
                Paragraph(rp(it.get("harga_satuan", 0)), _style_cell_right),
                Paragraph(f"<b>{rp(it.get('total_harga', 0))}</b>", _style_cell_right),
                Paragraph(it.get("no_surat_jalan", "-") or "-", _style_cell_center),
                Paragraph(f"<font color='{st_color}'><b>{st_bayar}</b></font>", _style_cell_center),
            ]
        data.append(row)

    # Footer Total
    span_col = 4 if is_pusat else 3
    footer_row = [
        Paragraph("<b>TOTAL KESELURUHAN</b>", _style_cell_bold_left),
    ] + [Paragraph("", _style_cell_left)] * span_col + [
        Paragraph(f"<b>{total_qty:,.0f} Qty</b>", _style_cell_bold_center),
        Paragraph("", _style_cell_left),
        Paragraph(f"<b>{rp(total_nominal)}</b>", _style_cell_bold_right),
        Paragraph("", _style_cell_left),
        Paragraph("", _style_cell_left),
    ]
    data.append(footer_row)
    last_row_idx = len(data) - 1
    table_style.extend([
        ("SPAN", (0, last_row_idx), (span_col, last_row_idx)),
        ("BACKGROUND", (0, last_row_idx), (-1, last_row_idx), colors.HexColor("#C5CAE9")),
        ("TOPPADDING", (0, last_row_idx), (-1, last_row_idx), 4.5),
        ("BOTTOMPADDING", (0, last_row_idx), (-1, last_row_idx), 4.5),
    ])

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(table_style))
    elements.append(table)

    doc.build(elements)
    if output_path is None:
        return buffer.getvalue()


# =========================================================================
# 5. OPERASIONAL SUPIR & KENEK PDF EXPORT
# =========================================================================

def generate_supir_kenek_pdf(items, filter_info, is_pusat=False, output_path=None):
    """
    items: list of dict -> hasil dari db.supir_kenek_repo.get_pengeluaran_supir_kenek()
    filter_info: dict {"periode": str, "cabang": str, "extra": str}
    """
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(
        target,
        pagesize=landscape(A4),
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
    )

    elements = _build_header_elements("Laporan Operasional Supir & Kenek", filter_info, is_landscape=True)

    # Metrik
    total_nominal = sum([it.get("nominal", 0) for it in items])
    total_jalan = sum([it.get("nominal", 0) for it in items if "jalan" in str(it.get("kategori_biaya", "")).lower()])
    total_bbm = sum([
        it.get("nominal", 0)
        for it in items
        if "bbm" in str(it.get("kategori_biaya", "")).lower() or "bensin" in str(it.get("kategori_biaya", "")).lower() or "tol" in str(it.get("kategori_biaya", "")).lower()
    ])
    count_trx = len(items)

    kpi_cards = [
        ("Total Operasional", rp(total_nominal), "#37474F", "#ECEFF1"),
        ("Total Uang Jalan", rp(total_jalan), "#1565C0", "#E3F2FD"),
        ("Total BBM & Tol", rp(total_bbm), "#E65100", "#FFF3E0"),
        ("Jumlah Transaksi", f"{count_trx} Transaksi", "#00695C", "#E0F2F1"),
    ]
    elements.append(_build_kpi_table(kpi_cards, total_width_cm=27.3))
    elements.append(Spacer(1, 10))

    if is_pusat:
        headers = ["No", "Tanggal", "Cabang", "Supir / Kenek", "Kategori Biaya", "Keterangan / Rute", "No. Bukti / Nota", "Nominal (Rp)"]
        col_widths = [0.9 * cm, 2.2 * cm, 2.8 * cm, 3.8 * cm, 3.4 * cm, 7.8 * cm, 3.2 * cm, 3.2 * cm]
    else:
        headers = ["No", "Tanggal", "Supir / Kenek", "Kategori Biaya", "Keterangan / Rute", "No. Bukti / Nota", "Nominal (Rp)"]
        col_widths = [1.0 * cm, 2.4 * cm, 4.4 * cm, 3.8 * cm, 8.8 * cm, 3.4 * cm, 3.5 * cm]

    header_row = [Paragraph(f"<b>{h}</b>", _style_th) for h in headers]
    data = [header_row]

    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474F")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]

    for idx, it in enumerate(items, start=1):
        tgl_str = _format_date_val(it.get("tanggal"))
        bg_row = colors.HexColor("#F5F5F5" if idx % 2 == 0 else "#FFFFFF")
        table_style.append(("BACKGROUND", (0, idx), (-1, idx), bg_row))

        personel_info = f"<b>{it.get('nama_personel', '-')}</b> <font size='6.5' color='#78909C'>({it.get('peran', 'Supir')})</font>"

        if is_pusat:
            row = [
                Paragraph(str(idx), _style_cell_center),
                Paragraph(tgl_str, _style_cell_center),
                Paragraph(it.get("nama_cabang", "-"), _style_cell_left),
                Paragraph(personel_info, _style_cell_left),
                Paragraph(it.get("kategori_biaya", "-"), _style_cell_left),
                Paragraph(it.get("keterangan", "-") or "-", _style_cell_left),
                Paragraph(it.get("nota", "-") or "-", _style_cell_center),
                Paragraph(f"<b>{rp(it.get('nominal', 0))}</b>", _style_cell_right),
            ]
        else:
            row = [
                Paragraph(str(idx), _style_cell_center),
                Paragraph(tgl_str, _style_cell_center),
                Paragraph(personel_info, _style_cell_left),
                Paragraph(it.get("kategori_biaya", "-"), _style_cell_left),
                Paragraph(it.get("keterangan", "-") or "-", _style_cell_left),
                Paragraph(it.get("nota", "-") or "-", _style_cell_center),
                Paragraph(f"<b>{rp(it.get('nominal', 0))}</b>", _style_cell_right),
            ]
        data.append(row)

    # Footer Total
    span_col = 6 if is_pusat else 5
    footer_row = [
        Paragraph("<b>TOTAL OPERASIONAL</b>", _style_cell_bold_left),
    ] + [Paragraph("", _style_cell_left)] * (span_col - 1) + [
        Paragraph("", _style_cell_left),
        Paragraph(f"<b>{rp(total_nominal)}</b>", _style_cell_bold_right),
    ]
    data.append(footer_row)
    last_row_idx = len(data) - 1
    table_style.extend([
        ("SPAN", (0, last_row_idx), (span_col, last_row_idx)),
        ("BACKGROUND", (0, last_row_idx), (-1, last_row_idx), colors.HexColor("#CFD8DC")),
        ("TOPPADDING", (0, last_row_idx), (-1, last_row_idx), 4.5),
        ("BOTTOMPADDING", (0, last_row_idx), (-1, last_row_idx), 4.5),
    ])

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(table_style))
    elements.append(table)

    doc.build(elements)
    if output_path is None:
        return buffer.getvalue()


# =========================================================================
# 6. REKAP BULANAN GABUNGAN PDF EXPORT
# =========================================================================

def generate_rekap_bulanan_pdf(rekap_data, filter_info, is_pusat=False, output_path=None):
    """
    rekap_data: dict {
        "kenek": {"items": [...], "total": Decimal},
        "pabrik": {"items": [...], "total": Decimal, "qty": float},
        "balaraja": {"items": [...], "total": Decimal, "qty": float},
        "grand_total": Decimal
    }
    filter_info: dict {"periode": str, "cabang": str, "extra": str}
    """
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(
        target,
        pagesize=landscape(A4),
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
    )

    elements = _build_header_elements("Laporan Rekap Bulanan Gabungan", filter_info, is_landscape=True)

    kenek_info = rekap_data.get("kenek", {})
    pabrik_info = rekap_data.get("pabrik", {})
    balaraja_info = rekap_data.get("balaraja", {})

    kenek_sum = Decimal(str(kenek_info.get("total", 0)))
    pabrik_sum = Decimal(str(pabrik_info.get("total", 0)))
    balaraja_sum = Decimal(str(balaraja_info.get("total", 0)))
    grand_sum = rekap_data.get("grand_total", kenek_sum + pabrik_sum + balaraja_sum)

    pct_k = (float(kenek_sum) / float(grand_sum) * 100) if grand_sum > 0 else 0
    pct_p = (float(pabrik_sum) / float(grand_sum) * 100) if grand_sum > 0 else 0
    pct_b = (float(balaraja_sum) / float(grand_sum) * 100) if grand_sum > 0 else 0

    kpi_cards = [
        ("Operasional Kenek & Supir", f"{rp(kenek_sum)} ({pct_k:.1f}%)", "#C62828", "#FFEBEE"),
        ("Pengambilan Pabrik", f"{rp(pabrik_sum)} ({pct_p:.1f}%)", "#1A237E", "#E8EAF6"),
        ("Pengambilan Balaraja", f"{rp(balaraja_sum)} ({pct_b:.1f}%)", "#E65100", "#FFF3E0"),
        ("Grand Total Pengeluaran", rp(grand_sum), "#004D40", "#E0F2F1"),
    ]
    elements.append(_build_kpi_table(kpi_cards, total_width_cm=27.3))
    elements.append(Spacer(1, 10))

    # Ringkasan Komposisi Table
    elements.append(Paragraph("<b>1. Ringkasan & Komposisi Pengeluaran Bulanan</b>", _style_section_heading))
    elements.append(Spacer(1, 3))

    comp_headers = [Paragraph("<b>No</b>", _style_th), Paragraph("<b>Kategori / Sumber Pengeluaran</b>", _style_th), Paragraph("<b>Jumlah Transaksi</b>", _style_th), Paragraph("<b>Volume Qty</b>", _style_th), Paragraph("<b>Total Pengeluaran (Rp)</b>", _style_th), Paragraph("<b>Porsi (%)</b>", _style_th)]
    comp_data = [
        comp_headers,
        [Paragraph("1", _style_cell_center), Paragraph("Operasional Kenek & Supir (Uang Jalan, BBM, Tol, dll)", _style_cell_left), Paragraph(f"{len(kenek_info.get('items', []))} Trx", _style_cell_center), Paragraph("-", _style_cell_center), Paragraph(f"<b>{rp(kenek_sum)}</b>", _style_cell_right), Paragraph(f"<b>{pct_k:.1f}%</b>", _style_cell_center)],
        [Paragraph("2", _style_cell_center), Paragraph("Pengambilan Barang Pabrik / Supplier", _style_cell_left), Paragraph(f"{len(pabrik_info.get('items', []))} Trx", _style_cell_center), Paragraph(f"{pabrik_info.get('qty', 0):,.0f} Item", _style_cell_center), Paragraph(f"<b>{rp(pabrik_sum)}</b>", _style_cell_right), Paragraph(f"<b>{pct_p:.1f}%</b>", _style_cell_center)],
        [Paragraph("3", _style_cell_center), Paragraph("Pengambilan Barang Gudang / Depo Balaraja", _style_cell_left), Paragraph(f"{len(balaraja_info.get('items', []))} Trx", _style_cell_center), Paragraph(f"{balaraja_info.get('qty', 0):,.0f} Item", _style_cell_center), Paragraph(f"<b>{rp(balaraja_sum)}</b>", _style_cell_right), Paragraph(f"<b>{pct_b:.1f}%</b>", _style_cell_center)],
        [Paragraph("<b>TOTAL GABUNGAN</b>", _style_cell_bold_left), Paragraph("", _style_cell_left), Paragraph(f"<b>{len(kenek_info.get('items', [])) + len(pabrik_info.get('items', [])) + len(balaraja_info.get('items', []))} Trx</b>", _style_cell_bold_center), Paragraph(f"<b>{pabrik_info.get('qty', 0) + balaraja_info.get('qty', 0):,.0f} Item</b>", _style_cell_bold_center), Paragraph(f"<b>{rp(grand_sum)}</b>", _style_cell_bold_right), Paragraph("<b>100.0%</b>", _style_cell_bold_center)],
    ]
    comp_widths = [1.2 * cm, 10.1 * cm, 4.0 * cm, 3.5 * cm, 5.5 * cm, 3.0 * cm]
    comp_table = Table(comp_data, colWidths=comp_widths)
    comp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D47A1")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("SPAN", (0, 4), (1, 4)),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#E0F2F1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    elements.append(comp_table)
    elements.append(Spacer(1, 14))

    # Section 2: Detail Operasional Kenek & Supir
    elements.append(Paragraph(f"<b>2. Rincian Pengeluaran Operasional Kenek & Supir ({rp(kenek_sum)})</b>", _style_section_heading))
    elements.append(Spacer(1, 3))
    k_items = kenek_info.get("items", [])
    if not k_items:
        elements.append(Paragraph("Tidak ada catatan pengeluaran kenek/supir pada periode ini.", _style_subtitle))
    else:
        k_headers = ["No", "Tanggal", "Supir / Kenek", "Kategori Biaya", "Keterangan", "Nota", "Nominal"]
        k_widths = [1.0 * cm, 2.5 * cm, 4.8 * cm, 4.2 * cm, 9.0 * cm, 2.8 * cm, 3.0 * cm]
        k_data = [[Paragraph(f"<b>{h}</b>", _style_th) for h in k_headers]]
        for idx, it in enumerate(k_items, start=1):
            k_data.append([
                Paragraph(str(idx), _style_cell_center),
                Paragraph(_format_date_val(it.get("tanggal")), _style_cell_center),
                Paragraph(f"<b>{it.get('nama_personel', '-')}</b> ({it.get('peran', 'Supir')})", _style_cell_left),
                Paragraph(it.get("kategori_biaya", "-"), _style_cell_left),
                Paragraph(it.get("keterangan", "-") or "-", _style_cell_left),
                Paragraph(it.get("nota", "-") or "-", _style_cell_center),
                Paragraph(rp(it.get("nominal", 0)), _style_cell_right),
            ])
        k_table = Table(k_data, colWidths=k_widths, repeatRows=1)
        k_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C62828")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(k_table)

    elements.append(Spacer(1, 14))

    # Section 3: Detail Pengambilan Pabrik
    elements.append(Paragraph(f"<b>3. Rincian Pengambilan Barang Pabrik ({rp(pabrik_sum)})</b>", _style_section_heading))
    elements.append(Spacer(1, 3))
    p_items = pabrik_info.get("items", [])
    if not p_items:
        elements.append(Paragraph("Tidak ada catatan pengambilan pabrik pada periode ini.", _style_subtitle))
    else:
        p_headers = ["No", "Tanggal", "Pabrik / Supplier", "Nama Barang", "Qty & Satuan", "Harga Satuan", "Total Harga", "No. DO/SJ", "Status"]
        p_widths = [1.0 * cm, 2.4 * cm, 4.2 * cm, 5.5 * cm, 2.6 * cm, 2.8 * cm, 3.2 * cm, 2.8 * cm, 2.8 * cm]
        p_data = [[Paragraph(f"<b>{h}</b>", _style_th) for h in p_headers]]
        for idx, it in enumerate(p_items, start=1):
            p_data.append([
                Paragraph(str(idx), _style_cell_center),
                Paragraph(_format_date_val(it.get("tanggal")), _style_cell_center),
                Paragraph(it.get("nama_pabrik", "-"), _style_cell_left),
                Paragraph(it.get("nama_barang", "-"), _style_cell_left),
                Paragraph(f"{it.get('qty', 0):,.0f} {it.get('satuan', '')}", _style_cell_center),
                Paragraph(rp(it.get("harga_satuan", 0)), _style_cell_right),
                Paragraph(f"<b>{rp(it.get('total_harga', 0))}</b>", _style_cell_right),
                Paragraph(it.get("no_surat_jalan", "-") or "-", _style_cell_center),
                Paragraph(it.get("status_pembayaran", "Lunas"), _style_cell_center),
            ])
        p_table = Table(p_data, colWidths=p_widths, repeatRows=1)
        p_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#283593")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(p_table)

    elements.append(Spacer(1, 14))

    # Section 4: Detail Pengambilan Balaraja
    elements.append(Paragraph(f"<b>4. Rincian Pengambilan Barang Balaraja ({rp(balaraja_sum)})</b>", _style_section_heading))
    elements.append(Spacer(1, 3))
    b_items = balaraja_info.get("items", [])
    if not b_items:
        elements.append(Paragraph("Tidak ada catatan pengambilan Balaraja pada periode ini.", _style_subtitle))
    else:
        b_headers = ["No", "Tanggal", "Lokasi Gudang", "Nama Barang", "Qty & Satuan", "Harga Satuan", "Total Harga", "No. SJ", "Driver / Armada"]
        b_widths = [1.0 * cm, 2.4 * cm, 4.0 * cm, 5.5 * cm, 2.6 * cm, 2.8 * cm, 3.2 * cm, 2.8 * cm, 3.0 * cm]
        b_data = [[Paragraph(f"<b>{h}</b>", _style_th) for h in b_headers]]
        for idx, it in enumerate(b_items, start=1):
            b_data.append([
                Paragraph(str(idx), _style_cell_center),
                Paragraph(_format_date_val(it.get("tanggal")), _style_cell_center),
                Paragraph(it.get("lokasi_gudang", "-"), _style_cell_left),
                Paragraph(it.get("nama_barang", "-"), _style_cell_left),
                Paragraph(f"{it.get('qty', 0):,.0f} {it.get('satuan', '')}", _style_cell_center),
                Paragraph(rp(it.get("harga_satuan", 0)), _style_cell_right),
                Paragraph(f"<b>{rp(it.get('total_harga', 0))}</b>", _style_cell_right),
                Paragraph(it.get("no_surat_jalan", "-") or "-", _style_cell_center),
                Paragraph(it.get("driver", "-") or "-", _style_cell_left),
            ])
        b_table = Table(b_data, colWidths=b_widths, repeatRows=1)
        b_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D84315")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(b_table)

    doc.build(elements)
    if output_path is None:
        return buffer.getvalue()
