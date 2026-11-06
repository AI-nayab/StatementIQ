import smtplib, os
from dotenv import load_dotenv

load_dotenv()
try:
    s = smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT")))
    s.starttls()
    s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
    print("Login OK")
    s.quit()
except Exception as e:
    print("Error:", e)