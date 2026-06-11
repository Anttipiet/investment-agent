
import os
from datetime import datetime
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from models import SessionLocal, PaperTrade

load_dotenv()

MIN_CONFIDENCE        = 0.70
MAX_DOLLARS_PER_TRADE = 2000
MAX_OPEN_POSITIONS    = 10
KILL_SWITCH_FILE      = "STOP_TRADING"

client = TradingClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), paper=True)


def committed_symbols():
    held = {p.symbol for p in client.get_all_positions()}
    open_orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))
    pending_buys = {o.symbol for o in open_orders if o.side == OrderSide.BUY}
    return held | pending_buys


def held_symbols():
    return {p.symbol for p in client.get_all_positions()}


def check_guardrails(signal):
    if os.path.exists(KILL_SWITCH_FILE):
        return False, "Kill switch active (STOP_TRADING file present)"
    side = signal["action"].lower()
    if side not in ("buy", "sell"):
        return False, f"Unknown action '{signal['action']}'"
    if signal["confidence"] < MIN_CONFIDENCE:
        return False, f"Confidence {signal['confidence']:.2f} < {MIN_CONFIDENCE}"
    try:
        asset = client.get_asset(signal["symbol"])
    except Exception:
        return False, f"Could not look up {signal['symbol']} on Alpaca"
    if not asset.tradable:
        return False, f"{signal['symbol']} is not tradable on Alpaca"
    if side == "buy":
        if not asset.fractionable:
            return False, f"{signal['symbol']} doesn't support dollar-based orders"
        committed = committed_symbols()
        if signal["symbol"] in committed:
            return False, f"Already in or pending {signal['symbol']} — not stacking"
        if len(committed) >= MAX_OPEN_POSITIONS:
            return False, f"At max positions/pending ({MAX_OPEN_POSITIONS})"
    else:
        if signal["symbol"] not in held_symbols():
            return False, f"No {signal['symbol']} position to close — ignoring SELL"
    return True, "All guardrails passed"


def log_open_trade(signal, order):
    db = SessionLocal()
    try:
        pt = PaperTrade(
            symbol=signal["symbol"],
            signal_type="BUY",
            tier=signal.get("tier"),
            entry_confidence=signal.get("entry_confidence_raw"),
            alpaca_order_id=str(order.id),
            notional=float(order.notional) if order.notional else None,
            entry_price=float(order.filled_avg_price) if order.filled_avg_price else None,
            entry_date=datetime.utcnow(),
            status="OPEN",
            triggered_by_signal_id=signal.get("signal_id"),
        )
        db.add(pt)
        db.commit()
        print(f"   LOGGED: paper_trades row {pt.id} (OPEN)")
    finally:
        db.close()


def log_close_trade(symbol, order):
    db = SessionLocal()
    try:
        pt = (db.query(PaperTrade)
                .filter(PaperTrade.symbol == symbol, PaperTrade.status == "OPEN")
                .order_by(PaperTrade.entry_date.desc())
                .first())
        if pt:
            pt.exit_date = datetime.utcnow()
            pt.exit_alpaca_order_id = str(order.id)
            pt.status = "CLOSED"
            db.commit()
            print(f"   LOGGED: paper_trades row {pt.id} marked CLOSED")
        else:
            print("   (no matching OPEN paper trade in DB to close)")
    finally:
        db.close()


def execute_signal(signal):
    approved, reason = check_guardrails(signal)
    print(f"[{signal['symbol']}] {signal['action'].upper()} (conf {signal['confidence']:.2f}) -> {reason}")
    if not approved:
        print("   REJECTED — no order placed.\n")
        return None
    if signal["action"].lower() == "buy":
        account = client.get_account()
        budget = min(MAX_DOLLARS_PER_TRADE, float(account.cash))
        order = client.submit_order(MarketOrderRequest(
            symbol=signal["symbol"], notional=round(budget, 2),
            side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
        print(f"   ORDER PLACED: BUY ${budget:.0f} of {signal['symbol']} (id {order.id}, status {order.status})")
        log_open_trade(signal, order)
        print()
        return order
    else:
        order = client.close_position(signal["symbol"])
        print(f"   POSITION CLOSED: SELL all {signal['symbol']} (id {order.id}, status {order.status})")
        log_close_trade(signal["symbol"], order)
        print()
        return order


def execute_engine_signal(engine_signal):
    translated = {
        "symbol": engine_signal["symbol"],
        "action": engine_signal["signal_type"],
        "confidence": engine_signal["confidence"] / 100,
        "entry_confidence_raw": engine_signal["confidence"],
        "tier": engine_signal.get("tier"),
        "signal_id": engine_signal.get("id"),
    }
    return execute_signal(translated)
