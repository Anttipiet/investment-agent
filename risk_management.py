"""
Risk Management System
Position sizing, stop losses, portfolio heat, risk scoring
"""

from models import SessionLocal, VirtualPortfolio, PortfolioRisk, VirtualTrade
from decimal import Decimal
from datetime import datetime

class RiskManager:
    """Manage portfolio risk and position sizing"""
    
    def __init__(self, db, user_id: int):
        self.db = db
        self.user_id = user_id
        self.portfolio = db.query(VirtualPortfolio).filter(
            VirtualPortfolio.user_id == user_id
        ).first()
        self.risk_config = db.query(PortfolioRisk).filter(
            PortfolioRisk.user_id == user_id
        ).first()
    
    # =========================================================================
    # POSITION SIZING
    # =========================================================================
    
    def calculate_position_size(self, capital_at_risk_pct: float = 2.0) -> Decimal:
        """
        Calculate position size using Kelly Criterion variant
        Only risk 1-2% of portfolio per trade
        """
        if not self.portfolio:
            return Decimal(0)
        
        portfolio_value = self.portfolio.total_value
        risk_amount = portfolio_value * Decimal(str(capital_at_risk_pct)) / 100
        
        return risk_amount
    
    def max_shares_for_stock(self, symbol: str, price: Decimal, 
                            capital_at_risk_pct: float = 2.0) -> int:
        """How many shares can we buy with risk limits?"""
        risk_amount = self.calculate_position_size(capital_at_risk_pct)
        
        if price <= 0:
            return 0
        
        max_shares = int(risk_amount / price)
        
        # Apply max position size constraint (e.g., 10% of portfolio)
        if self.risk_config:
            max_portfolio_pct = self.risk_config.max_position_size_pct
            max_value = self.portfolio.total_value * Decimal(str(max_portfolio_pct)) / 100
            max_shares_constraint = int(max_value / price)
            max_shares = min(max_shares, max_shares_constraint)
        
        return max_shares
    
    # =========================================================================
    # STOP LOSS & PROFIT TARGET
    # =========================================================================
    
    def calculate_stop_loss(self, entry_price: Decimal, 
                           stop_loss_pct: float = 5.0) -> Decimal:
        """
        Calculate stop loss level
        Default: 5% below entry
        """
        stop_level = entry_price * (1 - Decimal(str(stop_loss_pct)) / 100)
        return stop_level.quantize(Decimal('0.01'))
    
    def calculate_profit_target(self, entry_price: Decimal, 
                               profit_target_pct: float = 10.0) -> Decimal:
        """
        Calculate profit target
        Default: 10% above entry (risk:reward = 1:2)
        """
        target = entry_price * (1 + Decimal(str(profit_target_pct)) / 100)
        return target.quantize(Decimal('0.01'))
    
    def should_exit_position(self, current_price: Decimal, 
                            entry_price: Decimal,
                            stop_loss_pct: float = 5.0,
                            profit_target_pct: float = 10.0) -> str:
        """Check if position should be exited"""
        stop_loss = self.calculate_stop_loss(entry_price, stop_loss_pct)
        profit_target = self.calculate_profit_target(entry_price, profit_target_pct)
        
        if current_price <= stop_loss:
            return "STOP_LOSS_HIT"
        elif current_price >= profit_target:
            return "PROFIT_TARGET_HIT"
        else:
            return "HOLD"
    
    # =========================================================================
    # PORTFOLIO HEAT & EXPOSURE
    # =========================================================================
    
    def get_portfolio_heat(self) -> float:
        """
        Total portfolio risk as % of capital
        Sum of all position risks
        """
        if not self.portfolio:
            return 0
        
        positions = self.portfolio.positions
        total_risk = 0
        
        # Each open position = 2% risk (your position size limit)
        for symbol, pos_data in positions.items():
            if pos_data.get('shares', 0) > 0:  # Only long positions
                total_risk += 2.0  # Standard 2% per trade
        
        return min(total_risk, 100)  # Cap at 100%
    
    def get_sector_exposure(self) -> dict:
        """Get portfolio exposure by sector"""
        positions = self.portfolio.positions if self.portfolio else {}
        
        # Simplified sector mapping
        sector_map = {
            'NVDA': 'AI', 'MSFT': 'AI', 'AMD': 'AI', 'PLTR': 'AI',
            'RTX': 'DEFENSE', 'LMT': 'DEFENSE', 'GD': 'DEFENSE',
            'BA': 'AEROSPACE', 'SPR': 'AEROSPACE',
            'CVX': 'ENERGY', 'COP': 'ENERGY', 'EOG': 'ENERGY',
            'UEC': 'NUCLEAR', 'CCJ': 'NUCLEAR'
        }
        
        sectors = {}
        total_value = float(self.portfolio.total_value) if self.portfolio else 0
        
        for symbol, pos_data in positions.items():
            sector = sector_map.get(symbol, 'OTHER')
            pos_value = pos_data.get('current_value', 0)
            pct = (pos_value / total_value * 100) if total_value > 0 else 0
            
            sectors[sector] = sectors.get(sector, 0) + pct
        
        return sectors
    
    def is_overexposed_sector(self, sector: str, max_exposure_pct: float = 30) -> bool:
        """Check if any sector exceeds max exposure"""
        exposure = self.get_sector_exposure()
        return exposure.get(sector, 0) > max_exposure_pct
    
    # =========================================================================
    # PORTFOLIO HEALTH CHECKS
    # =========================================================================
    
    def get_max_drawdown(self) -> float:
        """Maximum loss from peak to current"""
        if not self.portfolio:
            return 0
        
        initial = float(self.portfolio.initial_cash)
        current = float(self.portfolio.total_value)
        
        if initial == 0:
            return 0
        
        drawdown_pct = ((initial - current) / initial) * 100
        return max(0, drawdown_pct)  # Don't show gains as drawdown
    
    def should_stop_trading(self) -> bool:
        """Stop trading if drawdown exceeds limit"""
        if not self.risk_config:
            return False
        
        max_loss = self.risk_config.max_portfolio_loss_pct
        current_drawdown = self.get_max_drawdown()
        
        return current_drawdown > max_loss
    
    def get_risk_score(self) -> int:
        """
        Portfolio risk score (0-100)
        0 = No risk
        100 = Maximum risk
        """
        heat = self.get_portfolio_heat()
        drawdown = self.get_max_drawdown()
        
        # Weighted average
        risk_score = (heat * 0.6 + drawdown * 0.4)
        
        return min(100, int(risk_score))
    
    # =========================================================================
    # RECOMMENDATIONS
    # =========================================================================
    
    def get_risk_recommendations(self) -> list:
        """Get risk management recommendations"""
        recs = []
        
        heat = self.get_portfolio_heat()
        if heat > 10:
            recs.append(f"⚠️  Portfolio heat high ({heat:.1f}%). Consider reducing position size.")
        
        if self.should_stop_trading():
            drawdown = self.get_max_drawdown()
            recs.append(f"🛑 Drawdown ({drawdown:.1f}%) exceeds limit. Stop trading to preserve capital.")
        
        sectors = self.get_sector_exposure()
        for sector, exposure in sectors.items():
            if exposure > 30:
                recs.append(f"⚠️  {sector} sector exposure is {exposure:.1f}%. Reduce concentration.")
        
        if not recs:
            recs.append("✓ Portfolio risk is healthy.")
        
        return recs