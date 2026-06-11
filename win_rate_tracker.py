"""
Signal Win Rate Tracker
Track which signals are profitable and learn from them
"""

from models import SessionLocal, Signal, SignalPerformance, VirtualTrade
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List

class WinRateTracker:
    """Track signal profitability and patterns"""
    
    def __init__(self, db):
        self.db = db
    
    # =========================================================================
    # SIGNAL PERFORMANCE LOGGING
    # =========================================================================
    
    def log_signal_outcome(self, signal_id: int, symbol: str, 
                          entry_price: Decimal, exit_price: Decimal = None,
                          exit_date: datetime = None):
        """Record how a signal performed"""
        signal = self.db.query(Signal).filter(Signal.id == signal_id).first()
        
        if not signal:
            return
        
        perf = SignalPerformance(
            signal_id=signal_id,
            symbol=symbol,
            signal_type=signal.signal_type,
            signal_tier=signal.tier,
            entry_date=signal.detected_at,
            entry_price=entry_price,
            entry_confidence=signal.confidence,
            exit_date=exit_date,
            exit_price=exit_price
        )
        
        # Calculate return if exited
        if exit_price:
            return_pct = ((float(exit_price) - float(entry_price)) / float(entry_price)) * 100
            perf.return_pct = return_pct
            perf.profitable = return_pct > 0
            
            # Days held
            if exit_date:
                perf.days_held = (exit_date - signal.detected_at).days
        
        self.db.add(perf)
        self.db.commit()
    
    # =========================================================================
    # WIN RATE CALCULATIONS
    # =========================================================================
    
    def get_win_rate(self, symbol: str = None, 
                     signal_type: str = None,
                     tier: int = None) -> Dict:
        """Calculate win rate for filtered signals"""
        
        query = self.db.query(SignalPerformance).filter(
            SignalPerformance.exit_price.isnot(None)  # Only closed positions
        )
        
        if symbol:
            query = query.filter(SignalPerformance.symbol == symbol)
        if signal_type:
            query = query.filter(SignalPerformance.signal_type == signal_type)
        if tier:
            query = query.filter(SignalPerformance.signal_tier == tier)
        
        perfs = query.all()
        
        if not perfs:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0
            }
        
        winning = [p for p in perfs if p.profitable == True]
        losing = [p for p in perfs if p.profitable == False]
        
        avg_win = sum([p.return_pct for p in winning]) / len(winning) if winning else 0
        avg_loss = sum([p.return_pct for p in losing]) / len(losing) if losing else 0
        
        # Profit factor = total wins / total losses
        total_wins = sum([p.return_pct for p in winning]) if winning else 0
        total_losses = abs(sum([p.return_pct for p in losing])) if losing else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        return {
            'total_trades': len(perfs),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': (len(winning) / len(perfs) * 100) if perfs else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_profit': total_wins + total_losses
        }
    
    # =========================================================================
    # SIGNAL QUALITY RANKING
    # =========================================================================
    
    def rank_signal_types(self) -> List[Dict]:
        """Rank signal types by profitability"""
        
        results = []
        
        for signal_type in ['BUY', 'SELL']:
            for tier in [1, 2, 3, 4]:
                stats = self.get_win_rate(signal_type=signal_type, tier=tier)
                
                if stats['total_trades'] > 0:
                    results.append({
                        'signal_type': signal_type,
                        'tier': tier,
                        'total_trades': stats['total_trades'],
                        'win_rate': stats['win_rate'],
                        'avg_return': (stats['avg_win'] + stats['avg_loss']) / 2,
                        'profit_factor': stats['profit_factor']
                    })
        
        # Sort by win rate
        results.sort(key=lambda x: x['profit_factor'], reverse=True)
        return results
    
    # =========================================================================
    # INSIGHTS
    # =========================================================================
    
    def get_best_performing_signal(self) -> Dict:
        """Which signal type is most profitable?"""
        rankings = self.rank_signal_types()
        return rankings[0] if rankings else None
    
    def get_signal_insight(self, symbol: str) -> str:
        """Generate insight for a specific symbol"""
        stats = self.get_win_rate(symbol=symbol)
        
        if stats['total_trades'] == 0:
            return f"No completed trades for {symbol} yet."
        
        if stats['win_rate'] >= 70:
            return f"✓ {symbol} signals are HIGHLY PROFITABLE ({stats['win_rate']:.1f}% win rate)"
        elif stats['win_rate'] >= 50:
            return f"✓ {symbol} signals are PROFITABLE ({stats['win_rate']:.1f}% win rate)"
        else:
            return f"✗ {symbol} signals are UNDERPERFORMING ({stats['win_rate']:.1f}% win rate)"
    
    # =========================================================================
    # HISTORICAL ANALYSIS
    # =========================================================================
    
    def get_stats_by_period(self, days: int = 30) -> Dict:
        """Get stats for last N days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(SignalPerformance).filter(
            SignalPerformance.entry_date >= cutoff,
            SignalPerformance.exit_price.isnot(None)
        )
        
        return self.get_win_rate()

# =========================================================================
# QUICK STATS SUMMARY
# =========================================================================

def print_win_rate_summary(db):
    """Print summary of signal performance"""
    tracker = WinRateTracker(db)
    
    print("\n" + "="*70)
    print("📊 SIGNAL WIN RATE ANALYSIS")
    print("="*70)
    
    # Overall stats
    overall = tracker.get_win_rate()
    print(f"\n🎯 OVERALL PERFORMANCE:")
    print(f"   Total Closed Trades: {overall['total_trades']}")
    print(f"   Winning: {overall['winning_trades']} | Losing: {overall['losing_trades']}")
    print(f"   Win Rate: {overall['win_rate']:.1f}%")
    print(f"   Avg Win: +{overall['avg_win']:.2f}% | Avg Loss: {overall['avg_loss']:.2f}%")
    print(f"   Profit Factor: {overall['profit_factor']:.2f}")
    
    # By tier
    print(f"\n📈 PERFORMANCE BY TIER:")
    for tier in [1, 2, 3, 4]:
        stats = tracker.get_win_rate(tier=tier)
        if stats['total_trades'] > 0:
            print(f"   Tier {tier}: {stats['total_trades']} trades, {stats['win_rate']:.1f}% win")
    
    # Best signal types
    print(f"\n⭐ TOP PERFORMING SIGNALS:")
    rankings = tracker.rank_signal_types()
    for i, rank in enumerate(rankings[:3], 1):
        print(f"   {i}. {rank['signal_type']} T{rank['tier']}: {rank['win_rate']:.1f}% win ({rank['total_trades']} trades)")
    
    print("\n" + "="*70 + "\n")