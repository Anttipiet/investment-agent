# Investment Agent System - Technical Specification

## 1. System Overview

Multi-user investment intelligence platform with:
- **Sector Focus:** Defense, Aerospace, Energy, Nuclear, AI
- **Data Sources:** SEC filings, AlphaPicks, congressional trades, institutional holdings
- **Features:** Buy/sell signals, virtual sandbox, alert scaling, multi-user support
- **Future:** Automated trading, portfolio management

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB DASHBOARD (React)                    │
│  - Real-time signals, portfolio tracking, alert settings    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              REST API Layer (FastAPI/Flask)                 │
│  - Authentication, user portfolios, signal history          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Core Agent Engine (Python)                      │
│  ├─ Data Collectors (SEC, AlphaPicks, Market Data)          │
│  ├─ Signal Generator (Buy/Sell Logic)                       │
│  ├─ Virtual Trading Engine                                  │
│  ├─ Alert Manager (with scaling)                            │
│  └─ Portfolio Manager                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              PostgreSQL Database                             │
│  ├─ Users & Portfolios                                      │
│  ├─ Stock Watchlist & Signals                               │
│  ├─ Trade History (Virtual)                                 │
│  ├─ Insider Trades & Congressional Activity                 │
│  └─ Alert Configuration                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Data Sources & Integration Points

### 3.1 Primary Data Sources

| Source | API | Frequency | Cost | Priority |
|--------|-----|-----------|------|----------|
| SEC EDGAR | REST API | Daily | Free | P0 |
| AlphaPicks | Web scrape/API | Daily | Free | P0 |
| Finnhub | REST API | Real-time | Free tier | P1 |
| Congressional | housestockwatcher.com | Weekly | Free | P1 |
| Market Data | yfinance | Real-time | Free | P1 |
| Institutional (13F) | SEC EDGAR | Quarterly | Free | P2 |

### 3.2 Target Sectors & Symbols

```python
SECTOR_FOCUS = {
    'DEFENSE': ['LMT', 'RTX', 'GD', 'NOC', 'HII'],
    'AEROSPACE': ['BA', 'SPR', 'TDG', 'UTX', 'PWA'],
    'ENERGY': ['XLE', 'CVX', 'COP', 'EOG', 'MPC'],
    'NUCLEAR': ['UEC', 'CCJ', 'NLR', 'URG', 'UUUU'],
    'AI': ['NVDA', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMD', 'SMCI']
}
```

---

## 4. Signal Logic (Buy/Sell Detection)

### 4.1 BUY Signals (Phase 1 - Conservative)

```
TIER 1 - Insider Accumulation:
├─ CEO/CFO buying >$100K in single transaction
├─ 3+ company insiders buying same stock (1 week window)
├─ Director buying (especially in growth companies)
└─ Multiple buys after bearish period

TIER 2 - Institutional Moves:
├─ Major fund initiating position (13F new entry)
├─ Institutional ownership increase >5% (quarterly)
└─ BlackRock/Vanguard concentration increase

TIER 3 - Congressional Activity:
├─ Congress member + spouse buying (healthcare/defense)
├─ Multiple representatives buying same sector

TIER 4 - Market Indicators:
├─ Volume spike >200% of 20-day avg
├─ Options call/put ratio >2.0 (bullish skew)
└─ Short interest decrease >10% (covering)
```

### 4.2 SELL Signals (Phase 1 - Conservative)

```
TIER 1 - Insider Selling:
├─ CEO/CFO selling >$500K (unusual for them)
├─ Multiple insiders selling in coordination
├─ After stock pump (pre-earnings)
└─ Selling above 52-week high

TIER 2 - Institutional Dumping:
├─ Top institutional holder reducing >20% position
├─ Fund closing position entirely (13F change)
└─ Concentration decrease in key holders

TIER 3 - Technical Breakdown:
├─ Stock breaks below key support (200-day MA)
├─ Volume surge on down days >300%
├─ Options skew shifts bearish (puts > calls)

TIER 4 - Congressional/Regulatory:
├─ Congress members selling sector heavily
├─ Regulatory announcement (patent, investigation)
└─ Short interest spike >30% increase
```

---

## 5. Alert Scaling Strategy

### Phase 1: MVP (Week 1-2)
- **Sensitivity:** HIGH (only top-tier signals)
- **Minimum threshold:** $500K insider buy, 3+ insiders, CEO involvement
- **Alert frequency:** Max 2-3 per day
- **False positive rate:** Expected ~40%

### Phase 2: Tuning (Week 3-4)
- **Add:** Volume anomalies, congressional moves
- **Sensitivity:** MEDIUM-HIGH
- **Alert frequency:** 4-8 per day
- **Adjust thresholds based on user feedback

### Phase 3: Advanced (Week 5+)
- **Add:** Options flow, institutional nuance
- **Sensitivity:** MEDIUM
- **Alert frequency:** 8-20 per day
- **Machine learning filtering**

---

## 6. Virtual Trading Sandbox

### 6.1 Features
- Starting capital: $100K (configurable per user)
- Full order types: market, limit, stop-loss
- Commission: $5/trade (realistic cost)
- Portfolio tracking with P&L
- Backtesting against historical data
- Live paper trading (tracks real prices)

### 6.2 Execution Model
```python
virtual_trade = {
    'user_id': 'user_123',
    'symbol': 'NVDA',
    'action': 'BUY',  # BUY or SELL
    'shares': 50,
    'entry_price': 875.50,  # Real market price at time
    'timestamp': '2024-01-15T14:30:00Z',
    'status': 'FILLED',  # PENDING, FILLED, CANCELLED
    'commission': 5.00,
    'p_l': None  # Calculated on exit or market price
}
```

---

## 7. Database Schema (PostgreSQL)

### 7.1 Users & Authentication
```sql
users
├─ id (PK)
├─ email (UNIQUE)
├─ username
├─ password_hash
├─ created_at
├─ api_key (for multi-user auth)
└─ preferences (JSON: alert_sensitivity, etc)

watchlist
├─ id (PK)
├─ user_id (FK)
├─ symbol
├─ sector
├─ added_date
└─ notes
```

### 7.2 Signals & Trading
```sql
signals
├─ id (PK)
├─ symbol
├─ signal_type (BUY/SELL)
├─ tier (1-4)
├─ confidence (0-100%)
├─ timestamp
├─ reason (JSON: insider_activity, volume_spike, etc)
├─ data_source
└─ dismissed_by (FK user, null=active)

virtual_trades
├─ id (PK)
├─ user_id (FK)
├─ symbol
├─ action (BUY/SELL)
├─ shares
├─ entry_price
├─ exit_price
├─ entry_date
├─ exit_date
├─ status (OPEN/CLOSED)
└─ p_l

virtual_portfolios
├─ id (PK)
├─ user_id (FK)
├─ cash_balance
├─ total_value
├─ positions (JSON array of holdings)
└─ last_updated
```

### 7.3 Data & Intelligence
```sql
insider_trades
├─ id (PK)
├─ symbol
├─ insider_name
├─ insider_role (CEO, CFO, Director, etc)
├─ company_id
├─ transaction_type (BUY/SELL)
├─ shares
├─ price
├─ transaction_date
├─ filing_date
└─ form_4_url

congressional_trades
├─ id (PK)
├─ member_name
├─ chamber (House/Senate)
├─ symbol
├─ action (BUY/SELL)
├─ amount_range
├─ transaction_date
├─ filing_date
└─ party

alpha_picks
├─ id (PK)
├─ symbol
├─ rating (BUY/HOLD/SELL)
├─ price_target
├─ analyst
├─ date
└─ reasoning (TEXT)
```

---

## 8. Technology Stack

### Backend
```
Python 3.10+
├─ FastAPI (REST API)
├─ SQLAlchemy (ORM)
├─ APScheduler (task scheduling)
├─ Pydantic (data validation)
├─ psycopg2 (PostgreSQL driver)
├─ aiohttp (async HTTP)
└─ python-jose (JWT auth)

Data Processing
├─ pandas (data manipulation)
├─ numpy (calculations)
├─ BeautifulSoup4 (web scraping)
├─ requests (HTTP client)
├─ yfinance (market data)
└─ finnhub-python (real-time data)
```

### Frontend
```
React 18+
├─ TypeScript
├─ Vite (build tool)
├─ TanStack Query (data fetching)
├─ Recharts (data visualization)
├─ Shadcn/ui (component library)
├─ Zustand (state management)
└─ Tailwind CSS (styling)
```

### Infrastructure
```
Docker (containerization)
PostgreSQL 14+
Redis (caching, sessions)
Docker Compose (local development)
AWS/Heroku (hosting)
```

---

## 9. Implementation Phases

### Phase 1: MVP (2 weeks)
- [x] Database schema & setup
- [x] SEC Form 4 scraper
- [x] AlphaPicks data fetcher
- [x] Basic buy signal detection (insider buys >$500K)
- [x] Email/Discord alerts
- [x] Virtual trading engine (basic)
- [x] Dashboard (minimal UI)
- [x] Multi-user auth

### Phase 2: Enhancement (2 weeks)
- [ ] Sell signal detection
- [ ] Congressional trading integration
- [ ] Volume/options anomaly detection
- [ ] Alert sensitivity tuning
- [ ] Portfolio P&L tracking
- [ ] Backtesting module
- [ ] Alert history & analytics

### Phase 3: Advanced (3+ weeks)
- [ ] Machine learning signal filtering
- [ ] Real-time streaming (WebSocket)
- [ ] Risk scoring system
- [ ] Automated order placement (sandbox first)
- [ ] Mobile app
- [ ] Advanced charting

---

## 10. API Endpoints (Summary)

```
Authentication
POST   /auth/register
POST   /auth/login
POST   /auth/refresh

Signals
GET    /signals (with filters: symbol, type, date range)
POST   /signals/{id}/dismiss
GET    /signals/{id}/history

Trading
POST   /trades (place virtual trade)
GET    /trades (user's trade history)
GET    /portfolio (current holdings)
GET    /portfolio/performance

Watchlist
GET    /watchlist
POST   /watchlist
DELETE /watchlist/{symbol}

Settings
GET    /user/settings
PUT    /user/settings (alert sensitivity, etc)
POST   /user/alert-preferences
```

---

## 11. Development Timeline & MVP Goals

**Week 1:**
- Database setup
- Core data collectors (SEC, AlphaPicks)
- Basic signal engine
- Email alerts

**Week 2:**
- Virtual trading
- Dashboard UI (minimal)
- Multi-user auth
- Deploy to staging

**Week 3+:**
- Refinement based on signal accuracy
- Add sell signals
- Enhance UI
- Scale to production

---

## 12. Success Metrics

- **Signal accuracy:** >50% win rate on buy signals (realistic for MVP)
- **Alert relevance:** User dismissal rate <20%
- **System uptime:** >99.5%
- **Response time:** API <200ms, Dashboard <1s load
- **User retention:** Track active users in virtual sandbox

---

## 13. Future Enhancements

- Automated trading (connected to broker API: Alpaca, Interactive Brokers)
- Advanced ML filtering (eliminate false positives)
- Sector rotation strategy
- Risk management (position sizing, stop-losses)
- Community features (share signals, tips)
- Mobile app for on-the-go alerts
- Integration with TradingView
