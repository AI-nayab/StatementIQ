import pandas as pd

CATEGORIES = {
    "Food": [
        "swiggy", "zomato", "blinkit", "zepto", "instamart", "dunzo",
        "grocery", "supermarket", "starbucks", "coffee", "restaurant",
        "cafe", "subway", "burger", "mcdonald", "domino", "kfc",
        "whole foods", "trader joe", "food"
    ],
    "Transport": [
        "uber", "ola", "rapido", "irctc", "metro", "fuel", "gas",
        "petrol", "shell", "chevron", "rail", "railway", "taxi",
        "transit", "lyft", "redbus", "fastag"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "meesho", "ajio", "nykaa",
        "target", "zara", "nike", "store", "clothing", "retail",
        "apparels", "mall", "electronics"
    ],
    "Bills": [
        "jio", "airtel", "vi", "vodafone", "bsnl", "electric", "electricity",
        "water", "utility", "broadband", "internet", "wifi", "phone",
        "mobile", "prepaid", "postpaid", "recharge", "bill", "dth",
        "tata play", "piped gas"
    ],
    "Subscriptions": [
        "netflix", "spotify", "apple", "icloud", "youtube", "prime",
        "hotstar", "disney", "sonyliv", "zee5", "membership", "gym",
        "streaming"
    ],
}

def categorize_transaction(description: str) -> str:
    """Categorize a transaction based on keyword matching in its description."""
    if not description or not isinstance(description, str):
        return "Other"
    desc_clean = description.lower()
    for category, keywords in CATEGORIES.items():
        if any(keyword in desc_clean for keyword in keywords):
            return category
    return "Other"

def categorize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply transaction categorization to a DataFrame and return a copy with a Category column."""
    df_result = df.copy()
    if "Description" in df_result.columns:
        df_result["Category"] = df_result["Description"].apply(categorize_transaction)
    else:
        df_result["Category"] = "Other"
    return df_result
