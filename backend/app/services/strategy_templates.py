"""
策略模板系统
提供预定义的策略模板，用户可以基于模板创建自己的策略
"""
from typing import Dict, List, Any
from enum import Enum


class StrategyTemplateType(str, Enum):
    """策略模板类型"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    PAIRS_TRADING = "pairs_trading"
    VOLATILITY = "volatility"


class StrategyTemplates:
    """策略模板库"""

    @staticmethod
    def get_all_templates() -> List[Dict[str, Any]]:
        """获取所有可用的策略模板"""
        return [
            StrategyTemplates.simple_ma_crossover(),
            StrategyTemplates.dual_ma_crossover(),
            StrategyTemplates.rsi_reversal(),
            StrategyTemplates.macd_momentum(),
            StrategyTemplates.bollinger_breakout(),
            StrategyTemplates.momentum_rotation(),
            StrategyTemplates.mean_reversion_rsi_bb(),
        ]

    @staticmethod
    def get_template(template_id: str) -> Dict[str, Any]:
        """根据ID获取特定模板"""
        templates = {
            "simple_ma": StrategyTemplates.simple_ma_crossover(),
            "dual_ma": StrategyTemplates.dual_ma_crossover(),
            "rsi_reversal": StrategyTemplates.rsi_reversal(),
            "macd_momentum": StrategyTemplates.macd_momentum(),
            "bollinger_breakout": StrategyTemplates.bollinger_breakout(),
            "momentum_rotation": StrategyTemplates.momentum_rotation(),
            "mean_reversion": StrategyTemplates.mean_reversion_rsi_bb(),
        }
        return templates.get(template_id)

    @staticmethod
    def simple_ma_crossover() -> Dict[str, Any]:
        """简单移动平均线交叉策略"""
        return {
            "id": "simple_ma",
            "name": "简单移动平均线交叉策略",
            "type": StrategyTemplateType.TREND_FOLLOWING,
            "description": "当短期均线上穿长期均线时买入，下穿时卖出。适合趋势明显的市场。",
            "difficulty": "初级",
            "parameters": {
                "strategy_type": "simple_ma",
                "short_window": {
                    "value": 20,
                    "min": 5,
                    "max": 50,
                    "step": 5,
                    "description": "短期移动平均线周期"
                },
                "long_window": {
                    "value": 50,
                    "min": 20,
                    "max": 200,
                    "step": 10,
                    "description": "长期移动平均线周期"
                },
                "position_size": {
                    "value": 100,
                    "min": 1,
                    "max": 10000,
                    "step": 100,
                    "description": "每次交易股数"
                },
                "symbols": {
                    "value": ["AAPL", "MSFT"],
                    "description": "交易标的列表"
                }
            },
            "indicators": ["SMA"],
            "signals": {
                "buy": "短期均线上穿长期均线（金叉）",
                "sell": "短期均线下穿长期均线（死叉）"
            },
            "risk_level": "中等",
            "typical_holding_period": "中长期 (数周到数月)",
            "pros": [
                "逻辑简单易懂",
                "适合趋势市场",
                "参数少易于优化"
            ],
            "cons": [
                "震荡市场会产生频繁假信号",
                "信号滞后",
                "需要较大的止损空间"
            ]
        }

    @staticmethod
    def dual_ma_crossover() -> Dict[str, Any]:
        """双均线交叉策略（使用EMA）"""
        return {
            "id": "dual_ma",
            "name": "指数移动平均线交叉策略",
            "type": StrategyTemplateType.TREND_FOLLOWING,
            "description": "使用EMA替代SMA，对近期价格变化更敏感。",
            "difficulty": "初级",
            "parameters": {
                "strategy_type": "dual_ma",
                "fast_period": {
                    "value": 12,
                    "min": 5,
                    "max": 30,
                    "step": 1,
                    "description": "快速EMA周期"
                },
                "slow_period": {
                    "value": 26,
                    "min": 20,
                    "max": 100,
                    "step": 1,
                    "description": "慢速EMA周期"
                },
                "position_size": {
                    "value": 100,
                    "min": 1,
                    "max": 10000,
                    "step": 100,
                    "description": "每次交易股数"
                },
                "symbols": {
                    "value": ["SPY", "QQQ"],
                    "description": "交易标的列表"
                }
            },
            "indicators": ["EMA"],
            "signals": {
                "buy": "快速EMA上穿慢速EMA",
                "sell": "快速EMA下穿慢速EMA"
            },
            "risk_level": "中等",
            "typical_holding_period": "中期 (数周)",
            "pros": [
                "对价格变化反应更快",
                "减少滞后性",
                "适合中短期交易"
            ],
            "cons": [
                "假信号仍然较多",
                "需要及时止损",
                "交易频率较高"
            ]
        }

    @staticmethod
    def rsi_reversal() -> Dict[str, Any]:
        """RSI反转策略"""
        return {
            "id": "rsi_reversal",
            "name": "RSI超买超卖反转策略",
            "type": StrategyTemplateType.MEAN_REVERSION,
            "description": "RSI进入超卖区后反转时买入，进入超买区后反转时卖出。",
            "difficulty": "初级",
            "parameters": {
                "strategy_type": "rsi",
                "rsi_period": {
                    "value": 14,
                    "min": 7,
                    "max": 30,
                    "step": 1,
                    "description": "RSI计算周期"
                },
                "oversold": {
                    "value": 30,
                    "min": 20,
                    "max": 40,
                    "step": 5,
                    "description": "超卖阈值"
                },
                "overbought": {
                    "value": 70,
                    "min": 60,
                    "max": 80,
                    "step": 5,
                    "description": "超买阈值"
                },
                "position_size": {
                    "value": 100,
                    "min": 1,
                    "max": 10000,
                    "step": 100,
                    "description": "每次交易股数"
                },
                "symbols": {
                    "value": ["TSLA", "NVDA"],
                    "description": "交易标的列表"
                }
            },
            "indicators": ["RSI"],
            "signals": {
                "buy": "RSI从超卖区向上突破",
                "sell": "RSI从超买区向下突破"
            },
            "risk_level": "中等偏高",
            "typical_holding_period": "短期 (数天)",
            "pros": [
                "适合震荡市场",
                "信号明确",
                "可以捕捉短期反转"
            ],
            "cons": [
                "趋势市场表现差",
                "可能错过大趋势",
                "需要严格止损"
            ]
        }

    @staticmethod
    def macd_momentum() -> Dict[str, Any]:
        """MACD动量策略"""
        return {
            "id": "macd_momentum",
            "name": "MACD动量交叉策略",
            "type": StrategyTemplateType.MOMENTUM,
            "description": "MACD柱状图由负转正时买入，由正转负时卖出。",
            "difficulty": "中级",
            "parameters": {
                "strategy_type": "macd",
                "fast_period": {
                    "value": 12,
                    "min": 8,
                    "max": 20,
                    "step": 1,
                    "description": "MACD快速周期"
                },
                "slow_period": {
                    "value": 26,
                    "min": 20,
                    "max": 40,
                    "step": 1,
                    "description": "MACD慢速周期"
                },
                "signal_period": {
                    "value": 9,
                    "min": 5,
                    "max": 15,
                    "step": 1,
                    "description": "信号线周期"
                },
                "position_size": {
                    "value": 100,
                    "min": 1,
                    "max": 10000,
                    "step": 100,
                    "description": "每次交易股数"
                },
                "symbols": {
                    "value": ["GOOGL", "AMZN"],
                    "description": "交易标的列表"
                }
            },
            "indicators": ["MACD"],
            "signals": {
                "buy": "MACD柱状图由负转正（多头交叉）",
                "sell": "MACD柱状图由正转负（空头交叉）"
            },
            "risk_level": "中等",
            "typical_holding_period": "中期 (数周)",
            "pros": [
                "结合趋势和动量",
                "信号相对可靠",
                "适合中期趋势"
            ],
            "cons": [
                "有一定滞后性",
                "震荡市信号频繁",
                "需要配合其他指标"
            ]
        }

    @staticmethod
    def bollinger_breakout() -> Dict[str, Any]:
        """布林带突破策略"""
        return {
            "id": "bollinger_breakout",
            "name": "布林带突破策略",
            "type": StrategyTemplateType.BREAKOUT,
            "description": "价格突破布林带上轨时买入，跌破下轨时卖出。",
            "difficulty": "中级",
            "parameters": {
                "strategy_type": "bollinger_breakout",
                "bb_period": {
                    "value": 20,
                    "min": 10,
                    "max": 50,
                    "step": 5,
                    "description": "布林带周期"
                },
                "bb_std": {
                    "value": 2.0,
                    "min": 1.0,
                    "max": 3.0,
                    "step": 0.5,
                    "description": "标准差倍数"
                },
                "position_size": {
                    "value": 100,
                    "min": 1,
                    "max": 10000,
                    "step": 100,
                    "description": "每次交易股数"
                },
                "symbols": {
                    "value": ["SPY"],
                    "description": "交易标的列表"
                }
            },
            "indicators": ["Bollinger Bands"],
            "signals": {
                "buy": "价格突破上轨",
                "sell": "价格跌破下轨"
            },
            "risk_level": "中等偏高",
            "typical_holding_period": "短中期 (数天到数周)",
            "pros": [
                "能捕捉突破行情",
                "止损位置明确",
                "适应性强"
            ],
            "cons": [
                "假突破风险",
                "需要严格止损",
                "参数敏感"
            ]
        }

    @staticmethod
    def momentum_rotation() -> Dict[str, Any]:
        """动量轮动策略"""
        return {
            "id": "momentum_rotation",
            "name": "多标的动量轮动策略",
            "type": StrategyTemplateType.MOMENTUM,
            "description": "定期选择动量最强的标的持有，动态轮换。",
            "difficulty": "高级",
            "parameters": {
                "strategy_type": "momentum_rotation",
                "lookback_period": {
                    "value": 20,
                    "min": 10,
                    "max": 60,
                    "step": 5,
                    "description": "回溯期"
                },
                "rebalance_frequency": {
                    "value": 5,
                    "min": 1,
                    "max": 20,
                    "step": 1,
                    "description": "再平衡频率（天）"
                },
                "top_n": {
                    "value": 3,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                    "description": "持有标的数量"
                },
                "symbols": {
                    "value": ["SPY", "QQQ", "IWM", "DIA", "EEM"],
                    "description": "候选标的池"
                }
            },
            "indicators": ["Price Momentum", "Relative Strength"],
            "signals": {
                "buy": "进入前N强势标的",
                "sell": "跌出前N强势标的"
            },
            "risk_level": "高",
            "typical_holding_period": "短期 (数天)",
            "pros": [
                "自动捕捉强势标的",
                "分散风险",
                "适应市场变化"
            ],
            "cons": [
                "交易频繁",
                "交易成本高",
                "复杂度高"
            ]
        }

    @staticmethod
    def mean_reversion_rsi_bb() -> Dict[str, Any]:
        """RSI+布林带均值回归策略"""
        return {
            "id": "mean_reversion",
            "name": "RSI+布林带双重确认均值回归策略",
            "type": StrategyTemplateType.MEAN_REVERSION,
            "description": "RSI超卖且价格触及布林带下轨时买入，RSI超买且价格触及上轨时卖出。",
            "difficulty": "高级",
            "parameters": {
                "strategy_type": "mean_reversion_rsi_bb",
                "rsi_period": {
                    "value": 14,
                    "min": 7,
                    "max": 30,
                    "step": 1,
                    "description": "RSI周期"
                },
                "rsi_oversold": {
                    "value": 30,
                    "min": 20,
                    "max": 40,
                    "step": 5,
                    "description": "RSI超卖阈值"
                },
                "rsi_overbought": {
                    "value": 70,
                    "min": 60,
                    "max": 80,
                    "step": 5,
                    "description": "RSI超买阈值"
                },
                "bb_period": {
                    "value": 20,
                    "min": 10,
                    "max": 50,
                    "step": 5,
                    "description": "布林带周期"
                },
                "bb_std": {
                    "value": 2.0,
                    "min": 1.0,
                    "max": 3.0,
                    "step": 0.5,
                    "description": "布林带标准差"
                },
                "position_size": {
                    "value": 100,
                    "min": 1,
                    "max": 10000,
                    "step": 100,
                    "description": "每次交易股数"
                },
                "symbols": {
                    "value": ["AAPL"],
                    "description": "交易标的列表"
                }
            },
            "indicators": ["RSI", "Bollinger Bands"],
            "signals": {
                "buy": "RSI超卖 且 价格 <= 布林带下轨",
                "sell": "RSI超买 且 价格 >= 布林带上轨"
            },
            "risk_level": "中等",
            "typical_holding_period": "短期 (数天)",
            "pros": [
                "双重确认减少假信号",
                "适合震荡市场",
                "风险收益比好"
            ],
            "cons": [
                "错过趋势行情",
                "信号较少",
                "需要精确入场"
            ]
        }
