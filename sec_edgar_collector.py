
import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
from models import SessionLocal, InsiderTrade

load_dotenv()
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT")}
SEC_RATE_DELAY = 0.2  # seconds between requests — well under SEC's 10/sec limit


def map_type(code):
    if code == "P":
        return "BUY"
    if code == "S":
        return "SELL"
    return code  # raw code preserved; never masquerades as BUY/SELL


def _text(node, path):
    el = node.find(path)
    return el.text.strip() if el is not None and el.text else None


def get_cik(ticker):
    url = "https://www.sec.gov/files/company_tickers.json"
    data = requests.get(url, headers=HEADERS).json()
    for entry in data.values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)
    return None


def recent_form4_urls(cik, limit=10):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = requests.get(url, headers=HEADERS).json()
    recent = data["filings"]["recent"]
    rows = list(zip(recent["form"], recent["filingDate"],
                    recent["accessionNumber"], recent["primaryDocument"]))
    form4s = [r for r in rows if r[0] == "4"][:limit]
    cik_no_zeros = cik.lstrip("0")
    out = []
    for form, date, accession, doc in form4s:
        acc_nodash = accession.replace("-", "")
        raw_url = (f"https://www.sec.gov/Archives/edgar/data/"
                   f"{cik_no_zeros}/{acc_nodash}/form4.xml")
        out.append((accession, date, raw_url))
    return out


def parse_and_store(accession, filing_date, raw_url, db):
    r = requests.get(raw_url, headers=HEADERS)
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        print(f"  ! could not parse XML for {accession}, skipping")
        return 0

    symbol = _text(root, "./issuer/issuerTradingSymbol")
    company = _text(root, "./issuer/issuerName")
    owner = _text(root, "./reportingOwner/reportingOwnerId/rptOwnerName")
    rel = root.find("./reportingOwner/reportingOwnerRelationship")
    title = _text(rel, "./officerTitle") if rel is not None else None
    is_dir = (_text(rel, "./isDirector") in ("1", "true")) if rel is not None else False
    role = title if title else ("DIRECTOR" if is_dir else "OTHER")

    txns = root.findall("./nonDerivativeTable/nonDerivativeTransaction")
    stored = 0
    for idx, t in enumerate(txns, 1):
        code = _text(t, "./transactionCoding/transactionCode")
        shares = _text(t, "./transactionAmounts/transactionShares/value")
        price = _text(t, "./transactionAmounts/transactionPricePerShare/value")
        tdate = _text(t, "./transactionDate/value")

        shares_n = float(shares) if shares else 0
        price_n = float(price) if price else 0
        amount = shares_n * price_n

        unique_id = f"{accession}-{idx}"  # accession + txn index = unique per row

        exists = db.query(InsiderTrade).filter(
            InsiderTrade.sec_filing_id == unique_id).first()
        if exists:
            continue

        db.add(InsiderTrade(
            sec_filing_id=unique_id,
            symbol=symbol,
            company_name=company,
            insider_name=owner,
            insider_role=role,
            transaction_type=map_type(code),
            shares=int(shares_n),
            price=price_n,
            transaction_amount=amount,
            transaction_date=datetime.strptime(tdate, "%Y-%m-%d") if tdate else None,
            filing_date=datetime.strptime(filing_date, "%Y-%m-%d"),
            form_4_url=raw_url,
        ))
        stored += 1
    db.commit()
    return stored


def collect(ticker, limit=10):
    cik = get_cik(ticker)
    if not cik:
        print(f"No CIK for {ticker}")
        return
    print(f"{ticker} -> CIK {cik}")
    urls = recent_form4_urls(cik, limit=limit)
    print(f"Processing {len(urls)} recent Form 4 filings...\n")

    db = SessionLocal()
    total = 0
    try:
        for accession, date, raw_url in urls:
            n = parse_and_store(accession, date, raw_url, db)
            print(f"  {date}  {accession}: +{n} new transaction(s)")
            total += n
            time.sleep(SEC_RATE_DELAY)
    finally:
        db.close()
    print(f"\nDone. {total} new InsiderTrade rows stored.")


if __name__ == "__main__":
    collect("AAPL", limit=10)
