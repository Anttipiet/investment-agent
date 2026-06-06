"""
Investment Agent - Database Models & ORM
PostgreSQL with SQLAlchemy
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
    'postgresql://user:password@localhost:5432/investment_agent'
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
    HIGH = "HIGH"      # Tier 1 only
    MEDIUM_HIGH = "MEDIUM_HIGH"  # Tiers 1-2
    MEDIUM = "MEDIUM"  # Tiers 1-3
    LOW = "LOW"        # All tiers

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
    
    # User preferences
    alert_sensitivity = Column(String, default=AlertSensitivity.MEDIUM_HIGH)
    email_alerts_enabled = Column(Boolean, default=True)
    discord_webhook = Column(String, nullable=True)
    sms_number = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
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
    sector = Column(String)  # DEFENSE, AEROSPACE, ENERGY, NUCLEAR, AI
    added_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="watchlist")
    
    def __repr__(self):
        return f"<Watchlist {self.symbol} - {self.sector}>"

# ============================================================================
# SIGNALS (Core Intelligence)
# ============================================================================

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal_type = Column(String, default=SignalType.BUY)  # BUY or SELL
    tier = Column(Integer, default=1)  # 1-4
    confidence = Column(Float, default=0.5)  # 0-100%
    
    # Signal metadata
    data_source = Column(String)  # INSIDER, INSTITUTIONAL, CONGRESSIONAL, VOLUME, OPTIONS
    reason = Column(JSON)  # {insider_name, transaction_amount, company, etc}
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Dismissals & tracking
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
    reason = Column(String, nullable=True)  # FALSE_POSITIVE, NOT_INTERESTED, etc
    
    # Relationships
    user = relationship("User", back_populates="signal_dismissals")

# ============================================================================
# INSIDER TRADING DATA
# ============================================================================

class InsiderTrade(Base):
    __tablename__ = "insider_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    sec_filing_id = Column(String, unique=True, index=True)  # Form 4 ID
    symbol = Column(String, index=True)
    company_name = Column(String)
    
    # Insider info
    insider_name = Column(String, index=True)
    insider_role = Column(String)  # CEO, CFO, Director, etc
    
    # Transaction details
    transaction_type = Column(String)  # BUY, SELL, EXERCISE, etc
    shares = Column(Integer)
    price = Column(Numeric(10, 2))
    transaction_amount = Column(Numeric(15, 2))  # shares * price
    transaction_date = Column(DateTime, index=True)
    filing_date = Column(DateTime)
    
    # Filing references
    form_4_url = Column(String)
    
    # Timestamps
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
    chamber = Column(String)  # HOUSE, SENATE
    party = Column(String)  # D, R, I
    
    # Trade info
    symbol = Column(String, index=True)
    action = Column(String)  # BUY, SELL
    amount_range = Column(String)  # $15K-$50K, $50K-$100K, etc
    transaction_date = Column(DateTime, index=True)
    filing_date = Column(DateTime)
    
    # Source
    url = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CongressionalTrade {self.member_name} {self.action} {self.symbol}>"

# ============================================================================
# ALPHA PICKS (Analyst Ratings)
# ============================================================================

class AlphaPick(Base):
    __tablename__ = "alpha_picks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    rating = Column(String)  # BUY, HOLD, SELL, OUTPERFORM, etc
    price_target = Column(Numeric(10, 2), nullable=True)
    current_price = Column(Numeric(10, 2), nullable=True)
    analyst_name = Column(String)
    firm = Column(String, nullable=True)
    date = Column(DateTime, index=True)
    reasoning = Column(Text)
    
    # Tracking
    confidence = Column(Float, default=0.5)  # Confidence score
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AlphaPick {self.symbol} {self.rating} - ${self.price_target}>"

# ============================================================================
# INSTITUTIONAL HOLDINGS (13F Filings)
# ============================================================================

class InstitutionalHolding(Base):
    __tablename__ = "institutional_holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    institution_name = Column(String, index=True)  # BlackRock, Vanguard, Fidelity, etc
    cik = Column(String)  # SEC CIK number
    
    symbol = Column(String, index=True)
    shares = Column(Integer)
    value = Column(Numeric(15, 2))  # Market value
    
    # Holdings percentage
    portfolio_percentage = Column(Float)  # % of fund's portfolio
    
    # Filing info
    filing_date = Column(DateTime, index=True)
    quarter = Column(String)  # Q1, Q2, Q3, Q4
    year = Column(Integer)
    
    # Change tracking (vs previous quarter)
    previous_shares = Column(Integer, nullable=True)
    change_percentage = Column(Float, nullable=True)  # % increase/decrease
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<InstitutionalHolding {self.institution_name} {self.shares} {self.symbol}>"

# ============================================================================
# VIRTUAL TRADING (Paper Trading/Sandbox)
# ============================================================================

class VirtualPortfolio(Base):
    __tablename__ = "virtual_portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Capital
    initial_cash = Column(Numeric(15, 2), default=100000)
    cash_balance = Column(Numeric(15, 2), default=100000)
    total_value = Column(Numeric(15, 2), default=100000)
    
    # Performance
    total_return = Column(Float, default=0)  # %
    realized_gains = Column(Numeric(15, 2), default=0)
    unrealized_gains = Column(Numeric(15, 2), default=0)
    
    # Holdings (JSON array of {symbol, shares, avg_cost, current_price})
    positions = Column(JSON, default=dict)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="portfolio")
    
    def __repr__(self):
        return f"<VirtualPortfolio ${self.total_value} ({self.total_return}%)>"

class VirtualTrade(Base):
    __tablename__ = "virtual_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    # Trade details
    symbol = Column(String, index=True)
    action = Column(String)  # BUY or SELL
    shares = Column(Integer)
    
    # Pricing
    entry_price = Column(Numeric(10, 2))
    entry_date = Column(DateTime)
    exit_price = Column(Numeric(10, 2), nullable=True)
    exit_date = Column(DateTime, nullable=True)
    
    # Execution
    status = Column(String, default=TradeStatus.FILLED)  # PENDING, FILLED, CANCELLED
    commission = Column(Numeric(10, 2), default=5)  # Fixed $5 per trade
    
    # Performance
    p_l = Column(Numeric(15, 2), nullable=True)  # Profit/Loss
    p_l_percentage = Column(Float, nullable=True)  # % return
    
    # Signal tracking (which signal triggered this trade)
    triggered_by_signal_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
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
    
    # Alert settings
    enabled = Column(Boolean, default=True)
    min_tier = Column(Integer, default=1)  # Minimum signal tier to alert on
    min_confidence = Column(Float, default=0.5)  # Minimum confidence threshold
    
    # Data sources to track
    track_insiders = Column(Boolean, default=True)
    track_institutional = Column(Boolean, default=True)
    track_congressional = Column(Boolean, default=True)
    track_volume = Column(Boolean, default=True)
    
    # Created/Updated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="alert_settings")
    
    def __repr__(self):
        return f"<AlertPreference {self.symbol} - Tier {self.min_tier}+>"

# ============================================================================
# MARKET DATA SNAPSHOTS (For analysis)
# ============================================================================

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    
    price = Column(Numeric(10, 2))
    volume = Column(Integer)
    market_cap = Column(Numeric(15, 2), nullable=True)
    pe_ratio = Column(Float, nullable=True)
    
    # 52-week data
    high_52w = Column(Numeric(10, 2), nullable=True)
    low_52w = Column(Numeric(10, 2), nullable=True)
    
    # Moving averages
    sma_20 = Column(Numeric(10, 2), nullable=True)  # 20-day simple moving avg
    sma_200 = Column(Numeric(10, 2), nullable=True)  # 200-day
    
    # Options data
    call_volume = Column(Integer, nullable=True)
    put_volume = Column(Integer, nullable=True)
    put_call_ratio = Column(Float, nullable=True)
    
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PriceSnapshot {self.symbol} ${self.price} {self.timestamp}>"

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
