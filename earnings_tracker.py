"""
Earnings Tracking - Calendar, Surprises, Guidance
"""

from models import SessionLocal, AlphaPick
from datetime import datetime, timedelta

class EarningsTracker:
    """Track earnings events and surprises"""
    
    def __init__(self, db):
        self.db = db
    
    def get_upcoming_earnings(self, symbol: str, days_ahead: int = 30) -> list:
        """Get upcoming earnings dates"""
        # Hardcoded sample earnings calendar (Phase 2: integrate real API)
        earnings_calendar = {
            'NVDA': datetime(2026, 7, 15),
            'RTX': datetime(2026, 6, 15),
            'LMT': datetime(2026, 6, 20),
            'BA': datetime(2026, 7, 1),
            'CVX': datetime(2026, 6, 10),
        }
        
        if symbol not in earnings_calendar:
            return []
        
        earnings_date = earnings_calendar[symbol]
        days_until = (earnings_date - datetime.utcnow()).days
        
        if 0 <= days_until <= days_ahead:
            return [{
                'symbol': symbol,
                'earnings_date': earnings_date,
                'days_until': days_until,
                'season': 'Q2' if earnings_date.month in [4, 5, 6] else 'Q3'
            }]
        return []
    
    def get_eps_surprise_history(self, symbol: str) -> list:
        """Historical EPS surprises"""
        # Hardcoded sample data (Phase 2: integrate real data)
        surprises = {
            'NVDA': [
                {'quarter': 'Q1 2026', 'expected': 0.80, 'actual': 0.92, 'surprise_pct': 15},
                {'quarter': 'Q4 2025', 'expected': 0.65, 'actual': 0.78, 'surprise_pct': 20},
            ],
            'RTX': [
                {'quarter': 'Q1 2026', 'expected': 1.20, 'actual': 1.18, 'surprise_pct': -1.5},
                {'quarter': 'Q4 2025', 'expected': 1.15, 'actual': 1.25, 'surprise_pct': 8.5},
            ],
        }
        return surprises.get(symbol, [])
    
    def get_avg_eps_surprise(self, symbol: str) -> float:
        """Average EPS surprise %"""
        history = self.get_eps_surprise_history(symbol)
        if not history:
            return 0
        
        surprises = [h['surprise_pct'] for h in history]
        return sum(surprises) / len(surprises)
    
    def get_revenue_guidance_trend(self, symbol: str) -> dict:
        """Revenue guidance trend"""
        # Hardcoded sample
        guidance = {
            'NVDA': {'current_guidance': 25, 'prev_guidance': 18, 'raise_pct': 39},
            'RTX': {'current_guidance': 12, 'prev_guidance': 12, 'raise_pct': 0},
            'BA': {'current_guidance': -5, 'prev_guidance': -8, 'raise_pct': 60},
        }
        
        data = guidance.get(symbol, {'current_guidance': 0, 'prev_guidance': 0, 'raise_pct': 0})
        
        if data['raise_pct'] > 10:
            trend = "RAISED_SIGNIFICANTLY"
        elif data['raise_pct'] > 0:
            trend = "RAISED"
        elif data['raise_pct'] < -10:
            trend = "LOWERED_SIGNIFICANTLY"
        elif data['raise_pct'] < 0:
            trend = "LOWERED"
        else:
            trend = "MAINTAINED"
        
        return {
            'current_guidance': data['current_guidance'],
            'prev_guidance': data['prev_guidance'],
            'change_pct': data['raise_pct'],
            'trend': trend
        }
    
    def get_earnings_summary(self, symbol: str) -> dict:
        """Complete earnings picture"""
        upcoming = self.get_upcoming_earnings(symbol)
        eps_surprise = self.get_avg_eps_surprise(symbol)
        guidance = self.get_revenue_guidance_trend(symbol)
        history = self.get_eps_surprise_history(symbol)
        
        earnings_score = 50  # Base score
        
        # Boost for positive EPS surprises
        if eps_surprise > 10:
            earnings_score += 20
        elif eps_surprise > 0:
            earnings_score += 10
        elif eps_surprise < -10:
            earnings_score -= 20
        
        # Boost for raised guidance
        if guidance['trend'] == "RAISED_SIGNIFICANTLY":
            earnings_score += 15
        elif guidance['trend'] == "RAISED":
            earnings_score += 8
        elif guidance['trend'] == "LOWERED_SIGNIFICANTLY":
            earnings_score -= 15
        
        return {
            'symbol': symbol,
            'upcoming_earnings': upcoming,
            'eps_surprise_avg': round(eps_surprise, 2),
            'recent_surprises': history[-2:] if history else [],
            'guidance_trend': guidance,
            'earnings_score': max(0, min(100, earnings_score)),
            'earnings_momentum': 'STRONG' if earnings_score > 65 else 'MODERATE' if earnings_score > 40 else 'WEAK'
        }

def get_earnings_signal_boost(tracker, symbol: str) -> float:
    """Boost signal if earnings momentum is strong"""
    summary = tracker.get_earnings_summary(symbol)
    
    boost = 0
    if summary['earnings_momentum'] == 'STRONG':
        boost = 15  # +15% confidence
    elif summary['earnings_momentum'] == 'WEAK':
        boost = -10  # -10% confidence
    
    return boost