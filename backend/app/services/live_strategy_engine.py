"""
实盘策略执行引擎
提供实时策略执行、信号监控和自动交易功能
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from sqlalchemy.orm import Session
import logging

from ..models import Strategy, Portfolio, Trade
from .market_data import MarketDataService
from .order_engine import OrderExecutionEngine as OrderEngine
from .technical_indicators import TechnicalIndicators
from .risk_management import RiskManager as RiskManagementService

logger = logging.getLogger(__name__)


class LiveStrategyEngine:
    """实盘策略执行引擎"""

    def __init__(
        self,
        market_data_service: MarketDataService,
        order_engine: OrderEngine,
        risk_service: RiskManagementService
    ):
        self.market_data_service = market_data_service
        self.order_engine = order_engine
        self.risk_service = risk_service
        self.running_strategies: Dict[int, Dict] = {}  # strategy_id -> execution context

    async def start_strategy(
        self,
        db: Session,
        strategy_id: int,
        portfolio_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        启动实盘策略

        Args:
            db: 数据库会话
            strategy_id: 策略ID
            portfolio_id: 投资组合ID
            user_id: 用户ID

        Returns:
            启动结果
        """
        # 检查策略是否已在运行
        if strategy_id in self.running_strategies:
            return {
                "success": False,
                "message": "Strategy is already running"
            }

        # 获取策略
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return {
                "success": False,
                "message": f"Strategy {strategy_id} not found"
            }

        # 获取投资组合
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            return {
                "success": False,
                "message": f"Portfolio {portfolio_id} not found"
            }

        # 风险检查
        risk_assessment = await self.risk_service.assess_portfolio_risk(
            portfolio_id, db, user_id
        )

        if not risk_assessment["can_trade"]:
            return {
                "success": False,
                "message": "Risk limits exceeded",
                "risk_assessment": risk_assessment
            }

        # 创建执行上下文
        execution_context = {
            "strategy_id": strategy_id,
            "portfolio_id": portfolio_id,
            "user_id": user_id,
            "strategy": strategy,
            "portfolio": portfolio,
            "status": "running",
            "start_time": datetime.now(),
            "positions": {},
            "last_signal_time": None
        }

        self.running_strategies[strategy_id] = execution_context

        # 启动策略监控任务
        asyncio.create_task(
            self._monitor_strategy(db, execution_context)
        )

        logger.info(f"Started live strategy {strategy_id} for portfolio {portfolio_id}")

        return {
            "success": True,
            "message": "Strategy started successfully",
            "strategy_id": strategy_id,
            "portfolio_id": portfolio_id
        }

    async def stop_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """
        停止实盘策略

        Args:
            strategy_id: 策略ID

        Returns:
            停止结果
        """
        if strategy_id not in self.running_strategies:
            return {
                "success": False,
                "message": "Strategy is not running"
            }

        context = self.running_strategies[strategy_id]
        context["status"] = "stopped"
        context["stop_time"] = datetime.now()

        # 从运行列表中移除
        del self.running_strategies[strategy_id]

        logger.info(f"Stopped live strategy {strategy_id}")

        return {
            "success": True,
            "message": "Strategy stopped successfully",
            "strategy_id": strategy_id,
            "runtime": (context["stop_time"] - context["start_time"]).total_seconds()
        }

    async def _monitor_strategy(self, db: Session, context: Dict[str, Any]):
        """
        监控策略执行

        Args:
            db: 数据库会话
            context: 执行上下文
        """
        strategy = context["strategy"]
        params = strategy.parameters or {}
        symbols = params.get("symbols", [])
        check_interval = params.get("check_interval", 60)  # 默认60秒检查一次

        logger.info(f"Monitoring strategy {strategy.id} for symbols {symbols}")

        while context["status"] == "running":
            try:
                # 获取实时市场数据
                current_prices = {}
                historical_data = {}

                for symbol in symbols:
                    try:
                        # 获取当前价格
                        quote = await self.market_data_service.get_real_time_quote(symbol)
                        current_prices[symbol] = quote

                        # 获取历史数据用于指标计算
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=100)  # 获取100天数据
                        df = await self.market_data_service.get_historical_data(
                            symbol, start_date, end_date
                        )
                        historical_data[symbol] = df

                    except Exception as e:
                        logger.error(f"Failed to get data for {symbol}: {e}")

                # 生成交易信号
                signals = self._generate_live_signals(
                    strategy,
                    current_prices,
                    historical_data,
                    context
                )

                # 执行交易
                for signal in signals:
                    await self._execute_live_trade(db, signal, context)

                # 等待下一次检查
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in strategy monitoring: {e}")
                await asyncio.sleep(check_interval)

        logger.info(f"Strategy {strategy.id} monitoring stopped")

    def _generate_live_signals(
        self,
        strategy: Strategy,
        current_prices: Dict[str, Dict],
        historical_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        生成实盘交易信号

        Args:
            strategy: 策略对象
            current_prices: 当前价格数据
            historical_data: 历史数据
            context: 执行上下文

        Returns:
            信号列表
        """
        signals = []
        params = strategy.parameters or {}
        strategy_type = params.get("strategy_type", "simple_ma")

        if strategy_type == "simple_ma":
            signals = self._simple_ma_live(params, current_prices, historical_data, context)
        elif strategy_type == "rsi":
            signals = self._rsi_live(params, current_prices, historical_data, context)
        elif strategy_type == "macd":
            signals = self._macd_live(params, current_prices, historical_data, context)

        return signals

    def _simple_ma_live(
        self,
        params: Dict,
        current_prices: Dict[str, Dict],
        historical_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """简单移动平均线实盘信号"""
        signals = []
        short_window = params.get("short_window", 20)
        long_window = params.get("long_window", 50)

        for symbol, price_data in current_prices.items():
            if symbol not in historical_data:
                continue

            df = historical_data[symbol]
            if len(df) < long_window:
                continue

            # 计算当前移动平均
            short_ma = df['Close'].rolling(window=short_window).mean().iloc[-1]
            long_ma = df['Close'].rolling(window=long_window).mean().iloc[-1]

            # 前一个值
            prev_short_ma = df['Close'].rolling(window=short_window).mean().iloc[-2]
            prev_long_ma = df['Close'].rolling(window=long_window).mean().iloc[-2]

            current_position = context["positions"].get(symbol, 0)

            # 金叉 - 买入信号
            if prev_short_ma <= prev_long_ma and short_ma > long_ma and current_position == 0:
                signals.append({
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": params.get("position_size", 100),
                    "price": price_data["current_price"],
                    "reason": f"Golden Cross: Short MA ({short_ma:.2f}) > Long MA ({long_ma:.2f})"
                })

            # 死叉 - 卖出信号
            elif prev_short_ma >= prev_long_ma and short_ma < long_ma and current_position > 0:
                signals.append({
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": current_position,
                    "price": price_data["current_price"],
                    "reason": f"Death Cross: Short MA ({short_ma:.2f}) < Long MA ({long_ma:.2f})"
                })

        return signals

    def _rsi_live(
        self,
        params: Dict,
        current_prices: Dict[str, Dict],
        historical_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """RSI策略实盘信号"""
        signals = []
        rsi_period = params.get("rsi_period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)

        for symbol, price_data in current_prices.items():
            if symbol not in historical_data:
                continue

            df = historical_data[symbol]
            if len(df) < rsi_period + 1:
                continue

            # 计算RSI
            rsi = TechnicalIndicators.rsi(df['Close'], rsi_period)
            if len(rsi) < 2:
                continue

            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]
            current_position = context["positions"].get(symbol, 0)

            # 超卖反转 - 买入
            if prev_rsi <= oversold and current_rsi > oversold and current_position == 0:
                signals.append({
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": params.get("position_size", 100),
                    "price": price_data["current_price"],
                    "reason": f"RSI oversold reversal: {current_rsi:.2f}"
                })

            # 超买反转 - 卖出
            elif prev_rsi >= overbought and current_rsi < overbought and current_position > 0:
                signals.append({
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": current_position,
                    "price": price_data["current_price"],
                    "reason": f"RSI overbought reversal: {current_rsi:.2f}"
                })

        return signals

    def _macd_live(
        self,
        params: Dict,
        current_prices: Dict[str, Dict],
        historical_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """MACD策略实盘信号"""
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
            macd_line, signal_line, macd_histogram = TechnicalIndicators.macd(
                df['Close'], fast_period, slow_period, signal_period
            )

            if len(macd_histogram) < 2:
                continue

            current_histogram = macd_histogram.iloc[-1]
            prev_histogram = macd_histogram.iloc[-2]
            current_position = context["positions"].get(symbol, 0)

            # 多头交叉 - 买入
            if prev_histogram <= 0 and current_histogram > 0 and current_position == 0:
                signals.append({
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": params.get("position_size", 100),
                    "price": price_data["current_price"],
                    "reason": f"MACD bullish crossover: {current_histogram:.2f}"
                })

            # 空头交叉 - 卖出
            elif prev_histogram >= 0 and current_histogram < 0 and current_position > 0:
                signals.append({
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": current_position,
                    "price": price_data["current_price"],
                    "reason": f"MACD bearish crossover: {current_histogram:.2f}"
                })

        return signals

    async def _execute_live_trade(
        self,
        db: Session,
        signal: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """
        执行实盘交易

        Args:
            db: 数据库会话
            signal: 交易信号
            context: 执行上下文
        """
        try:
            # 提交订单
            result = await self.order_engine.submit_order(
                db=db,
                user_id=context["user_id"],
                portfolio_id=context["portfolio_id"],
                symbol=signal["symbol"],
                action=signal["action"],
                quantity=Decimal(str(signal["quantity"])),
                order_type="MARKET",
                price=Decimal(str(signal.get("price", 0)))
            )

            if result["success"]:
                # 更新持仓记录
                if signal["action"] == "BUY":
                    context["positions"][signal["symbol"]] = \
                        context["positions"].get(signal["symbol"], 0) + signal["quantity"]
                else:
                    context["positions"][signal["symbol"]] = 0

                context["last_signal_time"] = datetime.now()

                logger.info(
                    f"Live trade executed: {signal['action']} {signal['quantity']} "
                    f"{signal['symbol']} @ {signal['price']:.2f} - {signal['reason']}"
                )
            else:
                logger.error(f"Failed to execute live trade: {result.get('message')}")

        except Exception as e:
            logger.error(f"Error executing live trade: {e}")

    def get_running_strategies(self) -> List[Dict[str, Any]]:
        """获取所有运行中的策略"""
        return [
            {
                "strategy_id": context["strategy_id"],
                "portfolio_id": context["portfolio_id"],
                "status": context["status"],
                "start_time": context["start_time"].isoformat(),
                "positions": context["positions"],
                "last_signal_time": context["last_signal_time"].isoformat()
                    if context["last_signal_time"] else None
            }
            for context in self.running_strategies.values()
        ]

    def get_strategy_status(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """获取特定策略的运行状态"""
        if strategy_id not in self.running_strategies:
            return None

        context = self.running_strategies[strategy_id]
        return {
            "strategy_id": strategy_id,
            "portfolio_id": context["portfolio_id"],
            "status": context["status"],
            "start_time": context["start_time"].isoformat(),
            "runtime_seconds": (datetime.now() - context["start_time"]).total_seconds(),
            "positions": context["positions"],
            "last_signal_time": context["last_signal_time"].isoformat()
                if context["last_signal_time"] else None
        }
