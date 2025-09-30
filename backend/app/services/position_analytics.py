"""
持仓分析服务
提供详细的持仓计算和盈亏分析功能
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from .. import models, crud
from ..database import SessionLocal
from .market_data import MarketDataService, get_market_service
from .cache import CacheService, get_cache_service

logger = logging.getLogger(__name__)


class PositionAnalytics:
    """持仓分析服务类"""
    
    def __init__(self):
        self.market_service = None
        self.cache_service = None
    
    async def _initialize_services(self):
        """初始化服务依赖"""
        if self.market_service is None:
            self.market_service = await get_market_service()
        if self.cache_service is None:
            self.cache_service = await get_cache_service()
    
    async def analyze_portfolio_positions(
        self, 
        user_id: int, 
        portfolio_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        分析投资组合持仓
        
        Args:
            user_id: 用户ID
            portfolio_id: 投资组合ID，为None时分析所有投资组合
            
        Returns:
            持仓分析结果
        """
        await self._initialize_services()
        
        try:
            db = SessionLocal()
            
            try:
                # 获取用户的投资组合
                if portfolio_id:
                    portfolios = [crud.get_portfolio(db, portfolio_id)]
                    if not portfolios[0] or portfolios[0].user_id != user_id:
                        return {"error": "投资组合不存在或权限不足"}
                else:
                    portfolios = crud.get_user_portfolios(db, user_id=user_id)
                
                if not portfolios:
                    return {"error": "未找到投资组合"}
                
                # 分析结果
                analysis_result = {
                    "portfolio_count": len(portfolios),
                    "total_market_value": 0,
                    "total_cash": 0,
                    "total_cost_basis": 0,
                    "total_unrealized_pnl": 0,
                    "total_realized_pnl": 0,
                    "portfolios": []
                }
                
                for portfolio in portfolios:
                    portfolio_analysis = await self._analyze_single_portfolio(db, portfolio)
                    analysis_result["portfolios"].append(portfolio_analysis)
                    
                    # 累计统计
                    analysis_result["total_market_value"] += portfolio_analysis["total_market_value"]
                    analysis_result["total_cash"] += portfolio_analysis["cash_balance"]
                    analysis_result["total_cost_basis"] += portfolio_analysis["total_cost_basis"]
                    analysis_result["total_unrealized_pnl"] += portfolio_analysis["total_unrealized_pnl"]
                
                # 计算已实现盈亏（从交易记录中）
                realized_pnl = self._calculate_realized_pnl(db, user_id)
                analysis_result["total_realized_pnl"] = realized_pnl
                
                # 计算总盈亏
                analysis_result["total_pnl"] = (
                    analysis_result["total_unrealized_pnl"] + 
                    analysis_result["total_realized_pnl"]
                )
                
                # 计算总收益率
                if analysis_result["total_cost_basis"] > 0:
                    analysis_result["total_return_rate"] = (
                        analysis_result["total_pnl"] / analysis_result["total_cost_basis"]
                    ) * 100
                else:
                    analysis_result["total_return_rate"] = 0
                
                # 计算资产配置
                analysis_result["asset_allocation"] = self._calculate_asset_allocation(
                    analysis_result["portfolios"]
                )
                
                return analysis_result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"持仓分析失败: {e}")
            return {"error": f"持仓分析失败: {str(e)}"}
    
    async def _analyze_single_portfolio(
        self, 
        db: Session, 
        portfolio: models.Portfolio
    ) -> Dict[str, Any]:
        """分析单个投资组合"""
        # 获取投资组合的所有资产
        assets = db.query(models.PortfolioAsset).filter(
            models.PortfolioAsset.portfolio_id == portfolio.id
        ).all()
        
        portfolio_analysis = {
            "portfolio_id": portfolio.id,
            "portfolio_name": portfolio.name,
            "cash_balance": portfolio.cash_balance,
            "total_market_value": 0,
            "total_cost_basis": 0,
            "total_unrealized_pnl": 0,
            "positions": []
        }
        
        # 获取所有资产的当前价格
        symbols = [asset.symbol for asset in assets]
        if symbols:
            current_prices = await self.market_service.get_multiple_prices(symbols)
        else:
            current_prices = {}
        
        for asset in assets:
            # 获取当前价格
            current_price = current_prices.get(asset.symbol, asset.average_price)
            
            # 计算持仓价值
            market_value = asset.quantity * current_price
            cost_basis = asset.quantity * asset.average_price
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_percent = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            position_analysis = {
                "symbol": asset.symbol,
                "quantity": asset.quantity,
                "average_price": asset.average_price,
                "current_price": current_price,
                "cost_basis": cost_basis,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_percent": unrealized_pnl_percent,
                "weight": 0,  # 稍后计算
                "last_updated": asset.updated_at
            }
            
            portfolio_analysis["positions"].append(position_analysis)
            portfolio_analysis["total_market_value"] += market_value
            portfolio_analysis["total_cost_basis"] += cost_basis
            portfolio_analysis["total_unrealized_pnl"] += unrealized_pnl
        
        # 计算各持仓权重
        total_value = portfolio_analysis["total_market_value"] + portfolio.cash_balance
        for position in portfolio_analysis["positions"]:
            if total_value > 0:
                position["weight"] = (position["market_value"] / total_value) * 100
            else:
                position["weight"] = 0
        
        # 添加现金权重
        portfolio_analysis["cash_weight"] = (
            (portfolio.cash_balance / total_value) * 100 if total_value > 0 else 100
        )
        
        return portfolio_analysis
    
    def _calculate_realized_pnl(self, db: Session, user_id: int) -> float:
        """计算已实现盈亏"""
        # 获取已执行的卖出交易
        sell_trades = db.query(models.Trade).filter(
            models.Trade.user_id == user_id,
            models.Trade.order_type == "sell",
            models.Trade.status == "executed",
            models.Trade.profit_loss.isnot(None)
        ).all()
        
        realized_pnl = sum(trade.profit_loss for trade in sell_trades)
        return realized_pnl
    
    def _calculate_asset_allocation(self, portfolios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算资产配置"""
        total_value = 0
        symbol_values = {}
        total_cash = 0
        
        for portfolio in portfolios:
            total_cash += portfolio["cash_balance"]
            for position in portfolio["positions"]:
                symbol = position["symbol"]
                value = position["market_value"]
                total_value += value
                
                if symbol in symbol_values:
                    symbol_values[symbol] += value
                else:
                    symbol_values[symbol] = value
        
        total_value += total_cash
        
        # 计算各资产占比
        allocations = []
        for symbol, value in symbol_values.items():
            allocations.append({
                "symbol": symbol,
                "value": value,
                "percentage": (value / total_value * 100) if total_value > 0 else 0
            })
        
        # 按价值排序
        allocations.sort(key=lambda x: x["value"], reverse=True)
        
        return {
            "total_value": total_value,
            "cash_percentage": (total_cash / total_value * 100) if total_value > 0 else 100,
            "asset_allocations": allocations[:10]  # 返回前10大持仓
        }
    
    async def analyze_position_performance(
        self, 
        user_id: int, 
        symbol: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        分析特定股票的持仓表现
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            days: 分析天数
            
        Returns:
            持仓表现分析
        """
        await self._initialize_services()
        
        try:
            db = SessionLocal()
            
            try:
                # 获取用户在该股票上的所有持仓
                assets = db.query(models.PortfolioAsset).join(
                    models.Portfolio
                ).filter(
                    models.Portfolio.user_id == user_id,
                    models.PortfolioAsset.symbol == symbol.upper()
                ).all()
                
                if not assets:
                    return {"error": f"未找到 {symbol} 的持仓"}
                
                # 获取该股票的交易历史
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                trades = db.query(models.Trade).filter(
                    models.Trade.user_id == user_id,
                    models.Trade.symbol == symbol.upper(),
                    models.Trade.created_at >= start_date,
                    models.Trade.status == "executed"
                ).order_by(models.Trade.executed_at).all()
                
                # 获取当前价格
                current_price = await self.market_service.get_real_time_price(symbol.upper())
                if not current_price:
                    current_price = assets[0].average_price
                
                # 计算总持仓
                total_quantity = sum(asset.quantity for asset in assets)
                total_cost_basis = sum(asset.quantity * asset.average_price for asset in assets)
                avg_cost = total_cost_basis / total_quantity if total_quantity > 0 else 0
                
                # 计算当前价值和盈亏
                current_value = total_quantity * current_price
                unrealized_pnl = current_value - total_cost_basis
                unrealized_pnl_percent = (unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
                
                # 计算已实现盈亏
                realized_pnl = sum(
                    trade.profit_loss or 0 
                    for trade in trades 
                    if trade.order_type == "sell"
                )
                
                # 计算交易统计
                buy_trades = [t for t in trades if t.order_type == "buy"]
                sell_trades = [t for t in trades if t.order_type == "sell"]
                
                total_bought = sum(t.quantity for t in buy_trades)
                total_sold = sum(t.quantity for t in sell_trades)
                
                analysis = {
                    "symbol": symbol.upper(),
                    "analysis_period_days": days,
                    "current_price": current_price,
                    "position_summary": {
                        "total_quantity": total_quantity,
                        "average_cost": avg_cost,
                        "total_cost_basis": total_cost_basis,
                        "current_value": current_value,
                        "unrealized_pnl": unrealized_pnl,
                        "unrealized_pnl_percent": unrealized_pnl_percent
                    },
                    "realized_pnl": realized_pnl,
                    "total_pnl": unrealized_pnl + realized_pnl,
                    "trading_summary": {
                        "total_trades": len(trades),
                        "buy_trades": len(buy_trades),
                        "sell_trades": len(sell_trades),
                        "total_bought": total_bought,
                        "total_sold": total_sold,
                        "net_position_change": total_bought - total_sold
                    },
                    "trade_history": [
                        {
                            "date": trade.executed_at,
                            "type": trade.order_type,
                            "quantity": trade.quantity,
                            "price": trade.price,
                            "value": trade.quantity * trade.price,
                            "profit_loss": trade.profit_loss
                        }
                        for trade in trades[-20:]  # 最近20笔交易
                    ]
                }
                
                return analysis
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"持仓表现分析失败: {e}")
            return {"error": f"持仓表现分析失败: {str(e)}"}
    
    async def get_portfolio_risk_metrics(self, user_id: int) -> Dict[str, Any]:
        """
        计算投资组合风险指标
        
        Args:
            user_id: 用户ID
            
        Returns:
            风险指标分析
        """
        await self._initialize_services()
        
        try:
            db = SessionLocal()
            
            try:
                # 获取用户所有投资组合
                portfolios = crud.get_user_portfolios(db, user_id=user_id)
                if not portfolios:
                    return {"error": "未找到投资组合"}
                
                # 计算总资产价值
                total_value = 0
                positions = []
                
                for portfolio in portfolios:
                    assets = db.query(models.PortfolioAsset).filter(
                        models.PortfolioAsset.portfolio_id == portfolio.id
                    ).all()
                    
                    for asset in assets:
                        current_price = await self.market_service.get_real_time_price(asset.symbol)
                        if current_price:
                            market_value = asset.quantity * current_price
                            total_value += market_value
                            positions.append({
                                "symbol": asset.symbol,
                                "value": market_value,
                                "quantity": asset.quantity,
                                "price": current_price
                            })
                
                # 计算集中度风险
                concentration_risk = self._calculate_concentration_risk(positions, total_value)
                
                # 计算流动性风险（基于持仓规模）
                liquidity_risk = self._calculate_liquidity_risk(positions)
                
                # 计算行业集中度（简化版，基于股票代码）
                sector_concentration = self._calculate_sector_concentration(positions, total_value)
                
                # 获取最近30天的交易记录计算波动率
                volatility_metrics = self._calculate_volatility_metrics(db, user_id)
                
                risk_metrics = {
                    "total_portfolio_value": total_value,
                    "position_count": len(positions),
                    "concentration_risk": concentration_risk,
                    "liquidity_risk": liquidity_risk,
                    "sector_concentration": sector_concentration,
                    "volatility_metrics": volatility_metrics,
                    "risk_assessment": self._assess_overall_risk(
                        concentration_risk, liquidity_risk, volatility_metrics
                    )
                }
                
                return risk_metrics
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"风险指标计算失败: {e}")
            return {"error": f"风险指标计算失败: {str(e)}"}
    
    def _calculate_concentration_risk(self, positions: List[Dict], total_value: float) -> Dict[str, Any]:
        """计算集中度风险"""
        if total_value == 0:
            return {"max_position_weight": 0, "top_5_weight": 0, "hhi_index": 0}
        
        # 计算各持仓权重
        weights = [(pos["value"] / total_value) for pos in positions]
        weights.sort(reverse=True)
        
        # 最大持仓权重
        max_weight = weights[0] if weights else 0
        
        # 前5大持仓权重
        top_5_weight = sum(weights[:5])
        
        # HHI指数（赫芬达尔-赫希曼指数）
        hhi_index = sum(w * w for w in weights) * 10000  # 转换为0-10000尺度
        
        return {
            "max_position_weight": max_weight * 100,
            "top_5_weight": top_5_weight * 100,
            "hhi_index": hhi_index,
            "risk_level": "高" if max_weight > 0.3 else "中" if max_weight > 0.15 else "低"
        }
    
    def _calculate_liquidity_risk(self, positions: List[Dict]) -> Dict[str, Any]:
        """计算流动性风险（简化版）"""
        large_positions = [pos for pos in positions if pos["value"] > 10000]  # 大于1万美元的持仓
        
        return {
            "large_position_count": len(large_positions),
            "large_position_value": sum(pos["value"] for pos in large_positions),
            "risk_level": "高" if len(large_positions) > 10 else "中" if len(large_positions) > 5 else "低"
        }
    
    def _calculate_sector_concentration(self, positions: List[Dict], total_value: float) -> Dict[str, Any]:
        """计算行业集中度（简化版，基于股票代码分类）"""
        # 简化的行业分类
        tech_stocks = ["AAPL", "GOOGL", "MSFT", "NVDA", "META", "NFLX"]
        auto_stocks = ["TSLA", "F", "GM"]
        finance_stocks = ["JPM", "BAC", "WFC", "GS"]
        
        tech_value = sum(pos["value"] for pos in positions if pos["symbol"] in tech_stocks)
        auto_value = sum(pos["value"] for pos in positions if pos["symbol"] in auto_stocks)
        finance_value = sum(pos["value"] for pos in positions if pos["symbol"] in finance_stocks)
        other_value = total_value - tech_value - auto_value - finance_value
        
        sectors = [
            {"name": "科技", "value": tech_value, "percentage": tech_value / total_value * 100 if total_value > 0 else 0},
            {"name": "汽车", "value": auto_value, "percentage": auto_value / total_value * 100 if total_value > 0 else 0},
            {"name": "金融", "value": finance_value, "percentage": finance_value / total_value * 100 if total_value > 0 else 0},
            {"name": "其他", "value": other_value, "percentage": other_value / total_value * 100 if total_value > 0 else 0}
        ]
        
        max_sector_weight = max(s["percentage"] for s in sectors)
        
        return {
            "sectors": sectors,
            "max_sector_weight": max_sector_weight,
            "risk_level": "高" if max_sector_weight > 60 else "中" if max_sector_weight > 40 else "低"
        }
    
    def _calculate_volatility_metrics(self, db: Session, user_id: int) -> Dict[str, Any]:
        """计算波动率指标"""
        # 获取最近30天的每日盈亏
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        trades = db.query(models.Trade).filter(
            models.Trade.user_id == user_id,
            models.Trade.executed_at >= start_date,
            models.Trade.status == "executed",
            models.Trade.profit_loss.isnot(None)
        ).all()
        
        if not trades:
            return {"daily_pnl_std": 0, "max_daily_loss": 0, "max_daily_gain": 0}
        
        daily_pnls = [trade.profit_loss for trade in trades]
        
        # 计算标准差（简化版）
        mean_pnl = sum(daily_pnls) / len(daily_pnls)
        variance = sum((pnl - mean_pnl) ** 2 for pnl in daily_pnls) / len(daily_pnls)
        std_pnl = variance ** 0.5
        
        return {
            "daily_pnl_std": std_pnl,
            "max_daily_loss": min(daily_pnls),
            "max_daily_gain": max(daily_pnls),
            "trade_count": len(trades)
        }
    
    def _assess_overall_risk(self, concentration_risk: Dict, liquidity_risk: Dict, volatility_metrics: Dict) -> str:
        """评估总体风险等级"""
        risk_factors = [
            concentration_risk.get("risk_level", "低"),
            liquidity_risk.get("risk_level", "低")
        ]
        
        high_risk_count = risk_factors.count("高")
        medium_risk_count = risk_factors.count("中")
        
        if high_risk_count >= 2:
            return "高风险"
        elif high_risk_count >= 1 or medium_risk_count >= 2:
            return "中风险"
        else:
            return "低风险"


# 全局持仓分析服务实例
position_analytics = PositionAnalytics()


async def get_position_analytics() -> PositionAnalytics:
    """获取持仓分析服务实例"""
    return position_analytics