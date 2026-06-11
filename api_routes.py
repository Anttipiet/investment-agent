"""
API Routes - Phase 1 + Phase 2 Signal & Analysis Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from models import SessionLocal, get_db, Signal
from signal_engine import SignalGenerator
from valuation_analyzer import ValuationAnalyzer
from earnings_tracker import EarningsTracker
from macro_analyzer import MacroAnalyzer
from datetime import datetime

router = APIRouter(prefix="/api", tags=["intelligence"])

@router.get("/signals/generate/{symbol}")
def generate_signals(symbol: str, sector: str = "AI", db = Depends(get_db)):
    """Generate buy/sell signals with Phase 1 + Phase 2 analysis"""
    try:
        generator = SignalGenerator(db)
        signals = generator.generate_all_signals(symbol, sector)
        
        return {
            'symbol': symbol,
            'signals_count': len(signals),
            'signals': signals[:3] if signals else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/valuation/{symbol}")
def get_valuation(symbol: str, sector: str = "AI", db = Depends(get_db)):
    """Get valuation analysis"""
    try:
        analyzer = ValuationAnalyzer(db)
        summary = analyzer.get_valuation_summary(symbol, sector)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/earnings/{symbol}")
def get_earnings(symbol: str, db = Depends(get_db)):
    """Get earnings analysis"""
    try:
        tracker = EarningsTracker(db)
        summary = tracker.get_earnings_summary(symbol)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/macro/summary")
def get_macro():
    """Get macro environment"""
    try:
        analyzer = MacroAnalyzer()
        summary = analyzer.get_macro_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intelligence/{symbol}")
def get_intelligence(symbol: str, sector: str = "AI", db = Depends(get_db)):
    """Complete intelligence endpoint"""
    try:
        generator = SignalGenerator(db)
        analyzer = ValuationAnalyzer(db)
        tracker = EarningsTracker(db)
        
        signals = generator.generate_all_signals(symbol, sector)
        valuation = analyzer.get_valuation_summary(symbol, sector)
        earnings = tracker.get_earnings_summary(symbol)
        
        signal_conf = max([s['confidence'] for s in signals], default=0)
        overall = (signal_conf * 0.4 + valuation['overall_valuation_score'] * 0.3 + earnings['earnings_score'] * 0.3)
        
        return {
            'symbol': symbol,
            'signal_confidence': signal_conf,
            'valuation_score': valuation['overall_valuation_score'],
            'earnings_score': earnings['earnings_score'],
            'overall_score': round(overall, 1),
            'recommendation': 'BUY' if overall > 65 else 'HOLD' if overall > 40 else 'AVOID'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
def health():
    return {'status': 'healthy', 'version': '2.0', 'phase': 'Phase 1 + Phase 2'}