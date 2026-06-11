from executor import execute_signal

# Hand-made signals to test the gate — not from your engine yet.
fake_signals = [
    {"symbol": "MSFT", "action": "buy", "confidence": 0.82},  # should PASS
    {"symbol": "NVDA", "action": "buy", "confidence": 0.55},  # should REJECT (low confidence)
    {"symbol": "AAPL", "action": "buy", "confidence": 0.90},  # should REJECT (already held from earlier)
]

for sig in fake_signals:
    execute_signal(sig)