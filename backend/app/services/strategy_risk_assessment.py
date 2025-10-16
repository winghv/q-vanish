"""
策略风险评估服务
提供策略级别的风险分析和评估
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from ..models import Strategy, BacktestResult, Portfolio


class StrategyRiskAssessor:
    """策略风险评估器"""

    @staticmethod
    def assess_strategy_risk(
        strategy_id: int,
        db: Session,
        portfolio_value: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        评估策略风险

        Args:
            strategy_id: 策略ID
            db: 数据库会话
            portfolio_value: 投资组合价值（可选）

        Returns:
            风险评估报告
        """
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        # 获取最新回测结果
        backtest = db.query(BacktestResult).filter(
            BacktestResult.strategy_id == strategy_id
        ).order_by(BacktestResult.created_at.desc()).first()

        if not backtest:
            return {
                "strategy_id": strategy_id,
                "risk_level": "UNKNOWN",
                "message": "No backtest results available"
            }

        # 基础风险指标
        max_drawdown = float(backtest.max_drawdown)
        sharpe_ratio = float(backtest.sharpe_ratio) if backtest.sharpe_ratio else None
        win_rate = float(backtest.win_rate)
        total_return = float(backtest.total_return)

        # 计算风险评分
        risk_score = StrategyRiskAssessor._calculate_risk_score(
            max_drawdown, sharpe_ratio, win_rate, total_return
        )

        # 确定风险等级
        risk_level = StrategyRiskAssessor._determine_risk_level(risk_score)

        # 计算最大推荐仓位
        max_position_size = StrategyRiskAssessor._calculate_max_position(
            risk_score, portfolio_value
        )

        # 风险警告
        warnings = []
        if max_drawdown > 20:
            warnings.append(f"High maximum drawdown: {max_drawdown:.1f}%")
        if sharpe_ratio and sharpe_ratio < 1:
            warnings.append(f"Low Sharpe ratio: {sharpe_ratio:.2f}")
        if win_rate < 50:
            warnings.append(f"Low win rate: {win_rate:.1f}%")

        return {
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "risk_assessment": {
                "risk_score": round(risk_score, 2),
                "risk_level": risk_level,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "win_rate": win_rate,
                "total_return": total_return
            },
            "recommendations": {
                "max_position_size": float(max_position_size) if max_position_size else None,
                "suggested_stop_loss": StrategyRiskAssessor._suggest_stop_loss(max_drawdown),
                "rebalance_frequency": StrategyRiskAssessor._suggest_rebalance_frequency(risk_level)
            },
            "warnings": warnings,
            "suitable_for": StrategyRiskAssessor._determine_suitability(risk_level)
        }

    @staticmethod
    def _calculate_risk_score(
        max_drawdown: float,
        sharpe_ratio: Optional[float],
        win_rate: float,
        total_return: float
    ) -> float:
        """
        计算风险评分 (0-100, 越高风险越大)

        Args:
            max_drawdown: 最大回撤
            sharpe_ratio: 夏普比率
            win_rate: 胜率
            total_return: 总回报率

        Returns:
            风险评分
        """
        score = 0

        # 最大回撤贡献 (40分)
        if max_drawdown < 10:
            score += 10
        elif max_drawdown < 20:
            score += 20
        elif max_drawdown < 30:
            score += 30
        else:
            score += 40

        # 夏普比率贡献 (30分)
        if sharpe_ratio:
            if sharpe_ratio > 2:
                score += 5
            elif sharpe_ratio > 1:
                score += 15
            elif sharpe_ratio > 0.5:
                score += 25
            else:
                score += 30
        else:
            score += 25  # 无数据时给中等分数

        # 胜率贡献 (20分)
        if win_rate > 60:
            score += 5
        elif win_rate > 50:
            score += 10
        elif win_rate > 40:
            score += 15
        else:
            score += 20

        # 波动性贡献 (10分) - 基于收益率波动
        volatility = abs(total_return) / 100  # 简化计算
        if volatility < 0.2:
            score += 2
        elif volatility < 0.5:
            score += 5
        else:
            score += 10

        return min(score, 100)

    @staticmethod
    def _determine_risk_level(risk_score: float) -> str:
        """确定风险等级"""
        if risk_score < 30:
            return "LOW"
        elif risk_score < 50:
            return "MEDIUM_LOW"
        elif risk_score < 70:
            return "MEDIUM"
        elif risk_score < 85:
            return "MEDIUM_HIGH"
        else:
            return "HIGH"

    @staticmethod
    def _calculate_max_position(
        risk_score: float,
        portfolio_value: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        计算最大推荐仓位

        Args:
            risk_score: 风险评分
            portfolio_value: 投资组合总价值

        Returns:
            最大仓位金额
        """
        if not portfolio_value:
            return None

        # 根据风险评分确定仓位比例
        if risk_score < 30:
            position_ratio = 0.30  # 低风险：30%
        elif risk_score < 50:
            position_ratio = 0.25  # 中低风险：25%
        elif risk_score < 70:
            position_ratio = 0.20  # 中等风险：20%
        elif risk_score < 85:
            position_ratio = 0.15  # 中高风险：15%
        else:
            position_ratio = 0.10  # 高风险：10%

        return portfolio_value * Decimal(str(position_ratio))

    @staticmethod
    def _suggest_stop_loss(max_drawdown: float) -> float:
        """建议止损百分比"""
        # 通常设置为最大回撤的一半到2/3
        suggested_stop = max_drawdown * 0.6
        return round(min(suggested_stop, 15), 1)  # 最大不超过15%

    @staticmethod
    def _suggest_rebalance_frequency(risk_level: str) -> str:
        """建议再平衡频率"""
        if risk_level in ["LOW", "MEDIUM_LOW"]:
            return "monthly"
        elif risk_level == "MEDIUM":
            return "weekly"
        else:
            return "daily"

    @staticmethod
    def _determine_suitability(risk_level: str) -> List[str]:
        """确定策略适用人群"""
        suitability_map = {
            "LOW": ["保守型投资者", "退休投资者", "新手投资者"],
            "MEDIUM_LOW": ["稳健型投资者", "长期投资者"],
            "MEDIUM": ["平衡型投资者", "有经验的投资者"],
            "MEDIUM_HIGH": ["积极型投资者", "专业投资者"],
            "HIGH": ["激进型投资者", "专业交易员", "高风险承受能力者"]
        }
        return suitability_map.get(risk_level, ["未分类"])

    @staticmethod
    def compare_strategy_risks(
        strategy_ids: List[int],
        db: Session
    ) -> Dict[str, Any]:
        """
        比较多个策略的风险

        Args:
            strategy_ids: 策略ID列表
            db: 数据库会话

        Returns:
            风险比较报告
        """
        comparison = {
            "strategies": [],
            "ranking": {
                "by_risk_score": [],
                "by_max_drawdown": [],
                "by_sharpe_ratio": []
            }
        }

        for strategy_id in strategy_ids:
            assessment = StrategyRiskAssessor.assess_strategy_risk(strategy_id, db)
            if "risk_assessment" in assessment:
                comparison["strategies"].append({
                    "strategy_id": strategy_id,
                    "strategy_name": assessment.get("strategy_name"),
                    "risk_score": assessment["risk_assessment"]["risk_score"],
                    "risk_level": assessment["risk_assessment"]["risk_level"],
                    "max_drawdown": assessment["risk_assessment"]["max_drawdown"],
                    "sharpe_ratio": assessment["risk_assessment"]["sharpe_ratio"]
                })

        if comparison["strategies"]:
            # 按风险评分排名（从低到高）
            comparison["ranking"]["by_risk_score"] = sorted(
                comparison["strategies"],
                key=lambda x: x["risk_score"]
            )

            # 按最大回撤排名（从低到高）
            comparison["ranking"]["by_max_drawdown"] = sorted(
                comparison["strategies"],
                key=lambda x: x["max_drawdown"]
            )

            # 按夏普比率排名（从高到低）
            valid_sharpe = [s for s in comparison["strategies"] if s["sharpe_ratio"] is not None]
            comparison["ranking"]["by_sharpe_ratio"] = sorted(
                valid_sharpe,
                key=lambda x: x["sharpe_ratio"],
                reverse=True
            )

        return comparison

    @staticmethod
    def calculate_var(
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        计算VaR (Value at Risk)

        Args:
            returns: 收益率序列
            confidence_level: 置信水平，默认95%

        Returns:
            VaR值
        """
        if len(returns) == 0:
            return 0

        return np.percentile(returns, (1 - confidence_level) * 100)

    @staticmethod
    def calculate_cvar(
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        计算CVaR (Conditional Value at Risk) / Expected Shortfall

        Args:
            returns: 收益率序列
            confidence_level: 置信水平，默认95%

        Returns:
            CVaR值
        """
        if len(returns) == 0:
            return 0

        var = StrategyRiskAssessor.calculate_var(returns, confidence_level)
        # CVaR是所有低于VaR的收益的平均值
        cvar = returns[returns <= var].mean()

        return cvar

    @staticmethod
    def stress_test_strategy(
        strategy_id: int,
        db: Session,
        shock_scenarios: Optional[List[Dict[str, float]]] = None
    ) -> Dict[str, Any]:
        """
        策略压力测试

        Args:
            strategy_id: 策略ID
            db: 数据库会话
            shock_scenarios: 冲击场景列表

        Returns:
            压力测试结果
        """
        if not shock_scenarios:
            # 默认压力场景
            shock_scenarios = [
                {"name": "Market Crash -20%", "market_shock": -0.20},
                {"name": "Market Crash -30%", "market_shock": -0.30},
                {"name": "Flash Crash -10%", "market_shock": -0.10},
                {"name": "Volatility Spike +50%", "volatility_shock": 0.50},
            ]

        backtest = db.query(BacktestResult).filter(
            BacktestResult.strategy_id == strategy_id
        ).order_by(BacktestResult.created_at.desc()).first()

        if not backtest:
            return {
                "strategy_id": strategy_id,
                "error": "No backtest results available"
            }

        results = []
        for scenario in shock_scenarios:
            # 简化的压力测试计算
            market_shock = scenario.get("market_shock", 0)
            volatility_shock = scenario.get("volatility_shock", 0)

            # 估算冲击后的表现
            shocked_return = float(backtest.total_return) * (1 + market_shock)
            shocked_drawdown = float(backtest.max_drawdown) * (1 + abs(market_shock) + volatility_shock)

            results.append({
                "scenario": scenario["name"],
                "estimated_return": round(shocked_return, 2),
                "estimated_max_drawdown": round(min(shocked_drawdown, 100), 2),
                "impact": "SEVERE" if shocked_drawdown > 40 else
                         "MODERATE" if shocked_drawdown > 25 else "MILD"
            })

        return {
            "strategy_id": strategy_id,
            "stress_test_results": results,
            "resilience_score": StrategyRiskAssessor._calculate_resilience(results)
        }

    @staticmethod
    def _calculate_resilience(stress_results: List[Dict]) -> str:
        """计算策略韧性评分"""
        severe_count = sum(1 for r in stress_results if r["impact"] == "SEVERE")
        moderate_count = sum(1 for r in stress_results if r["impact"] == "MODERATE")

        if severe_count >= len(stress_results) / 2:
            return "LOW"
        elif moderate_count >= len(stress_results) / 2:
            return "MEDIUM"
        else:
            return "HIGH"
