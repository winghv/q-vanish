"""
风险管理服务
提供全面的投资组合风险控制和监控功能
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import numpy as np

from .. import models, crud
from ..database import SessionLocal
from .market_data import MarketDataService, get_market_service

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskLimit:
    """风险限制配置"""
    name: str
    value: float
    max_value: float
    warning_threshold: float  # 警告阈值（相对于最大值的比例）
    description: str


@dataclass
class RiskAlert:
    """风险警报"""
    risk_type: str
    level: RiskLevel
    message: str
    current_value: float
    limit_value: float
    timestamp: datetime
    portfolio_id: Optional[int] = None
    symbol: Optional[str] = None


class RiskManager:
    """风险管理器"""
    
    def __init__(self):
        """初始化风险管理器"""
        self.market_service: Optional[MarketDataService] = None
        
        # 默认风险限制配置
        self.default_risk_limits = {
            "max_portfolio_loss": RiskLimit(
                name="max_portfolio_loss",
                value=0.0,
                max_value=0.20,  # 最大20%损失
                warning_threshold=0.8,  # 16%时警告
                description="投资组合最大损失限制"
            ),
            "max_position_concentration": RiskLimit(
                name="max_position_concentration",
                value=0.0,
                max_value=0.30,  # 单个股票最大30%
                warning_threshold=0.8,  # 24%时警告
                description="单个股票最大持仓比例"
            ),
            "max_sector_concentration": RiskLimit(
                name="max_sector_concentration",
                value=0.0,
                max_value=0.40,  # 单个行业最大40%
                warning_threshold=0.8,  # 32%时警告
                description="单个行业最大持仓比例"
            ),
            "min_cash_ratio": RiskLimit(
                name="min_cash_ratio",
                value=1.0,
                max_value=1.0,
                warning_threshold=0.15,  # 15%时警告
                description="最小现金比例"
            ),
            "max_daily_trades": RiskLimit(
                name="max_daily_trades",
                value=0,
                max_value=20,  # 每日最多20笔交易
                warning_threshold=0.8,  # 16笔时警告
                description="日交易次数限制"
            ),
            "max_leverage": RiskLimit(
                name="max_leverage",
                value=1.0,
                max_value=3.0,  # 最大3倍杠杆
                warning_threshold=0.8,  # 2.4倍时警告
                description="最大杠杆比例"
            )
        }
        
        logger.info("Risk manager initialized")
    
    async def _initialize_services(self):
        """初始化依赖服务"""
        if self.market_service is None:
            self.market_service = await get_market_service()
    
    async def assess_portfolio_risk(
        self, 
        user_id: int, 
        portfolio_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        评估投资组合风险
        
        Args:
            user_id: 用户ID
            portfolio_id: 投资组合ID，为None时评估所有投资组合
            
        Returns:
            风险评估结果
        """
        await self._initialize_services()
        
        try:
            db = SessionLocal()
            
            try:
                # 获取投资组合
                if portfolio_id:
                    portfolios = [crud.get_portfolio(db, portfolio_id)]
                    if not portfolios[0] or portfolios[0].user_id != user_id:
                        return {"error": "投资组合不存在或权限不足"}
                else:
                    portfolios = crud.get_user_portfolios(db, user_id=user_id)
                
                if not portfolios:
                    return {"error": "未找到投资组合"}
                
                # 综合风险评估
                overall_assessment = {
                    "user_id": user_id,
                    "assessment_time": datetime.utcnow(),
                    "portfolios": [],
                    "overall_risk_score": 0.0,
                    "risk_level": RiskLevel.LOW,
                    "alerts": [],
                    "recommendations": []
                }
                
                total_value = 0
                total_risk_scores = []
                
                for portfolio in portfolios:
                    portfolio_assessment = await self._assess_single_portfolio(db, portfolio)
                    overall_assessment["portfolios"].append(portfolio_assessment)
                    
                    total_value += portfolio_assessment["total_value"]
                    total_risk_scores.append(portfolio_assessment["risk_score"])
                    overall_assessment["alerts"].extend(portfolio_assessment["alerts"])
                
                # 计算综合风险评分
                if total_risk_scores:
                    overall_assessment["overall_risk_score"] = np.mean(total_risk_scores)
                    overall_assessment["risk_level"] = self._calculate_risk_level(
                        overall_assessment["overall_risk_score"]
                    )
                
                # 生成风险管理建议
                overall_assessment["recommendations"] = self._generate_recommendations(
                    overall_assessment
                )
                
            finally:
                db.close()
            
            return overall_assessment
            
        except Exception as e:
            logger.error(f"Portfolio risk assessment failed: {e}")
            return {"error": f"风险评估失败: {str(e)}"}
    
    async def _assess_single_portfolio(
        self, 
        db, 
        portfolio: models.Portfolio
    ) -> Dict[str, Any]:
        """评估单个投资组合的风险"""
        assessment = {
            "portfolio_id": portfolio.id,
            "portfolio_name": portfolio.name,
            "total_value": portfolio.total_value + portfolio.cash_balance,
            "cash_balance": portfolio.cash_balance,
            "cash_ratio": 0.0,
            "risk_score": 0.0,
            "risk_level": RiskLevel.LOW,
            "alerts": [],
            "metrics": {},
            "positions": []
        }
        
        try:
            # 获取持仓
            assets = crud.get_portfolio_assets(db, portfolio.id)
            total_value = assessment["total_value"]
            
            if total_value > 0:
                assessment["cash_ratio"] = portfolio.cash_balance / total_value
            
            # 分析每个持仓
            position_risks = []
            concentration_risks = {}
            
            for asset in assets:
                position_analysis = await self._analyze_position_risk(asset, total_value)
                assessment["positions"].append(position_analysis)
                position_risks.append(position_analysis["risk_score"])
                
                # 集中度风险分析
                symbol = asset.symbol
                weight = position_analysis["weight"]
                
                if weight > self.default_risk_limits["max_position_concentration"].max_value:
                    assessment["alerts"].append(RiskAlert(
                        risk_type="position_concentration",
                        level=RiskLevel.HIGH,
                        message=f"股票 {symbol} 持仓比例过高: {weight:.1%}",
                        current_value=weight,
                        limit_value=self.default_risk_limits["max_position_concentration"].max_value,
                        timestamp=datetime.utcnow(),
                        portfolio_id=portfolio.id,
                        symbol=symbol
                    ))
            
            # 计算投资组合级别风险指标
            portfolio_metrics = await self._calculate_portfolio_metrics(portfolio, assets)
            assessment["metrics"] = portfolio_metrics
            
            # 现金比例检查
            min_cash_limit = self.default_risk_limits["min_cash_ratio"].warning_threshold
            if assessment["cash_ratio"] < min_cash_limit:
                assessment["alerts"].append(RiskAlert(
                    risk_type="low_cash",
                    level=RiskLevel.MEDIUM,
                    message=f"现金比例过低: {assessment['cash_ratio']:.1%}",
                    current_value=assessment["cash_ratio"],
                    limit_value=min_cash_limit,
                    timestamp=datetime.utcnow(),
                    portfolio_id=portfolio.id
                ))
            
            # 计算综合风险评分
            if position_risks:
                base_risk = np.mean(position_risks)
                concentration_penalty = max(0, len([p for p in assessment["positions"] 
                                                  if p["weight"] > 0.20]) * 0.1)
                cash_penalty = max(0, (min_cash_limit - assessment["cash_ratio"]) * 0.5)
                
                assessment["risk_score"] = min(1.0, base_risk + concentration_penalty + cash_penalty)
            
            assessment["risk_level"] = self._calculate_risk_level(assessment["risk_score"])
            
        except Exception as e:
            logger.error(f"Single portfolio assessment failed: {e}")
            assessment["error"] = str(e)
        
        return assessment
    
    async def _analyze_position_risk(
        self, 
        asset: models.PortfolioAsset, 
        total_portfolio_value: float
    ) -> Dict[str, Any]:
        """分析单个持仓的风险"""
        position_analysis = {
            "symbol": asset.symbol,
            "quantity": asset.quantity,
            "market_value": asset.market_value or 0,
            "weight": 0.0,
            "unrealized_pnl": asset.profit_loss or 0,
            "unrealized_pnl_percent": asset.profit_loss_percentage or 0,
            "risk_score": 0.0,
            "volatility": 0.0,
            "beta": 0.0,
            "var_1d": 0.0  # 1日风险价值
        }
        
        try:
            if total_portfolio_value > 0:
                position_analysis["weight"] = position_analysis["market_value"] / total_portfolio_value
            
            # 获取历史数据计算波动率
            volatility_data = await self._calculate_volatility(asset.symbol)
            position_analysis["volatility"] = volatility_data.get("volatility", 0.0)
            position_analysis["beta"] = volatility_data.get("beta", 1.0)
            
            # 计算1日风险价值 (VaR)
            if position_analysis["volatility"] > 0:
                # 假设正态分布，95%置信度
                position_analysis["var_1d"] = (
                    position_analysis["market_value"] * 
                    position_analysis["volatility"] * 
                    1.645  # 95%置信度的Z值
                )
            
            # 计算持仓风险评分
            weight_risk = min(position_analysis["weight"] / 0.20, 1.0)  # 20%以上权重风险较高
            volatility_risk = min(position_analysis["volatility"] / 0.30, 1.0)  # 30%以上波动率风险较高
            pnl_risk = 0
            
            if position_analysis["unrealized_pnl_percent"] < -10:  # 亏损超过10%
                pnl_risk = min(abs(position_analysis["unrealized_pnl_percent"]) / 20, 1.0)
            
            position_analysis["risk_score"] = (weight_risk * 0.4 + volatility_risk * 0.4 + pnl_risk * 0.2)
            
        except Exception as e:
            logger.error(f"Position risk analysis failed for {asset.symbol}: {e}")
        
        return position_analysis
    
    async def _calculate_volatility(self, symbol: str, days: int = 30) -> Dict[str, float]:
        """计算股票波动率和贝塔值"""
        try:
            # 获取历史价格数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # 多获取一些数据
            
            hist_data = await self.market_service.get_historical_data(
                symbol, 
                period=f"{days + 10}d"
            )
            
            if hist_data is None or len(hist_data) < 10:
                return {"volatility": 0.0, "beta": 1.0}
            
            # 计算日收益率
            prices = hist_data['Close'].values
            returns = np.diff(np.log(prices))
            
            # 计算年化波动率
            volatility = np.std(returns) * np.sqrt(252)  # 252个交易日
            
            # 简化的贝塔计算（相对于市场，这里用SPY代替）
            # 在实际应用中，应该获取SPY的数据进行计算
            beta = min(max(volatility / 0.15, 0.5), 2.0)  # 简化假设
            
            return {"volatility": volatility, "beta": beta}
            
        except Exception as e:
            logger.error(f"Volatility calculation failed for {symbol}: {e}")
            return {"volatility": 0.0, "beta": 1.0}
    
    async def _calculate_portfolio_metrics(
        self, 
        portfolio: models.Portfolio, 
        assets: List[models.PortfolioAsset]
    ) -> Dict[str, float]:
        """计算投资组合级别风险指标"""
        metrics = {
            "total_positions": len(assets),
            "portfolio_var_1d": 0.0,
            "portfolio_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "diversification_ratio": 0.0
        }
        
        try:
            if not assets:
                return metrics
            
            total_value = portfolio.total_value + portfolio.cash_balance
            
            # 计算投资组合波动率（简化版）
            weighted_volatilities = []
            for asset in assets:
                weight = (asset.market_value or 0) / total_value if total_value > 0 else 0
                vol_data = await self._calculate_volatility(asset.symbol)
                weighted_volatilities.append(weight * vol_data["volatility"])
            
            if weighted_volatilities:
                metrics["portfolio_volatility"] = sum(weighted_volatilities)
                metrics["portfolio_var_1d"] = total_value * metrics["portfolio_volatility"] * 1.645
            
            # 多样化比率（持仓数量的平方根倒数）
            if len(assets) > 0:
                metrics["diversification_ratio"] = 1.0 / math.sqrt(len(assets))
            
        except Exception as e:
            logger.error(f"Portfolio metrics calculation failed: {e}")
        
        return metrics
    
    def _calculate_risk_level(self, risk_score: float) -> RiskLevel:
        """根据风险评分计算风险等级"""
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendations(self, assessment: Dict[str, Any]) -> List[str]:
        """生成风险管理建议"""
        recommendations = []
        
        try:
            risk_level = assessment["risk_level"]
            overall_score = assessment["overall_risk_score"]
            
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                recommendations.append("建议减少高风险持仓，增加现金比例")
                recommendations.append("考虑设置止损订单来控制下行风险")
            
            # 分析集中度风险
            for portfolio in assessment["portfolios"]:
                high_weight_positions = [p for p in portfolio["positions"] if p["weight"] > 0.25]
                if high_weight_positions:
                    symbols = [p["symbol"] for p in high_weight_positions]
                    recommendations.append(f"建议分散持仓，减少对以下股票的依赖: {', '.join(symbols)}")
                
                if portfolio["cash_ratio"] < 0.1:
                    recommendations.append(f"投资组合 {portfolio['portfolio_name']} 现金比例过低，建议增加现金头寸")
            
            # 通用建议
            if overall_score > 0.5:
                recommendations.append("建议定期审查持仓，及时调整投资组合配置")
                recommendations.append("考虑使用期权等衍生品进行风险对冲")
            
            if not recommendations:
                recommendations.append("投资组合风险控制良好，继续保持当前配置")
        
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            recommendations.append("风险分析建议生成失败，请手动评估投资组合风险")
        
        return recommendations
    
    async def check_order_risk(
        self, 
        user_id: int,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        price: float,
        order_type: str
    ) -> Dict[str, Any]:
        """
        检查订单风险
        
        Args:
            user_id: 用户ID
            portfolio_id: 投资组合ID
            symbol: 股票代码
            quantity: 数量（正数买入，负数卖出）
            price: 价格
            order_type: 订单类型
            
        Returns:
            风险检查结果
        """
        try:
            db = SessionLocal()
            
            try:
                portfolio = crud.get_portfolio(db, portfolio_id)
                if not portfolio or portfolio.user_id != user_id:
                    return {"passed": False, "reason": "投资组合不存在或权限不足"}
                
                order_value = abs(quantity) * price
                total_value = portfolio.total_value + portfolio.cash_balance
                
                # 基础检查
                if quantity > 0:  # 买入
                    # 资金充足性
                    if portfolio.cash_balance < order_value:
                        return {"passed": False, "reason": "现金余额不足"}
                    
                    # 单笔订单金额限制
                    if order_value > total_value * 0.5:  # 不超过总价值的50%
                        return {"passed": False, "reason": "单笔订单金额过大"}
                    
                    # 持仓集中度检查
                    current_asset = db.query(models.PortfolioAsset).filter(
                        models.PortfolioAsset.portfolio_id == portfolio_id,
                        models.PortfolioAsset.symbol == symbol
                    ).first()
                    
                    current_value = (current_asset.market_value or 0) if current_asset else 0
                    new_total_value = current_value + order_value
                    new_weight = new_total_value / total_value if total_value > 0 else 0
                    
                    max_concentration = self.default_risk_limits["max_position_concentration"].max_value
                    if new_weight > max_concentration:
                        return {
                            "passed": False, 
                            "reason": f"持仓集中度超限 ({new_weight:.1%} > {max_concentration:.1%})"
                        }
                    
                    # 现金比例检查
                    remaining_cash = portfolio.cash_balance - order_value
                    remaining_cash_ratio = remaining_cash / total_value if total_value > 0 else 0
                    min_cash_ratio = self.default_risk_limits["min_cash_ratio"].warning_threshold
                    
                    if remaining_cash_ratio < min_cash_ratio:
                        return {
                            "passed": False,
                            "reason": f"执行后现金比例过低 ({remaining_cash_ratio:.1%} < {min_cash_ratio:.1%})"
                        }
                
                else:  # 卖出
                    # 持仓充足性
                    asset = db.query(models.PortfolioAsset).filter(
                        models.PortfolioAsset.portfolio_id == portfolio_id,
                        models.PortfolioAsset.symbol == symbol
                    ).first()
                    
                    if not asset or asset.quantity < abs(quantity):
                        return {"passed": False, "reason": "持仓数量不足"}
                
                return {"passed": True, "reason": "风险检查通过"}
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Order risk check failed: {e}")
            return {"passed": False, "reason": f"风险检查异常: {str(e)}"}
    
    async def get_risk_limits(self, user_id: int) -> Dict[str, Any]:
        """获取用户的风险限制配置"""
        # 返回默认风险限制，未来可以支持用户自定义
        return {
            "limits": {
                name: {
                    "name": limit.name,
                    "max_value": limit.max_value,
                    "warning_threshold": limit.warning_threshold,
                    "description": limit.description
                }
                for name, limit in self.default_risk_limits.items()
            }
        }
    
    async def update_risk_limits(
        self, 
        user_id: int, 
        limits: Dict[str, float]
    ) -> Dict[str, Any]:
        """更新用户的风险限制配置"""
        # 简化实现，实际应该保存到数据库
        updated_limits = {}
        
        for limit_name, new_value in limits.items():
            if limit_name in self.default_risk_limits:
                # 验证新值的合理性
                if 0 <= new_value <= 1.0:  # 大部分限制都是比例
                    updated_limits[limit_name] = new_value
                else:
                    logger.warning(f"Invalid risk limit value: {limit_name} = {new_value}")
        
        return {
            "updated_limits": updated_limits,
            "message": f"已更新 {len(updated_limits)} 个风险限制"
        }


# 全局风险管理器实例
risk_manager = RiskManager()


async def get_risk_manager() -> RiskManager:
    """获取风险管理器实例"""
    return risk_manager