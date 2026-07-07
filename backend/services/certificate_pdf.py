"""Ownership Certificate PDF generator (reportlab).

Produces a clean, branded 'Certificate of Ownership' PDF for an exclusively-transferred
SiteGenie website. Pure vector drawing — no external asset dependencies.
"""
import io

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

BRAND = HexColor("#0055FF")
GOLD = HexColor("#B08D57")
INK = HexColor("#0A0A0C")
MUTED = HexColor("#6B7280")
PAGE_W, PAGE_H = letter


def _center(c, text, y, font, size, color=INK):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawCentredString(PAGE_W / 2, y, text)


def build_certificate_pdf(cert: dict) -> bytes:
    """cert: {title, owner_name, owner_email, price_usd, transferred_at (iso), cert_id}"""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    # Outer decorative border
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.rect(0.55 * inch, 0.55 * inch, PAGE_W - 1.1 * inch, PAGE_H - 1.1 * inch)
    c.setLineWidth(0.5)
    c.rect(0.7 * inch, 0.7 * inch, PAGE_W - 1.4 * inch, PAGE_H - 1.4 * inch)

    # Header brand
    _center(c, "SITEGENIE", PAGE_H - 1.5 * inch, "Helvetica-Bold", 20, BRAND)
    _center(c, "Your Website Wish, Granted", PAGE_H - 1.78 * inch, "Helvetica-Oblique", 10, MUTED)

    # Title
    _center(c, "CERTIFICATE OF OWNERSHIP", PAGE_H - 2.7 * inch, "Helvetica-Bold", 26, INK)

    # rule
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(2.2 * inch, PAGE_H - 2.95 * inch, PAGE_W - 2.2 * inch, PAGE_H - 2.95 * inch)

    _center(c, "This certifies that full and exclusive ownership of", PAGE_H - 3.5 * inch,
            "Helvetica", 12, MUTED)
    _center(c, cert.get("title", "Website"), PAGE_H - 4.05 * inch, "Helvetica-Bold", 22, GOLD)
    _center(c, "has been permanently transferred to", PAGE_H - 4.5 * inch, "Helvetica", 12, MUTED)
    _center(c, cert.get("owner_name") or cert.get("owner_email", ""), PAGE_H - 5.0 * inch,
            "Helvetica-Bold", 18, INK)

    # details block
    y = PAGE_H - 6.0 * inch
    left = 2.2 * inch
    right = PAGE_W - 2.2 * inch

    def row(label, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(MUTED)
        c.drawString(left, y, label.upper())
        c.setFont("Helvetica", 12)
        c.setFillColor(INK)
        c.drawRightString(right, y, str(value))
        c.setStrokeColor(HexColor("#E5E7EB"))
        c.setLineWidth(0.5)
        c.line(left, y - 8, right, y - 8)
        y -= 0.42 * inch

    date_str = str(cert.get("transferred_at", ""))[:10]
    row("Owner", cert.get("owner_name") or cert.get("owner_email", ""))
    if cert.get("owner_email"):
        row("Account email", cert["owner_email"])
    row("Transfer date", date_str)
    if cert.get("price_usd") is not None:
        row("Purchase price", f"${cert['price_usd']}")
    row("Certificate ID", cert.get("cert_id", ""))

    # footer note
    _center(c,
            "This website is one-of-one and is no longer offered for sale on the SiteGenie Marketplace.",
            1.55 * inch, "Helvetica", 9, MUTED)
    _center(c,
            "The owner holds full rights with free, unlimited AI edits and source export.",
            1.38 * inch, "Helvetica", 9, MUTED)
    _center(c, "sitegenie-ai.com", 1.05 * inch, "Helvetica-Bold", 10, BRAND)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
