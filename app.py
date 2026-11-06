import re
import streamlit as st
import pandas as pd
import altair as alt
from parser import parse_statement
from categorizer import categorize_dataframe
from db import insert_transactions, fetch_all_transactions
from email_report import send_email_report

def display_summary(df: pd.DataFrame):
    """Display total income, total expense, and net balance summary metrics."""
    total_income = float(df["Credit"].sum()) if "Credit" in df.columns else 0.0
    total_expense = float(df["Debit"].sum()) if "Debit" in df.columns else 0.0
    net_savings = total_income - total_expense

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income (Credit)", f"${total_income:,.2f}")
    col2.metric("Total Expenses (Debit)", f"${total_expense:,.2f}")
    col3.metric("Net Savings", f"${net_savings:,.2f}")

def display_charts(df: pd.DataFrame):
    """Render a pie chart showing spending distribution by category."""
    expense_df = df[df["Debit"] > 0]
    if expense_df.empty:
        st.info("No expense data available for charts.")
        return

    cat_spending = (
        expense_df.groupby("Category")["Debit"]
        .sum()
        .reset_index()
        .sort_values(by="Debit", ascending=False)
    )

    chart = (
        alt.Chart(cat_spending)
        .mark_arc(innerRadius=40)
        .encode(
            theta=alt.Theta(field="Debit", type="quantitative"),
            color=alt.Color(field="Category", type="nominal"),
            tooltip=["Category", alt.Tooltip("Debit", format=",.2f")],
        )
        .properties(title="Spending by Category")
    )
    st.altair_chart(chart, use_container_width=True)

def main():
    """Run the StatementIQ Streamlit web application."""
    st.set_page_config(page_title="StatementIQ", layout="wide")
    st.title("StatementIQ - Bank Statement Dashboard")

    uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type=["pdf"])
    pdf_password = st.text_input("Password (optional, for protected PDFs)", type="password")

    if "transactions" not in st.session_state:
        st.session_state["transactions"] = pd.DataFrame()

    if uploaded_file is not None:
        if st.button("Parse & Save Statement"):
            with st.spinner("Processing PDF..."):
                raw_df = parse_statement(
                    uploaded_file,
                    password=pdf_password.strip() if pdf_password and pdf_password.strip() else None,
                )
                if not raw_df.empty:
                    df = categorize_dataframe(raw_df)
                    st.session_state["transactions"] = df
                    saved = insert_transactions(df)
                    st.success(f"Parsed {len(df)} transactions. Saved {saved} new entries to MySQL.")
                else:
                    err_msg = raw_df.attrs.get("error", "Please verify the PDF format or password.")
                    st.error(f"No transactions found: {err_msg}")

    df = st.session_state["transactions"]
    if df.empty:
        df = fetch_all_transactions()
        if not df.empty:
            st.session_state["transactions"] = df

    if not df.empty:
        st.divider()
        display_summary(df)

        st.divider()
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("Transactions")
            all_categories = ["All"] + sorted(df["Category"].dropna().unique().tolist())
            selected_cat = st.selectbox("Filter by Category", all_categories)
            filtered_df = df if selected_cat == "All" else df[df["Category"] == selected_cat]
            st.dataframe(filtered_df, use_container_width=True)

        with col2:
            st.subheader("Category Distribution")
            display_charts(df)

        st.divider()
        recipient_email = st.text_input("Recipient email")
        if st.button("Send Report"):
            email_clean = recipient_email.strip()
            if not email_clean or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_clean):
                st.error("Please enter a valid email address (must contain '@' and a domain).")
            else:
                with st.spinner("Sending email report..."):
                    if send_email_report(df, email_clean):
                        st.success(f"Summary report successfully sent to {email_clean}!")
                    else:
                        st.error("Failed to send email. Check SMTP settings in .env.")
    else:
        st.info("Upload a bank statement PDF or connect to MySQL database to view transactions.")

if __name__ == "__main__":
    main()

