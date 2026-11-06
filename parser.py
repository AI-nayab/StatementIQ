import io
import re
import pdfplumber
import pandas as pd

DATE_TOKEN_REGEX = re.compile(
    r"("
    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"
    r"|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"
    r"|\d{1,2}[-/.\s]*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/.\s]*\d{2,4}"
    r")",
    re.IGNORECASE,
)

AMOUNT_RE = re.compile(
    r"([-+]?(?:[0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+)\.[0-9]{1,2}|[-+]?[0-9]{1,3}(?:,[0-9]{2,3})+|[-+]?[0-9]+(?:\.[0-9]{1,2})?\s*(?:Dr|Cr|DR|CR)\b)\s*(\((?:Dr|Cr|DR|CR)\)|(?:Dr|Cr|DR|CR)\b)?",
    re.IGNORECASE,
)

SKIP_BALANCE_KEYWORDS = [
    "opening balance", "closing balance", "brought forward", "carried forward",
    "opening bal", "closing bal", "start balance", "end balance",
    "bal b/f", "bal c/f", "balance b/f", "balance c/f", "open balance", "close balance",
]

SKIP_FOOTER_KEYWORDS = [
    "page ", "total turnover", "grand total", "total debit", "total credit",
    "total withdrawal", "total deposit", "computer generated", "generated on",
    "statement summary", "end of statement", "account balance", "customer care",
    "nomination registered", "statement of account", "registered office",
    "account number", "account no", "customer id", "cif no", "ifsc", "micr",
    "branch code", "statement period", "from date", "to date", "account name",
]

def try_parse_date(val: str) -> str | None:
    """Parse date from multiple formats (01/10/26, 01-10-2026, 01 Oct 2026, YYYY-MM-DD) with dayfirst=True."""
    if not val or not str(val).strip():
        return None
    val_str = str(val).strip()
    match = DATE_TOKEN_REGEX.search(val_str)
    if not match:
        return None
    candidate = match.group(0).strip()
    try:
        if re.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$", candidate):
            dt = pd.to_datetime(candidate, errors="coerce")
        else:
            dt = pd.to_datetime(candidate, dayfirst=True, errors="coerce")
        if pd.notna(dt) and 1990 <= dt.year <= 2100:
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None

def parse_amount(val) -> float:
    """Parse numeric amount, stripping commas (e.g. 1,25,000.00 -> 125000.00)."""
    if val is None:
        return 0.0
    s = str(val).replace(",", "").strip()
    if not s or s == "-":
        return 0.0
    match = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if match:
        try:
            return abs(float(match.group(0)))
        except ValueError:
            return 0.0
    return 0.0

def classify_header_cell(cell: str) -> str | None:
    """Identify column type from cell text."""
    c = str(cell).strip().lower()
    c = c.replace("\n", " ")
    c_clean = re.sub(r"[^a-z0-9/ ]", " ", c)
    c_clean = re.sub(r"\s+", " ", c_clean).strip()

    if any(k in c_clean for k in ["txn date", "txndate", "value date", "valuedate", "posting date", "trans date", "transaction date", "tran date", "post date"]):
        return "Date"
    if c_clean == "date" or c_clean.startswith("date ") or c_clean.endswith(" date"):
        return "Date"

    if any(k in c_clean for k in ["description", "narration", "particulars", "transaction details", "details", "remarks"]):
        return "Description"

    if any(k in c_clean for k in ["withdrawal", "debit", "withdraw"]):
        return "Debit"
    if c_clean in ["dr", "dr amt", "dr amount", "w/d", "dr."]:
        return "Debit"

    if any(k in c_clean for k in ["deposit", "credit"]):
        return "Credit"
    if c_clean in ["cr", "cr amt", "cr amount", "cr."]:
        return "Credit"

    if "balance" in c_clean or c_clean in ["bal", "bal."]:
        return "Balance"

    if any(k in c_clean for k in ["amount", "txn amt", "txn amount"]):
        return "Amount"

    if c_clean in ["dr/cr", "cr/dr", "type", "d/c", "indicator", "dr cr", "cr dr"]:
        return "Type"

    return None

def identify_columns(row: list[str]) -> dict[str, int]:
    """Map header column names to their 0-based indices."""
    col_map = {}
    for idx, cell in enumerate(row):
        col_type = classify_header_cell(cell)
        if not col_type:
            continue
        if col_type == "Date" and "Date" in col_map:
            c = str(cell).lower()
            if "txn" in c or c.strip() == "date":
                col_map["Date"] = idx
            continue
        if col_type not in col_map:
            col_map[col_type] = idx
    return col_map

def is_skip_line(line: str) -> bool:
    """Return True if the text represents metadata, footer, or balance line."""
    l = line.lower().strip()
    if not l:
        return True
    if any(k in l for k in SKIP_BALANCE_KEYWORDS):
        return True
    if any(k in l for k in SKIP_FOOTER_KEYWORDS):
        return True
    if l == "total" or l.startswith("total:") or l == "totals":
        return True
    return False

def is_header_line(line: str) -> bool:
    """Return True if the line contains column header names without an actual transaction date."""
    if DATE_TOKEN_REGEX.search(line):
        return False
    l = line.lower()
    return "date" in l and any(k in l for k in ["narration", "description", "particulars", "details", "withdrawal", "debit", "deposit", "credit", "balance", "chq", "ref no"])

def extract_opening_balance(line: str) -> float | None:
    """Extract opening balance amount if present."""
    l = line.lower()
    if any(k in l for k in SKIP_BALANCE_KEYWORDS):
        m = re.search(r"([-+]?(?:[0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+)(?:\.[0-9]{1,2})?)", line)
        if m:
            try:
                return abs(float(m.group(1).replace(",", "")))
            except ValueError:
                pass
    return None

def extract_amounts_and_desc(text: str) -> tuple[str, list[tuple[float, str]]]:
    """Find amounts in text and return (description, list_of_amounts)."""
    matches = list(AMOUNT_RE.finditer(text))
    if not matches:
        return text.strip(), []

    desc = text[:matches[0].start()].strip()
    amounts = []
    for m in matches[-3:]:
        raw_val = m.group(1).replace(",", "")
        marker = (m.group(2) or "").upper().replace("(", "").replace(")", "").strip()
        if not marker:
            if "DR" in raw_val.upper():
                marker = "DR"
            elif "CR" in raw_val.upper():
                marker = "CR"
        raw_val = re.sub(r"[A-Za-z]+", "", raw_val).strip()
        try:
            amounts.append((float(raw_val), marker))
        except ValueError:
            continue

    return desc, amounts

def determine_debit_credit(desc: str, amounts: list[tuple[float, str]], last_balance: float | None) -> tuple[float, float, float | None]:
    """Determine debit and credit values from parsed amount tokens and balance differential."""
    debit, credit = 0.0, 0.0
    current_balance = last_balance

    if len(amounts) >= 3:
        debit = abs(amounts[0][0])
        credit = abs(amounts[1][0])
        current_balance = amounts[2][0]
    elif len(amounts) == 2:
        val, marker = amounts[0]
        current_balance = amounts[1][0]
        if marker == "DR" or val < 0:
            debit = abs(val)
        elif marker == "CR":
            credit = abs(val)
        elif last_balance is not None and abs(current_balance - last_balance) > 0.01:
            diff = current_balance - last_balance
            if diff < 0:
                debit = abs(val)
            else:
                credit = abs(val)
        else:
            if any(k in desc.upper() for k in ["CREDIT", "CR", "SALARY", "REFUND", "DEPOSIT", "INT.PD", "DIVIDEND", "BY TRANSFER", "REVERSAL"]):
                credit = abs(val)
            else:
                debit = abs(val)
    elif len(amounts) == 1:
        val, marker = amounts[0]
        if marker == "DR" or val < 0:
            debit = abs(val)
        elif marker == "CR" or any(k in desc.upper() for k in ["CREDIT", "CR", "SALARY", "REFUND", "DEPOSIT", "INT.PD", "DIVIDEND", "BY TRANSFER"]):
            credit = abs(val)
        else:
            debit = abs(val)

    return debit, credit, current_balance

def extract_page_lines(page) -> list[str]:
    """Extract lines from a page, using word-coordinate grouping to preserve visual table layout."""
    words = page.extract_words()
    if words and len(words) >= 5:
        lines_dict = {}
        for w in sorted(words, key=lambda x: (x["top"], x["x0"])):
            matched_y = None
            for y in lines_dict:
                if abs(w["top"] - y) <= 3.5:
                    matched_y = y
                    break
            if matched_y is None:
                matched_y = w["top"]
                lines_dict[matched_y] = []
            lines_dict[matched_y].append(w)

        lines = []
        for y in sorted(lines_dict.keys()):
            row_words = sorted(lines_dict[y], key=lambda x: x["x0"])
            lines.append(" ".join(w["text"] for w in row_words).strip())
        return lines

    text = page.extract_text(layout=True) or page.extract_text()
    return [l.strip() for l in (text or "").splitlines() if l.strip()]

def parse_lines_to_transactions(lines: list[str]) -> list[dict]:
    """Parse transaction records from structured text lines."""
    transactions = []
    last_balance = None

    for line in lines:
        if not line:
            continue

        op_bal = extract_opening_balance(line)
        if op_bal is not None:
            last_balance = op_bal
            continue

        if is_header_line(line) or is_skip_line(line):
            continue

        m_date = DATE_TOKEN_REGEX.search(line)
        if m_date and m_date.start() <= 40:
            raw_date = m_date.group(0)
            parsed_date = try_parse_date(raw_date)
            if parsed_date:
                remainder = line[m_date.end():].strip()
                m_date2 = DATE_TOKEN_REGEX.search(remainder)
                if m_date2 and m_date2.start() <= 2:
                    remainder = remainder[m_date2.end():].strip()

                desc, amounts = extract_amounts_and_desc(remainder)
                desc = re.sub(
                    r"[\s|/\\-]*\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}[-/.\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/.\s]\d{2,4})\b\s*$",
                    "",
                    desc,
                    flags=re.IGNORECASE,
                ).strip()
                desc = re.sub(r"^[|\s\-:]+", "", desc)
                desc = re.sub(r"[|\s\-:]+$", "", desc)
                desc = " ".join(desc.split())

                debit, credit, current_balance = determine_debit_credit(desc, amounts, last_balance)
                if current_balance is not None:
                    last_balance = current_balance

                transactions.append({
                    "Date": parsed_date,
                    "Description": desc,
                    "Debit": debit,
                    "Credit": credit,
                })
        elif transactions:
            if not is_skip_line(line) and not is_header_line(line):
                cleaned = " ".join(line.split())
                if transactions[-1]["Debit"] == 0.0 and transactions[-1]["Credit"] == 0.0:
                    cont_desc, cont_amts = extract_amounts_and_desc(cleaned)
                    if cont_amts:
                        if cont_desc:
                            transactions[-1]["Description"] = (transactions[-1]["Description"] + " " + cont_desc).strip()
                        dr, cr, current_balance = determine_debit_credit(transactions[-1]["Description"], cont_amts, last_balance)
                        transactions[-1]["Debit"] = dr
                        transactions[-1]["Credit"] = cr
                        if current_balance is not None:
                            last_balance = current_balance
                        continue
                if cleaned and len(cleaned) > 1:
                    transactions[-1]["Description"] = (transactions[-1]["Description"] + " " + cleaned).strip()

    return transactions

def parse_statement_from_tables(pdf) -> list[dict]:
    """Extract transactions from structured tables if detected in PDF."""
    rows = []
    for page in pdf.pages:
        tables = page.extract_tables()
        if not tables:
            try:
                tables = page.extract_tables({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_y_tolerance": 4,
                    "intersection_x_tolerance": 15,
                })
            except Exception:
                tables = []
        for table in tables:
            for row in table:
                if not row or all(c is None or str(c).strip() == "" for c in row):
                    continue
                rows.append([str(c).strip() if c is not None else "" for c in row])

    if not rows:
        return []

    header_index = -1
    col_map = {}
    for i in range(min(15, len(rows))):
        mapping = identify_columns(rows[i])
        if "Date" in mapping and "Description" in mapping and ("Debit" in mapping or "Credit" in mapping or "Amount" in mapping):
            header_index = i
            col_map = mapping
            break
        if i + 1 < len(rows):
            merged = [f"{rows[i][c]} {rows[i+1][c]}".strip() for c in range(min(len(rows[i]), len(rows[i+1])))]
            m_mapping = identify_columns(merged)
            if "Date" in m_mapping and "Description" in m_mapping and ("Debit" in m_mapping or "Credit" in m_mapping or "Amount" in m_mapping):
                header_index = i + 1
                col_map = m_mapping
                break

    if header_index == -1:
        for i, row in enumerate(rows):
            mapping = identify_columns(row)
            if "Date" in mapping and "Description" in mapping:
                header_index = i
                col_map = mapping
                break

    if header_index == -1:
        return []

    data_rows = rows[header_index + 1:]
    transactions = []

    for row in data_rows:
        row_cells = [str(c).strip() if c is not None else "" for c in row]
        if not any(row_cells):
            continue

        row_header_map = identify_columns(row_cells)
        if "Date" in row_header_map and "Description" in row_header_map and ("Debit" in row_header_map or "Credit" in row_header_map or "Amount" in row_header_map):
            col_map = row_header_map
            continue

        row_text = " ".join(row_cells)
        if is_header_line(row_text):
            continue

        date_val = row_cells[col_map["Date"]] if "Date" in col_map and col_map["Date"] < len(row_cells) else ""
        desc_val = row_cells[col_map["Description"]] if "Description" in col_map and col_map["Description"] < len(row_cells) else ""
        desc_val = " ".join(desc_val.replace("\n", " ").split())

        if is_skip_line(desc_val):
            continue

        parsed_date = try_parse_date(date_val)

        if parsed_date is not None:
            if "Debit" in col_map and "Credit" in col_map:
                deb_str = row_cells[col_map["Debit"]] if col_map["Debit"] < len(row_cells) else ""
                cred_str = row_cells[col_map["Credit"]] if col_map["Credit"] < len(row_cells) else ""
                debit = parse_amount(deb_str)
                credit = parse_amount(cred_str)
            elif "Amount" in col_map:
                amt_str = row_cells[col_map["Amount"]] if col_map["Amount"] < len(row_cells) else ""
                type_str = row_cells[col_map["Type"]] if "Type" in col_map and col_map["Type"] < len(row_cells) else ""
                _, amounts = extract_amounts_and_desc(f"{amt_str} {type_str}")
                debit, credit, _ = determine_debit_credit(desc_val, amounts, None)
            else:
                debit, credit = 0.0, 0.0

            if not desc_val and debit == 0.0 and credit == 0.0:
                continue

            transactions.append({
                "Date": parsed_date,
                "Description": desc_val,
                "Debit": debit,
                "Credit": credit,
            })
        else:
            if desc_val and transactions:
                transactions[-1]["Description"] = (transactions[-1]["Description"] + " " + desc_val).strip()
                if transactions[-1]["Debit"] == 0.0 and transactions[-1]["Credit"] == 0.0:
                    if "Debit" in col_map and "Credit" in col_map:
                        deb_str = row_cells[col_map["Debit"]] if col_map["Debit"] < len(row_cells) else ""
                        cred_str = row_cells[col_map["Credit"]] if col_map["Credit"] < len(row_cells) else ""
                        transactions[-1]["Debit"] = parse_amount(deb_str)
                        transactions[-1]["Credit"] = parse_amount(cred_str)

    return transactions

def parse_statement_from_text(pdf) -> list[dict]:
    """Extract transactions from line-by-line page text when tables are absent or empty."""
    all_lines = []
    for page in pdf.pages:
        lines = extract_page_lines(page)
        all_lines.extend(lines)
    return parse_lines_to_transactions(all_lines)

def parse_statement_from_ocr(file_bytes: bytes, password: str | None = None) -> list[dict]:
    """Extract transactions from scanned/image PDFs using automated OCR."""
    try:
        import numpy as np
        import pypdfium2
        from rapidocr_onnxruntime import RapidOCR

        doc = pypdfium2.PdfDocument(file_bytes, password=password)
        ocr = RapidOCR()
        all_lines = []

        for page in doc:
            pil_img = page.render(scale=2).to_pil()
            img_arr = np.array(pil_img)
            result, _ = ocr(img_arr)
            if not result:
                continue

            lines_dict = {}
            for item in result:
                pts = item[0]
                top_y = min(p[1] for p in pts)
                left_x = min(p[0] for p in pts)
                txt = item[1].strip()
                if not txt:
                    continue

                matched_y = None
                for y in lines_dict:
                    if abs(top_y - y) <= 15:
                        matched_y = y
                        break
                if matched_y is None:
                    matched_y = top_y
                    lines_dict[matched_y] = []
                lines_dict[matched_y].append((left_x, txt))

            for y in sorted(lines_dict.keys()):
                row_items = sorted(lines_dict[y], key=lambda x: x[0])
                all_lines.append(" ".join(t[1] for t in row_items))

        if not all_lines:
            return []

        return parse_lines_to_transactions(all_lines)
    except Exception as e:
        print(f"OCR parsing failed: {e}")
        return []

def parse_statement(pdf_file, password: str | None = None) -> pd.DataFrame:
    """Extract transactions from bank statement PDF into a cleaned pandas DataFrame."""
    empty_df = pd.DataFrame(columns=["Date", "Description", "Debit", "Credit"])
    try:
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)

        if isinstance(pdf_file, (bytes, bytearray)):
            file_bytes = bytes(pdf_file)
        elif hasattr(pdf_file, "read"):
            file_bytes = pdf_file.read()
        else:
            file_bytes = None

        file_obj = io.BytesIO(file_bytes) if file_bytes is not None else pdf_file

        transactions = []
        is_encrypted = False

        # Attempt 1: Table Extraction (Structured PDFs)
        try:
            with pdfplumber.open(file_obj, password=password if password else None) as pdf:
                try:
                    transactions = parse_statement_from_tables(pdf)
                except Exception as e:
                    print(f"Table parsing failed: {e}")
                    transactions = []

                # Attempt 2: Text Extraction (Borderless Digital PDFs)
                if not transactions:
                    try:
                        transactions = parse_statement_from_text(pdf)
                    except Exception as e:
                        print(f"Text parsing failed: {e}")
                        transactions = []
        except Exception as pdf_err:
            err_str = str(pdf_err).lower()
            if "password" in err_str or "encrypt" in err_str:
                is_encrypted = True
                empty_df.attrs["error"] = "Password protected PDF. Please enter the correct password in the box above."
                return empty_df

        # Attempt 3: Optical Character Recognition (Scanned / Image PDFs)
        if not transactions and file_bytes and not is_encrypted:
            try:
                transactions = parse_statement_from_ocr(file_bytes, password=password)
            except Exception as e:
                print(f"OCR parsing failed: {e}")
                transactions = []

        if not transactions:
            if not empty_df.attrs.get("error"):
                empty_df.attrs["error"] = "Could not detect transaction rows. Please ensure the PDF is a valid bank statement."
            return empty_df

        df = pd.DataFrame(transactions)
        df = df[df["Description"].str.lower() != "description"]
        df = df[df["Description"].str.strip() != ""]
        df.reset_index(drop=True, inplace=True)
        return df

    except Exception as e:
        print(f"Error parsing PDF: {e}")
        empty_df.attrs["error"] = str(e)
        return empty_df
