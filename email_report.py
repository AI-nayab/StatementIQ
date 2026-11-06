import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def generate_report_content(df: pd.DataFrame) -> tuple[str, str]:
    """Generate plain text and HTML summary of total spent, category totals, and top 5 expenses."""
    expense_df = df[df["Debit"] > 0].copy()
    total_spent = float(expense_df["Debit"].sum()) if not expense_df.empty else 0.0

    category_totals = (
        expense_df.groupby("Category")["Debit"]
        .sum()
        .sort_values(ascending=False)
        if not expense_df.empty
        else pd.Series(dtype=float)
    )

    top_expenses = (
        expense_df.sort_values(by="Debit", ascending=False)
        .head(5)[["Date", "Description", "Debit", "Category"]]
        if not expense_df.empty
        else pd.DataFrame()
    )

    text_lines = [
        "StatementIQ - Spending Summary Report",
        "=" * 40,
        f"Total Spent: ${total_spent:,.2f}\n",
        "Category Breakdown:",
        "-" * 25,
    ]
    for cat, amt in category_totals.items():
        text_lines.append(f"- {cat}: ${amt:,.2f}")

    text_lines.append("\nTop 5 Expenses:")
    text_lines.append("-" * 25)
    for _, row in top_expenses.iterrows():
        text_lines.append(f"- {row['Date']} | {row['Description']} ({row['Category']}): ${row['Debit']:,.2f}")

    text_body = "\n".join(text_lines)

    cat_rows = "".join([
        f"<tr><td style='padding:6px;border:1px solid #ddd;'>{c}</td><td style='padding:6px;border:1px solid #ddd;'>${a:,.2f}</td></tr>"
        for c, a in category_totals.items()
    ])
    top_rows = "".join([
        f"<tr><td style='padding:6px;border:1px solid #ddd;'>{r['Date']}</td><td style='padding:6px;border:1px solid #ddd;'>{r['Description']}</td><td style='padding:6px;border:1px solid #ddd;'>{r['Category']}</td><td style='padding:6px;border:1px solid #ddd;'>${r['Debit']:,.2f}</td></tr>"
        for _, r in top_expenses.iterrows()
    ])

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>StatementIQ - Spending Summary Report</h2>
        <p><strong>Total Spent:</strong> ${total_spent:,.2f}</p>
        <h3>Category Breakdown</h3>
        <table style="border-collapse: collapse; width: 100%; max-width: 450px;">
            <tr style="background: #f4f4f4;"><th style="padding:6px;border:1px solid #ddd;text-align:left;">Category</th><th style="padding:6px;border:1px solid #ddd;text-align:left;">Total</th></tr>
            {cat_rows}
        </table>
        <h3>Top 5 Expenses</h3>
        <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
            <tr style="background: #f4f4f4;"><th style="padding:6px;border:1px solid #ddd;text-align:left;">Date</th><th style="padding:6px;border:1px solid #ddd;text-align:left;">Description</th><th style="padding:6px;border:1px solid #ddd;text-align:left;">Category</th><th style="padding:6px;border:1px solid #ddd;text-align:left;">Debit</th></tr>
            {top_rows}
        </table>
    </body>
    </html>
    """
    return text_body, html_body

def send_email_report(df: pd.DataFrame, recipient_email: str) -> bool:
    """Send spending summary report via SMTP using credentials in .env."""
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        recipient = recipient_email.strip()

        if not smtp_user or not smtp_password:
            print("SMTP configuration missing in .env")
            return False

        if not recipient:
            print("Recipient email is missing")
            return False

        text_body, html_body = generate_report_content(df)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "StatementIQ - Spending Summary"
        msg["From"] = smtp_user
        msg["To"] = recipient

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        print(f"Report emailed successfully to {recipient}")
        return True
    except Exception as e:
        print(f"Error sending email report: {e}")
        return False

