"""Hilfsskript zur Generierung einer beispielhaften Rechnungs-PDF mit einer inkrementellen ID.

Verhindert doppelte Rechnungsnummer-Konflikte bei Testdurchläufen.
Schreibt und liest den Zählerstand aus `rechnungs_counter.txt`.
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

PROJEKT_WURZEL = Path(__file__).resolve().parent.parent
COUNTER_DATEI = PROJEKT_WURZEL / "rechnungs_counter.txt"
ZIEL_ORDNER = PROJEKT_WURZEL / "Rechnungsdaten"
ZIEL_ORDNER.mkdir(exist_ok=True)
PDF_PFAD = ZIEL_ORDNER / "beispiel_rechnung.pdf"


def hole_naechsten_zaehler() -> int:
    """Liest den Zähler aus der Datei, inkrementiert ihn und speichert ihn wieder."""
    if COUNTER_DATEI.exists():
        try:
            with open(COUNTER_DATEI, "r", encoding="utf-8") as f:
                inhalt = f.read().strip()
                counter = int(inhalt)
        except Exception:
            counter = 100
    else:
        counter = 100

    counter += 1

    with open(COUNTER_DATEI, "w", encoding="utf-8") as f:
        f.write(str(counter))

    return counter


def erstelle_pdf(counter: int, dateiname: str = None) -> str:
    """Generiert die beispiel_rechnung.pdf unter Rechnungsdaten/."""
    invoice_id = f"INV-2026-{counter}"
    invoice_num = f"RE-2026-{counter}"
    
    if dateiname is None:
        dateiname = f"INV-2026-{counter}.pdf"
        
    ziel_pfad = ZIEL_ORDNER / dateiname
    
    # PDF Setup (letter size: 612 x 792 points)
    c = canvas.Canvas(str(ziel_pfad), pagesize=letter)
    
    # Header Line
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(1)
    c.line(50, 720, 562, 720)
    
    # Header Brand / Sender Details
    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(0.1, 0.3, 0.6) # Sleek blue
    c.drawString(50, 735, "DVG Lieferant GmbH")
    
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4) # Slate gray
    c.drawRightString(562, 735, "Hauptstraße 12, 12345 Berlin | E-Mail: lieferant@dvg.de")
    
    # Sender small line (above recipient)
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(50, 690, "DVG Lieferant GmbH - Hauptstraße 12 - 12345 Berlin")
    c.line(50, 685, 250, 685)
    
    # Recipient Address Box: genau eine, widerspruchsfreie Rechnungsadresse.
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(50, 670, "Rechnungsadresse:")
    c.drawString(50, 650, "Musterkunde AG")
    c.drawString(50, 635, "Finanzabteilung")
    c.drawString(50, 620, f"Hauptstrasse {counter}")
    c.drawString(50, 605, "12345 Berlin")
    
    # Invoice Metadata (Right side info block)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(380, 670, "RECHNUNGSDATEN")
    c.setFont("Helvetica", 9)
    c.drawString(380, 650, "Rechnungs-ID:")
    c.drawRightString(562, 650, invoice_id)
    c.drawString(380, 635, "Rechnungsnummer:")
    c.drawRightString(562, 635, invoice_num)
    c.drawString(380, 620, "Rechnungsdatum:")
    c.drawRightString(562, 620, "2026-06-08")
    c.drawString(380, 605, "Faelligkeitsdatum:")
    c.drawRightString(562, 605, "2026-07-08")
    c.drawString(380, 590, "Lieferant:")
    c.drawRightString(562, 590, "DVG Lieferant GmbH")
    c.drawString(380, 575, "E-Mail:")
    c.drawRightString(562, 575, "lieferant@dvg.de")
    
    # Large Title
    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(0.1, 0.3, 0.6)
    c.drawString(50, 530, f"Rechnung {invoice_num}")
    
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(50, 510, "Sehr geehrte Damen und Herren,")
    c.drawString(50, 495, "vielen Dank für die gute Zusammenarbeit. Wir erlauben uns, folgende Leistungen in Rechnung zu stellen:")
    
    # Label to trigger position parsing in pdf_handler.py
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, 475, "Positionen:")
    
    # Table Header
    y_table = 460
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(1.5)
    c.line(50, y_table, 562, y_table)
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y_table - 15, "Pos")
    c.drawString(85, y_table - 15, "Beschreibung")
    c.drawRightString(350, y_table - 15, "Menge")
    c.drawRightString(450, y_table - 15, "Einzelpreis")
    c.drawRightString(562, y_table - 15, "Gesamt")
    
    c.line(50, y_table - 22, 562, y_table - 22)
    
    # Table Items
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setFont("Helvetica", 9)
    
    # Structuring positions for both human display and automatic PDF extraction
    items = [
        ("1", "Software Lizenzen", "5.0", "20.00 EUR", "100.00 EUR", "- Software Lizenzen (Quantity: 5, UnitPrice: 20.00)"),
        ("2", "Consulting Dienstleistung", "2.0", "150.00 EUR", "300.00 EUR", "- Consulting Dienstleistung (Quantity: 2, UnitPrice: 150.00)"),
        ("3", "IT Support Pauschale", "1.0", "100.00 EUR", "100.00 EUR", "- IT Support Pauschale (Quantity: 1, UnitPrice: 100.00)"),
    ]
    
    y = y_table - 40
    for pos, desc, qty, unit, total, regex_str in items:
        c.drawString(50, y, pos)
        c.drawString(85, y, desc)
        c.drawRightString(350, y, qty)
        c.drawRightString(450, y, unit)
        c.drawRightString(562, y, total)
        
        # Draw the regex line in small light gray text as detail description
        c.setFont("Helvetica-Oblique", 7.5)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(85, y - 10, regex_str)
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0, 0, 0)
        
        c.line(50, y - 16, 562, y - 16)
        y -= 28
    
    # Total calculation box
    y -= 10
    c.setFont("Helvetica", 9)
    c.drawString(380, y, "Netto:")
    c.drawRightString(562, y, "500.00 EUR")
    c.drawString(380, y - 15, "Umsatzsteuer (19%):")
    c.drawRightString(562, y - 15, "95.00 EUR")
    
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.1, 0.3, 0.6)
    c.line(380, y - 22, 562, y - 22)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(380, y - 35, "Brutto:")
    c.drawRightString(562, y - 35, "595.00 EUR")
    
    c.line(380, y - 40, 562, y - 40)
    c.line(380, y - 42, 562, y - 42)
    
    # Technical fields matches for regex parsing in a gray block
    y_meta = 210
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(0.5)
    c.rect(50, y_meta - 65, 512, 70, fill=0, stroke=1)
    
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(60, y_meta - 10, "Systeminformationen zur automatisierten Verarbeitung:")
    c.setFont("Helvetica", 7.5)
    c.drawString(60, y_meta - 25, f"Rechnungs-ID: {invoice_id}  |  Rechnungsnummer: {invoice_num}  |  Waehrung: EUR")
    c.drawString(60, y_meta - 40, f"Netto: 500.00  |  Brutto: 595.00  |  IBAN: DE89370400440532013000")
    c.drawString(60, y_meta - 55, "Eingangskanal: EMAIL  |  Lieferant: DVG Lieferant GmbH")
    
    # Footer bank details
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(50, 60, "Zahlungskonditionen: Zahlbar innerhalb von 30 Tagen ohne Abzug.")
    c.drawString(50, 45, "Bankverbindung: DVG Bank, IBAN: DE89370400440532013000, BIC: DVGBDEBBXXX")
    
    c.save()
    import shutil
    shutil.copy(str(ziel_pfad), str(PDF_PFAD))
    print(f"[PDF-Generator] PDF erstellt unter: {ziel_pfad}")
    print(f"[PDF-Generator] Kopiert nach:        {PDF_PFAD}")
    print(f"[PDF-Generator] Rechnungs-ID:       {invoice_id}")
    print(f"[PDF-Generator] Rechnungsnummer:    {invoice_num}")
    return dateiname


def main():
    cnt = hole_naechsten_zaehler()
    erstelle_pdf(cnt)


if __name__ == "__main__":
    main()
