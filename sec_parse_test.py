
import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT")}

CODE_MEANINGS = {
    "P": "Open-market PURCHASE (real buy)",
    "S": "Open-market SALE",
    "A": "Grant/Award (compensation, NOT a buy)",
    "M": "Option exercise",
    "F": "Shares withheld for taxes",
    "G": "Gift",
    "C": "Conversion",
    "X": "Option exercise",
}

def map_type(code):
    if code == "P":
        return "BUY"
    if code == "S":
        return "SELL"
    return code  # preserve raw code; can never masquerade as BUY/SELL

def text(node, path):
    el = node.find(path)
    return el.text.strip() if el is not None and el.text else None

def parse_form4(raw_xml_url):
    r = requests.get(raw_xml_url, headers=HEADERS)
    root = ET.fromstring(r.content)

    symbol = text(root, "./issuer/issuerTradingSymbol")
    company = text(root, "./issuer/issuerName")
    owner = text(root, "./reportingOwner/reportingOwnerId/rptOwnerName")
    rel = root.find("./reportingOwner/reportingOwnerRelationship")
    title = text(rel, "./officerTitle") if rel is not None else None
    is_dir = text(rel, "./isDirector") if rel is not None else None
    is_off = text(rel, "./isOfficer") if rel is not None else None

    print(f"Company:  {company} ({symbol})")
    print(f"Insider:  {owner}")
    print(f"Role:     officer={is_off} director={is_dir} title={title!r}")
    print("-" * 60)

    txns = root.findall("./nonDerivativeTable/nonDerivativeTransaction")
    if not txns:
        print("No non-derivative transactions in this filing.")
        return

    for i, t in enumerate(txns, 1):
        sec = text(t, "./securityTitle/value")
        date = text(t, "./transactionDate/value")
        code = text(t, "./transactionCoding/transactionCode")
        shares = text(t, "./transactionAmounts/transactionShares/value")
        price = text(t, "./transactionAmounts/transactionPricePerShare/value")
        ad = text(t, "./transactionAmounts/transactionAcquiredDisposedCode/value")

        shares_n = float(shares) if shares else 0
        price_n = float(price) if price else 0
        amount = shares_n * price_n

        print(f"Txn {i}: {sec}  ({date})")
        print(f"   code {code} -> {CODE_MEANINGS.get(code, 'OTHER')}")
        print(f"   mapped transaction_type: {map_type(code)}")
        print(f"   shares {shares_n:,.0f} @ ${price_n:,.2f}  ({ad})  = ${amount:,.0f}")
        print()

if __name__ == "__main__":
    # Most recent AAPL Form 4 from the connection test (raw XML, no xsl prefix)
    url = "https://www.sec.gov/Archives/edgar/data/320193/000114036126023363/form4.xml"
    parse_form4(url)
