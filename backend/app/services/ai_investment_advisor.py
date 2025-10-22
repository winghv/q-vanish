"""
AI投资建议服务
基于用户持仓、风险偏好和市场数据，提供智能投资建议
"""

import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .. import models, crud
from .ai_service_manager import get_ai_service_manager
from .market_data import get_market_service
from decimal import Decimal

logger = logging.getLogger(__name__)


class AIInvestmentAdvisor:
    """AI投资顾问类"""

    def __init__(self):
        self.ai_manager = get_ai_service_manager()
        self.market_service = None

    async def _get_market_service(self):
        """获取市场数据服务"""
        if self.market_service is None:
            self.market_service = await get_market_service()
        return self.market_service

    async def get_portfolio_advice(
        self,
        db: Session,
        user_id: int,
        portfolio_id: int,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        获取投资组合建议

        Args:
            db: 数据库会话
            user_id: 用户ID
            portfolio_id: 投资组合ID
            focus_areas: 关注领域（如：rebalancing, diversification, risk, tax）
        """
        try:
            # 获取投资组合信息
            portfolio = crud.get_portfolio(db, portfolio_id)
            if not portfolio or portfolio.user_id != user_id:
                return {
                    "success": False,
                    "error": "Portfolio not found or access denied"
                }

            # 获取持仓资产
            assets = crud.get_portfolio_assets(db, portfolio_id)

            # 获取实时价格
            market_service = await self._get_market_service()
            symbols = [asset.symbol for asset in assets]
            prices = await market_service.get_multiple_prices(symbols)

            # 构建投资组合分析上下文
            portfolio_context = self._build_portfolio_context(portfolio, assets, prices)

            # 构建提示词
            prompt = self._build_advice_prompt(portfolio_context, focus_areas)

            # 调用AI生成建议
            advice = await self.ai_manager.structured_prompt(
                prompt=prompt,
                context=portfolio_context,
                system_prompt_type="investment_advisor",
                temperature=0.7,
                max_tokens=2000
            )

            return {
                "success": True,
                "advice": advice,
                "portfolio_summary": {
                    "total_value": float(portfolio.total_value),
                    "cash_balance": float(portfolio.cash_balance),
                    "positions_count": len(assets),
                    "symbols": symbols
                },
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating portfolio advice: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _build_portfolio_context(
        self,
        portfolio: models.Portfolio,
        assets: List[models.PortfolioAsset],
        prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """构建投资组合上下文"""
        total_value = float(portfolio.total_value)
        cash_balance = float(portfolio.cash_balance)

        # 计算持仓详情
        positions = []
        total_invested = 0
        total_profit_loss = 0

        for asset in assets:
            current_price = prices.get(asset.symbol, asset.current_price)
            market_value = asset.quantity * current_price
            cost_basis = asset.quantity * asset.average_price
            profit_loss = market_value - cost_basis
            profit_loss_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0
            allocation_pct = (market_value / total_value * 100) if total_value > 0 else 0

            positions.append({
                "symbol": asset.symbol,
                "quantity": float(asset.quantity),
                "average_price": float(asset.average_price),
                "current_price": float(current_price),
                "market_value": float(market_value),
                "cost_basis": float(cost_basis),
                "profit_loss": float(profit_loss),
                "profit_loss_pct": round(profit_loss_pct, 2),
                "allocation_pct": round(allocation_pct, 2)
            })

            total_invested += cost_basis
            total_profit_loss += profit_loss

        # 计算集中度风险
        max_allocation = max([p["allocation_pct"] for p in positions]) if positions else 0
        concentration_risk = "high" if max_allocation > 30 else "medium" if max_allocation > 20 else "low"

        return {
            "portfolio_name": portfolio.name,
            "total_value": round(total_value, 2),
            "cash_balance": round(cash_balance, 2),
            "cash_allocation_pct": round((cash_balance / total_value * 100) if total_value > 0 else 0, 2),
            "total_invested": round(total_invested, 2),
            "total_profit_loss": round(total_profit_loss, 2),
            "total_return_pct": round((total_profit_loss / total_invested * 100) if total_invested > 0 else 0, 2),
            "positions_count": len(positions),
            "positions": positions,
            "concentration_risk": concentration_risk,
            "max_position_allocation": round(max_allocation, 2)
        }

    def _build_advice_prompt(
        self,
        portfolio_context: Dict[str, Any],
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """构建建议提示词"""
        prompt = f"""请对以下投资组合进行分析并提供专业建议：

投资组合概况：
- 总价值: ${portfolio_context['total_value']:,.2f}
- 现金余额: ${portfolio_context['cash_balance']:,.2f} ({portfolio_context['cash_allocation_pct']}%)
- 持仓数量: {portfolio_context['positions_count']}
- 总投资成本: ${portfolio_context['total_invested']:,.2f}
- 总盈亏: ${portfolio_context['total_profit_loss']:,.2f} ({portfolio_context['total_return_pct']}%)
- 集中度风险: {portfolio_context['concentration_risk']}
- 最大仓位占比: {portfolio_context['max_position_allocation']}%

持仓明细：
"""
        for i, pos in enumerate(portfolio_context['positions'], 1):
            prompt += f"""
{i}. {pos['symbol']}:
   - 持仓: {pos['quantity']} 股
   - 成本价: ${pos['average_price']:.2f}, 现价: ${pos['current_price']:.2f}
   - 市值: ${pos['market_value']:,.2f} (占比 {pos['allocation_pct']}%)
   - 盈亏: ${pos['profit_loss']:,.2f} ({pos['profit_loss_pct']:.2f}%)
"""

        # 添加关注领域
        if focus_areas:
            prompt += f"\n请特别关注以下方面：{', '.join(focus_areas)}\n"

        prompt += """
请提供以下建议：
1. **资产配置分析**: 评估当前配置是否合理，是否需要再平衡
2. **风险评估**: 识别主要风险点（集中度、行业、市场风险等）
3. **优化建议**: 具体的操作建议（买入/卖出/持有哪些股票，建议仓位）
4. **时机判断**: 当前市场环境下的操作时机建议
5. **风险管理**: 止损/止盈建议，风险对冲建议

请用简洁、专业的语言回答，提供具体可执行的建议。使用markdown格式组织回答。
"""
        return prompt

    async def get_rebalancing_advice(
        self,
        db: Session,
        user_id: int,
        portfolio_id: int,
        target_allocations: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        获取再平衡建议

        Args:
            db: 数据库会话
            user_id: 用户ID
            portfolio_id: 投资组合ID
            target_allocations: 目标配置（symbol -> percentage）
        """
        try:
            portfolio = crud.get_portfolio(db, portfolio_id)
            if not portfolio or portfolio.user_id != user_id:
                return {"success": False, "error": "Portfolio not found"}

            assets = crud.get_portfolio_assets(db, portfolio_id)
            market_service = await self._get_market_service()
            symbols = [asset.symbol for asset in assets]
            prices = await market_service.get_multiple_prices(symbols)

            # 计算当前配置
            total_value = float(portfolio.total_value)
            current_allocations = {}
            for asset in assets:
                current_price = prices.get(asset.symbol, asset.current_price)
                market_value = asset.quantity * current_price
                current_allocations[asset.symbol] = (market_value / total_value * 100) if total_value > 0 else 0

            # 如果没有提供目标配置，使用均衡配置
            if not target_allocations:
                num_positions = len(assets)
                target_allocations = {symbol: 100 / num_positions for symbol in symbols}

            # 计算需要调整的交易
            rebalancing_trades = []
            for symbol in symbols:
                current_pct = current_allocations.get(symbol, 0)
                target_pct = target_allocations.get(symbol, 0)
                diff_pct = target_pct - current_pct

                if abs(diff_pct) > 2:  # 只调整差异大于2%的持仓
                    current_price = prices.get(symbol, 0)
                    if current_price > 0:
                        value_change = total_value * (diff_pct / 100)
                        shares_change = value_change / current_price

                        rebalancing_trades.append({
                            "symbol": symbol,
                            "action": "buy" if shares_change > 0 else "sell",
                            "shares": abs(int(shares_change)),
                            "current_allocation": round(current_pct, 2),
                            "target_allocation": round(target_pct, 2),
                            "difference": round(diff_pct, 2),
                            "estimated_value": abs(value_change)
                        })

            # 生成AI建议
            prompt = f"""投资组合再平衡分析：

当前总价值: ${total_value:,.2f}

当前配置:
{chr(10).join([f"- {s}: {a:.2f}%" for s, a in current_allocations.items()])}

目标配置:
{chr(10).join([f"- {s}: {a:.2f}%" for s, a in target_allocations.items()])}

建议交易:
"""
            for trade in rebalancing_trades:
                prompt += f"""
- {trade['action'].upper()} {trade['shares']} shares of {trade['symbol']}
  当前: {trade['current_allocation']}% → 目标: {trade['target_allocation']}%
  价值: ${trade['estimated_value']:,.2f}
"""

            prompt += "\n请评估这个再平衡计划的合理性，并提供优化建议。考虑交易成本、税收影响和市场时机。"

            advice = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["investment_advisor"],
                temperature=0.7,
                max_tokens=1500
            )

            return {
                "success": True,
                "rebalancing_plan": rebalancing_trades,
                "ai_advice": advice,
                "total_value": total_value,
                "current_allocations": current_allocations,
                "target_allocations": target_allocations,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating rebalancing advice: {e}")
            return {"success": False, "error": str(e)}

    async def get_asset_recommendation(
        self,
        db: Session,
        user_id: int,
        risk_tolerance: str = "moderate",
        investment_amount: float = 10000.0,
        investment_horizon: str = "medium",
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        获取资产推荐

        Args:
            db: 数据库会话
            user_id: 用户ID
            risk_tolerance: 风险承受能力 (low, moderate, high)
            investment_amount: 投资金额
            investment_horizon: 投资期限 (short, medium, long)
            preferences: 投资偏好（行业、主题等）
        """
        try:
            # 获取用户现有持仓
            portfolios = crud.get_portfolios(db, user_id)
            all_positions = []
            for portfolio in portfolios:
                assets = crud.get_portfolio_assets(db, portfolio.id)
                all_positions.extend([asset.symbol for asset in assets])

            # 构建推荐提示词
            prompt = f"""请为以下投资者推荐合适的资产：

投资者画像:
- 风险承受能力: {risk_tolerance}
- 投资金额: ${investment_amount:,.2f}
- 投资期限: {investment_horizon}
- 现有持仓: {', '.join(all_positions) if all_positions else '无'}
"""

            if preferences:
                prompt += f"\n投资偏好:\n"
                for key, value in preferences.items():
                    prompt += f"- {key}: {value}\n"

            prompt += """
请推荐5-8只合适的股票或ETF，并说明：
1. 推荐理由（基本面、技术面、市场环境）
2. 建议配置比例
3. 预期风险收益特征
4. 注意事项和风险提示

使用markdown格式，按优先级排序推荐。
"""

            advice = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["investment_advisor"],
                temperature=0.8,  # 稍高温度以增加多样性
                max_tokens=2000
            )

            return {
                "success": True,
                "recommendations": advice,
                "parameters": {
                    "risk_tolerance": risk_tolerance,
                    "investment_amount": investment_amount,
                    "investment_horizon": investment_horizon,
                    "existing_positions": all_positions
                },
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating asset recommendations: {e}")
            return {"success": False, "error": str(e)}


# 全局实例
_investment_advisor: Optional[AIInvestmentAdvisor] = None


def get_investment_advisor() -> AIInvestmentAdvisor:
    """获取AI投资顾问实例"""
    global _investment_advisor
    if _investment_advisor is None:
        _investment_advisor = AIInvestmentAdvisor()
    return _investment_advisor
