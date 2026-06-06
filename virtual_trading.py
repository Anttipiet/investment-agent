"""
Investment Agent - Virtual Trading Engine
Paper trading / sandbox for testing signals before real money
"""

from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from models import (
    VirtualPortfolio, VirtualTrade, User, Signal,
    TradeAction, TradeStatus
)
import logging
import json

logger = logging.getLogger(__name__)

# ============================================================================
# VIRTUAL TRADING ENGINE
# ============================================================================

class VirtualTradingEngine:
    """
    Paper trading engine that simulates trading without real money
    Tracks all trades, calculates P&L, manages virtual portfolio
    """
    
    COMMISSION = Decimal('5.00')  # $5 per trade
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.user = self.db.query(User).filter(User.id == user_id).first()
        
        if not self.user:
            raise ValueError(f"User {user_id} not found")
        
        # Get or create portfolio
        self.portfolio = self.db.query(VirtualPortfolio).filter(
            VirtualPortfolio.user_id == user_id
        ).first()
        
        if not self.portfolio:
            self.portfolio = self._create_portfolio()
    
    def _create_portfolio(self) -> VirtualPortfolio:
        """Initialize new virtual portfolio with $100K"""
        portfolio = VirtualPortfolio(
            user_id=self.user_id,
            initial_cash=Decimal('100000.00'),
            cash_balance=Decimal('100000.00'),
            total_value=Decimal('100000.00'),
            positions={}
        )
        self.db.add(portfolio)
        self.db.commit()
        logger.info(f"✓ Created portfolio for user {self.user_id} with $100,000")
        return portfolio
    
    # ========================================================================
    # ORDER EXECUTION
    # ========================================================================
    
    def buy(self, symbol: str, shares: int, price: Decimal, 
            signal_id: Optional[int] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a BUY order
        
        Returns:
            {
                'success': bool,
                'message': str,
                'trade': VirtualTrade or None,
                'portfolio_value': Decimal
            }
        """
        
        # Validate
        if shares <= 0:
            return {'success': False, 'message': 'Shares must be positive', 'trade': None}
        
        if price <= 0:
            return {'success': False, 'message': 'Price must be positive', 'trade': None}
        
        # Calculate cost
        total_cost = Decimal(str(shares)) * price + self.COMMISSION
        
        # Check available cash
        if total_cost > self.portfolio.cash_balance:
            return {
                'success': False,
                'message': f'Insufficient funds. Need ${total_cost}, have ${self.portfolio.cash_balance}',
                'trade': None,
                'portfolio_value': self.portfolio.total_value
            }
        
        # Create trade record
        trade = VirtualTrade(
            user_id=self.user_id,
            symbol=symbol,
            action=TradeAction.BUY,
            shares=shares,
            entry_price=price,
            entry_date=datetime.utcnow(),
            status=TradeStatus.FILLED,
            commission=self.COMMISSION,
            triggered_by_signal_id=signal_id,
            notes=notes
        )
        
        # Update portfolio
        self.portfolio.cash_balance -= total_cost
        
        # Add to positions
        positions = self.portfolio.positions or {}
        if symbol not in positions:
            positions[symbol] = {
                'shares': 0,
                'avg_cost': 0,
                'current_price': float(price),
                'value': 0
            }
        
        pos = positions[symbol]
        total_shares = pos['shares'] + shares
        pos['avg_cost'] = (pos['avg_cost'] * pos['shares'] + float(price) * shares) / total_shares
        pos['shares'] = total_shares
        pos['current_price'] = float(price)
        pos['value'] = total_shares * float(price)
        
        self.portfolio.positions = positions
        
        # Recalculate portfolio value
        self._update_portfolio_value()
        
        # Save to database
        self.db.add(trade)
        self.db.commit()
        
        logger.info(f"✓ BUY: {shares}x {symbol} @ ${price} for user {self.user_id}")
        
        return {
            'success': True,
            'message': f'Bought {shares} shares of {symbol} @ ${price}',
            'trade': trade,
            'portfolio_value': self.portfolio.total_value,
            'cash_remaining': self.portfolio.cash_balance
        }
    
    def sell(self, symbol: str, shares: int, price: Decimal,
             signal_id: Optional[int] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a SELL order (close position or partial exit)
        
        Returns:
            {
                'success': bool,
                'message': str,
                'trade': VirtualTrade or None,
                'profit_loss': Decimal,
                'profit_loss_pct': float
            }
        """
        
        # Validate
        if shares <= 0:
            return {'success': False, 'message': 'Shares must be positive', 'trade': None}
        
        if price <= 0:
            return {'success': False, 'message': 'Price must be positive', 'trade': None}
        
        # Check if position exists
        positions = self.portfolio.positions or {}
        if symbol not in positions:
            return {
                'success': False,
                'message': f'No position in {symbol} to sell',
                'trade': None
            }
        
        pos = positions[symbol]
        if pos['shares'] < shares:
            return {
                'success': False,
                'message': f'Can only sell {pos["shares"]} shares, requested {shares}',
                'trade': None
            }
        
        # Calculate proceeds
        gross_proceeds = Decimal(str(shares)) * price
        net_proceeds = gross_proceeds - self.COMMISSION
        
        # Calculate P&L
        avg_cost = Decimal(str(pos['avg_cost']))
        cost_basis = Decimal(str(shares)) * avg_cost
        profit_loss = net_proceeds - cost_basis - self.COMMISSION
        profit_loss_pct = float(profit_loss / cost_basis * 100) if cost_basis > 0 else 0
        
        # Create trade record
        trade = VirtualTrade(
            user_id=self.user_id,
            symbol=symbol,
            action=TradeAction.SELL,
            shares=shares,
            entry_price=avg_cost,  # Avg cost
            exit_price=price,
            entry_date=datetime.utcnow(),
            exit_date=datetime.utcnow(),
            status=TradeStatus.FILLED,
            commission=self.COMMISSION * 2,  # Both buy and sell commission
            p_l=profit_loss,
            p_l_percentage=profit_loss_pct,
            triggered_by_signal_id=signal_id,
            notes=notes
        )
        
        # Update portfolio
        self.portfolio.cash_balance += net_proceeds
        self.portfolio.realized_gains += profit_loss
        
        # Update position
        pos['shares'] -= shares
        if pos['shares'] == 0:
            del positions[symbol]
        else:
            pos['value'] = pos['shares'] * pos['current_price']
        
        self.portfolio.positions = positions
        
        # Recalculate
        self._update_portfolio_value()
        
        # Save
        self.db.add(trade)
        self.db.commit()
        
        logger.info(f"✓ SELL: {shares}x {symbol} @ ${price} - P&L: ${profit_loss} ({profit_loss_pct}%)")
        
        return {
            'success': True,
            'message': f'Sold {shares} shares of {symbol} @ ${price}',
            'trade': trade,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'portfolio_value': self.portfolio.total_value,
            'cash_remaining': self.portfolio.cash_balance
        }
    
    # ========================================================================
    # PORTFOLIO MANAGEMENT
    # ========================================================================
    
    def _update_portfolio_value(self):
        """
        Recalculate total portfolio value
        = cash + (all open positions at current price)
        """
        total_position_value = Decimal('0')
        
        positions = self.portfolio.positions or {}
        for symbol, pos in positions.items():
            position_value = Decimal(str(pos['shares'])) * Decimal(str(pos['current_price']))
            total_position_value += position_value
        
        self.portfolio.total_value = self.portfolio.cash_balance + total_position_value
        
        # Calculate total return %
        initial = self.portfolio.initial_cash
        if initial > 0:
            self.portfolio.total_return = float(
                (self.portfolio.total_value - initial) / initial * 100
            )
        
        self.db.commit()
    
    def update_positions_price(self, prices: Dict[str, Decimal]):
        """
        Update current prices for all positions
        Recalculates portfolio value
        
        Args:
            prices: {'NVDA': Decimal('875.50'), ...}
        """
        positions = self.portfolio.positions or {}
        
        for symbol, price in prices.items():
            if symbol in positions:
                positions[symbol]['current_price'] = float(price)
                positions[symbol]['value'] = positions[symbol]['shares'] * float(price)
        
        self.portfolio.positions = positions
        self._update_portfolio_value()
        
        logger.info(f"✓ Updated prices for {len(prices)} positions")
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        positions = self.portfolio.positions or {}
        
        open_trades = self.db.query(VirtualTrade).filter(
            VirtualTrade.user_id == self.user_id,
            VirtualTrade.status == TradeStatus.FILLED,
            VirtualTrade.exit_date == None
        ).all()
        
        return {
            'user_id': self.user_id,
            'total_value': float(self.portfolio.total_value),
            'cash_balance': float(self.portfolio.cash_balance),
            'initial_cash': float(self.portfolio.initial_cash),
            'total_return_pct': self.portfolio.total_return,
            'realized_gains': float(self.portfolio.realized_gains),
            'unrealized_gains': float(self.portfolio.unrealized_gains),
            'positions': positions,
            'open_position_count': len(positions),
            'total_trades': len(open_trades),
            'updated_at': self.portfolio.updated_at.isoformat()
        }
    
    def get_trade_history(self, limit: int = 50) -> list:
        """Get recent trades"""
        trades = self.db.query(VirtualTrade).filter(
            VirtualTrade.user_id == self.user_id
        ).order_by(VirtualTrade.entry_date.desc()).limit(limit).all()
        
        return [
            {
                'id': t.id,
                'symbol': t.symbol,
                'action': t.action,
                'shares': t.shares,
                'entry_price': float(t.entry_price),
                'exit_price': float(t.exit_price) if t.exit_price else None,
                'entry_date': t.entry_date.isoformat(),
                'exit_date': t.exit_date.isoformat() if t.exit_date else None,
                'p_l': float(t.p_l) if t.p_l else None,
                'p_l_pct': t.p_l_percentage,
                'status': t.status,
                'signal_id': t.triggered_by_signal_id
            }
            for t in trades
        ]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        trades = self.db.query(VirtualTrade).filter(
            VirtualTrade.user_id == self.user_id,
            VirtualTrade.status == TradeStatus.FILLED,
            VirtualTrade.p_l != None
        ).all()
        
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'total_profit': 0,
                'largest_win': 0,
                'largest_loss': 0
            }
        
        winning = [t for t in trades if t.p_l > 0]
        losing = [t for t in trades if t.p_l < 0]
        
        total_profit = sum(t.p_l for t in trades)
        avg_win = sum(t.p_l for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.p_l for t in losing) / len(losing) if losing else 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / len(trades) * 100 if trades else 0,
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'total_profit': float(total_profit),
            'largest_win': float(max((t.p_l for t in winning), default=0)),
            'largest_loss': float(min((t.p_l for t in losing), default=0))
        }

# ============================================================================
# TRADING SIGNALS TO VIRTUAL ORDERS
# ============================================================================

class SignalToOrderConverter:
    """
    Converts high-confidence signals into virtual trading orders
    Applies position sizing, risk management, and order logic
    """
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.engine = VirtualTradingEngine(db, user_id)
    
    def execute_signal(self, signal: Signal, current_price: Decimal, 
                      auto_execute: bool = False) -> Dict[str, Any]:
        """
        Convert signal to trade order
        
        Args:
            signal: Signal object
            current_price: Current market price
            auto_execute: If True, execute immediately. If False, return suggestion
        """
        
        # Only trade Tier 1 and 2 signals initially (MVP conservative)
        if signal.tier > 2:
            return {'executed': False, 'reason': 'Low tier signal (tier > 2)'}
        
        # Position sizing: Risk 2% of portfolio per position
        portfolio_value = self.engine.portfolio.total_value
        max_position_risk = portfolio_value * Decimal('0.02')
        
        # For buy signals: position size = 2% of portfolio / current price
        shares_to_buy = int(max_position_risk / current_price)
        
        if shares_to_buy <= 0:
            return {'executed': False, 'reason': 'Insufficient capital for position'}
        
        if signal.signal_type == 'BUY':
            if not auto_execute:
                return {
                    'executed': False,
                    'suggestion': 'BUY',
                    'symbol': signal.symbol,
                    'shares': shares_to_buy,
                    'price': float(current_price),
                    'signal_id': signal.id
                }
            
            result = self.engine.buy(
                symbol=signal.symbol,
                shares=shares_to_buy,
                price=current_price,
                signal_id=signal.id,
                notes=f"Auto-triggered by Tier {signal.tier} signal"
            )
            return {'executed': result['success'], 'order': result}
        
        elif signal.signal_type == 'SELL':
            # For sells: liquidate position or partial exit
            positions = self.engine.portfolio.positions or {}
            if signal.symbol not in positions:
                return {'executed': False, 'reason': f'No position in {signal.symbol}'}
            
            shares_to_sell = min(
                positions[signal.symbol]['shares'],
                int(max_position_risk / current_price)
            )
            
            if not auto_execute:
                return {
                    'executed': False,
                    'suggestion': 'SELL',
                    'symbol': signal.symbol,
                    'shares': shares_to_sell,
                    'price': float(current_price),
                    'signal_id': signal.id
                }
            
            result = self.engine.sell(
                symbol=signal.symbol,
                shares=shares_to_sell,
                price=current_price,
                signal_id=signal.id,
                notes=f"Auto-triggered by Tier {signal.tier} signal"
            )
            return {'executed': result['success'], 'order': result}
        
        return {'executed': False, 'reason': 'Unknown signal type'}

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    from models import SessionLocal
    from decimal import Decimal
    
    db = SessionLocal()
    
    # Create engine for user 1
    engine = VirtualTradingEngine(db, user_id=1)
    
    # Simulate some trades
    print("=== VIRTUAL TRADING DEMO ===\n")
    
    # BUY NVDA
    result = engine.buy('NVDA', 10, Decimal('875.50'))
    print(f"BUY NVDA: {result['message']}")
    print(f"Portfolio: ${result['portfolio_value']}\n")
    
    # Update price
    engine.update_positions_price({'NVDA': Decimal('900.00')})
    print(f"Updated NVDA to $900")
    status = engine.get_portfolio_status()
    print(f"Portfolio Value: ${status['total_value']} ({status['total_return_pct']:.2f}%)\n")
    
    # SELL partial position
    result = engine.sell('NVDA', 5, Decimal('900.00'))
    print(f"SELL 5x NVDA: {result['message']}")
    print(f"P&L: ${result['profit_loss']} ({result['profit_loss_pct']:.2f}%)\n")
    
    # Print portfolio
    status = engine.get_portfolio_status()
    print("=== FINAL PORTFOLIO ===")
    print(f"Total Value: ${status['total_value']}")
    print(f"Cash: ${status['cash_balance']}")
    print(f"Return: {status['total_return_pct']:.2f}%")
    print(f"Positions: {status['positions']}")
    
    db.close()
