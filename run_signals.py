from models import SessionLocal, Watchlist, User
from signal_engine import SignalGenerator
from executor import execute_engine_signal

db = SessionLocal()
generator = SignalGenerator(db)

user = db.query(User).filter(User.username == "testtrader").first()
watchlist = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()

print(f"Running {len(watchlist)} watchlist symbols through the gate...\n")

for watch in watchlist:
    signals = generator.generate_all_signals(watch.symbol, watch.sector)
    for sig in signals:
        execute_engine_signal(sig)

print("Done.")
db.close()