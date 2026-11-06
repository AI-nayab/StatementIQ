import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def get_connection():
    """Establish and return a MySQL database connection using .env configuration."""
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "statementiq_db"),
        )
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db() -> bool:
    """Create the target MySQL database and the transactions table if they do not exist."""
    try:
        server_conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
        )
        cursor = server_conn.cursor()
        db_name = os.getenv("DB_NAME", "statementiq_db")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        cursor.close()
        server_conn.close()

        conn = get_connection()
        if not conn:
            return False

        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date VARCHAR(20) NOT NULL,
                description VARCHAR(255) NOT NULL,
                debit DECIMAL(10, 2) DEFAULT 0.00,
                credit DECIMAL(10, 2) DEFAULT 0.00,
                category VARCHAR(50) DEFAULT 'Other',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_tx (date, description, debit, credit)
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"Error initializing database: {e}")
        return False

def insert_transactions(df: pd.DataFrame) -> int:
    """Insert DataFrame records into transactions table, skipping duplicates."""
    if df.empty:
        return 0
    try:
        init_db()
        conn = get_connection()
        if not conn:
            return 0

        cursor = conn.cursor()
        query = """
            INSERT IGNORE INTO transactions (date, description, debit, credit, category)
            VALUES (%s, %s, %s, %s, %s)
        """
        records = [
            (
                str(row.get("Date", "")),
                str(row.get("Description", "")),
                float(row.get("Debit", 0.0)),
                float(row.get("Credit", 0.0)),
                str(row.get("Category", "Other")),
            )
            for _, row in df.iterrows()
        ]
        cursor.executemany(query, records)
        conn.commit()
        inserted = cursor.rowcount
        cursor.close()
        conn.close()
        return inserted
    except Error as e:
        print(f"Error saving transactions: {e}")
        return 0

def fetch_all_transactions() -> pd.DataFrame:
    """Retrieve all saved transactions from the database as a DataFrame."""
    try:
        conn = get_connection()
        if not conn:
            return pd.DataFrame()
        query = "SELECT date AS Date, description AS Description, debit AS Debit, credit AS Credit, category AS Category FROM transactions ORDER BY id DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Error as e:
        print(f"Error fetching transactions: {e}")
        return pd.DataFrame()

