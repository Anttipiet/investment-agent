import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()
client = TradingClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), paper=True)
cancelled = client.cancel_orders()
print(f"Cancelled {len(cancelled)} open order(s). Account is clean.")