"""
AI智能风险提醒服务
实时监控持仓风险并生成智能提醒
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from decimal import Decimal

from .. import models, crud
from .ai_service_manager import get_ai_service_manager
from .market_data import get_market_service

logger = logging.getLogger(__name__)


class AIRiskAlerter:
    """AI风险提醒类"""

    def __init__(self):
        self.ai_manager = get_ai_service_manager()
        self.market_service = None

        # 风险阈值配置
        self.thresholds = {
            "concentration_risk": 30.0,  # 单一持仓占比%
            "daily_loss_limit": 5.0,     # 单日亏损限制%
            "portfolio_loss_limit": 15.0, # 组合亏损限制%
            "volatility_spike": 50.0,     # 波动率飙升%
            "correlation_risk": 0.8       # 相关性风险
        }

    async def _get_market_service(self):
        """获取市场数据服务"""
        if self.market_service is None:
            self.market_service = await get_market_service()
        return self.market_service

    async def scan_portfolio_risks(
        self,
        db: Session,
        user_id: int,
        portfolio_id: int
    ) -> Dict[str, Any]:
        """
        扫描投资组合风险

        Args:
            db: 数据库会话
            user_id: 用户ID
            portfolio_id: 投资组合ID
        """
        try:
            # 获取投资组合
            portfolio = crud.get_portfolio(db, portfolio_id)
            if not portfolio or portfolio.user_id != user_id:
                return {"success": False, "error": "Portfolio not found"}

            # 获取持仓
            assets = crud.get_portfolio_assets(db, portfolio_id)
            if not assets:
                return {
                    "success": True,
                    "alerts": [],
                    "risk_level": "low",
                    "message": "No positions to analyze"
                }

            # 获取实时价格
            market_service = await self._get_market_service()
            symbols = [asset.symbol for asset in assets]
            prices = await market_service.get_multiple_prices(symbols)

            # 检测各类风险
            risk_alerts = []

            # 1. 集中度风险
            concentration_alerts = self._check_concentration_risk(assets, prices, portfolio.total_value)
            risk_alerts.extend(concentration_alerts)

            # 2. 亏损风险
            loss_alerts = self._check_loss_risk(assets, prices)
            risk_alerts.extend(loss_alerts)

            # 3. 波动率风险（需要历史数据，这里简化）
            # volatility_alerts = await self._check_volatility_risk(db, assets)
            # risk_alerts.extend(volatility_alerts)

            # 确定整体风险等级
            risk_level = self._determine_risk_level(risk_alerts)

            # 生成AI风险分析
            if risk_alerts:
                ai_analysis = await self._generate_risk_analysis(
                    portfolio, assets, prices, risk_alerts
                )
            else:
                ai_analysis = "当前投资组合风险在可控范围内，未发现重大风险信号。建议继续监控市场动态。"

            return {
                "success": True,
                "risk_level": risk_level,
                "alerts": risk_alerts,
                "ai_analysis": ai_analysis,
                "portfolio_id": portfolio_id,
                "scanned_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error scanning portfolio risks: {e}")
            return {"success": False, "error": str(e)}

    def _check_concentration_risk(
        self,
        assets: List[models.PortfolioAsset],
        prices: Dict[str, float],
        total_value: float
    ) -> List[Dict[str, Any]]:
        """检查集中度风险"""
        alerts = []

        for asset in assets:
            current_price = prices.get(asset.symbol, asset.current_price)
            market_value = asset.quantity * current_price
            allocation_pct = (market_value / total_value * 100) if total_value > 0 else 0

            if allocation_pct > self.thresholds["concentration_risk"]:
                alerts.append({
                    "type": "concentration_risk",
                    "severity": "high" if allocation_pct > 40 else "medium",
                    "symbol": asset.symbol,
                    "message": f"{asset.symbol} 占比过高 ({allocation_pct:.1f}%)，建议分散投资",
                    "data": {
                        "allocation_pct": round(allocation_pct, 2),
                        "market_value": float(market_value),
                        "threshold": self.thresholds["concentration_risk"]
                    }
                })

        return alerts

    def _check_loss_risk(
        self,
        assets: List[models.PortfolioAsset],
        prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """检查亏损风险"""
        alerts = []

        for asset in assets:
            current_price = prices.get(asset.symbol, asset.current_price)
            cost_basis = asset.quantity * asset.average_price
            current_value = asset.quantity * current_price
            loss_pct = ((current_value - cost_basis) / cost_basis * 100) if cost_basis > 0 else 0

            if loss_pct < -self.thresholds["daily_loss_limit"]:
                severity = "critical" if loss_pct < -15 else "high" if loss_pct < -10 else "medium"
                alerts.append({
                    "type": "loss_risk",
                    "severity": severity,
                    "symbol": asset.symbol,
                    "message": f"{asset.symbol} 亏损 {abs(loss_pct):.1f}%，建议评估止损",
                    "data": {
                        "loss_pct": round(loss_pct, 2),
                        "loss_amount": float(current_value - cost_basis),
                        "current_price": float(current_price),
                        "cost_basis_price": float(asset.average_price)
                    }
                })

        return alerts

    def _determine_risk_level(self, alerts: List[Dict[str, Any]]) -> str:
        """确定整体风险等级"""
        if not alerts:
            return "low"

        severity_counts = {"critical": 0, "high": 0, "medium": 0}
        for alert in alerts:
            severity = alert.get("severity", "medium")
            if severity in severity_counts:
                severity_counts[severity] += 1

        if severity_counts["critical"] > 0:
            return "critical"
        elif severity_counts["high"] >= 2:
            return "high"
        elif severity_counts["high"] >= 1 or severity_counts["medium"] >= 3:
            return "medium"
        else:
            return "low"

    async def _generate_risk_analysis(
        self,
        portfolio: models.Portfolio,
        assets: List[models.PortfolioAsset],
        prices: Dict[str, float],
        alerts: List[Dict[str, Any]]
    ) -> str:
        """生成AI风险分析"""
        prompt = f"""投资组合风险分析：

组合概况:
- 总价值: ${portfolio.total_value:,.2f}
- 现金余额: ${portfolio.cash_balance:,.2f}
- 持仓数量: {len(assets)}

检测到的风险:
"""
        for i, alert in enumerate(alerts, 1):
            prompt += f"\n{i}. [{alert['severity'].upper()}] {alert['message']}"

        prompt += """

请提供：
1. **风险评估**: 对当前风险的整体评价
2. **主要关注点**: 需要立即关注的风险项
3. **建议措施**: 具体的风险缓解建议（止损、对冲、减仓等）
4. **监控建议**: 需要密切监控的指标

简洁专业，使用markdown格式。
"""

        try:
            analysis = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["risk_assessor"],
                temperature=0.6,  # 较低温度以保持专业性
                max_tokens=1500
            )
            return analysis
        except Exception as e:
            logger.error(f"Error generating risk analysis: {e}")
            return "无法生成详细风险分析，请手动评估风险情况。"

    async def get_symbol_risk_assessment(
        self,
        symbol: str,
        position_size: float,
        entry_price: float
    ) -> Dict[str, Any]:
        """
        评估单个股票的风险

        Args:
            symbol: 股票代码
            position_size: 持仓数量
            entry_price: 入场价格
        """
        try:
            market_service = await self._get_market_service()

            # 获取当前价格
            current_price = await market_service.get_real_time_price(symbol)
            if not current_price:
                return {"success": False, "error": f"Cannot fetch price for {symbol}"}

            # 获取股票信息
            stock_info = await market_service.get_stock_info(symbol)

            # 计算当前状态
            position_value = position_size * current_price
            cost_basis = position_size * entry_price
            unrealized_pnl = position_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0

            # 基于beta和波动率评估风险
            beta = stock_info.get('beta', 1.0) if stock_info else 1.0

            prompt = f"""评估 {symbol} 的持仓风险：

持仓信息:
- 股票代码: {symbol}
- 持仓数量: {position_size}
- 入场价格: ${entry_price:.2f}
- 当前价格: ${current_price:.2f}
- 持仓市值: ${position_value:,.2f}
- 未实现盈亏: ${unrealized_pnl:,.2f} ({unrealized_pnl_pct:+.2f}%)
- Beta值: {beta:.2f}

请提供：
1. **风险评级**: 低/中/高
2. **主要风险**: 识别3-5个主要风险因素
3. **止损建议**: 合理的止损位和止损理由
4. **仓位建议**: 当前仓位是否合适，是否需要调整

简洁明了，使用markdown格式。
"""

            analysis = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["risk_assessor"],
                temperature=0.6,
                max_tokens=1200
            )

            return {
                "success": True,
                "symbol": symbol,
                "risk_assessment": analysis,
                "position_data": {
                    "current_price": float(current_price),
                    "entry_price": float(entry_price),
                    "position_value": float(position_value),
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                    "beta": beta
                },
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error assessing risk for {symbol}: {e}")
            return {"success": False, "error": str(e)}


# 全局实例
_risk_alerter: Optional[AIRiskAlerter] = None


def get_risk_alerter() -> AIRiskAlerter:
    """获取风险提醒器实例"""
    global _risk_alerter
    if _risk_alerter is None:
        _risk_alerter = AIRiskAlerter()
    return _risk_alerter
