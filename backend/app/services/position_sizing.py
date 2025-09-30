"""
动态持仓大小计算服务
基于风险管理原则计算最优持仓大小
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
import numpy as np

from .. import models, crud
from ..database import SessionLocal
from .market_data import MarketDataService, get_market_service
from .risk_management import RiskManager, get_risk_manager

logger = logging.getLogger(__name__)


class PositionSizingMethod(Enum):
    """持仓大小计算方法"""
    FIXED_AMOUNT = "fixed_amount"                # 固定金额
    FIXED_PERCENTAGE = "fixed_percentage"        # 固定百分比
    VOLATILITY_TARGET = "volatility_target"      # 波动率目标
    KELLY_CRITERION = "kelly_criterion"          # 凯利公式
    RISK_PARITY = "risk_parity"                  # 风险平价
    MAX_DRAWDOWN_TARGET = "max_drawdown_target"  # 最大回撤目标


class PositionSizer:
    """持仓大小计算器"""
    
    def __init__(self):
        """初始化持仓大小计算器"""
        self.market_service: Optional[MarketDataService] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # 默认参数配置
        self.default_params = {
            PositionSizingMethod.FIXED_AMOUNT: {
                "amount": 10000.0  # 每笔投资固定金额
            },
            PositionSizingMethod.FIXED_PERCENTAGE: {
                "percentage": 0.05  # 投资组合的5%
            },
            PositionSizingMethod.VOLATILITY_TARGET: {
                "target_volatility": 0.02,  # 目标日波动率2%
                "lookback_days": 30
            },
            PositionSizingMethod.KELLY_CRITERION: {
                "win_rate": 0.55,           # 胜率55%
                "avg_win": 0.08,            # 平均盈利8%
                "avg_loss": 0.05,           # 平均亏损5%
                "max_kelly_fraction": 0.25  # 凯利结果最大25%
            },
            PositionSizingMethod.RISK_PARITY: {
                "target_risk_contribution": 0.1,  # 目标风险贡献10%
                "lookback_days": 60
            },
            PositionSizingMethod.MAX_DRAWDOWN_TARGET: {
                "max_drawdown": 0.15,       # 最大回撤15%
                "confidence_level": 0.95,   # 95%置信度
                "lookback_days": 90
            }
        }
        
        logger.info("Position sizer initialized")
    
    async def _initialize_services(self):
        """初始化依赖服务"""
        if self.market_service is None:
            self.market_service = await get_market_service()
        if self.risk_manager is None:
            self.risk_manager = await get_risk_manager()
    
    async def calculate_position_size(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        entry_price: float,
        method: PositionSizingMethod = PositionSizingMethod.VOLATILITY_TARGET,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算建议的持仓大小
        
        Args:
            user_id: 用户ID
            portfolio_id: 投资组合ID
            symbol: 股票代码
            entry_price: 入场价格
            method: 持仓大小计算方法
            custom_params: 自定义参数
            
        Returns:
            持仓大小计算结果
        """
        await self._initialize_services()
        
        try:
            db = SessionLocal()
            
            try:
                # 获取投资组合信息
                portfolio = crud.get_portfolio(db, portfolio_id)
                if not portfolio or portfolio.user_id != user_id:
                    return {"error": "投资组合不存在或权限不足"}
                
                # 合并参数
                params = self.default_params.get(method, {}).copy()
                if custom_params:
                    params.update(custom_params)
                
                # 根据方法计算持仓大小
                if method == PositionSizingMethod.FIXED_AMOUNT:
                    result = await self._calculate_fixed_amount(
                        portfolio, symbol, entry_price, params
                    )
                elif method == PositionSizingMethod.FIXED_PERCENTAGE:
                    result = await self._calculate_fixed_percentage(
                        portfolio, symbol, entry_price, params
                    )
                elif method == PositionSizingMethod.VOLATILITY_TARGET:
                    result = await self._calculate_volatility_target(
                        portfolio, symbol, entry_price, params
                    )
                elif method == PositionSizingMethod.KELLY_CRITERION:
                    result = await self._calculate_kelly_criterion(
                        portfolio, symbol, entry_price, params
                    )
                elif method == PositionSizingMethod.RISK_PARITY:
                    result = await self._calculate_risk_parity(
                        portfolio, symbol, entry_price, params
                    )
                elif method == PositionSizingMethod.MAX_DRAWDOWN_TARGET:
                    result = await self._calculate_max_drawdown_target(
                        portfolio, symbol, entry_price, params
                    )
                else:
                    return {"error": f"不支持的持仓大小计算方法: {method.value}"}
                
                # 应用风险控制限制
                result = await self._apply_risk_constraints(
                    db, portfolio, symbol, result
                )
                
                # 添加执行建议
                result["execution_suggestion"] = self._generate_execution_suggestion(result)
                
                return result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Position size calculation failed: {e}")
            return {"error": f"持仓大小计算失败: {str(e)}"}
    
    async def _calculate_fixed_amount(
        self,
        portfolio: models.Portfolio,
        symbol: str,
        entry_price: float,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算固定金额的持仓大小"""
        target_amount = params["amount"]
        quantity = target_amount / entry_price
        
        return {
            "method": "fixed_amount",
            "suggested_quantity": quantity,
            "suggested_amount": target_amount,
            "entry_price": entry_price,
            "portfolio_weight": target_amount / (portfolio.total_value + portfolio.cash_balance),
            "rationale": f"固定投资金额: ${target_amount:,.2f}",
            "confidence": 1.0,
            "risk_level": "medium"
        }
    
    async def _calculate_fixed_percentage(
        self,
        portfolio: models.Portfolio,
        symbol: str,
        entry_price: float,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算固定百分比的持仓大小"""
        percentage = params["percentage"]
        total_value = portfolio.total_value + portfolio.cash_balance
        target_amount = total_value * percentage
        quantity = target_amount / entry_price
        
        return {
            "method": "fixed_percentage",
            "suggested_quantity": quantity,
            "suggested_amount": target_amount,
            "entry_price": entry_price,
            "portfolio_weight": percentage,
            "rationale": f"投资组合固定比例: {percentage:.1%}",
            "confidence": 1.0,
            "risk_level": "medium"
        }
    
    async def _calculate_volatility_target(
        self,
        portfolio: models.Portfolio,
        symbol: str,
        entry_price: float,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于波动率目标计算持仓大小"""
        target_volatility = params["target_volatility"]
        lookback_days = params["lookback_days"]
        
        try:
            # 获取历史波动率
            volatility_data = await self._get_volatility_data(symbol, lookback_days)
            stock_volatility = volatility_data["daily_volatility"]
            
            if stock_volatility <= 0:
                return {
                    "error": "无法获取有效的波动率数据",
                    "method": "volatility_target"
                }
            
            # 计算持仓权重：目标波动率 / 股票波动率
            position_weight = min(target_volatility / stock_volatility, 0.5)  # 最大50%
            
            total_value = portfolio.total_value + portfolio.cash_balance
            target_amount = total_value * position_weight
            quantity = target_amount / entry_price
            
            # 计算预期的投资组合波动率贡献
            portfolio_vol_contribution = position_weight * stock_volatility
            
            return {
                "method": "volatility_target",
                "suggested_quantity": quantity,
                "suggested_amount": target_amount,
                "entry_price": entry_price,
                "portfolio_weight": position_weight,
                "rationale": f"波动率目标: {target_volatility:.2%}, 股票波动率: {stock_volatility:.2%}",
                "confidence": volatility_data["confidence"],
                "risk_level": self._assess_risk_level(position_weight, stock_volatility),
                "metrics": {
                    "target_volatility": target_volatility,
                    "stock_volatility": stock_volatility,
                    "portfolio_vol_contribution": portfolio_vol_contribution,
                    "volatility_ratio": target_volatility / stock_volatility
                }
            }
            
        except Exception as e:
            logger.error(f"Volatility target calculation failed: {e}")
            return {"error": f"波动率目标计算失败: {str(e)}"}
    
    async def _calculate_kelly_criterion(
        self,
        portfolio: models.Portfolio,
        symbol: str,
        entry_price: float,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用凯利公式计算持仓大小"""
        win_rate = params["win_rate"]
        avg_win = params["avg_win"]
        avg_loss = params["avg_loss"]
        max_kelly_fraction = params["max_kelly_fraction"]
        
        try:
            # 凯利公式: f = (bp - q) / b
            # 其中 b = 平均盈利/平均亏损, p = 胜率, q = 败率
            b = avg_win / avg_loss if avg_loss > 0 else 1
            p = win_rate
            q = 1 - win_rate
            
            kelly_fraction = (b * p - q) / b if b > 0 else 0
            
            # 限制凯利结果
            kelly_fraction = max(0, min(kelly_fraction, max_kelly_fraction))
            
            total_value = portfolio.total_value + portfolio.cash_balance
            target_amount = total_value * kelly_fraction
            quantity = target_amount / entry_price
            
            # 计算预期收益
            expected_return = win_rate * avg_win - (1 - win_rate) * avg_loss
            
            return {
                "method": "kelly_criterion",
                "suggested_quantity": quantity,
                "suggested_amount": target_amount,
                "entry_price": entry_price,
                "portfolio_weight": kelly_fraction,
                "rationale": f"凯利公式计算: 胜率{win_rate:.1%}, 预期收益{expected_return:.2%}",
                "confidence": 0.7,  # 凯利公式基于历史统计，置信度中等
                "risk_level": self._assess_risk_level(kelly_fraction, 0.2),
                "metrics": {
                    "kelly_fraction": kelly_fraction,
                    "win_rate": win_rate,
                    "avg_win": avg_win,
                    "avg_loss": avg_loss,
                    "expected_return": expected_return,
                    "risk_reward_ratio": avg_win / avg_loss
                }
            }
            
        except Exception as e:
            logger.error(f"Kelly criterion calculation failed: {e}")
            return {"error": f"凯利公式计算失败: {str(e)}"}
    
    async def _calculate_risk_parity(
        self,
        portfolio: models.Portfolio,
        symbol: str,
        entry_price: float,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用风险平价方法计算持仓大小"""
        target_risk_contribution = params["target_risk_contribution"]
        lookback_days = params["lookback_days"]
        
        try:
            # 获取股票波动率
            volatility_data = await self._get_volatility_data(symbol, lookback_days)
            stock_volatility = volatility_data["daily_volatility"]
            
            if stock_volatility <= 0:
                return {"error": "无法获取有效的波动率数据"}
            
            # 风险平价：权重 = 目标风险贡献 / 波动率
            # 这里简化处理，实际应该考虑与其他持仓的相关性
            position_weight = min(target_risk_contribution / stock_volatility, 0.4)
            
            total_value = portfolio.total_value + portfolio.cash_balance
            target_amount = total_value * position_weight
            quantity = target_amount / entry_price
            
            # 计算风险贡献
            risk_contribution = position_weight * stock_volatility
            
            return {
                "method": "risk_parity",
                "suggested_quantity": quantity,
                "suggested_amount": target_amount,
                "entry_price": entry_price,
                "portfolio_weight": position_weight,
                "rationale": f"风险平价: 目标风险贡献{target_risk_contribution:.2%}",
                "confidence": 0.8,
                "risk_level": self._assess_risk_level(position_weight, stock_volatility),
                "metrics": {
                    "target_risk_contribution": target_risk_contribution,
                    "actual_risk_contribution": risk_contribution,
                    "stock_volatility": stock_volatility,
                    "risk_adjusted_weight": position_weight
                }
            }
            
        except Exception as e:
            logger.error(f"Risk parity calculation failed: {e}")
            return {"error": f"风险平价计算失败: {str(e)}"}
    
    async def _calculate_max_drawdown_target(
        self,
        portfolio: models.Portfolio,
        symbol: str,
        entry_price: float,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于最大回撤目标计算持仓大小"""
        max_drawdown = params["max_drawdown"]
        confidence_level = params["confidence_level"]
        lookback_days = params["lookback_days"]
        
        try:
            # 获取历史波动率和价格数据
            volatility_data = await self._get_volatility_data(symbol, lookback_days)
            stock_volatility = volatility_data["daily_volatility"]
            
            if stock_volatility <= 0:
                return {"error": "无法获取有效的波动率数据"}
            
            # 估算在给定置信度下的最大可能损失
            # 使用正态分布假设
            z_score = self._get_z_score(confidence_level)
            max_possible_loss = stock_volatility * z_score * math.sqrt(lookback_days / 252)
            
            # 计算持仓权重，使得最大可能损失不超过目标回撤
            if max_possible_loss > 0:
                position_weight = min(max_drawdown / max_possible_loss, 0.5)
            else:
                position_weight = 0.1  # 默认10%
            
            total_value = portfolio.total_value + portfolio.cash_balance
            target_amount = total_value * position_weight
            quantity = target_amount / entry_price
            
            # 计算预期的最大回撤
            expected_max_drawdown = position_weight * max_possible_loss
            
            return {
                "method": "max_drawdown_target",
                "suggested_quantity": quantity,
                "suggested_amount": target_amount,
                "entry_price": entry_price,
                "portfolio_weight": position_weight,
                "rationale": f"最大回撤目标: {max_drawdown:.1%}, 置信度: {confidence_level:.0%}",
                "confidence": 0.75,
                "risk_level": self._assess_risk_level(position_weight, stock_volatility),
                "metrics": {
                    "target_max_drawdown": max_drawdown,
                    "expected_max_drawdown": expected_max_drawdown,
                    "max_possible_loss": max_possible_loss,
                    "confidence_level": confidence_level,
                    "stock_volatility": stock_volatility
                }
            }
            
        except Exception as e:
            logger.error(f"Max drawdown target calculation failed: {e}")
            return {"error": f"最大回撤目标计算失败: {str(e)}"}
    
    async def _get_volatility_data(self, symbol: str, days: int) -> Dict[str, float]:
        """获取股票的波动率数据"""
        try:
            hist_data = await self.market_service.get_historical_data(
                symbol, 
                period=f"{days + 10}d"
            )
            
            if hist_data is None or len(hist_data) < 10:
                return {"daily_volatility": 0.0, "confidence": 0.0}
            
            # 计算日收益率
            prices = hist_data['Close'].values
            returns = np.diff(np.log(prices))
            
            # 计算日波动率
            daily_volatility = np.std(returns)
            
            # 置信度基于数据点数量
            confidence = min(len(returns) / 30, 1.0)  # 30天数据置信度为1
            
            return {
                "daily_volatility": daily_volatility,
                "annual_volatility": daily_volatility * np.sqrt(252),
                "confidence": confidence,
                "data_points": len(returns)
            }
            
        except Exception as e:
            logger.error(f"Volatility data retrieval failed for {symbol}: {e}")
            return {"daily_volatility": 0.0, "confidence": 0.0}
    
    def _get_z_score(self, confidence_level: float) -> float:
        """获取给定置信度的Z分数"""
        z_scores = {
            0.90: 1.282,
            0.95: 1.645,
            0.99: 2.326
        }
        
        # 找到最接近的置信度
        closest_level = min(z_scores.keys(), key=lambda x: abs(x - confidence_level))
        return z_scores[closest_level]
    
    def _assess_risk_level(self, position_weight: float, volatility: float) -> str:
        """评估风险等级"""
        risk_score = position_weight * volatility
        
        if risk_score >= 0.1:
            return "high"
        elif risk_score >= 0.05:
            return "medium"
        else:
            return "low"
    
    async def _apply_risk_constraints(
        self,
        db,
        portfolio: models.Portfolio,
        symbol: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """应用风险控制约束"""
        if "error" in result:
            return result
        
        try:
            # 检查现金余额约束
            available_cash = portfolio.cash_balance
            suggested_amount = result["suggested_amount"]
            
            if suggested_amount > available_cash:
                # 调整到可用现金
                adjusted_amount = available_cash * 0.95  # 保留5%现金
                adjusted_quantity = adjusted_amount / result["entry_price"]
                
                result["suggested_amount"] = adjusted_amount
                result["suggested_quantity"] = adjusted_quantity
                result["portfolio_weight"] = adjusted_amount / (portfolio.total_value + portfolio.cash_balance)
                result["constraint_applied"] = "cash_limit"
                result["original_suggestion"] = suggested_amount
            
            # 检查持仓集中度约束
            max_position_weight = 0.3  # 最大30%持仓
            if result["portfolio_weight"] > max_position_weight:
                total_value = portfolio.total_value + portfolio.cash_balance
                adjusted_amount = total_value * max_position_weight
                adjusted_quantity = adjusted_amount / result["entry_price"]
                
                result["suggested_amount"] = adjusted_amount
                result["suggested_quantity"] = adjusted_quantity
                result["portfolio_weight"] = max_position_weight
                result["constraint_applied"] = "concentration_limit"
                result["original_weight"] = result.get("original_weight", result["portfolio_weight"])
            
            # 检查现有持仓
            existing_asset = db.query(models.PortfolioAsset).filter(
                models.PortfolioAsset.portfolio_id == portfolio.id,
                models.PortfolioAsset.symbol == symbol
            ).first()
            
            if existing_asset:
                current_value = existing_asset.market_value or 0
                total_value = portfolio.total_value + portfolio.cash_balance
                current_weight = current_value / total_value if total_value > 0 else 0
                
                result["existing_position"] = {
                    "quantity": existing_asset.quantity,
                    "market_value": current_value,
                    "weight": current_weight
                }
                
                # 如果已有持仓，建议增量投资
                new_total_weight = current_weight + result["portfolio_weight"]
                if new_total_weight > max_position_weight:
                    max_additional_weight = max_position_weight - current_weight
                    if max_additional_weight > 0:
                        adjusted_amount = total_value * max_additional_weight
                        adjusted_quantity = adjusted_amount / result["entry_price"]
                        
                        result["suggested_amount"] = adjusted_amount
                        result["suggested_quantity"] = adjusted_quantity
                        result["portfolio_weight"] = max_additional_weight
                        result["constraint_applied"] = "incremental_limit"
                    else:
                        result["suggested_amount"] = 0
                        result["suggested_quantity"] = 0
                        result["portfolio_weight"] = 0
                        result["constraint_applied"] = "position_full"
                        result["warning"] = "已达到该股票的最大持仓限制"
            
            return result
            
        except Exception as e:
            logger.error(f"Risk constraint application failed: {e}")
            result["warning"] = f"风险约束应用失败: {str(e)}"
            return result
    
    def _generate_execution_suggestion(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """生成执行建议"""
        if "error" in result or result["suggested_quantity"] <= 0:
            return {"recommendation": "不建议执行此交易"}
        
        suggestions = {
            "recommendation": "建议执行",
            "execution_style": "normal",
            "time_horizon": "immediate",
            "risk_management": []
        }
        
        # 根据持仓权重调整执行建议
        weight = result["portfolio_weight"]
        
        if weight > 0.2:
            suggestions["execution_style"] = "gradual"
            suggestions["time_horizon"] = "1-3_days"
            suggestions["risk_management"].append("建议分批买入以降低时机风险")
        
        if weight > 0.3:
            suggestions["risk_management"].append("建议设置止损订单")
        
        # 根据风险等级调整建议
        risk_level = result.get("risk_level", "medium")
        
        if risk_level == "high":
            suggestions["risk_management"].append("高风险持仓，建议密切监控")
            suggestions["time_horizon"] = "1-5_days"
        
        # 根据计算方法调整建议
        method = result.get("method", "")
        
        if method == "volatility_target":
            suggestions["risk_management"].append("基于波动率计算，建议定期重新评估")
        elif method == "kelly_criterion":
            suggestions["risk_management"].append("凯利公式结果，建议保守执行")
        
        return suggestions
    
    async def get_sizing_methods(self) -> List[Dict[str, Any]]:
        """获取支持的持仓大小计算方法"""
        methods = []
        
        for method in PositionSizingMethod:
            method_info = {
                "method": method.value,
                "name": self._get_method_name(method),
                "description": self._get_method_description(method),
                "parameters": self.default_params.get(method, {}),
                "risk_level": self._get_method_risk_level(method),
                "suitable_for": self._get_method_suitability(method)
            }
            methods.append(method_info)
        
        return methods
    
    def _get_method_name(self, method: PositionSizingMethod) -> str:
        """获取方法名称"""
        names = {
            PositionSizingMethod.FIXED_AMOUNT: "固定金额",
            PositionSizingMethod.FIXED_PERCENTAGE: "固定百分比",
            PositionSizingMethod.VOLATILITY_TARGET: "波动率目标",
            PositionSizingMethod.KELLY_CRITERION: "凯利公式",
            PositionSizingMethod.RISK_PARITY: "风险平价",
            PositionSizingMethod.MAX_DRAWDOWN_TARGET: "最大回撤目标"
        }
        return names.get(method, method.value)
    
    def _get_method_description(self, method: PositionSizingMethod) -> str:
        """获取方法描述"""
        descriptions = {
            PositionSizingMethod.FIXED_AMOUNT: "每笔投资使用固定金额，简单直接",
            PositionSizingMethod.FIXED_PERCENTAGE: "按投资组合固定比例分配资金",
            PositionSizingMethod.VOLATILITY_TARGET: "基于目标波动率动态调整持仓大小",
            PositionSizingMethod.KELLY_CRITERION: "使用凯利公式优化长期收益",
            PositionSizingMethod.RISK_PARITY: "根据风险贡献平衡持仓配置",
            PositionSizingMethod.MAX_DRAWDOWN_TARGET: "控制最大回撤风险的持仓配置"
        }
        return descriptions.get(method, "")
    
    def _get_method_risk_level(self, method: PositionSizingMethod) -> str:
        """获取方法风险等级"""
        risk_levels = {
            PositionSizingMethod.FIXED_AMOUNT: "low",
            PositionSizingMethod.FIXED_PERCENTAGE: "low",
            PositionSizingMethod.VOLATILITY_TARGET: "medium",
            PositionSizingMethod.KELLY_CRITERION: "high",
            PositionSizingMethod.RISK_PARITY: "medium",
            PositionSizingMethod.MAX_DRAWDOWN_TARGET: "medium"
        }
        return risk_levels.get(method, "medium")
    
    def _get_method_suitability(self, method: PositionSizingMethod) -> List[str]:
        """获取方法适用性"""
        suitability = {
            PositionSizingMethod.FIXED_AMOUNT: ["初学者", "定投策略", "简单配置"],
            PositionSizingMethod.FIXED_PERCENTAGE: ["多元化投资", "平衡配置", "风险分散"],
            PositionSizingMethod.VOLATILITY_TARGET: ["风险控制", "专业投资者", "量化策略"],
            PositionSizingMethod.KELLY_CRITERION: ["长期投资", "专业投资者", "收益优化"],
            PositionSizingMethod.RISK_PARITY: ["风险管理", "机构投资", "组合优化"],
            PositionSizingMethod.MAX_DRAWDOWN_TARGET: ["保守投资", "回撤控制", "风险厌恶"]
        }
        return suitability.get(method, [])


# 全局持仓大小计算器实例
position_sizer = PositionSizer()


async def get_position_sizer() -> PositionSizer:
    """获取持仓大小计算器实例"""
    return position_sizer