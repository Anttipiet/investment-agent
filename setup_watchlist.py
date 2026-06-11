
from models import SessionLocal, User, Watchlist

# ============================================================
# YOUR WATCHLIST — edit freely. (symbol, sector)
# Just the universe of companies to COLLECT data on.
# Collecting data is NOT trading — this commits to nothing.
# ============================================================
WATCHLIST = [
    ("AAPL", "Technology"),
    ("MSFT", "Technology"),
    ("NVDA", "Technology"),
    ("JPM",  "Financials"),
    ("BAC",  "Financials"),
    ("JNJ",  "Healthcare"),
    ("UNH",  "Healthcare"),
    ("XOM",  "Energy"),
    ("CVX",  "Energy"),
    ("CAT",  "Industrials"),
    ("HD",   "Consumer Discretionary"),
    ("WMT",  "Consumer Staples"),
    ("PG",   "Consumer Staples"),
    ("DIS",  "Communication Services"),
]

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "testtrader").first()
    if not user:
        user = User(username="testtrader", email="testtrader@local")
        db.add(user); db.commit(); db.refresh(user)
        print("Created testtrader user.")
    else:
        print("Using existing testtrader user.")

    added, skipped = 0, 0
    for symbol, sector in WATCHLIST:
        exists = db.query(Watchlist).filter(
            Watchlist.user_id == user.id,
            Watchlist.symbol == symbol).first()
        if exists:
            skipped += 1
            continue
        db.add(Watchlist(user_id=user.id, symbol=symbol, sector=sector))
        added += 1
    db.commit()

    print(f"Watchlist: +{added} added, {skipped} already present.")
    rows = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
    print(f"Total watchlist size: {len(rows)}")
    for w in rows:
        print(f"  {w.symbol:6} {w.sector}")
finally:
    db.close()
