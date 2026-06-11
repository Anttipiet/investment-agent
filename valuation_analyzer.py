"""
Valuation Analysis - P/E, P/S, Debt, Growth Metrics
"""

from models import SessionLocal, PriceSnapshot, AlphaPick
from decimal import Decimal
import statistics

class ValuationAnalyzer:
    """Analyze stock valuations for value/growth opportunities"""
    
    def __init__(self, db):
        self.db = db
    
    def get_pe_ratio(self, symbol: str) -> float:
        """Get P/E ratio from latest snapshot"""
        snapshot = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).first()
        
        return float(snapshot.pe_ratio) if snapshot and snapshot.pe_ratio else None
    
    def get_industry_average_pe(self, sector: str) -> float:
        """Get average P/E for a sector"""
        # Hardcoded sector averages (Phase 2 enhancement: fetch real data)
        sector_pe = {
            'DEFENSE': 18.5,
            'AEROSPACE': 16.2,
            'ENERGY': 12.8,
            'NUCLEAR': 14.5,
            'AI': 35.0,
        }
        return sector_pe.get(sector, 20.0)
    
    def pe_valuation_score(self, symbol: str, sector: str) -> dict:
        """Score stock valuation vs industry"""
        pe = self.get_pe_ratio(symbol)
        industry_pe = self.get_industry_average_pe(sector)
        
        if not pe:
            return {'score': 0, 'status': 'INSUFFICIENT_DATA', 'discount_pct': None}
        
        discount_pct = ((industry_pe - pe) / industry_pe) * 100
        
        if discount_pct > 20:
            status = "DEEPLY_UNDERVALUED"
        elif discount_pct > 10:
            status = "UNDERVALUED"
        elif discount_pct > -10:
            status = "FAIRLY_VALUED"
        elif discount_pct > -20:
            status = "OVERVALUED"
        else:
            status = "DEEPLY_OVERVALUED"
        
        return {
            'pe': pe,
            'industry_avg_pe': industry_pe,
            'discount_pct': round(discount_pct, 2),
            'status': status,
            'score': max(0, min(100, 50 + discount_pct * 2))
        }
    
    def get_ps_ratio(self, symbol: str) -> float:
        """Get Price-to-Sales ratio"""
        snapshot = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).first()
        
        return float(snapshot.price_to_sales) if snapshot and snapshot.price_to_sales else None
    
    def get_debt_to_equity(self, symbol: str) -> float:
        """Get Debt-to-Equity ratio"""
        snapshot = self.db.query(PriceSnapshot).filter(
            PriceSnapshot.symbol == symbol
        ).order_by(PriceSnapshot.timestamp.desc()).first()
        
        return float(snapshot.debt_to_equity) if snapshot and snapshot.debt_to_equity else None
    
    def debt_health_score(self, symbol: str) -> dict:
        """Assess debt level health"""
        de = self.get_debt_to_equity(symbol)
        
        if not de:
            return {'score': 0, 'status': 'INSUFFICIENT_DATA'}
        
        if de < 0.5:
            status = "VERY_HEALTHY"
            score = 90
        elif de < 1.0:
            status = "HEALTHY"
            score = 75
        elif de < 1.5:
            status = "MODERATE"
            score = 50
        elif de < 2.0:
            status = "HIGH"
            score = 25
        else:
            status = "VERY_HIGH"
            score = 10
        
        return {
            'debt_to_equity': round(de, 2),
            'status': status,
            'score': score
        }
    
    def peg_ratio(self, symbol: str, earnings_growth_pct: float) -> dict:
        """PEG Ratio = P/E / Growth Rate (lower = better value)"""
        pe = self.get_pe_ratio(symbol)
        
        if not pe or earnings_growth_pct <= 0:
            return {'peg': None, 'status': 'INSUFFICIENT_DATA'}
        
        peg = pe / earnings_growth_pct
        
        if peg < 1.0:
            status = "UNDERVALUED_FOR_GROWTH"
        elif peg < 1.5:
            status = "FAIRLY_VALUED"
        else:
            status = "OVERVALUED_FOR_GROWTH"
        
        return {
            'peg': round(peg, 2),
            'pe': pe,
            'growth_rate': earnings_growth_pct,
            'status': status
        }
    
    def get_valuation_summary(self, symbol: str, sector: str, growth_rate: float = 15) -> dict:
        """Complete valuation scorecard"""
        pe_score = self.pe_valuation_score(symbol, sector)
        debt_score = self.debt_health_score(symbol)
        peg = self.peg_ratio(symbol, growth_rate)
        
        # Overall valuation score (0-100)
        scores = [pe_score['score'], debt_score['score']]
        overall = statistics.mean(scores) if scores else 50
        
        return {
            'symbol': symbol,
            'pe_analysis': pe_score,
            'debt_analysis': debt_score,
            'peg_analysis': peg,
            'overall_valuation_score': round(overall, 1),
            'investment_grade': 'BUY' if overall > 70 else 'HOLD' if overall > 40 else 'AVOID'
        }

def get_valuation_signal_boost(analyzer, symbol: str, sector: str) -> float:
    """Boost signal confidence if fundamentals are strong"""
    summary = analyzer.get_valuation_summary(symbol, sector)
    
    boost = 0
    if summary['investment_grade'] == 'BUY':
        boost = 10  # +10% confidence if undervalued
    elif summary['investment_grade'] == 'AVOID':
        boost = -10  # -10% confidence if overvalued
    
    return boost