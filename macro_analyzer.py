"""
Macro Analysis - Fed Rates, Inflation, Economic Context
"""

from datetime import datetime

class MacroAnalyzer:
    """Analyze macroeconomic context"""
    
    def __init__(self):
        pass
    
    def get_current_fed_rate(self) -> dict:
        """Get current Fed funds rate"""
        # Hardcoded current data (Phase 2: fetch real data)
        return {
            'rate': 4.75,
            'range': "4.50% - 4.75%",
            'last_change': datetime(2025, 12, 18),
            'direction': 'NEUTRAL',
            'outlook': 'UNCERTAIN'
        }
    
    def get_inflation_data(self) -> dict:
        """Get CPI and inflation metrics"""
        return {
            'cpi_yoy': 3.2,  # Year-over-year
            'cpi_mom': 0.2,  # Month-over-month
            'pce_inflation': 2.8,
            'trend': 'COOLING',
            'target': 2.0
        }
    
    def get_sector_rotation_context(self) -> dict:
        """Sector rotation opportunities"""
        return {
            'growth_favored': True,
            'defensive_favored': False,
            'energy_outlook': 'MIXED',
            'tech_outlook': 'STRONG',
            'defense_outlook': 'STRONG',
            'ai_outlook': 'VERY_STRONG'
        }
    
    def get_market_breadth(self) -> dict:
        """Market breadth indicators"""
        return {
            'advance_decline_ratio': 1.8,
            'new_highs': 452,
            'new_lows': 28,
            'breadth_trend': 'POSITIVE',
            'health': 'STRONG'
        }
    
    def get_macro_summary(self) -> dict:
        """Complete macro context"""
        fed = self.get_current_fed_rate()
        inflation = self.get_inflation_data()
        rotation = self.get_sector_rotation_context()
        breadth = self.get_market_breadth()
        
        # Macro score for signal boosting
        macro_score = 50
        
        if fed['direction'] == 'CUT':
            macro_score += 10
        elif fed['direction'] == 'HIKE':
            macro_score -= 10
        
        if inflation['trend'] == 'COOLING':
            macro_score += 5
        elif inflation['trend'] == 'RISING':
            macro_score -= 5
        
        if breadth['breadth_trend'] == 'POSITIVE':
            macro_score += 15
        elif breadth['breadth_trend'] == 'NEGATIVE':
            macro_score -= 15
        
        return {
            'fed_rate': fed,
            'inflation': inflation,
            'sector_rotation': rotation,
            'market_breadth': breadth,
            'macro_score': max(0, min(100, macro_score)),
            'market_environment': 'FAVORABLE' if macro_score > 60 else 'NEUTRAL' if macro_score > 40 else 'CHALLENGING'
        }
    
    def get_sector_boost(self, sector: str) -> float:
        """Get macro boost for specific sector"""
        rotation = self.get_sector_rotation_context()
        
        sector_boost = {
            'AI': 15 if rotation['ai_outlook'] == 'VERY_STRONG' else 8,
            'DEFENSE': 10 if rotation['defense_outlook'] == 'STRONG' else 5,
            'AEROSPACE': 8 if rotation['defense_outlook'] == 'STRONG' else 3,
            'ENERGY': 5 if rotation['energy_outlook'] == 'STRONG' else -5,
            'NUCLEAR': 5,
        }
        
        return sector_boost.get(sector, 0)

def get_macro_signal_boost(analyzer, sector: str) -> float:
    """Get macro-based signal boost"""
    summary = analyzer.get_macro_summary()
    base_boost = analyzer.get_sector_boost(sector)
    
    if summary['market_environment'] == 'FAVORABLE':
        base_boost += 5
    elif summary['market_environment'] == 'CHALLENGING':
        base_boost -= 5
    
    return base_boost