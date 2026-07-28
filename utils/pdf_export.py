from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from database.db import query_all, query_one

MONTH_NAMES_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"


def format_rp(value: int) -> str:
    return f"{value:,.0f}".replace(",", ".")


def export_invoice_pdf(year: int, month: int) -> Path:
    """Bikin PDF laporan invoice untuk satu bulan tertentu. Mengembalikan path file yang dihasilkan."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    folder = query_one(
        "SELECT * FROM v_month_folder_summary WHERE year = ? AND month = ?",
        (year, month),
    )
    invoices = query_all(
        "SELECT * FROM invoices WHERE month_folder_id = ? ORDER BY invoice_date ASC",
        (folder["month_folder_id"],) if folder else (0,),
    )

    month_name = MONTH_NAMES_ID[month - 1]
    filename = f"Laporan_Invoice_{month_name}_{year}.pdf"
    filepath = EXPORT_DIR / filename

    doc = SimpleDocTemplate(str(filepath), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>MetroSnack — Laporan Invoice</b>", styles["Title"]))
    elements.append(Paragraph(f"Periode: {month_name} {year}", styles["Normal"]))
    elements.append(Paragraph(f"Dicetak: {datetime.now().strftime('%d %B %Y, %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    total_omzet = folder["total_omzet"] if folder else 0
    total_hpp = folder["total_hpp"] if folder else 0
    laba_kotor = folder["laba_kotor"] if folder else 0
    total_beban = folder["total_beban"] if folder else 0

    summary_data = [
        ["Total Omzet", f"Rp {format_rp(total_omzet)}"],
        ["Total HPP", f"Rp {format_rp(total_hpp)}"],
        ["Laba Kotor", f"Rp {format_rp(laba_kotor)}"],
        ["Total Beban", f"Rp {format_rp(total_beban)}"],
    ]
    summary_table = Table(summary_data, colWidths=[6 * cm, 6 * cm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#64748B")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.8 * cm))

    table_data = [["Nota", "Tanggal", "Masuk Barang", "Masuk Uang", "Lebih Uang", "Beban"]]
    for inv in invoices:
        table_data.append([
            inv["nota_number"],
            inv["invoice_date"],
            format_rp(inv["total_amount"]),
            format_rp(inv["hpp_amount"]),
            format_rp(inv["laba_amount"]),
            format_rp(inv["beban_amount"]),
        ])

    if len(table_data) == 1:
        table_data.append(["-", "-", "-", "-", "-", "-"])

    invoice_table = Table(table_data, colWidths=[3 * cm, 2.7 * cm, 2.8 * cm, 2.8 * cm, 2.8 * cm, 2.8 * cm])
    invoice_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(invoice_table)

    doc.build(elements)
    return filepath