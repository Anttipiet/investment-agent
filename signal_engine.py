"""
Investment Agent - Signal Generation Engine
Buy/Sell detection with tier-based confidence scoring
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from models import (
    Signal, InsiderTrade, CongressionalTrade, AlphaPick,
    InstitutionalHolding, PriceSnapshot, SignalType, SignalTier
)
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS & THRESHOLDS
# ============================================================================

BUY_SIGNAL_THRESHOLDS = {
    'INSIDER_LARGE_BUY': 500_000,      # $500K minimum
    'INSIDER_GROUP_BUY': 3,             # 3+ insiders buying
    'INSIDER_CEO_CFO_BUY': 100_000,    # CEO/CFO $100K minimum
    'VOLUME_SPIKE': 2.0,                # 200% of 20-day average
    'OPTIONS_BULLISH': 0.5,             # Call/put ratio > 0.5
    'INSTITUTIONAL_NEW': 0.05,          # 5% new position threshold
}

SELL_SIGNAL_THRESHOLDS = {
    'INSIDER_LARGE_SELL': 500_000,      # $500K minimum
    'INSIDER_COORDINATED_SELL': 2,      # 2+ insiders selling
    'INSTITUTIONAL_REDUCTION': 0.20,    # 20% position reduction
    'VOLUME_SPIKE_DOWN': 3.0,           # 300% volume on down day
    'OPTIONS_BEARISH': 1.5,             # Put/call ratio > 1.5
}

SECTOR_FOCUS = {
    'DEFENSE': ['LMT', 'RTX', 'GD', 'NOC', 'HII', 'TDG', 'ITA'],
    'AEROSPACE': ['BA', 'SPR', 'UTX', 'PWA', 'RGC', 'AVAV'],
    'ENERGY': ['XLE', 'CVX', 'COP', 'EOG', 'MPC', 'PSX', 'VLO'],
    'NUCLEAR': ['UEC', 'CCJ', 'NLR', 'URG', 'UUUU', 'NNPTF'],
    'AI': ['NVDA', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMD', 'SMCI', 'PLTR', 'UPST']
}

# ============================================================================
# SIGNAL GENERATOR
# ============================================================================

class SignalGenerator:
    """
    Core engine for generating buy/sell signals
    Analyzes insider activity, institutional moves, congressional trades, and market data
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.signals_generated = []
    
    # ========================================================================
    # BUY SIGNALS
    # ========================================================================
    
    def detect_insider_accumulation_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        TIER 1: Large insider buys + CEO/CFO involvement
        TIER 2: Multiple insider buys
        """
        signals = []
        
        # Last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # Get all insider buys for this symbol
        insider_buys = self.db.query(InsiderTrade).filter(
            InsiderTrade.symbol == symbol,
            InsiderTrade.transaction_type == 'BUY',
            InsiderTrade.transaction_date >= seven_days_ago
        ).all()
        
        if not insider_buys:
            return signals
        
        # -------- TIER 1: CEO/CFO large buy --------
        for trade in insider_buys:
            if trade.insider_role in ['CEO', 'CFO'] and \
               trade.transaction_amount >= BUY_SIGNAL_THRESHOLDS['INSIDER_CEO_CFO_BUY']:
                
                signals.append({
                    'signal_type': SignalType.BUY,
                    'tier': 1,
                    'confidence': 75,
                    'data_source': 'INSIDER_ACTIVITY',
                    'reason': {
                        'category': 'CEO/CFO Accumulation',
                        'insider_name': trade.insider_name,
                        'insider_role': trade.insider_role,
                        'shares': int(trade.shares),
                        'amount': float(trade.transaction_amount),
                        'date': trade.transaction_date.isoformat(),
                        'reasoning': f"{trade.insider_role} buying their own stock is strong bullish signal"
                    }
                })
        
        # -------- TIER 1: Single large buy >$500K --------
        for trade in insider_buys:
            if trade.transaction_amount >= BUY_SIGNAL_THRESHOLDS['INSIDER_LARGE_BUY']:
                signals.append({
                    'signal_type': SignalType.BUY,
                    'tier': 1,
                    'confidence': 65,
                    'data_source': 'INSIDER_ACTIVITY',
                    'reason': {
                        'category': 'Large Insider Buy',
                        'insider_name': trade.insider_name,
                        'insider_role': trade.insider_role,
                        'shares': int(trade.shares),
                        'amount': float(trade.transaction_amount),
                        'date': trade.transaction_date.isoformat(),
                    }
                })
        
        # -------- TIER 2: Multiple insiders buying --------
        insider_count = len(set(t.insider_name for t in insider_buys))
        if insider_count >= BUY_SIGNAL_THRESHOLDS['INSIDER_GROUP_BUY']:
            signals.append({
                'signal_type': SignalType.BUY,
                'tier': 2,
                'confidence': 70,
                'data_source': 'INSIDER_ACTIVITY',
                'reason': {
                    'category': 'Coordinated Insider Buying',
                    'insider_count': insider_count,
                    'total_amount': float(sum(t.transaction_amount for t in insider_buys)),
                    'insiders': [t.insider_name for t in insider_buys],
                    'date_range': f"{min(t.transaction_date for t in insider_buys).date()} to {max(t.transaction_date for t in insider_buys).date()}",
                }
            })
        
        return signals
    
    def detect_congressional_buy_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        TIER 3: Congressional members buying stock (especially defense/energy/AI)
        Multiple members = higher confidence
        """
        signals = []
        
        # Last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        congressional_buys = self.db.query(CongressionalTrade).filter(
            CongressionalTrade.symbol == symbol,
            CongressionalTrade.action == 'BUY',
            CongressionalTrade.transaction_date >= thirty_days_ago
        ).all()
        
        if not congressional_buys:
            return signals
        
        # Single congressional buy
        if len(congressional_buys) >= 1:
            signals.append({
                'signal_type': SignalType.BUY,
                'tier': 3,
                'confidence': 55,
                'data_source': 'CONGRESSIONAL_ACTIVITY',
                'reason': {
                    'category': 'Congressional Member Buying',
                    'member_count': len(congressional_buys),
                    'members': [cb.member_name for cb in congressional_buys],
                    'date': congressional_buys[0].transaction_date.isoformat(),
                    'notes': 'Congress members with advance knowledge often buy ahead of industry boom'
                }
            })
        
        # Multiple members = higher confidence
        if len(congressional_buys) >= 2:
            signals[-1]['confidence'] = 70
            signals[-1]['tier'] = 2
        
        return signals
    
    def detect_institutional_move_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        TIER 2: New institutional position or large increases
        Look for BlackRock, Vanguard, Fidelity buying
        """
        signals = []
        
        # Get latest quarter holdings
        latest_holdings = self.db.query(InstitutionalHolding).filter(
            InstitutionalHolding.symbol == symbol
        ).order_by(InstitutionalHolding.filing_date.desc()).limit(20).all()
        
        if not latest_holdings:
            return signals
        
        # Group by institution and check latest quarter vs previous
        institutions = {}
        for holding in latest_holdings:
            if holding.institution_name not in institutions:
                institutions[holding.institution_name] = []
            institutions[holding.institution_name].append(holding)
        
        for inst_name, holdings in institutions.items():
            if len(holdings) >= 2:
                # Compare latest to previous quarter
                latest = holdings[0]
                previous = holdings[1]
                
                if latest.previous_shares and previous.shares:
                    change_pct = (latest.shares - previous.shares) / previous.shares
                    
                    # Major fund increasing position by 5%+
                    if change_pct >= BUY_SIGNAL_THRESHOLDS['INSTITUTIONAL_NEW'] and \
                       inst_name in ['Blackrock', 'Vanguard', 'Fidelity', 'State Street']:
                        
                        signals.append({
                            'signal_type': SignalType.BUY,
                            'tier': 2,
                            'confidence': 65,
                            'data_source': 'INSTITUTIONAL_ACTIVITY',
                            'reason': {
                                'category': 'Major Fund Accumulation',
                                'institution': inst_name,
                                'previous_shares': previous.shares,
                                'current_shares': latest.shares,
                                'change_percentage': float(change_pct) * 100,
                                'quarter': latest.quarter,
                                'value': float(latest.value),
                            }
                        })
            
            # New position (institution didn't hold before)
            elif len(holdings) == 1:
                latest = holdings[0]
                if latest.value >= 100_000_000 and latest.institution_name in ['Blackrock', 'Vanguard']:
                    signals.append({
                        'signal_type': SignalType.BUY,
                        'tier': 2,
                        'confidence': 60,
                        'data_source': 'INSTITUTIONAL_ACTIVITY',
                        'reason': {
                            'category': 'New Major Fund Position',
                            'institution': latest.institution_name,
                            'shares': latest.shares,
                            'value': float(latest.value),
                            'portfolio_percentage': float(latest.portfolio_percentage),
                        }
                    })
        
        return signals
    
    def detect_alpha_pick_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        TIER 3: Analyst upgrades to BUY, especially from known firms
        """
        signals = []
        
        # Last 14 days
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        
        alpha_picks = self.db.query(AlphaPick).filter(
            AlphaPick.symbol == symbol,
            AlphaPick.rating.in_(['BUY', 'OUTPERFORM', 'STRONG BUY']),
            AlphaPick.date >= two_weeks_ago
        ).all()
        
        if not alpha_picks:
            return signals
        
        # Recent analyst upgrade
        signals.append({
            'signal_type': SignalType.BUY,
            'tier': 3,
            'confidence': 60,
            'data_source': 'ALPHA_PICK',
            'reason': {
                'category': 'Analyst Upgrade',
                'analyst': alpha_picks[0].analyst_name,
                'firm': alpha_picks[0].firm,
                'rating': alpha_picks[0].rating,
                'price_target': float(alpha_picks[0].price_target) if alpha_picks[0].price_target else None,
                'current_price': float(alpha_picks[0].current_price) if alpha_picks[0].current_price else None,
                'date': alpha_picks[0].date.isoformat(),
                'reasoning': alpha_picks[0].reasoning[:200]
            }
        })
        
        return signals
    
    # ========================================================================
    # SELL SIGNALS
    # ========================================================================
    
    def detect_insider_selling_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        TIER 1: CEO/CFO large sell (>$500K)
        TIER 2: Multiple insiders selling in coordination
        """
        signals = []
        
        # Last 14 days
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        
        insider_sells = self.db.query(InsiderTrade).filter(
            InsiderTrade.symbol == symbol,
            InsiderTrade.transaction_type == 'SELL',
            InsiderTrade.transaction_date >= two_weeks_ago
        ).all()
        
        if not insider_sells:
            return signals
        
        # -------- TIER 1: CEO/CFO large sell --------
        for trade in insider_sells:
            if trade.insider_role in ['CEO', 'CFO'] and \
               trade.transaction_amount >= SELL_SIGNAL_THRESHOLDS['INSIDER_LARGE_SELL']:
                
                signals.append({
                    'signal_type': SignalType.SELL,
                    'tier': 1,
                    'confidence': 70,
                    'data_source': 'INSIDER_ACTIVITY',
                    'reason': {
                        'category': 'Executive Selling',
                        'insider_name': trade.insider_name,
                        'insider_role': trade.insider_role,
                        'shares': int(trade.shares),
                        'amount': float(trade.transaction_amount),
                        'date': trade.transaction_date.isoformat(),
                        'warning': f'{trade.insider_role} dumping shares - potential loss of confidence'
                    }
                })
        
        # -------- TIER 2: Multiple insiders selling --------
        insider_count = len(set(t.insider_name for t in insider_sells))
        if insider_count >= SELL_SIGNAL_THRESHOLDS['INSIDER_COORDINATED_SELL']:
            signals.append({
                'signal_type': SignalType.SELL,
                'tier': 2,
                'confidence': 75,
                'data_source': 'INSIDER_ACTIVITY',
                'reason': {
                    'category': 'Coordinated Insider Selling',
                    'insider_count': insider_count,
                    'total_amount': float(sum(t.transaction_amount for t in insider_sells)),
                    'insiders': [t.insider_name for t in insider_sells],
                    'date_range': f"{min(t.transaction_date for t in insider_sells).date()} to {max(t.transaction_date for t in insider_sells).date()}",
                }
            })
        
        return signals
    
    def detect_congressional_selling_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        TIER 3: Congressional members selling (potential regulatory issues)
        """
        signals = []
        
        # Last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        congressional_sells = self.db.query(CongressionalTrade).filter(
            CongressionalTrade.symbol == symbol,
            CongressionalTrade.action == 'SELL',
            CongressionalTrade.transaction_date >= thirty_days_ago
        ).all()
        
        if len(congressional_sells) >= 2:
            signals.append({
                'signal_type': SignalType.SELL,
                'tier': 3,
                'confidence': 60,
                'data_source': 'CONGRESSIONAL_ACTIVITY',
                'reason': {
                    'category': 'Congressional Member Liquidation',
                    'member_count': len(congressional_sells),
                    'members': [cs.member_name for cs in congressional_sells],
                    'notes': 'Multiple members exiting position - potential regulatory headwind'
                }
            })
        
        return signals
    
    def detect_institutional_reduction_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        TIER 2: Major fund reducing position by 20%+
        """
        signals = []
        
        latest_holdings = self.db.query(InstitutionalHolding).filter(
            InstitutionalHolding.symbol == symbol
        ).order_by(InstitutionalHolding.filing_date.desc()).limit(20).all()
        
        if len(latest_holdings) < 2:
            return signals
        
        institutions = {}
        for holding in latest_holdings:
            if holding.institution_name not in institutions:
                institutions[holding.institution_name] = []
            institutions[holding.institution_name].append(holding)
        
        for inst_name, holdings in institutions.items():
            if len(holdings) >= 2:
                latest = holdings[0]
                previous = holdings[1]
                
                if latest.previous_shares and previous.shares and latest.previous_shares > 0:
                    change_pct = (latest.shares - previous.shares) / previous.shares
                    
                    # Reduction of 20%+
                    if change_pct <= -SELL_SIGNAL_THRESHOLDS['INSTITUTIONAL_REDUCTION']:
                        signals.append({
                            'signal_type': SignalType.SELL,
                            'tier': 2,
                            'confidence': 65,
                            'data_source': 'INSTITUTIONAL_ACTIVITY',
                            'reason': {
                                'category': 'Major Fund Dumping',
                                'institution': inst_name,
                                'previous_shares': previous.shares,
                                'current_shares': latest.shares,
                                'change_percentage': float(change_pct) * 100,
                                'quarter': latest.quarter,
                                'warning': f'{inst_name} reducing position significantly'
                            }
                        })
        
        return signals
    
    # ========================================================================
    # MAIN SIGNAL GENERATION
    # ========================================================================
    
    def generate_signals_for_symbol(self, symbol: str) -> List[Signal]:
        """
        Generate all signals for a given stock
        Combines buy and sell signals from all sources
        """
        all_signals = []
        
        # Buy signals
        all_signals.extend(self.detect_insider_accumulation_signals(symbol))
        all_signals.extend(self.detect_congressional_buy_signals(symbol))
        all_signals.extend(self.detect_institutional_move_signals(symbol))
        all_signals.extend(self.detect_alpha_pick_signals(symbol))
        
        # Sell signals
        all_signals.extend(self.detect_insider_selling_signals(symbol))
        all_signals.extend(self.detect_congressional_selling_signals(symbol))
        all_signals.extend(self.detect_institutional_reduction_signals(symbol))
        
        # Avoid duplicate signals
        all_signals = self._deduplicate_signals(all_signals)
        
        # Create database records
        signal_objects = []
        for sig in all_signals:
            signal_obj = Signal(
                symbol=symbol,
                signal_type=sig['signal_type'],
                tier=sig['tier'],
                confidence=sig['confidence'],
                data_source=sig['data_source'],
                reason=sig['reason'],
                detected_at=datetime.utcnow()
            )
            signal_objects.append(signal_obj)
        
        return signal_objects
    
    def generate_signals_for_sector(self, sector: str) -> List[Signal]:
        """
        Generate signals for all stocks in a sector
        """
        symbols = SECTOR_FOCUS.get(sector, [])
        all_signals = []
        
        for symbol in symbols:
            all_signals.extend(self.generate_signals_for_symbol(symbol))
        
        return all_signals
    
    def generate_all_signals(self) -> List[Signal]:
        """
        Generate signals for all tracked sectors
        """
        all_signals = []
        
        for sector in SECTOR_FOCUS.keys():
            all_signals.extend(self.generate_signals_for_sector(sector))
        
        return all_signals
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _deduplicate_signals(self, signals: List[Dict]) -> List[Dict]:
        """
        Remove duplicate signals (same symbol, type, tier, reason)
        Keep highest confidence signal
        """
        dedup = {}
        
        for sig in signals:
            key = (sig['symbol'] if 'symbol' in sig else '', 
                   sig['signal_type'], 
                   sig['tier'],
                   sig['data_source'])
            
            if key not in dedup:
                dedup[key] = sig
            elif sig['confidence'] > dedup[key]['confidence']:
                dedup[key] = sig
        
        return list(dedup.values())
    
    def save_signals(self, signals: List[Signal]):
        """Save signals to database"""
        try:
            self.db.add_all(signals)
            self.db.commit()
            logger.info(f"✓ Saved {len(signals)} signals to database")
            return len(signals)
        except Exception as e:
            logger.error(f"✗ Error saving signals: {e}")
            self.db.rollback()
            return 0

# ============================================================================
# BATCH SIGNAL GENERATION
# ============================================================================

def run_signal_generation_batch(db: Session) -> Dict[str, int]:
    """
    Run full signal generation across all sectors
    Typically called once per day
    """
    generator = SignalGenerator(db)
    
    results = {}
    
    for sector in SECTOR_FOCUS.keys():
        logger.info(f"Generating signals for {sector}...")
        signals = generator.generate_signals_for_sector(sector)
        count = generator.save_signals(signals)
        results[sector] = count
    
    total = sum(results.values())
    logger.info(f"✓ Total signals generated: {total}")
    
    return results

if __name__ == "__main__":
    from models import SessionLocal
    
    db = SessionLocal()
    generator = SignalGenerator(db)
    
    # Test for a single symbol
    signals = generator.generate_signals_for_symbol('NVDA')
    for sig in signals:
        print(f"{sig.signal_type} ({sig.tier}, {sig.confidence}%) - {sig.data_source}")
        print(f"  → {sig.reason}")
    
    db.close()
