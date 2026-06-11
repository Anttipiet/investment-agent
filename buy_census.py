
import os
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT")}
DELAY = 0.12


def find_recent_index():
    for back in range(0, 7):
        d = datetime.utcnow() - timedelta(days=back)
        q = (d.month - 1) // 3 + 1
        url = (f"https://www.sec.gov/Archives/edgar/daily-index/"
               f"{d.year}/QTR{q}/master.{d.strftime('%Y%m%d')}.idx")
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200 and "|" in r.text:
            return d.strftime("%Y-%m-%d"), url, r.text
        time.sleep(DELAY)
    return None, None, None


def form4_filings(idx_text):
    out = []
    for line in idx_text.splitlines():
        parts = line.split("|")
        if len(parts) == 5 and parts[2].strip() == "4":
            cik, company, _, _, fname = parts
            url = "https://www.sec.gov/Archives/" + fname.strip()
            out.append((cik.strip(), company.strip(), url))
    return out


def extract_buys(txt_url):
    r = requests.get(txt_url, headers=HEADERS)
    m = re.search(r"<ownershipDocument>.*?</ownershipDocument>", r.text, re.DOTALL)
    if not m:
        return []
    try:
        root = ET.fromstring(m.group(0))
    except ET.ParseError:
        return []
    symbol = (root.findtext("./issuer/issuerTradingSymbol") or "").strip()
    owner = (root.findtext("./reportingOwner/reportingOwnerId/rptOwnerName") or "").strip()
    buys = []
    for t in root.findall("./nonDerivativeTable/nonDerivativeTransaction"):
        code = (t.findtext("./transactionCoding/transactionCode") or "").strip()
        if code != "P":
            continue
        shares = float(t.findtext("./transactionAmounts/transactionShares/value") or 0)
        price = float(t.findtext("./transactionAmounts/transactionPricePerShare/value") or 0)
        buys.append((symbol, owner, shares, price, shares * price))
    return buys


def census():
    date, url, idx_text = find_recent_index()
    if not date:
        print("Could not find a recent daily index.")
        return
    filings = form4_filings(idx_text)
    print(f"Daily index for {date}: {len(filings)} Form 4 filings market-wide.")
    print(f"Scanning each for genuine open-market BUYS (code P)...\n")
    all_buys = []
    for i, (cik, company, txt_url) in enumerate(filings, 1):
        try:
            all_buys.extend(extract_buys(txt_url))
        except Exception:
            pass
        if i % 25 == 0:
            print(f"  ...scanned {i}/{len(filings)} filings, {len(all_buys)} buys so far")
        time.sleep(DELAY)
    print(f"\n========== RESULT for {date} ==========")
    print(f"Form 4 filings scanned: {len(filings)}")
    print(f"Genuine open-market BUYS found: {len(all_buys)}")
    pct = (len(all_buys) / len(filings) * 100) if filings else 0
    print(f"That's {pct:.1f}% of all insider filings being actual purchases.\n")
    if all_buys:
        print("The buys:")
        for symbol, owner, shares, price, value in sorted(all_buys, key=lambda x: -x[4]):
            print(f"  {symbol:6} {owner[:28]:28} {shares:>10,.0f}sh @ ${price:>8,.2f} = ${value:>14,.0f}")
