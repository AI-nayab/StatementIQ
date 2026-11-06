import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def generate_sample_pdf(output_path="sample_data/bank_statement.pdf"):
    """Generate a 30-transaction sample bank statement PDF."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()

    elements = [
        Paragraph("<b>STATEMENTIQ BANK - ACCOUNT STATEMENT</b>", styles["Title"]),
        Paragraph("Account Holder: Alex Mercer | Account: 4092817290 | Period: 01-Oct-2026 to 30-Oct-2026", styles["Normal"]),
        Spacer(1, 15),
    ]

    transactions = [
        ["Date", "Description", "Debit", "Credit"],
        ["2026-10-01", "Monthly Salary Deposit", "0.00", "4800.00"],
        ["2026-10-02", "Whole Foods Supermarket Grocery", "135.40", "0.00"],
        ["2026-10-02", "Starbucks Coffee House", "7.50", "0.00"],
        ["2026-10-03", "Uber Trip Downtown", "22.30", "0.00"],
        ["2026-10-04", "Netflix Monthly Subscription", "15.99", "0.00"],
        ["2026-10-05", "Amazon Online Retail Order", "85.20", "0.00"],
        ["2026-10-06", "Shell Fuel Station Petrol", "48.50", "0.00"],
        ["2026-10-07", "Electric Utility Power Bill", "98.70", "0.00"],
        ["2026-10-08", "Spotify Premium Music", "9.99", "0.00"],
        ["2026-10-09", "Zomato Food Delivery", "32.40", "0.00"],
        ["2026-10-10", "Freelance Client Consulting Credit", "0.00", "750.00"],
        ["2026-10-11", "Target Store Clothing & Household", "64.80", "0.00"],
        ["2026-10-12", "Subway Sandwiches Restaurant", "12.20", "0.00"],
        ["2026-10-13", "Metro Rail Pass Recharge", "45.00", "0.00"],
        ["2026-10-14", "City Water Board Utility Bill", "38.60", "0.00"],
        ["2026-10-15", "Apple iCloud Storage Subscription", "2.99", "0.00"],
        ["2026-10-16", "Zara Fashion Apparels", "130.00", "0.00"],
        ["2026-10-17", "Trader Joe's Supermarket", "78.50", "0.00"],
        ["2026-10-18", "Broadband Internet Service Bill", "65.00", "0.00"],
        ["2026-10-19", "Chevron Fuel Gas Station", "52.10", "0.00"],
        ["2026-10-20", "Stock Investment Dividend Credit", "0.00", "210.00"],
        ["2026-10-21", "Burger King Fast Food", "14.90", "0.00"],
        ["2026-10-22", "Fitness Gym Monthly Membership", "50.00", "0.00"],
        ["2026-10-23", "Nike Shoes Retail Store", "118.00", "0.00"],
        ["2026-10-24", "CVS Pharmacy Prescription", "27.30", "0.00"],
        ["2026-10-25", "Swiggy Dinner Delivery", "28.80", "0.00"],
        ["2026-10-26", "Mobile Prepaid Phone Bill", "35.00", "0.00"],
        ["2026-10-27", "Lyft Ride Service", "19.40", "0.00"],
        ["2026-10-28", "YouTube Premium Subscription", "13.99", "0.00"],
        ["2026-10-29", "ATM Cash Withdrawal", "100.00", "0.00"],
    ]

    table = Table(transactions, colWidths=[80, 240, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))

    elements.append(table)
    doc.build(elements)
    print(f"Sample PDF created at: {output_path}")

if __name__ == "__main__":
    generate_sample_pdf()

