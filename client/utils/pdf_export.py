from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from utils.formatting import rp
from utils.hutang_calc import hutang_amount
from io import BytesIO

_styles = getSampleStyleSheet()
_style_invoice_title = ParagraphStyle(
    "InvoiceTitle", parent=_styles["Heading3"], textColor=colors.HexColor("#1565C0"), spaceBefore=14,
)
_style_small = ParagraphStyle("SmallGrey", parent=_styles["Normal"], textColor=colors.grey, fontSize=9)


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

    doc = SimpleDocTemplate(target, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
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
    """Elemen PDF untuk 1 folder bulan: tabel ringkasan + detail transaksi
    tiap invoice. Dipakai baik oleh generate_folder_pdf (1 folder saja)
    maupun generate_cabang_pdf (banyak folder, 1 section per bulan)."""
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
    """
    invoices_with_transaksi: list of dict, tiap item:
        {"header": (id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, total_omzet, total_barang),
         "transaksi": [(id, tanggal, masuk_barang, masuk_uang, lebih_kurang, keterangan), ...]}
    "header" -> baris dari db.invoice_repo.get_invoices()
    "transaksi" -> hasil db.transaksi_repo.get_transaksi(invoice_id) untuk invoice itu
    """
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(target, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    elements = [Paragraph(f"Laporan Keuangan - {nama_folder}", _styles["Title"]), Spacer(1, 12)]

    section_elements, _, _, _ = _folder_section_elements(nama_folder, invoices_with_transaksi, _styles["Heading2"])
    # Judul folder sudah ada di Title di atas, jadi lewati heading Paragraph
    # pertama dari section (indeks 0) supaya tidak dobel.
    elements.extend(section_elements[2:] if len(section_elements) > 2 else section_elements)

    doc.build(elements)
    if output_path is None:
        return buffer.getvalue()


def generate_cabang_pdf(nama_cabang, folders_data, output_path=None):
    """
    folders_data: list of dict, tiap item:
        {"nama_folder": "Januari 2026", "invoices_with_transaksi": [ ... sama seperti generate_folder_pdf ... ]}
    Urutkan folders_data dari yang lama ke baru sebelum dipanggil (biar laporan runtut).
    """
    buffer = BytesIO()
    target = output_path if isinstance(output_path, str) else buffer
    doc = SimpleDocTemplate(target, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
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

    # Ringkasan total gabungan semua bulan, ditaruh di paling atas.
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
