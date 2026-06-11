
from models import SessionLocal, User, Watchlist
from sec_edgar_collector import collect

db = SessionLocal()
user = db.query(User).filter(User.username == "testtrader").first()
symbols = [w.symbol for w in db.query(Watchlist).filter(Watchlist.user_id == user.id).all()]
db.close()

print(f"Collecting real Form 4 data for {len(symbols)} watchlist symbols...\n")
for sym in symbols:
    print(f"===== {sym} =====")
    try:
        collect(sym, limit=10)
    except Exception as e:
        print(f"  ! error on {sym}: {e}")
    print()
print("All done.")
