"""
策略性能分析服务
提供策略绩效评估和风险分析功能
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import BacktestResult, Strategy, Trade


class StrategyPerformanceAnalyzer:
    """策略性能分析器"""

    @staticmethod
    def analyze_backtest(backtest_id: int, db: Session) -> Dict[str, Any]:
        """
        分析回测结果

        Args:
            backtest_id: 回测ID
            db: 数据库会话

        Returns:
            详细的性能分析报告
        """
        backtest = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        metrics = backtest.metrics or {}

        # 基础指标
        performance = {
            "backtest_id": backtest_id,
            "strategy_id": backtest.strategy_id,
            "period": {
                "start": backtest.start_date.isoformat(),
                "end": backtest.end_date.isoformat(),
                "duration_days": (backtest.end_date - backtest.start_date).days
            },
            "returns": {
                "total_return": float(backtest.total_return),
                "annual_return": metrics.get("annual_return", 0),
                "initial_capital": float(backtest.initial_capital),
                "final_capital": float(backtest.final_capital),
                "profit": float(backtest.final_capital - backtest.initial_capital)
            },
            "risk_metrics": {
                "sharpe_ratio": float(backtest.sharpe_ratio) if backtest.sharpe_ratio else None,
                "max_drawdown": float(backtest.max_drawdown),
                "volatility": metrics.get("volatility"),
                "sortino_ratio": metrics.get("sortino_ratio")
            },
            "trade_statistics": {
                "total_trades": backtest.total_trades,
                "win_rate": float(backtest.win_rate),
                "winning_trades": metrics.get("winning_trades", 0),
                "losing_trades": metrics.get("losing_trades", 0),
                "profit_factor": metrics.get("profit_factor", 0),
                "avg_win": metrics.get("avg_win", 0),
                "avg_loss": metrics.get("avg_loss", 0)
            }
        }

        return performance

    @staticmethod
    def compare_strategies(
        strategy_ids: List[int],
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        比较多个策略的性能

        Args:
            strategy_ids: 策略ID列表
            db: 数据库会话
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            策略比较报告
        """
        comparison = {
            "strategies": [],
            "ranking": {
                "by_return": [],
                "by_sharpe": [],
                "by_win_rate": [],
                "by_max_drawdown": []
            }
        }

        for strategy_id in strategy_ids:
            # 获取策略最新回测结果
            query = db.query(BacktestResult).filter(BacktestResult.strategy_id == strategy_id)

            if start_date:
                query = query.filter(BacktestResult.start_date >= start_date)
            if end_date:
                query = query.filter(BacktestResult.end_date <= end_date)

            backtest = query.order_by(BacktestResult.created_at.desc()).first()

            if backtest:
                strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
                comparison["strategies"].append({
                    "strategy_id": strategy_id,
                    "strategy_name": strategy.name if strategy else f"Strategy {strategy_id}",
                    "total_return": float(backtest.total_return),
                    "sharpe_ratio": float(backtest.sharpe_ratio) if backtest.sharpe_ratio else None,
                    "max_drawdown": float(backtest.max_drawdown),
                    "win_rate": float(backtest.win_rate),
                    "total_trades": backtest.total_trades
                })

        # 排名
        if comparison["strategies"]:
            # 按总回报排名
            comparison["ranking"]["by_return"] = sorted(
                comparison["strategies"],
                key=lambda x: x["total_return"],
                reverse=True
            )

            # 按夏普比率排名
            valid_sharpe = [s for s in comparison["strategies"] if s["sharpe_ratio"] is not None]
            comparison["ranking"]["by_sharpe"] = sorted(
                valid_sharpe,
                key=lambda x: x["sharpe_ratio"],
                reverse=True
            )

            # 按胜率排名
            comparison["ranking"]["by_win_rate"] = sorted(
                comparison["strategies"],
                key=lambda x: x["win_rate"],
                reverse=True
            )

            # 按最大回撤排名（越小越好）
            comparison["ranking"]["by_max_drawdown"] = sorted(
                comparison["strategies"],
                key=lambda x: x["max_drawdown"]
            )

        return comparison

    @staticmethod
    def calculate_portfolio_performance(
        portfolio_id: int,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        计算投资组合性能

        Args:
            portfolio_id: 投资组合ID
            db: 数据库会话
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            投资组合性能分析
        """
        # 获取交易记录
        query = db.query(Trade).filter(Trade.portfolio_id == portfolio_id)

        if start_date:
            query = query.filter(Trade.timestamp >= start_date)
        if end_date:
            query = query.filter(Trade.timestamp <= end_date)

        trades = query.order_by(Trade.timestamp).all()

        if not trades:
            return {
                "portfolio_id": portfolio_id,
                "error": "No trades found for the specified period"
            }

        # 构建交易数据
        trade_data = []
        for trade in trades:
            trade_data.append({
                "date": trade.timestamp,
                "symbol": trade.symbol,
                "action": trade.action,
                "quantity": float(trade.quantity),
                "price": float(trade.price),
                "value": float(trade.quantity * trade.price)
            })

        df = pd.DataFrame(trade_data)

        # 计算性能指标
        total_buy_value = df[df['action'] == 'BUY']['value'].sum()
        total_sell_value = df[df['action'] == 'SELL']['value'].sum()
        net_profit = total_sell_value - total_buy_value

        # 按交易对计算盈亏
        realized_trades = StrategyPerformanceAnalyzer._match_trades(df)
        winning_trades = [t for t in realized_trades if t['profit'] > 0]
        losing_trades = [t for t in realized_trades if t['profit'] < 0]

        win_rate = len(winning_trades) / len(realized_trades) if realized_trades else 0

        total_profit = sum(t['profit'] for t in winning_trades)
        total_loss = abs(sum(t['profit'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        return {
            "portfolio_id": portfolio_id,
            "period": {
                "start": start_date.isoformat() if start_date else trades[0].timestamp.isoformat(),
                "end": end_date.isoformat() if end_date else trades[-1].timestamp.isoformat()
            },
            "summary": {
                "total_trades": len(trades),
                "buy_trades": len(df[df['action'] == 'BUY']),
                "sell_trades": len(df[df['action'] == 'SELL']),
                "total_buy_value": round(total_buy_value, 2),
                "total_sell_value": round(total_sell_value, 2),
                "net_profit": round(net_profit, 2)
            },
            "performance": {
                "realized_trades": len(realized_trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": round(win_rate * 100, 2),
                "profit_factor": round(profit_factor, 2),
                "avg_profit": round(total_profit / len(winning_trades), 2) if winning_trades else 0,
                "avg_loss": round(total_loss / len(losing_trades), 2) if losing_trades else 0
            },
            "top_performers": {
                "best_trades": sorted(realized_trades, key=lambda x: x['profit'], reverse=True)[:5],
                "worst_trades": sorted(realized_trades, key=lambda x: x['profit'])[:5]
            }
        }

    @staticmethod
    def _match_trades(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """匹配买入卖出交易对"""
        matched_trades = []
        positions = {}

        for _, row in df.iterrows():
            symbol = row['symbol']
            if symbol not in positions:
                positions[symbol] = []

            if row['action'] == 'BUY':
                positions[symbol].append({
                    'date': row['date'],
                    'quantity': row['quantity'],
                    'price': row['price']
                })
            elif row['action'] == 'SELL':
                # 匹配卖出与买入（FIFO）
                remaining_quantity = row['quantity']
                sell_price = row['price']

                while remaining_quantity > 0 and positions[symbol]:
                    buy_trade = positions[symbol][0]
                    matched_quantity = min(remaining_quantity, buy_trade['quantity'])

                    profit = (sell_price - buy_trade['price']) * matched_quantity
                    matched_trades.append({
                        'symbol': symbol,
                        'buy_date': buy_trade['date'],
                        'sell_date': row['date'],
                        'quantity': matched_quantity,
                        'buy_price': buy_trade['price'],
                        'sell_price': sell_price,
                        'profit': profit,
                        'return_pct': (sell_price - buy_trade['price']) / buy_trade['price'] * 100
                    })

                    buy_trade['quantity'] -= matched_quantity
                    remaining_quantity -= matched_quantity

                    if buy_trade['quantity'] <= 0:
                        positions[symbol].pop(0)

        return matched_trades

    @staticmethod
    def calculate_risk_adjusted_metrics(
        returns: pd.Series,
        risk_free_rate: float = 0.02
    ) -> Dict[str, float]:
        """
        计算风险调整后的绩效指标

        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率，默认2%

        Returns:
            风险调整指标
        """
        if len(returns) < 2:
            return {
                "sharpe_ratio": None,
                "sortino_ratio": None,
                "calmar_ratio": None
            }

        # 年化收益率
        annual_return = returns.mean() * 252

        # 夏普比率
        excess_returns = returns - (risk_free_rate / 252)
        sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else None

        # 索提诺比率 (只考虑下行风险)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        sortino_ratio = (excess_returns.mean() / downside_std) * np.sqrt(252) if downside_std > 0 else None

        # 卡玛比率 (收益与最大回撤之比)
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else None

        return {
            "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio else None,
            "sortino_ratio": round(sortino_ratio, 2) if sortino_ratio else None,
            "calmar_ratio": round(calmar_ratio, 2) if calmar_ratio else None
        }
