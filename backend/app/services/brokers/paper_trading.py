"""
模拟交易券商实现
提供完整的模拟交易功能，用于测试和演示
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from .base import (
    BrokerInterface,
    OrderRequest,
    OrderResponse,
    Position,
    AccountInfo,
    OrderStatus,
    OrderType,
    OrderSide,
    TimeInForce,
    BrokerError,
    OrderRejectedException,
    InsufficientFundsException,
    MarketClosedException
)
from ..market_data import MarketDataService

logger = logging.getLogger(__name__)


class PaperTradingBroker(BrokerInterface):
    """模拟交易券商实现"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化模拟交易券商
        
        Args:
            config: 配置参数，包含初始资金等
        """
        super().__init__(config)
        
        # 初始化账户信息
        self.account_info = AccountInfo(
            account_id=config.get("account_id", "PAPER_ACCOUNT"),
            cash_balance=config.get("initial_cash", 100000.0),
            total_value=config.get("initial_cash", 100000.0),
            buying_power=config.get("initial_cash", 100000.0) * 4,  # 4倍杠杆
            day_trading_buying_power=config.get("initial_cash", 100000.0) * 4,
            maintenance_margin=0.0,
            currency="USD"
        )
        
        # 内存存储
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, OrderResponse] = {}
        self.pending_orders: Dict[str, OrderRequest] = {}
        
        # 市场数据服务
        self.market_service: Optional[MarketDataService] = None
        
        # 运行中的订单监控任务
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # 交易记录
        self.trade_history: List[Dict[str, Any]] = []
        
        logger.info("Paper trading broker initialized with ${:,.2f}".format(
            self.account_info.cash_balance
        ))
    
    async def connect(self) -> bool:
        """连接到模拟交易系统"""
        try:
            # 初始化市场数据服务
            from ..market_data import get_market_service
            self.market_service = await get_market_service()
            
            self.is_connected = True
            logger.info("Paper trading broker connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect paper trading broker: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        # 取消所有监控任务
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        # 等待任务完成
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
        
        self.monitoring_tasks.clear()
        self.is_connected = False
        logger.info("Paper trading broker disconnected")
    
    async def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        # 更新总价值
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        self.account_info.total_value = self.account_info.cash_balance + total_position_value
        self.account_info.buying_power = self.account_info.cash_balance * 4  # 更新购买力
        
        return self.account_info
    
    async def get_positions(self) -> List[Position]:
        """获取所有持仓"""
        # 更新持仓的当前价格和市场价值
        for position in self.positions.values():
            await self._update_position_value(position)
        
        return list(self.positions.values())
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """获取特定股票的持仓"""
        symbol = symbol.upper()
        if symbol in self.positions:
            await self._update_position_value(self.positions[symbol])
            return self.positions[symbol]
        return None
    
    async def _update_position_value(self, position: Position):
        """更新持仓的市场价值"""
        if self.market_service:
            current_price = await self.market_service.get_real_time_price(position.symbol)
            if current_price:
                position.current_price = current_price
                position.market_value = position.quantity * current_price
                position.unrealized_pnl = position.market_value - (position.quantity * position.average_price)
                if position.average_price > 0:
                    position.unrealized_pnl_percent = (position.unrealized_pnl / (position.quantity * position.average_price)) * 100
    
    async def submit_order(self, order_request: OrderRequest) -> OrderResponse:
        """提交订单"""
        if not self.is_connected:
            raise BrokerError("Broker not connected")
        
        # 验证订单
        validation = await self.validate_order(order_request)
        if not validation["valid"]:
            raise OrderRejectedException(validation["error"])
        
        # 生成订单ID
        broker_order_id = f"PAPER_{uuid.uuid4().hex[:8].upper()}"
        
        # 创建订单响应
        order_response = OrderResponse(
            broker_order_id=broker_order_id,
            client_order_id=order_request.client_order_id,
            symbol=order_request.symbol.upper(),
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            filled_quantity=0.0,
            remaining_quantity=order_request.quantity,
            price=order_request.price,
            average_fill_price=None,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 存储订单
        self.orders[broker_order_id] = order_response
        self.pending_orders[broker_order_id] = order_request
        
        # 根据订单类型处理
        if order_request.order_type == OrderType.MARKET:
            # 市价单立即执行
            await self._execute_market_order(broker_order_id)
        else:
            # 其他订单类型启动监控
            task = asyncio.create_task(self._monitor_order(broker_order_id))
            self.monitoring_tasks[broker_order_id] = task
        
        logger.info(f"Order submitted: {broker_order_id} - {order_request.symbol} {order_request.side.value} {order_request.quantity}")
        return self.orders[broker_order_id]
    
    async def _execute_market_order(self, broker_order_id: str):
        """执行市价单"""
        order_response = self.orders[broker_order_id]
        order_request = self.pending_orders[broker_order_id]
        
        try:
            # 获取当前市价
            current_price = await self.market_service.get_real_time_price(order_response.symbol)
            if not current_price:
                order_response.status = OrderStatus.REJECTED
                order_response.message = "Unable to get market price"
                return
            
            # 执行交易
            await self._execute_trade(broker_order_id, current_price, order_request.quantity)
            
        except Exception as e:
            logger.error(f"Market order execution failed: {e}")
            order_response.status = OrderStatus.REJECTED
            order_response.message = str(e)
    
    async def _monitor_order(self, broker_order_id: str):
        """监控订单执行条件"""
        order_response = self.orders[broker_order_id]
        order_request = self.pending_orders[broker_order_id]
        
        try:
            while order_response.status == OrderStatus.PENDING:
                # 检查时间限制
                if order_request.time_in_force == TimeInForce.DAY:
                    if datetime.utcnow().date() > order_response.created_at.date():
                        order_response.status = OrderStatus.EXPIRED
                        order_response.message = "Order expired (DAY time in force)"
                        break
                
                # 获取当前价格
                current_price = await self.market_service.get_real_time_price(order_response.symbol)
                if not current_price:
                    await asyncio.sleep(5)
                    continue
                
                should_execute = False
                execution_price = current_price
                
                # 检查执行条件
                if order_request.order_type == OrderType.LIMIT:
                    if order_request.side == OrderSide.BUY and current_price <= order_request.price:
                        should_execute = True
                        execution_price = order_request.price
                    elif order_request.side == OrderSide.SELL and current_price >= order_request.price:
                        should_execute = True
                        execution_price = order_request.price
                
                elif order_request.order_type == OrderType.STOP_LOSS:
                    if order_request.side == OrderSide.SELL and current_price <= order_request.stop_price:
                        should_execute = True
                        execution_price = current_price
                
                elif order_request.order_type == OrderType.TAKE_PROFIT:
                    if order_request.side == OrderSide.SELL and current_price >= order_request.take_profit_price:
                        should_execute = True
                        execution_price = current_price
                
                elif order_request.order_type == OrderType.STOP_LIMIT:
                    if order_request.side == OrderSide.BUY:
                        if current_price >= order_request.stop_price and current_price <= order_request.price:
                            should_execute = True
                            execution_price = order_request.price
                    else:  # SELL
                        if current_price <= order_request.stop_price and current_price >= order_request.price:
                            should_execute = True
                            execution_price = order_request.price
                
                # 执行订单
                if should_execute:
                    await self._execute_trade(broker_order_id, execution_price, order_request.quantity)
                    break
                
                # 等待5秒再检查
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info(f"Order monitoring cancelled: {broker_order_id}")
        except Exception as e:
            logger.error(f"Order monitoring error: {e}")
            order_response.status = OrderStatus.REJECTED
            order_response.message = str(e)
        finally:
            # 清理任务引用
            if broker_order_id in self.monitoring_tasks:
                del self.monitoring_tasks[broker_order_id]
            if broker_order_id in self.pending_orders:
                del self.pending_orders[broker_order_id]
    
    async def _execute_trade(self, broker_order_id: str, execution_price: float, quantity: float):
        """执行交易"""
        order_response = self.orders[broker_order_id]
        order_request = self.pending_orders[broker_order_id]
        
        try:
            trade_value = quantity * execution_price
            commission = await self.calculate_commission(order_request, execution_price)
            
            if order_request.side == OrderSide.BUY:
                # 买入检查
                total_cost = trade_value + commission
                if self.account_info.cash_balance < total_cost:
                    raise InsufficientFundsException("Insufficient cash balance")
                
                # 更新现金余额
                self.account_info.cash_balance -= total_cost
                
                # 更新持仓
                symbol = order_response.symbol
                if symbol in self.positions:
                    # 更新现有持仓
                    pos = self.positions[symbol]
                    total_cost_basis = (pos.quantity * pos.average_price) + trade_value
                    pos.quantity += quantity
                    pos.average_price = total_cost_basis / pos.quantity
                else:
                    # 创建新持仓
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=quantity,
                        average_price=execution_price,
                        current_price=execution_price,
                        market_value=trade_value,
                        unrealized_pnl=0.0,
                        unrealized_pnl_percent=0.0,
                        side="long"
                    )
                
            else:  # SELL
                # 卖出检查
                symbol = order_response.symbol
                if symbol not in self.positions or self.positions[symbol].quantity < quantity:
                    raise OrderRejectedException("Insufficient position to sell")
                
                # 更新持仓
                pos = self.positions[symbol]
                pos.quantity -= quantity
                
                # 如果卖完了就删除持仓
                if pos.quantity <= 0:
                    del self.positions[symbol]
                
                # 更新现金余额
                net_proceeds = trade_value - commission
                self.account_info.cash_balance += net_proceeds
            
            # 更新订单状态
            order_response.status = OrderStatus.FILLED
            order_response.filled_quantity = quantity
            order_response.remaining_quantity = 0.0
            order_response.average_fill_price = execution_price
            order_response.commission = commission
            order_response.updated_at = datetime.utcnow()
            order_response.message = "Order filled successfully"
            
            # 记录交易历史
            self.trade_history.append({
                "broker_order_id": broker_order_id,
                "symbol": order_response.symbol,
                "side": order_request.side.value,
                "quantity": quantity,
                "price": execution_price,
                "commission": commission,
                "timestamp": datetime.utcnow(),
                "trade_value": trade_value
            })
            
            logger.info(f"Trade executed: {broker_order_id} - {order_response.symbol} {order_request.side.value} {quantity} @ ${execution_price:.2f}")
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            order_response.status = OrderStatus.REJECTED
            order_response.message = str(e)
    
    async def cancel_order(self, broker_order_id: str) -> bool:
        """取消订单"""
        if broker_order_id not in self.orders:
            return False
        
        order_response = self.orders[broker_order_id]
        
        if order_response.status != OrderStatus.PENDING:
            return False
        
        # 取消监控任务
        if broker_order_id in self.monitoring_tasks:
            self.monitoring_tasks[broker_order_id].cancel()
            del self.monitoring_tasks[broker_order_id]
        
        # 更新订单状态
        order_response.status = OrderStatus.CANCELLED
        order_response.updated_at = datetime.utcnow()
        order_response.message = "Order cancelled by user"
        
        # 清理待处理订单
        if broker_order_id in self.pending_orders:
            del self.pending_orders[broker_order_id]
        
        logger.info(f"Order cancelled: {broker_order_id}")
        return True
    
    async def get_order_status(self, broker_order_id: str) -> Optional[OrderResponse]:
        """获取订单状态"""
        return self.orders.get(broker_order_id)
    
    async def get_orders(
        self, 
        status: Optional[OrderStatus] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[OrderResponse]:
        """获取订单列表"""
        orders = list(self.orders.values())
        
        # 应用过滤器
        if status:
            orders = [o for o in orders if o.status == status]
        if symbol:
            symbol = symbol.upper()
            orders = [o for o in orders if o.symbol == symbol]
        
        # 按创建时间倒序排列
        orders.sort(key=lambda x: x.created_at, reverse=True)
        
        return orders[:limit]
    
    async def get_market_price(self, symbol: str) -> Optional[float]:
        """获取市场价格"""
        if self.market_service:
            return await self.market_service.get_real_time_price(symbol.upper())
        return None
    
    async def validate_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """验证订单"""
        # 先执行基础验证
        base_validation = await super().validate_order(order_request)
        if not base_validation["valid"]:
            return base_validation
        
        # 检查市场是否开放（模拟交易可能不需要）
        market_open_check = self.config.get("check_market_hours", False)
        if market_open_check and not self.is_market_open():
            return {"valid": False, "error": "Market is closed"}
        
        # 检查资金充足性（买入订单）
        if order_request.side == OrderSide.BUY:
            estimated_price = order_request.price
            if not estimated_price:
                # 获取市场价格估算
                estimated_price = await self.get_market_price(order_request.symbol)
                if not estimated_price:
                    return {"valid": False, "error": "Unable to get market price for validation"}
            
            estimated_cost = order_request.quantity * estimated_price
            estimated_commission = estimated_cost * self.config.get("commission_rate", 0.001)
            total_cost = estimated_cost + estimated_commission
            
            if self.account_info.cash_balance < total_cost:
                return {"valid": False, "error": "Insufficient cash balance"}
        
        # 检查持仓充足性（卖出订单）
        elif order_request.side == OrderSide.SELL:
            symbol = order_request.symbol.upper()
            if symbol in self.positions:
                available_quantity = self.positions[symbol].quantity
                if available_quantity < order_request.quantity:
                    return {"valid": False, "error": "Insufficient position to sell"}
            else:
                return {"valid": False, "error": "No position to sell"}
        
        return {"valid": True, "error": None}
    
    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取交易历史"""
        return self.trade_history[-limit:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取模拟交易表现摘要"""
        initial_cash = self.config.get("initial_cash", 100000.0)
        current_total = self.account_info.cash_balance + sum(pos.market_value for pos in self.positions.values())
        
        total_pnl = current_total - initial_cash
        total_return = (total_pnl / initial_cash) * 100 if initial_cash > 0 else 0
        
        return {
            "initial_cash": initial_cash,
            "current_cash": self.account_info.cash_balance,
            "current_total_value": current_total,
            "total_pnl": total_pnl,
            "total_return_percent": total_return,
            "total_trades": len(self.trade_history),
            "active_positions": len(self.positions),
            "pending_orders": len([o for o in self.orders.values() if o.status == OrderStatus.PENDING])
        }