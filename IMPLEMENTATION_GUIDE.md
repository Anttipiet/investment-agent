# Investment Agent - Complete Implementation Guide

## 📋 Quick Start (MVP in 2 weeks)

### Week 1: Foundation
- Database setup & schema
- Core signal engine
- Basic data collection (SEC insider trades)
- Email alerts
- Virtual trading sandbox

### Week 2: Polish
- Dashboard UI (React)
- Multi-user authentication
- Alert sensitivity tuning
- Deploy to staging
- Begin live testing

---

## 🛠️ Local Development Setup

### Prerequisites
```bash
# System requirements
- Python 3.10+
- PostgreSQL 14+
- Node.js 18+
- Git

# Verify installations
python --version       # 3.10+
psql --version        # 14.0+
node --version        # 18+
```

### 1. Database Setup

```bash
# Create PostgreSQL database
psql -U postgres
postgres=# CREATE DATABASE investment_agent;
postgres=# CREATE USER invest_user WITH PASSWORD 'secure_password';
postgres=# ALTER ROLE invest_user SET client_encoding TO 'utf8';
postgres=# ALTER ROLE invest_user SET default_transaction_isolation TO 'read committed';
postgres=# ALTER ROLE invest_user SET default_transaction_deferrable TO on;
postgres=# ALTER ROLE invest_user SET default_transaction_mode TO 'read committed';
postgres=# GRANT ALL PRIVILEGES ON DATABASE investment_agent TO invest_user;
postgres=# \q

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://invest_user:secure_password@localhost:5432/investment_agent
FINNHUB_API_KEY=your_api_key_here
SECRET_KEY=your_jwt_secret_key_here
DEBUG=True
ENVIRONMENT=development
EOF
```

### 2. Backend Setup

```bash
# Clone/setup project
mkdir investment-agent && cd investment-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from models import init_db; init_db()"

# Start Celery worker (for async tasks)
celery -A tasks worker --loglevel=info

# Run signal generation (first time)
python -c "from signal_engine import run_signal_generation_batch; from models import SessionLocal; db = SessionLocal(); run_signal_generation_batch(db)"
```

### 3. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev  # http://localhost:5173
```

### 4. API Server

```bash
# From root directory
# Install FastAPI dependencies
pip install fastapi uvicorn

# Create API server (main.py)
# [See API Server section below]

# Run server
uvicorn main:app --reload --port 8000
```

---

## 📦 Requirements.txt

```txt
# Core
python-dotenv==1.0.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9

# Data Collection
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
yfinance==0.2.32
pandas==2.1.1
numpy==1.26.0

# API & Web
fastapi==0.104.1
uvicorn==0.24.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic==2.5.0

# Task Scheduling
celery==5.3.4
redis==5.0.1

# Notifications
sendgrid==6.11.0
twilio==8.10.0
discord.py==2.3.2

# Development
pytest==7.4.3
black==23.12.0
flake8==6.1.0
```

---

## 🔌 API Server (FastAPI)

Create `main.py`:

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
from datetime import timedelta
import os
from dotenv import load_dotenv

from models import SessionLocal, User, Signal, get_db
from signal_engine import SignalGenerator
from virtual_trading import VirtualTradingEngine
from data_collectors import run_daily_data_collection

load_dotenv()

app = FastAPI(title="Investment Agent API", version="1.0.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/auth/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    """Register new user"""
    # Hash password, create user, return API key
    pass

@app.post("/auth/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    """Login and get JWT token"""
    pass

# ============================================================================
# SIGNALS ENDPOINTS
# ============================================================================

@app.get("/signals")
def get_signals(
    symbol: str = None,
    signal_type: str = None,
    tier: int = None,
    limit: int = 50,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get signals with optional filters"""
    # Verify user
    user_id = verify_token(credentials.credentials)
    
    query = db.query(Signal)
    if symbol:
        query = query.filter(Signal.symbol == symbol)
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if tier:
        query = query.filter(Signal.tier == tier)
    
    signals = query.order_by(Signal.detected_at.desc()).limit(limit).all()
    
    return {
        'count': len(signals),
        'signals': [
            {
                'id': s.id,
                'symbol': s.symbol,
                'type': s.signal_type,
                'tier': s.tier,
                'confidence': s.confidence,
                'source': s.data_source,
                'reason': s.reason,
                'timestamp': s.detected_at.isoformat()
            }
            for s in signals
        ]
    }

@app.post("/signals/{signal_id}/dismiss")
def dismiss_signal(
    signal_id: int,
    reason: str = None,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Dismiss a signal"""
    user_id = verify_token(credentials.credentials)
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.dismissed_at = datetime.utcnow()
    signal.dismissed_by_user_id = user_id
    db.commit()
    
    return {'status': 'dismissed', 'signal_id': signal_id}

# ============================================================================
# TRADING ENDPOINTS
# ============================================================================

@app.post("/trades")
def place_trade(
    symbol: str,
    action: str,  # BUY or SELL
    shares: int,
    price: float,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Place a virtual trade"""
    user_id = verify_token(credentials.credentials)
    
    engine = VirtualTradingEngine(db, user_id)
    
    if action == "BUY":
        result = engine.buy(symbol, shares, Decimal(str(price)))
    elif action == "SELL":
        result = engine.sell(symbol, shares, Decimal(str(price)))
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    return result

@app.get("/portfolio")
def get_portfolio(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current portfolio status"""
    user_id = verify_token(credentials.credentials)
    engine = VirtualTradingEngine(db, user_id)
    
    return engine.get_portfolio_status()

@app.get("/portfolio/performance")
def get_performance(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get portfolio performance metrics"""
    user_id = verify_token(credentials.credentials)
    engine = VirtualTradingEngine(db, user_id)
    
    return engine.get_performance_metrics()

@app.get("/trades")
def get_trades(
    limit: int = 50,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get trade history"""
    user_id = verify_token(credentials.credentials)
    engine = VirtualTradingEngine(db, user_id)
    
    return {'trades': engine.get_trade_history(limit)}

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.post("/admin/run-collection")
def run_collection(
    api_key: str,
    db: Session = Depends(get_db)
):
    """Manually trigger data collection"""
    # Verify admin API key
    if api_key != os.getenv('ADMIN_API_KEY'):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    results = run_daily_data_collection(db)
    
    return {'status': 'completed', 'results': results}

@app.post("/admin/run-signals")
def run_signals(
    api_key: str,
    db: Session = Depends(get_db)
):
    """Manually trigger signal generation"""
    if api_key != os.getenv('ADMIN_API_KEY'):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from signal_engine import run_signal_generation_batch
    results = run_signal_generation_batch(db)
    
    return {'status': 'completed', 'results': results}

# ============================================================================
# HEALTH & INFO
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}

@app.get("/info")
def get_info():
    """System info"""
    return {
        'name': 'Investment Agent',
        'version': '1.0.0',
        'status': 'operational'
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def verify_token(token: str) -> int:
    """Verify JWT token and return user_id"""
    # Implementation using python-jose
    try:
        # Decode and verify
        payload = jose.jwt.get_unverified_claims(token)
        user_id = payload.get('sub')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 📅 Task Scheduling (Celery)

Create `tasks.py`:

```python
from celery import Celery
from celery.schedules import crontab
from data_collectors import run_daily_data_collection
from signal_engine import run_signal_generation_batch
from alert_manager import send_daily_digest
from models import SessionLocal
import os

app = Celery('investment_agent', broker=os.getenv('REDIS_URL', 'redis://localhost'))

# Tasks
@app.task
def collect_data():
    """Daily data collection (9:30 AM - market open)"""
    db = SessionLocal()
    run_daily_data_collection(db)
    db.close()

@app.task
def generate_signals():
    """Generate signals (9:45 AM - after data collected)"""
    db = SessionLocal()
    run_signal_generation_batch(db)
    db.close()

@app.task
def send_alerts():
    """Send alert digests (3x daily)"""
    db = SessionLocal()
    send_daily_digest(db)
    db.close()

# Schedule
app.conf.beat_schedule = {
    'collect-data': {
        'task': 'tasks.collect_data',
        'schedule': crontab(hour=9, minute=30, day_of_week='mon-fri'),  # Market open
    },
    'generate-signals': {
        'task': 'tasks.generate_signals',
        'schedule': crontab(hour=9, minute=45, day_of_week='mon-fri'),  # After collection
    },
    'send-alerts-morning': {
        'task': 'tasks.send_alerts',
        'schedule': crontab(hour=10, minute=0, day_of_week='mon-fri'),
    },
    'send-alerts-noon': {
        'task': 'tasks.send_alerts',
        'schedule': crontab(hour=13, minute=0, day_of_week='mon-fri'),
    },
    'send-alerts-close': {
        'task': 'tasks.send_alerts',
        'schedule': crontab(hour=16, minute=30, day_of_week='mon-fri'),  # Market close
    },
}
```

---

## 🚀 Deployment (Production)

### Option 1: Heroku (Easiest)

```bash
# Install Heroku CLI
heroku login

# Create app
heroku create investment-agent

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:standard-0

# Add Redis addon
heroku addons:create heroku-redis:premium-0

# Deploy
git push heroku main

# Scale dynos
heroku ps:scale web=2 worker=1
heroku ps:scale clock=1  # For Celery Beat

# View logs
heroku logs --tail
```

### Option 2: AWS EC2 + RDS

```bash
# Launch EC2 instance (Ubuntu 22.04)
# Create RDS PostgreSQL database
# Create ElastiCache Redis

# On EC2:
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y python3.10 python3-pip postgresql-client redis-tools

# 3. Clone repo and setup
git clone <repo>
cd investment-agent
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Create systemd service for API
sudo cat > /etc/systemd/system/investment-api.service << EOF
[Unit]
Description=Investment Agent API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/investment-agent
Environment="PATH=/home/ubuntu/investment-agent/venv/bin"
ExecStart=/home/ubuntu/investment-agent/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl start investment-api
sudo systemctl enable investment-api

# 5. Create systemd service for Celery worker
sudo cat > /etc/systemd/system/investment-worker.service << EOF
[Unit]
Description=Investment Agent Celery Worker
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/investment-agent
Environment="PATH=/home/ubuntu/investment-agent/venv/bin"
ExecStart=/home/ubuntu/investment-agent/venv/bin/celery -A tasks worker --loglevel=info

[Install]
WantedBy=multi-user.target
EOF

# 6. Create systemd service for Celery Beat
sudo cat > /etc/systemd/system/investment-beat.service << EOF
[Unit]
Description=Investment Agent Celery Beat
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/investment-agent
Environment="PATH=/home/ubuntu/investment-agent/venv/bin"
ExecStart=/home/ubuntu/investment-agent/venv/bin/celery -A tasks beat --loglevel=info

[Install]
WantedBy=multi-user.target
EOF

# 7. Setup Nginx reverse proxy
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/investment-agent
# [Configure nginx]
sudo systemctl restart nginx
```

---

## 📊 Key Metrics to Monitor

```
Dashboard KPIs:
├─ Signal Accuracy: % of signals that resulted in profitable trades
├─ Alert Volume: Signals/day (trend over time)
├─ User Growth: Active traders in sandbox
├─ System Uptime: API availability %
├─ API Response Time: <200ms for all endpoints
├─ Database Performance: Query times <100ms
└─ Data Freshness: Hours since last collection run
```

---

## 🔒 Security Checklist

- [ ] All passwords hashed with bcrypt
- [ ] JWT tokens expire after 24 hours
- [ ] API keys rotated quarterly
- [ ] Database backups daily (3 copies)
- [ ] HTTPS only (SSL certificates)
- [ ] Rate limiting on all endpoints (1000 req/min per user)
- [ ] SQL injection prevention (SQLAlchemy ORM)
- [ ] CORS properly configured
- [ ] Secrets in environment variables only
- [ ] Regular security audits

---

## 📈 Scaling Strategy

**Phase 1 (MVP):** 
- Single API server
- PostgreSQL database
- Celery on same instance
- <100 active users

**Phase 2 (Growth):**
- Load balancer (Nginx/ALB)
- Multiple API servers (horizontal scale)
- RDS with read replicas
- Separate Celery workers

**Phase 3 (Enterprise):**
- Kubernetes (EKS/GKE)
- Managed PostgreSQL (RDS Aurora)
- ElastiCache for session/cache
- CDN for frontend
- 1000+ active users

---

## 🎯 Next Steps (Post-MVP)

1. **Week 3-4:** Add sell signal detection, congressional trading
2. **Week 5-6:** Machine learning filtering (eliminate false positives)
3. **Week 7-8:** Real-time WebSocket updates, advanced charting
4. **Month 3:** Automated trading (paper + real), risk management
5. **Month 4+:** Mobile app, community features, premium tiers

---

## 💬 Support & Troubleshooting

### Common Issues

**Database connection error:**
```bash
# Check PostgreSQL is running
psql -U invest_user -d investment_agent -c "SELECT 1;"

# Verify DATABASE_URL in .env
echo $DATABASE_URL
```

**Celery not processing tasks:**
```bash
# Check Redis is running
redis-cli ping

# View Celery tasks
celery -A tasks inspect active
```

**Signals not generating:**
```bash
# Check if data exists in database
psql -c "SELECT COUNT(*) FROM insider_trades;"

# Manually run signal generation
python -c "from signal_engine import run_signal_generation_batch; ..."
```

---

## 📚 Resources

- **FastAPI:** https://fastapi.tiangolo.com/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Celery:** https://docs.celeryproject.org/
- **React:** https://react.dev/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Finnhub API:** https://finnhub.io/docs/api
- **SEC EDGAR:** https://www.sec.gov/cgi-bin/browse-edgar

---

**Built with ❤️ for intelligent investing**
