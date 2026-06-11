import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

# paper=True forces every call to the paper endpoint — real money cannot be touched here
client = TradingClient(api_key, secret_key, paper=True)

account = client.get_account()

print("Connected to Alpaca PAPER account")
print("Account number:", account.account_number)
print("Status:        ", account.status)
print("Cash:          ", account.cash)
print("Buying power:  ", account.buying_power)