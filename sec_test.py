
import os
import requests
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT")}

def get_cik(ticker):
    """Resolve a ticker to its 10-digit zero-padded CIK."""
    url = "https://www.sec.gov/files/company_tickers.json"
    data = requests.get(url, headers=HEADERS).json()
    for entry in data.values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)
    return None

def get_recent_form4s(ticker, limit=5):
    """Fetch recent Form 4 filings for a ticker. Connection test only."""
    cik = get_cik(ticker)
    if not cik:
        print(f"Could not find CIK for {ticker}")
        return
    print(f"{ticker} -> CIK {cik}")

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = requests.get(url, headers=HEADERS).json()
    print(f"Company: {data.get('name')}")

    recent = data["filings"]["recent"]
    # Parallel arrays — zip by shared index, never sort/filter one alone
    rows = list(zip(
        recent["form"],
        recent["filingDate"],
        recent["accessionNumber"],
        recent["primaryDocument"],
    ))
    form4s = [r for r in rows if r[0] == "4"]
    print(f"Found {len(form4s)} Form 4 filings in recent history. Showing {min(limit, len(form4s))}:\n")

    cik_no_zeros = cik.lstrip("0")
    for form, date, accession, doc in form4s[:limit]:
        acc_no_dashes = accession.replace("-", "")
        filing_url = (f"https://www.sec.gov/Archives/edgar/data/"
                      f"{cik_no_zeros}/{acc_no_dashes}/{doc}")
        print(f"  {date}  acc {accession}")
        print(f"    {filing_url}")

if __name__ == "__main__":
    get_recent_form4s("AAPL", limit=5)
