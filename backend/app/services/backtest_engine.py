"""
策略回测引擎
提供完整的回测功能，包括历史数据加载、信号生成、交易模拟和绩效分析
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from ..models import Strategy, BacktestResult
from .market_data import MarketDataService
from .technical_indicators import TechnicalIndicators
import logging

logger = logging.getLogger(__name__)


class BacktestEngine:
    """策略回测引擎"""

    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service

    async def run_backtest(
        self,
        db: Session,
        strategy_id: int,
        start_date: datetime,
        end_date: datetime,
        initial_capital: Decimal = Decimal("100000"),
        commission_rate: Decimal = Decimal("0.001"),
        slippage_rate: Decimal = Decimal("0.0005")
    ) -> Dict[str, Any]:
        """
        运行策略回测

        Args:
            db: 数据库会话
            strategy_id: 策略ID
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_capital: 初始资金
            commission_rate: 佣金费率
            slippage_rate: 滑点率

        Returns:
            回测结果字典
        """
        # 获取策略
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        # 获取策略参数
        params = strategy.parameters or {}
        symbols = params.get("symbols", [])
        if not symbols:
            raise ValueError("No symbols specified in strategy parameters")

        # 加载历史数据
        logger.info(f"Loading historical data for {symbols} from {start_date} to {end_date}")
        historical_data = await self._load_historical_data(symbols, start_date, end_date)

        # 初始化回测状态
        portfolio = {
            "cash": float(initial_capital),
            "positions": {},  # symbol -> quantity
            "initial_capital": float(initial_capital)
        }

        trades = []
        equity_curve = []

        # 按时间顺序处理数据
        dates = sorted(set(date for data in historical_data.values() for date in data.index))

        for date in dates:
            # 获取当前日期的市场数据
            current_prices = {}
            for symbol in symbols:
                if symbol in historical_data and date in historical_data[symbol].index:
                    current_prices[symbol] = historical_data[symbol].loc[date]

            if not current_prices:
                continue

            # 生成交易信号
            signals = self._generate_signals(strategy, current_prices, historical_data, date)

            # 执行交易
            for signal in signals:
                trade = self._execute_trade(
                    signal,
                    current_prices,
                    portfolio,
                    commission_rate,
                    slippage_rate,
                    date
                )
                if trade:
                    trades.append(trade)

            # 记录净值曲线
            portfolio_value = self._calculate_portfolio_value(portfolio, current_prices)
            equity_curve.append({
                "date": date,
                "value": portfolio_value,
                "cash": portfolio["cash"],
                "positions_value": portfolio_value - portfolio["cash"]
            })

        # 计算绩效指标
        performance = self._calculate_performance(equity_curve, trades, initial_capital)

        # 保存回测结果
        backtest_result = BacktestResult(
            strategy_id=strategy_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=Decimal(str(equity_curve[-1]["value"])) if equity_curve else initial_capital,
            total_return=Decimal(str(performance["total_return"])),
            sharpe_ratio=Decimal(str(performance["sharpe_ratio"])) if performance["sharpe_ratio"] else None,
            max_drawdown=Decimal(str(performance["max_drawdown"])),
            win_rate=Decimal(str(performance["win_rate"])),
            total_trades=len(trades),
            metrics=performance
        )
        db.add(backtest_result)
        db.commit()
        db.refresh(backtest_result)

        return {
            "backtest_id": backtest_result.id,
            "performance": performance,
            "trades": trades,
            "equity_curve": equity_curve
        }

    async def _load_historical_data(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """加载历史数据"""
        data = {}
        for symbol in symbols:
            try:
                df = await self.market_data_service.get_historical_data(
                    symbol,
                    start_date,
                    end_date
                )
                data[symbol] = df
            except Exception as e:
                logger.error(f"Failed to load data for {symbol}: {e}")

        return data

    def _generate_signals(
        self,
        strategy: Strategy,
        current_prices: Dict[str, pd.Series],
        historical_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        生成交易信号
        根据策略类型和参数生成买入/卖出信号
        """
        signals = []
        params = strategy.parameters or {}
        strategy_type = params.get("strategy_type", "simple_ma")

        if strategy_type == "simple_ma":
            # 简单移动平均策略
            signals = self._simple_ma_strategy(params, current_prices, historical_data, current_date)
        elif strategy_type == "rsi":
            # RSI策略
            signals = self._rsi_strategy(params, current_prices, historical_data, current_date)
        elif strategy_type == "macd":
            # MACD策略
            signals = self._macd_strategy(params, current_prices, historical_data, current_date)
        else:
            logger.warning(f"Unknown strategy type: {strategy_type}")

        return signals

    def _simple_ma_strategy(
        self,
        params: Dict,
        current_prices: Dict[str, pd.Series],
        historical_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ) -> List[Dict[str, Any]]:
        """简单移动平均策略"""
        signals = []
        short_window = params.get("short_window", 20)
        long_window = params.get("long_window", 50)

        for symbol, price_data in current_prices.items():
            if symbol not in historical_data:
                continue

            df = historical_data[symbol]
            if len(df) < long_window:
                continue

            # 计算移动平均
            df_until_now = df[df.index <= current_date]
            short_ma = df_until_now['Close'].rolling(window=short_window).mean().iloc[-1]
            long_ma = df_until_now['Close'].rolling(window=long_window).mean().iloc[-1]

            # 前一天的移动平均
            if len(df_until_now) > 1:
                prev_short_ma = df_until_now['Close'].rolling(window=short_window).mean().iloc[-2]
                prev_long_ma = df_until_now['Close'].rolling(window=long_window).mean().iloc[-2]

                # 金叉 - 买入信号
                if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                    signals.append({
                        "symbol": symbol,
                        "action": "BUY",
                        "quantity": params.get("position_size", 100),
                        "price": float(price_data["Close"]),
                        "reason": f"Golden Cross: Short MA ({short_ma:.2f}) > Long MA ({long_ma:.2f})"
                    })
                # 死叉 - 卖出信号
                elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
                    signals.append({
                        "symbol": symbol,
                        "action": "SELL",
                        "quantity": params.get("position_size", 100),
                        "price": float(price_data["Close"]),
                        "reason": f"Death Cross: Short MA ({short_ma:.2f}) < Long MA ({long_ma:.2f})"
                    })

        return signals

    def _rsi_strategy(
        self,
        params: Dict,
        current_prices: Dict[str, pd.Series],
        historical_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ) -> List[Dict[str, Any]]:
        """RSI策略"""
        signals = []
        rsi_period = params.get("rsi_period", 14)
        oversold_threshold = params.get("oversold", 30)
        overbought_threshold = params.get("overbought", 70)

        for symbol, price_data in current_prices.items():
            if symbol not in historical_data:
                continue

            df = historical_data[symbol]
            if len(df) < rsi_period + 1:
                continue

            # 计算RSI
            df_until_now = df[df.index <= current_date]
            rsi = TechnicalIndicators.rsi(df_until_now['Close'], rsi_period)

            if len(rsi) < 2 or pd.isna(rsi.iloc[-1]):
                continue

            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]

            # 超卖区域向上突破 - 买入信号
            if prev_rsi <= oversold_threshold and current_rsi > oversold_threshold:
                signals.append({
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": params.get("position_size", 100),
                    "price": float(price_data["Close"]),
                    "reason": f"RSI oversold reversal: {current_rsi:.2f} > {oversold_threshold}"
                })
            # 超买区域向下突破 - 卖出信号
            elif prev_rsi >= overbought_threshold and current_rsi < overbought_threshold:
                signals.append({
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": params.get("position_size", 100),
                    "price": float(price_data["Close"]),
                    "reason": f"RSI overbought reversal: {current_rsi:.2f} < {overbought_threshold}"
                })

        return signals

    def _macd_strategy(
        self,
        params: Dict,
        current_prices: Dict[str, pd.Series],
        historical_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ) -> List[Dict[str, Any]]:
        """MACD策略"""
        signals = []
        fast_period = params.get("fast_period", 12)
        slow_period = params.get("slow_period", 26)
        signal_period = params.get("signal_period", 9)

        for symbol, price_data in current_prices.items():
            if symbol not in historical_data:
                continue

            df = historical_data[symbol]
            if len(df) < slow_period + signal_period:
                continue

            # 计算MACD
            df_until_now = df[df.index <= current_date]
            macd_line, signal_line, macd_histogram = TechnicalIndicators.macd(
                df_until_now['Close'],
                fast_period,
                slow_period,
                signal_period
            )

            if len(macd_histogram) < 2 or pd.isna(macd_histogram.iloc[-1]):
                continue

            current_histogram = macd_histogram.iloc[-1]
            prev_histogram = macd_histogram.iloc[-2]

            # MACD柱状图由负转正 - 买入信号
            if prev_histogram <= 0 and current_histogram > 0:
                signals.append({
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": params.get("position_size", 100),
                    "price": float(price_data["Close"]),
                    "reason": f"MACD bullish crossover: histogram {current_histogram:.2f}"
                })
            # MACD柱状图由正转负 - 卖出信号
            elif prev_histogram >= 0 and current_histogram < 0:
                signals.append({
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": params.get("position_size", 100),
                    "price": float(price_data["Close"]),
                    "reason": f"MACD bearish crossover: histogram {current_histogram:.2f}"
                })

        return signals

    def _execute_trade(
        self,
        signal: Dict[str, Any],
        current_prices: Dict[str, pd.Series],
        portfolio: Dict,
        commission_rate: Decimal,
        slippage_rate: Decimal,
        date: datetime
    ) -> Optional[Dict[str, Any]]:
        """执行交易"""
        symbol = signal["symbol"]
        action = signal["action"]
        quantity = signal["quantity"]
        price = signal["price"]

        # 计算滑点
        if action == "BUY":
            execution_price = price * (1 + float(slippage_rate))
        else:
            execution_price = price * (1 - float(slippage_rate))

        # 计算佣金
        commission = execution_price * quantity * float(commission_rate)

        if action == "BUY":
            # 检查资金是否充足
            total_cost = execution_price * quantity + commission
            if portfolio["cash"] < total_cost:
                logger.warning(f"Insufficient cash for {symbol}: need {total_cost}, have {portfolio['cash']}")
                return None

            # 执行买入
            portfolio["cash"] -= total_cost
            portfolio["positions"][symbol] = portfolio["positions"].get(symbol, 0) + quantity

            return {
                "date": date,
                "symbol": symbol,
                "action": "BUY",
                "quantity": quantity,
                "price": execution_price,
                "commission": commission,
                "total_cost": total_cost,
                "reason": signal.get("reason", "")
            }

        else:  # SELL
            # 检查持仓是否充足
            current_position = portfolio["positions"].get(symbol, 0)
            if current_position < quantity:
                logger.warning(f"Insufficient position for {symbol}: need {quantity}, have {current_position}")
                return None

            # 执行卖出
            total_proceeds = execution_price * quantity - commission
            portfolio["cash"] += total_proceeds
            portfolio["positions"][symbol] -= quantity
            if portfolio["positions"][symbol] == 0:
                del portfolio["positions"][symbol]

            return {
                "date": date,
                "symbol": symbol,
                "action": "SELL",
                "quantity": quantity,
                "price": execution_price,
                "commission": commission,
                "total_proceeds": total_proceeds,
                "reason": signal.get("reason", "")
            }

    def _calculate_portfolio_value(
        self,
        portfolio: Dict,
        current_prices: Dict[str, pd.Series]
    ) -> float:
        """计算投资组合总值"""
        total = portfolio["cash"]
        for symbol, quantity in portfolio["positions"].items():
            if symbol in current_prices:
                total += current_prices[symbol]["Close"] * quantity
        return total

    def _calculate_performance(
        self,
        equity_curve: List[Dict],
        trades: List[Dict],
        initial_capital: Decimal
    ) -> Dict[str, Any]:
        """计算绩效指标"""
        if not equity_curve:
            return {
                "total_return": 0,
                "annual_return": 0,
                "sharpe_ratio": None,
                "max_drawdown": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "avg_win": 0,
                "avg_loss": 0
            }

        # 转换为DataFrame便于计算
        df = pd.DataFrame(equity_curve)
        df.set_index("date", inplace=True)

        # 总回报率
        final_value = df["value"].iloc[-1]
        total_return = (final_value - float(initial_capital)) / float(initial_capital)

        # 年化回报率
        days = (df.index[-1] - df.index[0]).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 夏普比率
        returns = df["value"].pct_change().dropna()
        sharpe_ratio = None
        if len(returns) > 1 and returns.std() != 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # 年化

        # 最大回撤
        cummax = df["value"].cummax()
        drawdown = (df["value"] - cummax) / cummax
        max_drawdown = abs(drawdown.min())

        # 交易统计
        winning_trades = [t for t in trades if self._is_winning_trade(t, trades)]
        losing_trades = [t for t in trades if self._is_losing_trade(t, trades)]

        win_rate = len(winning_trades) / len(trades) if trades else 0

        total_profit = sum(self._get_trade_profit(t, trades) for t in winning_trades)
        total_loss = abs(sum(self._get_trade_profit(t, trades) for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        avg_win = total_profit / len(winning_trades) if winning_trades else 0
        avg_loss = total_loss / len(losing_trades) if losing_trades else 0

        return {
            "total_return": round(total_return * 100, 2),  # 百分比
            "annual_return": round(annual_return * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio else None,
            "max_drawdown": round(max_drawdown * 100, 2),
            "win_rate": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades)
        }

    def _is_winning_trade(self, trade: Dict, all_trades: List[Dict]) -> bool:
        """判断是否为盈利交易"""
        if trade["action"] == "SELL":
            # 找到对应的买入交易
            buy_trade = self._find_matching_buy(trade, all_trades)
            if buy_trade:
                return trade["price"] > buy_trade["price"]
        return False

    def _is_losing_trade(self, trade: Dict, all_trades: List[Dict]) -> bool:
        """判断是否为亏损交易"""
        if trade["action"] == "SELL":
            buy_trade = self._find_matching_buy(trade, all_trades)
            if buy_trade:
                return trade["price"] < buy_trade["price"]
        return False

    def _get_trade_profit(self, trade: Dict, all_trades: List[Dict]) -> float:
        """计算交易盈亏"""
        if trade["action"] == "SELL":
            buy_trade = self._find_matching_buy(trade, all_trades)
            if buy_trade:
                return (trade["price"] - buy_trade["price"]) * trade["quantity"]
        return 0

    def _find_matching_buy(self, sell_trade: Dict, all_trades: List[Dict]) -> Optional[Dict]:
        """找到对应的买入交易"""
        for trade in reversed(all_trades):
            if (trade["action"] == "BUY" and
                trade["symbol"] == sell_trade["symbol"] and
                trade["date"] < sell_trade["date"]):
                return trade
        return None
