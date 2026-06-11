import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

load_dotenv()

client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True,
)

order_request = MarketOrderRequest(
    symbol="AAPL",
    qty=1,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
)

order = client.submit_order(order_request)

print("Order submitted")
print("ID:    ", order.id)
print("Symbol:", order.symbol)
print("Qty:   ", order.qty)
print("Side:  ", order.side)
print("Status:", order.status)