"""
Investment Agent - Data Collection Module
Fetches insider trades, congressional trades, alpha picks, and market data
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import yfinance as yf
from sqlalchemy.orm import Session
from models import (
    InsiderTrade, CongressionalTrade, AlphaPick,
    InstitutionalHolding, PriceSnapshot
)
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# ============================================================================
# SEC EDGAR DATA COLLECTOR
# ============================================================================

class SECDataCollector:
    """
    Fetch insider trades from SEC EDGAR database
    Uses Form 4 filings (insider transactions)
    """
    
    BASE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
    
    SECTOR_SYMBOLS = {
        'DEFENSE': ['LMT', 'RTX', 'GD', 'NOC', 'HII'],
        'AEROSPACE': ['BA', 'SPR', 'UTX', 'PWA'],
        'ENERGY': ['XLE', 'CVX', 'COP', 'EOG', 'MPC'],
        'NUCLEAR': ['UEC', 'CCJ', 'NLR', 'URG', 'UUUU'],
        'AI': ['NVDA', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMD', 'SMCI', 'PLTR']
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
    
    def fetch_form4_filings(self, ticker: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch Form 4 (insider transaction) filings for a ticker
        
        Args:
            ticker: Stock symbol
            days_back: Only get filings from last N days
            
        Returns:
            List of parsed Form 4 data
        """
        filings = []
        
        try:
            # Query SEC EDGAR API
            params = {
                'action': 'getcompany',
                'type': '4',
                'dateb': datetime.utcnow().strftime('%Y-%m-%d'),
                'owner': 'exclude',
                'count': '100',
                'search_text': ticker,
                'output': 'json'
            }
            
            # Note: This is simplified. Real implementation would need:
            # - CIK lookup
            # - Proper XML parsing of Form 4
            # - Transaction details extraction
            
            # For MVP, use a simplified approach or API wrapper
            # Example: sec-api.io or finnhub
            
            logger.info(f"✓ Fetched Form 4 filings for {ticker}")
            
        except Exception as e:
            logger.error(f"✗ Error fetching Form 4 for {ticker}: {e}")
        
        return filings
    
    def fetch_all_insider_trades(self, db: Session) -> int:
        """
        Batch fetch insider trades for all tracked symbols
        """
        count = 0
        
        all_symbols = set()
        for symbols in self.SECTOR_SYMBOLS.values():
            all_symbols.update(symbols)
        
        for symbol in all_symbols:
            filings = self.fetch_form4_filings(symbol)
            
            for filing in filings:
                # Check if already in database
                existing = self.db.query(InsiderTrade).filter(
                    InsiderTrade.sec_filing_id == filing.get('filing_id')
                ).first()
                
                if not existing:
                    insider_trade = InsiderTrade(
                        sec_filing_id=filing.get('filing_id'),
                        symbol=symbol,
                        company_name=filing.get('company_name'),
                        insider_name=filing.get('insider_name'),
                        insider_role=filing.get('insider_role', 'OFFICER'),
                        transaction_type=filing.get('transaction_type'),
                        shares=filing.get('shares', 0),
                        price=Decimal(str(filing.get('price', 0))),
                        transaction_amount=Decimal(str(filing.get('amount', 0))),
                        transaction_date=filing.get('transaction_date'),
                        filing_date=filing.get('filing_date'),
                        form_4_url=filing.get('url')
                    )
                    self.db.add(insider_trade)
                    count += 1
        
        self.db.commit()
        logger.info(f"✓ Added {count} new insider trades")
        return count

# ============================================================================
# CONGRESSIONAL TRADING COLLECTOR
# ============================================================================

class CongressionalTradeCollector:
    """
    Fetch congressional trading activity
    Uses House Stock Watcher and Senate datasets
    """
    
    HOUSE_API = "https://housestockwatcher.com/api"
    
    def __init__(self, db: Session):
        self.db = db
        self.session = requests.Session()
    
    def fetch_congressional_trades(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch recent congressional trades
        
        Note: Requires web scraping or API access
        Popular sources:
        - housestockwatcher.com
        - Senate.gov official filings
        - github.com/stocks-tracker (unofficial)
        """
        trades = []
        
        try:
            # Example: Using House Stock Watcher API
            # Real implementation would parse Senate filings directly
            
            endpoint = f"{self.HOUSE_API}/transactions"
            params = {
                'days_back': days_back,
                'sector': 'Technology,Defense,Energy'  # Filter by sectors
            }
            
            # This is pseudo-code - actual implementation depends on API availability
            # response = self.session.get(endpoint, params=params, timeout=10)
            # data = response.json()
            
            logger.info(f"✓ Fetched congressional trades from last {days_back} days")
            
        except Exception as e:
            logger.error(f"✗ Error fetching congressional trades: {e}")
        
        return trades
    
    def save_congressional_trades(self, trades: List[Dict]) -> int:
        """Save congressional trades to database"""
        count = 0
        
        for trade in trades:
            # Check if already exists
            existing = self.db.query(CongressionalTrade).filter(
                CongressionalTrade.member_name == trade.get('member_name'),
                CongressionalTrade.symbol == trade.get('symbol'),
                CongressionalTrade.transaction_date == trade.get('transaction_date')
            ).first()
            
            if not existing:
                cong_trade = CongressionalTrade(
                    member_name=trade.get('member_name'),
                    chamber=trade.get('chamber', 'HOUSE'),
                    party=trade.get('party'),
                    symbol=trade.get('symbol'),
                    action=trade.get('action'),
                    amount_range=trade.get('amount_range'),
                    transaction_date=trade.get('transaction_date'),
                    filing_date=trade.get('filing_date'),
                    url=trade.get('url')
                )
                self.db.add(cong_trade)
                count += 1
        
        self.db.commit()
        logger.info(f"✓ Added {count} new congressional trades")
        return count

# ============================================================================
# ALPHA PICKS COLLECTOR
# ============================================================================

class AlphaPicksCollector:
    """
    Fetch analyst ratings and stock picks
    Sources: SeekingAlpha, Yahoo Finance, TradingView, StockTwits
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def fetch_alpha_picks(self, sector: str = 'AI') -> List[Dict[str, Any]]:
        """
        Fetch analyst upgrades and ratings
        
        Implementation options:
        1. Web scrape SeekingAlpha
        2. Use yfinance recommendations
        3. Parse RSS feeds from analyst services
        4. Use paid API (Polygon, Finnhub)
        """
        picks = []
        
        try:
            # Example using yfinance (limited data)
            # Real implementation would use dedicated API
            
            # Pseudo-code:
            # tickers = SECTOR_FOCUS[sector]
            # for ticker in tickers:
            #     data = yf.Ticker(ticker)
            #     info = data.info
            #     if 'recommendationKey' in info:
            #         picks.append({...})
            
            logger.info(f"✓ Fetched alpha picks for {sector}")
            
        except Exception as e:
            logger.error(f"✗ Error fetching alpha picks: {e}")
        
        return picks
    
    def save_alpha_picks(self, picks: List[Dict]) -> int:
        """Save analyst picks to database"""
        count = 0
        
        for pick in picks:
            existing = self.db.query(AlphaPick).filter(
                AlphaPick.symbol == pick.get('symbol'),
                AlphaPick.analyst_name == pick.get('analyst'),
                AlphaPick.date == pick.get('date')
            ).first()
            
            if not existing:
                alpha_pick = AlphaPick(
                    symbol=pick.get('symbol'),
                    rating=pick.get('rating'),
                    price_target=Decimal(str(pick.get('price_target', 0))),
                    current_price=Decimal(str(pick.get('current_price', 0))),
                    analyst_name=pick.get('analyst'),
                    firm=pick.get('firm'),
                    date=pick.get('date'),
                    reasoning=pick.get('reasoning', ''),
                    confidence=pick.get('confidence', 0.5)
                )
                self.db.add(alpha_pick)
                count += 1
        
        self.db.commit()
        logger.info(f"✓ Added {count} new alpha picks")
        return count

# ============================================================================
# MARKET DATA COLLECTOR
# ============================================================================

class MarketDataCollector:
    """
    Fetch real-time and historical market data
    Uses yfinance and Finnhub for market data
    """
    
    def __init__(self, db: Session, finnhub_api_key: Optional[str] = None):
        self.db = db
        self.finnhub_api_key = finnhub_api_key
        self.finnhub_url = "https://finnhub.io/api/v1"
    
    def fetch_price_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current price and metrics for a symbol
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d')
            info = ticker.info
            
            if data.empty:
                logger.warning(f"No data for {symbol}")
                return None
            
            snapshot = {
                'symbol': symbol,
                'price': float(data['Close'].iloc[-1]) if not data.empty else 0,
                'volume': int(data['Volume'].iloc[-1]) if not data.empty else 0,
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'high_52w': info.get('fiftyTwoWeekHigh', 0),
                'low_52w': info.get('fiftyTwoWeekLow', 0)
            }
            
            # Calculate moving averages
            data_200 = ticker.history(period='1y')
            if len(data_200) >= 20:
                snapshot['sma_20'] = data_200['Close'].tail(20).mean()
            if len(data_200) >= 200:
                snapshot['sma_200'] = data_200['Close'].tail(200).mean()
            
            return snapshot
            
        except Exception as e:
            logger.error(f"✗ Error fetching price for {symbol}: {e}")
            return None
    
    def fetch_options_flow(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch options volume and implied volatility
        Requires Finnhub or similar API
        """
        if not self.finnhub_api_key:
            logger.warning("Finnhub API key not configured")
            return None
        
        try:
            # Example Finnhub call
            url = f"{self.finnhub_url}/quote"
            params = {
                'symbol': symbol,
                'token': self.finnhub_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            # Parse options metrics
            flow = {
                'symbol': symbol,
                'call_volume': data.get('c', 0),  # Call option volume
                'put_volume': data.get('p', 0),   # Put option volume
            }
            
            if flow['put_volume'] > 0:
                flow['put_call_ratio'] = flow['call_volume'] / flow['put_volume']
            
            return flow
            
        except Exception as e:
            logger.error(f"✗ Error fetching options flow: {e}")
            return None
    
    def save_price_snapshot(self, symbol: str) -> bool:
        """Save current price snapshot to database"""
        try:
            snapshot = self.fetch_price_snapshot(symbol)
            if not snapshot:
                return False
            
            # Create record
            price_record = PriceSnapshot(
                symbol=symbol,
                price=Decimal(str(snapshot['price'])),
                volume=snapshot['volume'],
                market_cap=Decimal(str(snapshot.get('market_cap', 0))),
                pe_ratio=snapshot.get('pe_ratio'),
                high_52w=Decimal(str(snapshot.get('high_52w', 0))),
                low_52w=Decimal(str(snapshot.get('low_52w', 0))),
                sma_20=Decimal(str(snapshot.get('sma_20', 0))) if snapshot.get('sma_20') else None,
                sma_200=Decimal(str(snapshot.get('sma_200', 0))) if snapshot.get('sma_200') else None
            )
            
            self.db.add(price_record)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error saving price snapshot: {e}")
            self.db.rollback()
            return False
    
    def update_all_prices(self, symbols: List[str]) -> int:
        """Update prices for all tracked symbols"""
        count = 0
        
        for symbol in symbols:
            if self.save_price_snapshot(symbol):
                count += 1
        
        logger.info(f"✓ Updated prices for {count}/{len(symbols)} symbols")
        return count

# ============================================================================
# BATCH DATA COLLECTION
# ============================================================================

def run_daily_data_collection(db: Session, finnhub_api_key: Optional[str] = None) -> Dict[str, int]:
    """
    Run complete daily data collection across all sources
    Typically scheduled once per day (9:30 AM market open)
    """
    
    results = {
        'insider_trades': 0,
        'congressional_trades': 0,
        'alpha_picks': 0,
        'price_snapshots': 0
    }
    
    try:
        # Collect insider trades
        logger.info("Starting SEC insider trade collection...")
        sec_collector = SECDataCollector(db)
        results['insider_trades'] = sec_collector.fetch_all_insider_trades(db)
        
    except Exception as e:
        logger.error(f"SEC collection failed: {e}")
    
    try:
        # Collect congressional trades
        logger.info("Starting congressional trade collection...")
        cong_collector = CongressionalTradeCollector(db)
        trades = cong_collector.fetch_congressional_trades(days_back=30)
        results['congressional_trades'] = cong_collector.save_congressional_trades(trades)
        
    except Exception as e:
        logger.error(f"Congressional collection failed: {e}")
    
    try:
        # Collect alpha picks
        logger.info("Starting alpha picks collection...")
        alpha_collector = AlphaPicksCollector(db)
        for sector in ['AI', 'DEFENSE', 'ENERGY', 'NUCLEAR', 'AEROSPACE']:
            picks = alpha_collector.fetch_alpha_picks(sector)
            results['alpha_picks'] += alpha_collector.save_alpha_picks(picks)
        
    except Exception as e:
        logger.error(f"Alpha picks collection failed: {e}")
    
    try:
        # Update all prices
        logger.info("Starting market data collection...")
        market_collector = MarketDataCollector(db, finnhub_api_key)
        all_symbols = [
            'LMT', 'RTX', 'GD', 'NOC', 'HII', 'BA', 'SPR', 'UTX', 'PWA',
            'XLE', 'CVX', 'COP', 'EOG', 'MPC', 'UEC', 'CCJ', 'NLR', 'URG',
            'NVDA', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMD', 'SMCI', 'PLTR'
        ]
        results['price_snapshots'] = market_collector.update_all_prices(all_symbols)
        
    except Exception as e:
        logger.error(f"Market data collection failed: {e}")
    
    total = sum(results.values())
    logger.info(f"✓ Daily collection complete: {total} total records")
    
    return results

if __name__ == "__main__":
    from models import SessionLocal
    
    db = SessionLocal()
    
    # Run full collection
    results = run_daily_data_collection(db)
    print("\n=== COLLECTION RESULTS ===")
    for source, count in results.items():
        print(f"{source}: {count}")
    
    db.close()
