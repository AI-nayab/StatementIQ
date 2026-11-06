# StatementIQ - Bank Statement Dashboard

StatementIQ is an automated bank statement analyzer and financial dashboard built with Python, Streamlit, and MySQL. It parses bank statements (both digital e-statements and scanned image PDFs), categorizes expenses, saves records to MySQL, and emails spending summary reports.

---

## Features

- **Multi-Bank Statement Parsing**: Supports major Indian bank formats (SBI, HDFC, ICICI, Axis, Kotak, etc.) with flexible header and date recognition (`DD/MM/YYYY`, `DD-MM-YY`, `DD Mon YYYY`, `YYYY-MM-DD`).
- **Scanned PDF & OCR Support**: Automatically falls back to OCR via `RapidOCR` and `pypdfium2` when PDFs have no digital text layer.
- **Password-Protected PDFs**: Securely unlock and parse encrypted statement PDFs.
- **Auto Categorization**: Matches transactions (including UPI descriptors like Swiggy, Zomato, Uber, Amazon, Jio, etc.) into categories (Food, Transport, Shopping, Bills, Subscriptions).
- **Interactive Visualizations**: View spending breakdown charts and metrics with Streamlit and Altair.
- **Email Spending Reports**: Send summary reports directly via SMTP to any recipient email.
- **MySQL Storage**: Stores transactions with duplicate prevention.

---

## Project Structure

```
statementiq/
├── app.py               # Streamlit web dashboard
├── parser.py            # PDF statement parser (tables, text lines, OCR)
├── categorizer.py       # Transaction rule-based categorizer
├── db.py                # MySQL database connection & CRUD operations
├── email_report.py      # HTML/text email summary report generator
├── make_sample_pdf.py   # Generates test sample statement PDF
├── requirements.txt     # Python dependencies
├── .env.example         # Template for environment variables
├── .gitignore           # Ignored files (secrets, virtual environments, personal PDFs)
└── README.md            # Project documentation
```

---

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/statementiq.git
cd statementiq
```

### 2. Create and activate virtual environment
```bash
python -m venv .venv
```
- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Linux / macOS**:
  ```bash
  source .venv/bin/activate
  ```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Update `.env` with your MySQL and SMTP credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=statementiq

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

---

## Running the Application

Start the Streamlit application:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

