from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from utils.formatting import rp


def generate_folder_pdf(nama_folder, invoices, output_path):
    """
    invoices: list tuple (id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, total_omzet, total_barang)
    -> hasil dari db.invoice_repo.get_invoices()
    """
    doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Laporan Keuangan - {nama_folder}", styles["Title"]))
    elements.append(Spacer(1, 12))

    data = [["No.", "TGL Laporan", "Invoice/Bon", "Omset", "Laba Bersih", "Sisa Hutang"]]
    total_omzet_all = 0
    total_laba_all = 0
    total_hutang_all = 0

    for inv in invoices:
        iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, total_omzet, total_barang = inv
        laba_bersih = total_omzet - total_barang
        sisa_hutang = (invoice_bon or 0) + total_barang - total_omzet
        data.append([
            no_laporan or "-",
            tgl_laporan.strftime("%d-%m-%Y") if tgl_laporan else "-",
            rp(invoice_bon),
            rp(total_omzet),
            rp(laba_bersih),
            rp(sisa_hutang),
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

    doc.build(elements)