"""
Investment Agent - Database Models & ORM
SQLite with SQLAlchemy
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, ForeignKey, JSON, Enum, Text, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum
from dotenv import load_dotenv
import os

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite:///investment_agent.db'
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================

class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class SignalTier(int, enum.Enum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4

class TradeAction(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class TradeStatus(str, enum.Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

class AlertSensitivity(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM_HIGH = "MEDIUM_HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class InsiderRole(str, enum.Enum):
    CEO = "CEO"
    CFO = "CFO"
    CTO = "CTO"
    DIRECTOR = "DIRECTOR"
    OFFICER = "OFFICER"
    OTHER = "OTHER"

# ============================================================================
# USER & AUTHENTICATION
# ============================================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    api_key = Column(String, unique=True, index=True)
    
    alert_sensitivity = Column(String, default=AlertSensitivity.MEDIUM_HIGH)
    email_alerts_enabled = Column(Boolean, default=True)
    discord_webhook = Column(String, nullable=True)
    sms_number = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    watchlist = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    virtual_trades = relationship("VirtualTrade", back_populates="user", cascade="all, delete-orphan")
    portfolio = relationship("VirtualPortfolio", back_populates="user", uselist=False, cascade="all, delete-orphan")
    signal_dismissals = relationship("SignalDismissal", back_populates="user", cascade="all, delete-orphan")
    alert_settings = relationship("AlertPreference", back_populates="user", cascade="all, delete-orphan")

# ============================================================================
# WATCHLIST
# ============================================================================

class Watchlist(Base):
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    symbol = Column(String, index=True)
    sector = Column(String)
    added_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="watchlist")
    
    def __repr__(self):
        return f"<Watchlist {self.symbol} - {self.sector}>"

# ============================================================================
# SIGNALS
# ============================================================================

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal_type = Column(String, default=SignalType.BUY)
    tier = Column(Integer, default=1)
    confidence = Column(Float, default=0.5)
    
    data_source = Column(String)
    reason = Column(JSON)
    
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    dismissed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    alerted = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Signal {self.symbol} {self.signal_type} T{self.tier} {self.confidence}%>"

class SignalDismissal(Base):
    __tablename__ = "signal_dismissals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    dismissed_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, nullable=True)
    
    user = relationship("User", back_populates="signal_dismissals")

# ============================================================================
# INSIDER TRADING DATA
# ============================================================================

class InsiderTrade(Base):
    __tablename__ = "insider_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    sec_filing_id = Column(String, unique=True, index=True)
    symbol = Column(String, index=True)
    company_name = Column(String)
    
    insider_name = Column(String, index=True)
    insider_role = Column(String)
    
    transaction_type = Column(String)
    shares = Column(Integer)
    price = Column(Numeric(10, 2))
    transaction_amount = Column(Numeric(15, 2))
    transaction_date = Column(DateTime, index=True)
    filing_date = Column(DateTime)
    
    form_4_url = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<InsiderTrade {self.insider_name} {self.transaction_type} {self.shares}x {self.symbol}>"

# ============================================================================
# CONGRESSIONAL TRADING
# ============================================================================

class CongressionalTrade(Base):
    __tablename__ = "congressional_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    member_name = Column(String, index=True)
    chamber = Column(String)
    party = Column(String)
    
    symbol = Column(String, index=True)
    action = Column(String)
    amount_range = Column(String)
    transaction_date = Column(DateTime, index=True)
    filing_date = Column(DateTime)
    
    url = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CongressionalTrade {self.member_name} {self.action} {self.symbol}>"

# ============================================================================
# ALPHA PICKS
# ============================================================================

class AlphaPick(Base):
    __tablename__ = "alpha_picks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    rating = Column(String)
    price_target = Column(Numeric(10, 2), nullable=True)
    current_price = Column(Numeric(10, 2), nullable=True)
    analyst_name = Column(String)
    firm = Column(String, nullable=True)
    date = Column(DateTime, index=True)
    reasoning = Column(Text)
    
    confidence = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AlphaPick {self.symbol} {self.rating} - ${self.price_target}>"

# ============================================================================
# INSTITUTIONAL HOLDINGS
# ============================================================================

class InstitutionalHolding(Base):
    __tablename__ = "institutional_holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    institution_name = Column(String, index=True)
    cik = Column(String)
    
    symbol = Column(String, index=True)
    shares = Column(Integer)
    value = Column(Numeric(15, 2))
    
    portfolio_percentage = Column(Float)
    
    filing_date = Column(DateTime, index=True)
    quarter = Column(String)
    year = Column(Integer)
    
    previous_shares = Column(Integer, nullable=True)
    change_percentage = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<InstitutionalHolding {self.institution_name} {self.shares} {self.symbol}>"

# ============================================================================
# VIRTUAL TRADING
# ============================================================================

class VirtualPortfolio(Base):
    __tablename__ = "virtual_portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    initial_cash = Column(Numeric(15, 2), default=100000)
    cash_balance = Column(Numeric(15, 2), default=100000)
    total_value = Column(Numeric(15, 2), default=100000)
    
    total_return = Column(Float, default=0)
    realized_gains = Column(Numeric(15, 2), default=0)
    unrealized_gains = Column(Numeric(15, 2), default=0)
    
    positions = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="portfolio")
    
    def __repr__(self):
        return f"<VirtualPortfolio ${self.total_value} ({self.total_return}%)>"

class VirtualTrade(Base):
    __tablename__ = "virtual_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    symbol = Column(String, index=True)
    action = Column(String)
    shares = Column(Integer)
    
    entry_price = Column(Numeric(10, 2))
    entry_date = Column(DateTime)
    exit_price = Column(Numeric(10, 2), nullable=True)
    exit_date = Column(DateTime, nullable=True)
    
    status = Column(String, default=TradeStatus.FILLED)
    commission = Column(Numeric(10, 2), default=5)
    
    p_l = Column(Numeric(15, 2), nullable=True)
    p_l_percentage = Column(Float, nullable=True)
    
    triggered_by_signal_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="virtual_trades")
    
    def __repr__(self):
        status_str = f"CLOSED ({self.p_l_percentage}%)" if self.p_l_percentage else "OPEN"
        return f"<VirtualTrade {self.action} {self.shares}x {self.symbol} {status_str}>"

# ============================================================================
# ALERT PREFERENCES
# ============================================================================

class AlertPreference(Base):
    __tablename__ = "alert_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    symbol = Column(String, index=True)
    
    enabled = Column(Boolean, default=True)
    min_tier = Column(Integer, default=1)
    min_confidence = Column(Float, default=0.5)
    
    track_insiders = Column(Boolean, default=True)
    track_institutional = Column(Boolean, default=True)
    track_congressional = Column(Boolean, default=True)
    track_volume = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="alert_settings")
    
    def __repr__(self):
        return f"<AlertPreference {self.symbol} - Tier {self.min_tier}+>"

# ============================================================================
# NEWS ARTICLES
# ============================================================================

class NewsArticle(Base):
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    url = Column(String)
    source = Column(String)
    
    sentiment = Column(String)
    sentiment_score = Column(Float)
    
    category = Column(String)
    relevance_score = Column(Float)
    
    published_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<NewsArticle {self.symbol} - {self.sentiment} - {self.title[:30]}>"

# ============================================================================
# PRICE SNAPSHOTS & TECHNICAL ANALYSIS
# ============================================================================

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    
    price = Column(Numeric(10, 2))
    open_price = Column(Numeric(10, 2), nullable=True)
    high_price = Column(Numeric(10, 2), nullable=True)
    low_price = Column(Numeric(10, 2), nullable=True)
    volume = Column(Integer)
    
    market_cap = Column(Numeric(15, 2), nullable=True)
    pe_ratio = Column(Float, nullable=True)
    price_to_sales = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    
    high_52w = Column(Numeric(10, 2), nullable=True)
    low_52w = Column(Numeric(10, 2), nullable=True)
    
    sma_20 = Column(Numeric(10, 2), nullable=True)
    sma_50 = Column(Numeric(10, 2), nullable=True)
    sma_200 = Column(Numeric(10, 2), nullable=True)
    
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    
    trend = Column(String, nullable=True)
    support_level = Column(Numeric(10, 2), nullable=True)
    resistance_level = Column(Numeric(10, 2), nullable=True)
    
    avg_volume_20d = Column(Integer, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    
    call_volume = Column(Integer, nullable=True)
    put_volume = Column(Integer, nullable=True)
    put_call_ratio = Column(Float, nullable=True)
    
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PriceSnapshot {self.symbol} ${self.price} Trend:{self.trend}>"

# ============================================================================
# SIGNAL PERFORMANCE TRACKING
# ============================================================================

class SignalPerformance(Base):
    __tablename__ = "signal_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    symbol = Column(String, index=True)
    signal_type = Column(String)
    signal_tier = Column(Integer)
    
    entry_date = Column(DateTime)
    entry_price = Column(Numeric(10, 2))
    entry_confidence = Column(Float)
    
    exit_date = Column(DateTime, nullable=True)
    exit_price = Column(Numeric(10, 2), nullable=True)
    
    days_held = Column(Integer, nullable=True)
    return_pct = Column(Float, nullable=True)
    profitable = Column(Boolean, nullable=True)
    
    technical_trend = Column(String, nullable=True)
    rsi_at_entry = Column(Float, nullable=True)
    price_vs_sma200 = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        status = "✓ WIN" if self.profitable else "✗ LOSS" if self.profitable == False else "OPEN"
        return f"<SignalPerf {self.symbol} {self.signal_type} {status}>"

# ============================================================================
# PORTFOLIO RISK METRICS
# ============================================================================

class PortfolioRisk(Base):
    __tablename__ = "portfolio_risk"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    max_position_size_pct = Column(Float, default=10)
    max_sector_exposure_pct = Column(Float, default=30)
    max_portfolio_loss_pct = Column(Float, default=20)
    
    largest_position_pct = Column(Float, default=0)
    portfolio_heat_pct = Column(Float, default=0)
    current_drawdown_pct = Column(Float, default=0)
    
    sector_exposure = Column(JSON, default=dict)
    
    portfolio_risk_score = Column(Float, default=50)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PortfolioRisk MaxPos:{self.max_position_size_pct}% Heat:{self.portfolio_heat_pct}%>"
# ============================================================================
# PAPER TRADES (Alpaca paper account — real fills, signal-linked)
# ============================================================================

class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal_type = Column(String)            # BUY / SELL
    tier = Column(Integer, nullable=True)
    entry_confidence = Column(Float)        # 0–100, matches your Signal table

    alpaca_order_id = Column(String, index=True)        # entry order
    exit_alpaca_order_id = Column(String, nullable=True)  # close order
    notional = Column(Numeric(15, 2), nullable=True)    # dollars committed

    entry_price = Column(Numeric(10, 2), nullable=True)  # null until filled
    entry_date = Column(DateTime, default=datetime.utcnow)
    exit_price = Column(Numeric(10, 2), nullable=True)
    exit_date = Column(DateTime, nullable=True)

    status = Column(String, default="OPEN")  # OPEN / CLOSED
    return_pct = Column(Float, nullable=True)
    profitable = Column(Boolean, nullable=True)

    triggered_by_signal_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PaperTrade {self.symbol} {self.signal_type} {self.status}>"
    
# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")

def get_db():
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    