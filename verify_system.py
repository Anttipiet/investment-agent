"""
System verification - Check all files and data
"""

import os
import sys
from pathlib import Path

print("\n" + "="*80)
print("🔍 INVESTMENT AGENT SYSTEM VERIFICATION")
print("="*80)

# ============================================================================
# 1. CHECK FILES EXIST
# ============================================================================

print("\n📁 CHECKING FILES...")
print("─" * 80)

required_files = {
    'models.py': 'Database models (users, signals, trades, news)',
    'signal_engine.py': 'Signal generation engine',
    'virtual_trading.py': 'Virtual trading sandbox',
    'data_collectors.py': 'Data fetching modules',
    'load_sample_data.py': 'Sample data loader',
    'load_more_data.py': 'Comprehensive data loader',
    'load_news.py': 'News article loader',
    'main.py': 'FastAPI server',
    'frontend/index.html': 'Dashboard UI',
    '.env': 'Environment configuration'
}

missing_files = []
for filename, description in required_files.items():
    if os.path.exists(filename):
        print(f"  ✅ {filename:25} - {description}")
    else:
        print(f"  ❌ {filename:25} - MISSING!")
        missing_files.append(filename)

# ============================================================================
# 2. CHECK DATABASE TABLES
# ============================================================================

print("\n📊 CHECKING DATABASE TABLES...")
print("─" * 80)

try:
    from models import SessionLocal, Base
    
    # Get all table names
    tables = Base.metadata.tables.keys()
    
    required_tables = [
        'users',
        'signals', 
        'insider_trades',
        'congressional_trades',
        'alpha_picks',
        'institutional_holdings',
        'virtual_portfolios',
        'virtual_trades',
        'news_articles',
        'watchlist',
        'alert_preferences',
        'price_snapshots'
    ]
    
    for table in required_tables:
        if table in tables:
            print(f"  ✅ {table:25}")
        else:
            print(f"  ❌ {table:25} - MISSING!")
    
    # Check data
    db = SessionLocal()
    
    from models import InsiderTrade, Signal, NewsArticle, VirtualTrade
    
    insider_count = db.query(InsiderTrade).count()
    signal_count = db.query(Signal).count()
    news_count = db.query(NewsArticle).count()
    trade_count = db.query(VirtualTrade).count()
    
    print("\n📈 DATA COUNTS:")
    print(f"  • Insider Trades: {insider_count}")
    print(f"  • Signals: {signal_count}")
    print(f"  • News Articles: {news_count}")
    print(f"  • Virtual Trades: {trade_count}")
    
    db.close()
    
except Exception as e:
    print(f"  ❌ Database error: {str(e)[:60]}")

# ============================================================================
# 3. CHECK PYTHON IMPORTS
# ============================================================================

print("\n🐍 CHECKING PYTHON MODULES...")
print("─" * 80)

modules_to_check = {
    'sqlalchemy': 'Database ORM',
    'fastapi': 'API framework',
    'uvicorn': 'ASGI server',
    'pydantic': 'Data validation',
    'yfinance': 'Market data',
    'requests': 'HTTP client',
    'pandas': 'Data processing',
    'numpy': 'Numerical computing'
}

for module, description in modules_to_check.items():
    try:
        __import__(module)
        print(f"  ✅ {module:20} - {description}")
    except ImportError:
        print(f"  ❌ {module:20} - NOT INSTALLED")

# ============================================================================
# 4. CHECK KEY CODE SECTIONS
# ============================================================================

print("\n🔧 CHECKING KEY CODE SECTIONS...")
print("─" * 80)

def check_file_contains(filename, keywords):
    """Check if file contains all keywords"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        found = all(keyword in content for keyword in keywords)
        return found
    except:
        return False

# Check models.py has NewsArticle
if check_file_contains('models.py', ['class NewsArticle', 'sentiment', 'news_articles']):
    print("  ✅ models.py has NewsArticle table")
else:
    print("  ❌ models.py missing NewsArticle table!")

# Check signal_engine.py has news integration
if check_file_contains('signal_engine.py', ['NewsArticle', 'sentiment', 'news_sentiment']):
    print("  ✅ signal_engine.py has news sentiment integration")
else:
    print("  ❌ signal_engine.py missing news integration!")

# Check load_news.py exists and has data
if os.path.exists('load_news.py'):
    if check_file_contains('load_news.py', ['NewsArticle', 'sentiment', 'POSITIVE', 'NEGATIVE']):
        print("  ✅ load_news.py is properly configured")
    else:
        print("  ⚠️  load_news.py exists but may be incomplete")
else:
    print("  ❌ load_news.py not found!")

# Check frontend has news section
if check_file_contains('frontend/index.html', ['news', 'News', 'sentiment', 'POSITIVE', 'NEGATIVE']):
    print("  ✅ frontend/index.html has news section")
else:
    print("  ❌ frontend/index.html missing news section!")

# ============================================================================
# 5. SUMMARY
# ============================================================================

print("\n" + "="*80)
print("📋 VERIFICATION SUMMARY")
print("="*80)

if missing_files:
    print(f"\n⚠️  MISSING FILES ({len(missing_files)}):")
    for f in missing_files:
        print(f"   • {f}")
    print("\n💡 Create missing files with the code provided above.")
else:
    print("\n✅ All required files exist!")

print("\n🚀 NEXT STEPS:")
print("   1. If files are missing, create them with the provided code")
print("   2. Run: python load_more_data.py")
print("   3. Run: python load_news.py")
print("   4. Refresh dashboard at http://localhost:5173")

print("\n" + "="*80 + "\n")