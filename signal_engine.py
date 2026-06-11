"""
Signal Generation Engine - Enhanced with Phase 2 Fundamentals
Insider trades, institutional holdings, congressional trades + News sentiment + Valuation + Earnings + Macro
"""

from models import SessionLocal, Signal, InsiderTrade, InstitutionalHolding, CongressionalTrade, AlphaPick, NewsArticle
from datetime import datetime, timedelta
from valuation_analyzer import ValuationAnalyzer, get_valuation_signal_boost
from earnings_tracker import EarningsTracker, get_earnings_signal_boost
from macro_analyzer import MacroAnalyzer, get_macro_signal_boost
import statistics

class SignalGenerator:
    """Generate buy/sell signals from multiple data sources with Phase 2 fundamental analysis"""
    
    def __init__(self, db):
        self.db = db
        self.valuation = ValuationAnalyzer(db)
        self.earnings = EarningsTracker(db)
        self.macro = MacroAnalyzer()
    
    # ========================================================================
    # PHASE 1: INSIDER TRADING SIGNALS
    # ========================================================================
    
    def generate_insider_signals(self, symbol: str) -> list:
        """Detect insider trading patterns"""
        signals = []
        
        # Get recent insider trades (last 30 days)
        recent_trades = self.db.query(InsiderTrade).filter(
            InsiderTrade.symbol == symbol,
            InsiderTrade.transaction_date >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        if not recent_trades:
            return signals
        
        # Separate buys and sells by insider role
        ceo_cfo_buys = [t for t in recent_trades 
                       if t.transaction_type == 'BUY' 
                       and t.insider_role in ['CEO', 'CFO']
                       and float(t.transaction_amount) > 500000]
        
        ceo_cfo_sells = [t for t in recent_trades 
                        if t.transaction_type == 'SELL' 
                        and t.insider_role in ['CEO', 'CFO']
                        and float(t.transaction_amount) > 500000]
        
        # BUY Signal: CEO/CFO buying >$500K
        if ceo_cfo_buys:
            confidence = 75
            reason = {
                'type': 'INSIDER_BUYING',
                'count': len(ceo_cfo_buys),
                'insiders': [t.insider_name for t in ceo_cfo_buys],
                'total_amount': sum(float(t.transaction_amount) for t in ceo_cfo_buys)
            }
            signals.append({
                'symbol': symbol,
                'signal_type': 'BUY',
                'tier': 1,
                'base_confidence': confidence,
                'reason': reason,
                'source': 'INSIDER'
            })
        
        # SELL Signal: CEO/CFO selling >$500K
        if ceo_cfo_sells:
            confidence = 70
            reason = {
                'type': 'INSIDER_SELLING',
                'count': len(ceo_cfo_sells),
                'insiders': [t.insider_name for t in ceo_cfo_sells],
                'total_amount': sum(float(t.transaction_amount) for t in ceo_cfo_sells)
            }
            signals.append({
                'symbol': symbol,
                'signal_type': 'SELL',
                'tier': 1,
                'base_confidence': confidence,
                'reason': reason,
                'source': 'INSIDER'
            })
        
        # TIER 2: Coordinated buying (3+ insiders in 14 days)
        insider_names = set([t.insider_name for t in recent_trades if t.transaction_type == 'BUY'])
        if len(insider_names) >= 3:
            signals.append({
                'symbol': symbol,
                'signal_type': 'BUY',
                'tier': 2,
                'base_confidence': 70,
                'reason': {'type': 'COORDINATED_INSIDER_BUYING', 'insider_count': len(insider_names)},
                'source': 'INSIDER'
            })
        
        return signals
    
    # ========================================================================
    # PHASE 1: INSTITUTIONAL SIGNALS
    # ========================================================================
    
    def generate_institutional_signals(self, symbol: str) -> list:
        """Detect major fund accumulation/distribution"""
        signals = []
        
        # Get recent 13F filings (last 90 days)
        recent_holdings = self.db.query(InstitutionalHolding).filter(
            InstitutionalHolding.symbol == symbol,
            InstitutionalHolding.filing_date >= datetime.utcnow() - timedelta(days=90)
        ).all()
        
        if not recent_holdings:
            return signals
        
        # Check for major fund increases (5%+ increase)
        major_increases = [h for h in recent_holdings 
                          if h.change_percentage and h.change_percentage > 5]
        
        if major_increases:
            confidence = 65
            largest = max(major_increases, key=lambda x: x.change_percentage)
            signals.append({
                'symbol': symbol,
                'signal_type': 'BUY',
                'tier': 2,
                'base_confidence': confidence,
                'reason': {
                    'type': 'INSTITUTIONAL_ACCUMULATION',
                    'institutions': [h.institution_name for h in major_increases],
                    'avg_increase_pct': statistics.mean([h.change_percentage for h in major_increases])
                },
                'source': 'INSTITUTIONAL'
            })
        
        return signals
    
    # ========================================================================
    # PHASE 1: CONGRESSIONAL SIGNALS
    # ========================================================================
    
    def generate_congressional_signals(self, symbol: str) -> list:
        """Detect congressional trading patterns"""
        signals = []
        
        # Get recent congressional trades (last 30 days)
        recent_trades = self.db.query(CongressionalTrade).filter(
            CongressionalTrade.symbol == symbol,
            CongressionalTrade.transaction_date >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        if not recent_trades:
            return signals
        
        buys = [t for t in recent_trades if t.action == 'BUY']
        sells = [t for t in recent_trades if t.action == 'SELL']
        
        if len(buys) >= 2:
            signals.append({
                'symbol': symbol,
                'signal_type': 'BUY',
                'tier': 3,
                'base_confidence': 55,
                'reason': {'type': 'CONGRESSIONAL_BUYING', 'count': len(buys)},
                'source': 'CONGRESSIONAL'
            })
        
        if len(sells) >= 2:
            signals.append({
                'symbol': symbol,
                'signal_type': 'SELL',
                'tier': 3,
                'base_confidence': 55,
                'reason': {'type': 'CONGRESSIONAL_SELLING', 'count': len(sells)},
                'source': 'CONGRESSIONAL'
            })
        
        return signals
    
    # ========================================================================
    # NEWS SENTIMENT BOOST
    # ========================================================================
    
    def get_news_sentiment_boost(self, symbol: str, signal_type: str) -> float:
        """Boost signal confidence with news sentiment"""
        recent_news = self.db.query(NewsArticle).filter(
            NewsArticle.symbol == symbol,
            NewsArticle.fetched_at >= datetime.utcnow() - timedelta(days=7)
        ).all()
        
        if not recent_news:
            return 0
        
        # Match sentiment to signal direction
        matching_news = []
        if signal_type == 'BUY':
            matching_news = [n for n in recent_news if n.sentiment == 'POSITIVE']
        else:  # SELL
            matching_news = [n for n in recent_news if n.sentiment == 'NEGATIVE']
        
        if matching_news:
            return 10  # +10% confidence boost
        
        return 0
    
    # ========================================================================
    # PHASE 2: VALUATION BOOST
    # ========================================================================
    
    def get_valuation_boost(self, symbol: str, sector: str, signal_type: str) -> float:
        """Boost signal if fundamentals are attractive"""
        val_summary = self.valuation.get_valuation_summary(symbol, sector)
        
        # For BUY signals, boost if undervalued
        if signal_type == 'BUY' and val_summary['investment_grade'] == 'BUY':
            return 10  # +10% confidence
        
        # For SELL signals, boost if overvalued
        if signal_type == 'SELL' and val_summary['investment_grade'] == 'AVOID':
            return 10  # +10% confidence
        
        # Penalty for opposite signals
        if signal_type == 'BUY' and val_summary['investment_grade'] == 'AVOID':
            return -10  # -10% confidence
        
        return 0
    
    # ========================================================================
    # PHASE 2: EARNINGS BOOST
    # ========================================================================
    
    def get_earnings_boost(self, symbol: str, signal_type: str) -> float:
        """Boost signal based on earnings momentum"""
        earnings_summary = self.earnings.get_earnings_summary(symbol)
        
        if signal_type == 'BUY' and earnings_summary['earnings_momentum'] == 'STRONG':
            return 15  # +15% confidence
        
        if signal_type == 'SELL' and earnings_summary['earnings_momentum'] == 'WEAK':
            return 10  # +10% confidence
        
        return 0
    
    # ========================================================================
    # PHASE 2: MACRO BOOST
    # ========================================================================
    
    def get_macro_boost(self, sector: str, signal_type: str) -> float:
        """Boost signal based on macro environment"""
        macro_summary = self.macro.get_macro_summary()
        sector_boost = self.macro.get_sector_boost(sector)
        
        # Apply sector boost
        boost = sector_boost
        
        # Market environment adjustment
        if signal_type == 'BUY':
            if macro_summary['market_environment'] == 'FAVORABLE':
                boost += 5
            elif macro_summary['market_environment'] == 'CHALLENGING':
                boost -= 5
        
        return boost
    
    # ========================================================================
    # FINAL SIGNAL GENERATION WITH PHASE 2 BOOSTS
    # ========================================================================
    
    def generate_all_signals(self, symbol: str, sector: str) -> list:
        """Generate all signals for a symbol with Phase 1 + Phase 2 enhancements"""
        all_signals = []
        
        # Phase 1: Base signals
        all_signals.extend(self.generate_insider_signals(symbol))
        all_signals.extend(self.generate_institutional_signals(symbol))
        all_signals.extend(self.generate_congressional_signals(symbol))
        
        # Phase 2: Apply boosts to each signal
        for signal in all_signals:
            signal_type = signal['signal_type']
            
            # Calculate all boosts
            news_boost = self.get_news_sentiment_boost(symbol, signal_type)
            val_boost = self.get_valuation_boost(symbol, sector, signal_type)
            earnings_boost = self.get_earnings_boost(symbol, signal_type)
            macro_boost = self.get_macro_boost(sector, signal_type)
            
            # Apply boosts
            signal['news_boost'] = news_boost
            signal['valuation_boost'] = val_boost
            signal['earnings_boost'] = earnings_boost
            signal['macro_boost'] = macro_boost
            
            # Final confidence = base + boosts (capped at 100%)
            base_conf = signal['base_confidence']
            total_boost = news_boost + val_boost + earnings_boost + macro_boost
            final_confidence = min(100, base_conf + total_boost)
            
            signal['confidence'] = final_confidence
            signal['phase2_analysis'] = {
                'valuation': self.valuation.get_valuation_summary(symbol, sector),
                'earnings': self.earnings.get_earnings_summary(symbol),
                'macro': self.macro.get_macro_summary()
            }
        
        return all_signals
    
    def save_signal_to_db(self, signal: dict):
        """Save signal to database"""
        db_signal = Signal(
            symbol=signal['symbol'],
            signal_type=signal['signal_type'],
            tier=signal['tier'],
            confidence=signal['confidence'],
            data_source=signal['source'],
            reason=signal['reason'],
            detected_at=datetime.utcnow()
        )
        self.db.add(db_signal)
        self.db.commit()
        return db_signal

def generate_signals_for_all(db):
    """Generate signals for all watchlist symbols"""
    from models import Watchlist, User
    
    generator = SignalGenerator(db)
    
    # Get test user
    user = db.query(User).filter(User.username == "testtrader").first()
    if not user:
        print("No test user found")
        return
    
    # Get watchlist
    watchlist = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
    
    for watch in watchlist:
        print(f"\n📊 {watch.symbol} ({watch.sector})")
        signals = generator.generate_all_signals(watch.symbol, watch.sector)
        
        if signals:
            for signal in signals:
                generator.save_signal_to_db(signal)
                print(f"  ✓ {signal['signal_type']} Signal T{signal['tier']} - {signal['confidence']:.1f}% confidence")
                print(f"    Base: {signal['base_confidence']}% | News: +{signal['news_boost']}% | Valuation: +{signal['valuation_boost']}% | Earnings: +{signal['earnings_boost']}% | Macro: +{signal['macro_boost']}%")
        else:
            print(f"  (no signals)")

if __name__ == "__main__":
    db = SessionLocal()
    generate_signals_for_all(db)
    db.close()