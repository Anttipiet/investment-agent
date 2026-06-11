"""
Technical Analysis Module
Calculates moving averages, trends, momentum, support/resistance
"""

from models import SessionLocal, PriceSnapshot
from decimal import Decimal
from datetime import datetime, timedelta
import statistics

class TechnicalAnalyzer:
    """Analyze price data to identify trends and momentum"""
    
    def __init__(self, db):
        self.db = db
    
    # =========================================================================
    # MOVING AVERAGES & TRENDS
    # =========================================================================
    
    def calculate_moving_average(self, symbol: str, days: int) -> Decimal:
        """Calculate simple moving average"""
        snapshots = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).limit(days).all()
        
        if not snapshots or len(snapshots) < days:
            return None
        
        prices = [float(s.price) for s in snapshots]
        return Decimal(str(statistics.mean(prices)))
    
    def get_trend(self, symbol: str) -> str:
        """
        Determine trend direction
        UPTREND: Price > SMA200 and SMA50 > SMA200
        DOWNTREND: Price < SMA200 and SMA50 < SMA200
        SIDEWAYS: Between moving averages
        """
        snapshot = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).first()
        
        if not snapshot:
            return "UNKNOWN"
        
        sma20 = self.calculate_moving_average(symbol, 20)
        sma50 = self.calculate_moving_average(symbol, 50)
        sma200 = self.calculate_moving_average(symbol, 200)
        
        if not all([sma20, sma50, sma200]):
            return "INSUFFICIENT_DATA"
        
        price = snapshot.price
        
        # Strong uptrend
        if price > sma50 > sma200:
            return "UPTREND"
        
        # Strong downtrend
        elif price < sma50 < sma200:
            return "DOWNTREND"
        
        # Weak uptrend
        elif price > sma200 and price < sma50:
            return "WEAK_UPTREND"
        
        # Weak downtrend
        elif price < sma200 and price > sma50:
            return "WEAK_DOWNTREND"
        
        else:
            return "SIDEWAYS"
    
    # =========================================================================
    # MOMENTUM INDICATORS
    # =========================================================================
    
    def calculate_rsi(self, symbol: str, period: int = 14) -> float:
        """
        Calculate Relative Strength Index (0-100)
        <30 = Oversold (potential buy)
        >70 = Overbought (potential sell)
        """
        snapshots = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).limit(period + 1).all()
        
        if not snapshots or len(snapshots) < period + 1:
            return None
        
        # Calculate gains and losses
        prices = [float(s.price) for s in reversed(snapshots)]
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        # Calculate average gain/loss
        avg_gain = statistics.mean(gains) if gains else 0
        avg_loss = statistics.mean(losses) if losses else 0
        
        if avg_loss == 0:
            return 100 if avg_gain > 0 else 0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def is_oversold(self, symbol: str, threshold: int = 30) -> bool:
        """Check if stock is oversold (RSI < 30)"""
        rsi = self.calculate_rsi(symbol)
        return rsi and rsi < threshold
    
    def is_overbought(self, symbol: str, threshold: int = 70) -> bool:
        """Check if stock is overbought (RSI > 70)"""
        rsi = self.calculate_rsi(symbol)
        return rsi and rsi > threshold
    
    # =========================================================================
    # SUPPORT & RESISTANCE
    # =========================================================================
    
    def find_support_resistance(self, symbol: str, lookback_days: int = 60):
        """Find support and resistance levels"""
        snapshots = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).limit(lookback_days).all()
        
        if not snapshots:
            return None, None
        
        prices = [float(s.price) for s in reversed(snapshots)]
        
        # Support = recent low
        support = min(prices[-20:]) if len(prices) >= 20 else min(prices)
        
        # Resistance = recent high
        resistance = max(prices[-20:]) if len(prices) >= 20 else max(prices)
        
        return Decimal(str(support)), Decimal(str(resistance))
    
    # =========================================================================
    # VOLUME ANALYSIS
    # =========================================================================
    
    def get_volume_ratio(self, symbol: str) -> float:
        """Current volume vs 20-day average"""
        snapshots = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).limit(20).all()
        
        if not snapshots:
            return None
        
        current_volume = float(snapshots[0].volume)
        avg_volume = statistics.mean([float(s.volume) for s in snapshots])
        
        if avg_volume == 0:
            return None
        
        return round(current_volume / avg_volume, 2)
    
    def has_volume_spike(self, symbol: str, spike_threshold: float = 1.5) -> bool:
        """Check if current volume is significantly above average"""
        ratio = self.get_volume_ratio(symbol)
        return ratio and ratio > spike_threshold
    
    # =========================================================================
    # PRICE POSITION ANALYSIS
    # =========================================================================
    
    def price_vs_sma200(self, symbol: str) -> str:
        """Is price above or below 200-day moving average?"""
        snapshot = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).first()
        
        if not snapshot:
            return "UNKNOWN"
        
        sma200 = self.calculate_moving_average(symbol, 200)
        
        if not sma200:
            return "INSUFFICIENT_DATA"
        
        if snapshot.price > sma200:
            return "ABOVE"
        else:
            return "BELOW"
    
    def distance_from_52week_high(self, symbol: str) -> float:
        """% distance from 52-week high (0 = at high, 50 = halfway down)"""
        snapshot = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).first()
        
        if not snapshot or not snapshot.high_52w:
            return None
        
        high = float(snapshot.high_52w)
        current = float(snapshot.price)
        
        distance_pct = ((high - current) / high) * 100
        return round(distance_pct, 2)

# =========================================================================
# SUMMARY REPORT
# =========================================================================

def get_technical_summary(db, symbol: str) -> dict:
    """Get complete technical analysis summary"""
    analyzer = TechnicalAnalyzer(db)
    
    return {
        'symbol': symbol,
        'trend': analyzer.get_trend(symbol),
        'rsi': analyzer.calculate_rsi(symbol),
        'is_oversold': analyzer.is_oversold(symbol),
        'is_overbought': analyzer.is_overbought(symbol),
        'volume_ratio': analyzer.get_volume_ratio(symbol),
        'volume_spike': analyzer.has_volume_spike(symbol),
        'price_vs_sma200': analyzer.price_vs_sma200(symbol),
        'distance_from_high': analyzer.distance_from_52week_high(symbol),
    }