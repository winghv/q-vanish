"""
AI策略推荐服务
基于用户交易历史和市场条件推荐合适的交易策略
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from collections import defaultdict

from .. import models, crud
from .ai_service_manager import get_ai_service_manager
from .strategy_templates import StrategyTemplates

logger = logging.getLogger(__name__)


class AIStrategyRecommender:
    """AI策略推荐类"""

    def __init__(self):
        self.ai_manager = get_ai_service_manager()

    async def recommend_strategies(
        self,
        db: Session,
        user_id: int,
        portfolio_id: Optional[int] = None,
        market_condition: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        推荐交易策略

        Args:
            db: 数据库会话
            user_id: 用户ID
            portfolio_id: 投资组合ID（可选）
            market_condition: 市场条件（trending/ranging/volatile）
        """
        try:
            # 分析用户交易历史
            trading_profile = self._analyze_user_trading_history(db, user_id)

            # 获取用户现有策略
            user_strategies = crud.get_user_strategies(db, user_id)

            # 获取所有可用策略模板
            all_templates = StrategyTemplates.get_all_templates()

            # 构建推荐提示词
            prompt = self._build_recommendation_prompt(
                trading_profile,
                user_strategies,
                all_templates,
                market_condition
            )

            # 调用AI生成推荐
            recommendations = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["strategy_expert"],
                temperature=0.7,
                max_tokens=2000
            )

            # 获取推荐的策略详情
            recommended_templates = self._match_templates(recommendations, all_templates)

            return {
                "success": True,
                "recommendations": recommendations,
                "trading_profile": trading_profile,
                "recommended_templates": recommended_templates,
                "market_condition": market_condition or "unknown",
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error recommending strategies: {e}")
            return {"success": False, "error": str(e)}

    def _analyze_user_trading_history(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """分析用户交易历史"""
        # 获取用户最近的交易
        trades = crud.get_user_recent_trades(db, user_id, limit=50)

        if not trades:
            return {
                "total_trades": 0,
                "experience_level": "beginner",
                "preferred_holding_period": "unknown",
                "win_rate": 0,
                "avg_profit_per_trade": 0,
                "risk_tolerance": "unknown"
            }

        # 统计交易数据
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.profit_loss and t.profit_loss > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # 计算平均盈亏
        profits = [float(t.profit_loss) for t in trades if t.profit_loss]
        avg_profit = sum(profits) / len(profits) if profits else 0

        # 分析持仓时间（简化）
        avg_holding_days = 7  # 默认值，实际应该根据created_at和executed_at计算

        # 确定经验等级
        if total_trades < 10:
            experience_level = "beginner"
        elif total_trades < 50:
            experience_level = "intermediate"
        else:
            experience_level = "advanced"

        # 推断风险承受能力
        if win_rate > 60 and avg_profit > 0:
            risk_tolerance = "aggressive"
        elif win_rate > 45:
            risk_tolerance = "moderate"
        else:
            risk_tolerance = "conservative"

        return {
            "total_trades": total_trades,
            "experience_level": experience_level,
            "win_rate": round(win_rate, 2),
            "avg_profit_per_trade": round(avg_profit, 2),
            "avg_holding_days": avg_holding_days,
            "risk_tolerance": risk_tolerance,
            "preferred_holding_period": "short" if avg_holding_days < 5 else "medium" if avg_holding_days < 20 else "long"
        }

    def _build_recommendation_prompt(
        self,
        trading_profile: Dict[str, Any],
        user_strategies: List[models.Strategy],
        all_templates: List[Dict[str, Any]],
        market_condition: Optional[str]
    ) -> str:
        """构建推荐提示词"""
        prompt = f"""请为以下投资者推荐合适的量化交易策略：

投资者画像：
- 交易经验: {trading_profile['experience_level']}
- 历史交易次数: {trading_profile['total_trades']}
- 胜率: {trading_profile['win_rate']:.1f}%
- 风险偏好: {trading_profile['risk_tolerance']}
- 偏好持仓周期: {trading_profile['preferred_holding_period']}
"""

        if market_condition:
            prompt += f"\n当前市场环境: {market_condition}\n"

        if user_strategies:
            prompt += f"\n用户现有策略 ({len(user_strategies)}个):\n"
            for strategy in user_strategies[:5]:
                prompt += f"- {strategy.name}: {strategy.type}\n"

        prompt += "\n可选策略模板:\n"
        for i, template in enumerate(all_templates, 1):
            prompt += f"{i}. {template['name']} - {template['description'][:100]}\n"

        prompt += """
请推荐3-5个最适合的策略，并说明：
1. **推荐理由**: 为什么这个策略适合用户
2. **策略优势**: 在当前市场环境下的优势
3. **参数建议**: 推荐的策略参数设置
4. **风险提示**: 使用这个策略需要注意的风险
5. **学习路径**: 如果是新策略，如何学习和掌握

按优先级排序，使用markdown格式。
"""
        return prompt

    def _match_templates(
        self,
        recommendations: str,
        templates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """从推荐文本中匹配策略模板"""
        matched = []

        for template in templates:
            # 简单的关键词匹配
            if template['name'] in recommendations or template['id'] in recommendations:
                matched.append({
                    "id": template['id'],
                    "name": template['name'],
                    "type": template['type'],
                    "description": template['description'],
                    "risk_level": template.get('risk_level', 'medium')
                })

        return matched[:5]  # 最多返回5个

    async def optimize_strategy_parameters(
        self,
        db: Session,
        user_id: int,
        strategy_id: int
    ) -> Dict[str, Any]:
        """
        优化策略参数

        Args:
            db: 数据库会话
            user_id: 用户ID
            strategy_id: 策略ID
        """
        try:
            # 获取策略
            strategy = crud.get_strategy(db, strategy_id)
            if not strategy or strategy.owner_id != user_id:
                return {"success": False, "error": "Strategy not found"}

            # 获取策略的历史回测结果（如果有）
            backtests = crud.get_backtests(db, user_id, strategy_id=strategy_id, limit=10)

            prompt = f"""请为以下交易策略提供参数优化建议：

策略信息：
- 名称: {strategy.name}
- 类型: {strategy.type}
- 描述: {strategy.description}
- 当前参数: {strategy.parameters}
"""

            if backtests:
                prompt += "\n历史回测结果:\n"
                for bt in backtests[:5]:
                    prompt += f"""- 回测期间: {bt.start_date.strftime('%Y-%m-%d')} 至 {bt.end_date.strftime('%Y-%m-%d')}
  总回报: {bt.profit_loss if bt.profit_loss else 'N/A'}
  夏普比率: {bt.sharpe_ratio if bt.sharpe_ratio else 'N/A'}
  最大回撤: {bt.max_drawdown if bt.max_drawdown else 'N/A'}%
"""

            prompt += """
请提供：
1. **参数分析**: 当前参数的优缺点
2. **优化建议**: 具体的参数调整建议（如均线周期、止损比例等）
3. **预期效果**: 参数调整后可能带来的改善
4. **测试建议**: 如何验证优化效果
5. **风险提示**: 参数优化的潜在风险

具体可执行，使用markdown格式。
"""

            optimization_advice = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["strategy_expert"],
                temperature=0.7,
                max_tokens=1800
            )

            return {
                "success": True,
                "strategy_name": strategy.name,
                "optimization_advice": optimization_advice,
                "current_parameters": strategy.parameters,
                "backtest_count": len(backtests),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error optimizing strategy parameters: {e}")
            return {"success": False, "error": str(e)}

    async def compare_strategies(
        self,
        db: Session,
        user_id: int,
        strategy_ids: List[int]
    ) -> Dict[str, Any]:
        """
        比较多个策略

        Args:
            db: 数据库会话
            user_id: 用户ID
            strategy_ids: 策略ID列表
        """
        try:
            strategies_info = []

            for strategy_id in strategy_ids:
                strategy = crud.get_strategy(db, strategy_id)
                if strategy and strategy.owner_id == user_id:
                    # 获取最新回测结果
                    backtests = crud.get_backtests(db, user_id, strategy_id=strategy_id, limit=1)
                    backtest = backtests[0] if backtests else None

                    strategies_info.append({
                        "name": strategy.name,
                        "type": strategy.type,
                        "description": strategy.description,
                        "parameters": strategy.parameters,
                        "backtest": {
                            "total_return": backtest.profit_loss if backtest else None,
                            "sharpe_ratio": backtest.sharpe_ratio if backtest else None,
                            "max_drawdown": backtest.max_drawdown if backtest else None,
                            "win_rate": backtest.win_rate if backtest else None
                        } if backtest else None
                    })

            if len(strategies_info) < 2:
                return {"success": False, "error": "Need at least 2 strategies to compare"}

            prompt = "请比较以下交易策略:\n\n"
            for i, info in enumerate(strategies_info, 1):
                prompt += f"""策略{i}: {info['name']}
- 类型: {info['type']}
- 描述: {info['description']}
"""
                if info['backtest']:
                    bt = info['backtest']
                    prompt += f"""- 回测表现:
  总回报: {bt['total_return'] if bt['total_return'] else 'N/A'}
  夏普比率: {bt['sharpe_ratio'] if bt['sharpe_ratio'] else 'N/A'}
  最大回撤: {bt['max_drawdown'] if bt['max_drawdown'] else 'N/A'}%
  胜率: {bt['win_rate'] if bt['win_rate'] else 'N/A'}%
"""
                prompt += "\n"

            prompt += """
请提供：
1. **综合对比**: 各策略的优劣势对比表
2. **适用场景**: 每个策略最适合的市场环境
3. **风险收益**: 风险收益特征对比
4. **选择建议**: 基于不同目标的策略选择建议
5. **组合建议**: 是否可以组合使用，如何组合

使用markdown格式，包含对比表格。
"""

            comparison = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["strategy_expert"],
                temperature=0.7,
                max_tokens=2000
            )

            return {
                "success": True,
                "comparison": comparison,
                "strategies_compared": len(strategies_info),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error comparing strategies: {e}")
            return {"success": False, "error": str(e)}


# 全局实例
_strategy_recommender: Optional[AIStrategyRecommender] = None


def get_strategy_recommender() -> AIStrategyRecommender:
    """获取策略推荐器实例"""
    global _strategy_recommender
    if _strategy_recommender is None:
        _strategy_recommender = AIStrategyRecommender()
    return _strategy_recommender
