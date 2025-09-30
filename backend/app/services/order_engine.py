"""
订单执行引擎
处理各种订单类型的执行逻辑，包括市价单、限价单、止损单、止盈单等
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import logging

from .. import models, schemas, crud
from ..database import SessionLocal
from .market_data import MarketDataService, get_market_service
from .cache import CacheService, get_cache_service

logger = logging.getLogger(__name__)


class OrderExecutionEngine:
    """订单执行引擎"""
    
    def __init__(self):
        self.market_service = None
        self.cache_service = None
        self.running_orders: Dict[int, asyncio.Task] = {}  # 活跃的订单监控任务
        self.execution_rules = {
            "max_order_value": 100000.0,  # 单笔订单最大金额
            "max_position_ratio": 0.3,    # 单个标的最大仓位比例
            "min_cash_ratio": 0.1,        # 最小现金比例
            "price_deviation_limit": 0.05  # 价格偏差限制（5%）
        }
    
    async def _initialize_services(self):
        """初始化服务依赖"""
        if self.market_service is None:
            self.market_service = await get_market_service()
        if self.cache_service is None:
            self.cache_service = await get_cache_service()
    
    async def _log_trading_action(
        self,
        db: Session,
        user_id: int,
        action: models.TradingAction,
        portfolio_id: Optional[int] = None,
        trade_id: Optional[int] = None,
        symbol: Optional[str] = None,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        amount: Optional[float] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录交易行为审计日志"""
        try:
            audit_log = models.TradingAuditLog(
                user_id=user_id,
                portfolio_id=portfolio_id,
                trade_id=trade_id,
                action=action,
                symbol=symbol,
                quantity=quantity,
                price=price,
                amount=amount,
                old_values=old_values,
                new_values=new_values,
                message=message,
                extra_data=extra_data,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.utcnow()
            )
            db.add(audit_log)
            # 不在这里提交，让调用者决定何时提交
            logger.info(f"Trading action logged: {action.value} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log trading action: {e}")
            # 不回滚，让调用者处理
    
    async def _log_order_state_change(
        self,
        db: Session,
        trade_id: int,
        previous_status: Optional[models.OrderStatus],
        new_status: models.OrderStatus,
        filled_quantity: float = 0.0,
        remaining_quantity: float = 0.0,
        fill_price: Optional[float] = None,
        commission: float = 0.0,
        reason: Optional[str] = None,
        broker_order_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """记录订单状态变更日志"""
        try:
            state_log = models.OrderStateLog(
                trade_id=trade_id,
                previous_status=previous_status,
                new_status=new_status,
                filled_quantity=filled_quantity,
                remaining_quantity=remaining_quantity,
                fill_price=fill_price,
                commission=commission,
                reason=reason,
                broker_order_id=broker_order_id,
                extra_data=extra_data,
                created_at=datetime.utcnow()
            )
            db.add(state_log)
            # 不在这里提交，让调用者决定何时提交
            logger.info(f"Order state change logged: {trade_id} {previous_status} -> {new_status}")
        except Exception as e:
            logger.error(f"Failed to log order state change: {e}")
            # 不回滚，让调用者处理
    
    async def _log_risk_event(
        self,
        db: Session,
        user_id: int,
        risk_type: str,
        risk_level: models.RiskLevel,
        current_value: float,
        limit_value: float,
        message: str,
        portfolio_id: Optional[int] = None,
        trade_id: Optional[int] = None,
        symbol: Optional[str] = None,
        actions_taken: Optional[Dict[str, Any]] = None
    ):
        """记录风险事件"""
        try:
            risk_event = models.RiskEvent(
                user_id=user_id,
                portfolio_id=portfolio_id,
                trade_id=trade_id,
                risk_type=risk_type,
                risk_level=risk_level,
                current_value=current_value,
                limit_value=limit_value,
                threshold_exceeded=True,
                symbol=symbol,
                message=message,
                actions_taken=actions_taken,
                resolved=False,
                created_at=datetime.utcnow()
            )
            db.add(risk_event)
            # 不在这里提交，让调用者决定何时提交
            logger.warning(f"Risk event logged: {risk_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log risk event: {e}")
            # 不回滚，让调用者处理
    
    async def _log_compliance_check(
        self,
        db: Session,
        user_id: int,
        check_type: str,
        check_result: str,
        rule_name: str,
        rule_description: str,
        trade_id: Optional[int] = None,
        violation_details: Optional[Dict[str, Any]] = None,
        action_required: Optional[str] = None,
        action_taken: Optional[str] = None
    ):
        """记录合规检查"""
        try:
            compliance_check = models.ComplianceCheck(
                user_id=user_id,
                trade_id=trade_id,
                check_type=check_type,
                check_result=check_result,
                rule_name=rule_name,
                rule_description=rule_description,
                violation_details=violation_details,
                action_required=action_required,
                action_taken=action_taken,
                checked_at=datetime.utcnow()
            )
            db.add(compliance_check)
            # 不在这里提交，让调用者决定何时提交
            logger.info(f"Compliance check logged: {check_type} - {check_result} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log compliance check: {e}")
            # 不回滚，让调用者处理
    
    async def _create_bracket_order(
        self,
        db: Session,
        parent_order: models.Trade,
        order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建括号订单（包含主订单、止损单和止盈单）
        
        Args:
            db: 数据库会话
            parent_order: 主订单
            order_data: 订单数据
            
        Returns:
            创建结果
        """
        try:
            stop_price = order_data.get("stop_price")
            take_profit_price = order_data.get("take_profit_price")
            
            if not stop_price and not take_profit_price:
                return {
                    "success": False,
                    "message": "括号订单必须提供止损价格或止盈价格"
                }
            
            bracket_orders = []
            
            # 如果是市价单，立即执行主订单
            if parent_order.advanced_order_type == "MARKET":
                execution_result = await self._execute_market_order(db, parent_order)
                if not execution_result["success"]:
                    return execution_result
                
                # 主订单执行成功后，创建保护性订单
                if stop_price and parent_order.order_type == "buy":
                    # 买入后的止损单（卖出）
                    stop_loss_order = models.Trade(
                        user_id=parent_order.user_id,
                        portfolio_id=parent_order.portfolio_id,
                        symbol=parent_order.symbol,
                        order_type="sell",
                        advanced_order_type="STOP_LOSS",
                        quantity=parent_order.quantity,
                        price=0,  # 市价执行
                        stop_price=stop_price,
                        time_in_force=parent_order.time_in_force,
                        status="pending",
                        strategy_id=parent_order.strategy_id,
                        notes=f"括号订单止损单，关联主订单 {parent_order.id}"
                    )
                    db.add(stop_loss_order)
                    db.flush()
                    bracket_orders.append(stop_loss_order)
                    
                    # 记录止损单创建
                    await self._log_trading_action(
                        db=db,
                        user_id=parent_order.user_id,
                        action=models.TradingAction.ORDER_SUBMITTED,
                        portfolio_id=parent_order.portfolio_id,
                        trade_id=stop_loss_order.id,
                        symbol=parent_order.symbol,
                        quantity=parent_order.quantity,
                        price=stop_price,
                        message=f"括号订单止损单已创建，止损价: ${stop_price:.2f}",
                        extra_data={
                            "order_type": "STOP_LOSS",
                            "parent_order_id": parent_order.id,
                            "bracket_component": "stop_loss"
                        }
                    )
                
                if take_profit_price and parent_order.order_type == "buy":
                    # 买入后的止盈单（卖出）
                    take_profit_order = models.Trade(
                        user_id=parent_order.user_id,
                        portfolio_id=parent_order.portfolio_id,
                        symbol=parent_order.symbol,
                        order_type="sell",
                        advanced_order_type="TAKE_PROFIT",
                        quantity=parent_order.quantity,
                        price=0,  # 市价执行
                        take_profit_price=take_profit_price,
                        time_in_force=parent_order.time_in_force,
                        status="pending",
                        strategy_id=parent_order.strategy_id,
                        notes=f"括号订单止盈单，关联主订单 {parent_order.id}"
                    )
                    db.add(take_profit_order)
                    db.flush()
                    bracket_orders.append(take_profit_order)
                    
                    # 记录止盈单创建
                    await self._log_trading_action(
                        db=db,
                        user_id=parent_order.user_id,
                        action=models.TradingAction.ORDER_SUBMITTED,
                        portfolio_id=parent_order.portfolio_id,
                        trade_id=take_profit_order.id,
                        symbol=parent_order.symbol,
                        quantity=parent_order.quantity,
                        price=take_profit_price,
                        message=f"括号订单止盈单已创建，止盈价: ${take_profit_price:.2f}",
                        extra_data={
                            "order_type": "TAKE_PROFIT",
                            "parent_order_id": parent_order.id,
                            "bracket_component": "take_profit"
                        }
                    )
                
                db.commit()
                
                # 启动保护性订单监控
                for order in bracket_orders:
                    task = asyncio.create_task(
                        self._monitor_bracket_order(order.id, parent_order.id)
                    )
                    self.running_orders[order.id] = task
                
                return {
                    "success": True,
                    "message": f"括号订单创建成功，主订单已执行，创建了{len(bracket_orders)}个保护性订单",
                    "parent_order_id": parent_order.id,
                    "bracket_orders": [order.id for order in bracket_orders],
                    "execution_price": parent_order.price
                }
            
            else:
                # 限价单等其他类型的括号订单
                # 主订单尚未执行，需要等待执行后再创建保护性订单
                task = asyncio.create_task(
                    self._monitor_bracket_parent_order(parent_order.id, order_data)
                )
                self.running_orders[parent_order.id] = task
                
                return {
                    "success": True,
                    "message": "括号订单已提交，等待主订单执行后创建保护性订单",
                    "parent_order_id": parent_order.id
                }
                
        except Exception as e:
            logger.error(f"创建括号订单失败: {e}")
            db.rollback()
            return {
                "success": False,
                "message": f"创建括号订单失败: {str(e)}"
            }
    
    async def _monitor_bracket_parent_order(
        self,
        parent_order_id: int,
        order_data: Dict[str, Any]
    ):
        """监控括号订单的主订单执行"""
        try:
            db = SessionLocal()
            
            try:
                parent_order = db.query(models.Trade).filter(
                    models.Trade.id == parent_order_id
                ).first()
                
                if not parent_order:
                    return
                
                # 监控主订单直到执行
                while True:
                    db.refresh(parent_order)
                    
                    if parent_order.status == "executed":
                        # 主订单执行成功，创建保护性订单
                        await self._create_protective_orders(db, parent_order, order_data)
                        break
                    elif parent_order.status in ["canceled", "failed"]:
                        # 主订单失败或取消，不需要创建保护性订单
                        logger.info(f"主订单 {parent_order_id} 状态为 {parent_order.status}，取消创建保护性订单")
                        break
                    
                    await asyncio.sleep(5)
                    
            finally:
                db.close()
                if parent_order_id in self.running_orders:
                    del self.running_orders[parent_order_id]
                    
        except Exception as e:
            logger.error(f"监控括号订单主订单异常: {e}")
    
    async def _create_protective_orders(
        self,
        db: Session,
        parent_order: models.Trade,
        order_data: Dict[str, Any]
    ):
        """为已执行的主订单创建保护性订单"""
        try:
            stop_price = order_data.get("stop_price")
            take_profit_price = order_data.get("take_profit_price")
            bracket_orders = []
            
            if stop_price and parent_order.order_type == "buy":
                # 创建止损单
                stop_loss_order = models.Trade(
                    user_id=parent_order.user_id,
                    portfolio_id=parent_order.portfolio_id,
                    symbol=parent_order.symbol,
                    order_type="sell",
                    advanced_order_type="STOP_LOSS",
                    quantity=parent_order.quantity,
                    price=0,
                    stop_price=stop_price,
                    time_in_force=parent_order.time_in_force,
                    status="pending",
                    strategy_id=parent_order.strategy_id,
                    notes=f"括号订单止损单，关联主订单 {parent_order.id}"
                )
                db.add(stop_loss_order)
                db.flush()
                bracket_orders.append(stop_loss_order)
            
            if take_profit_price and parent_order.order_type == "buy":
                # 创建止盈单
                take_profit_order = models.Trade(
                    user_id=parent_order.user_id,
                    portfolio_id=parent_order.portfolio_id,
                    symbol=parent_order.symbol,
                    order_type="sell",
                    advanced_order_type="TAKE_PROFIT",
                    quantity=parent_order.quantity,
                    price=0,
                    take_profit_price=take_profit_price,
                    time_in_force=parent_order.time_in_force,
                    status="pending",
                    strategy_id=parent_order.strategy_id,
                    notes=f"括号订单止盈单，关联主订单 {parent_order.id}"
                )
                db.add(take_profit_order)
                db.flush()
                bracket_orders.append(take_profit_order)
            
            db.commit()
            
            # 启动保护性订单监控
            for order in bracket_orders:
                task = asyncio.create_task(
                    self._monitor_bracket_order(order.id, parent_order.id)
                )
                self.running_orders[order.id] = task
            
            logger.info(f"为主订单 {parent_order.id} 创建了 {len(bracket_orders)} 个保护性订单")
            
        except Exception as e:
            logger.error(f"创建保护性订单失败: {e}")
            db.rollback()
    
    async def _monitor_bracket_order(
        self,
        bracket_order_id: int,
        parent_order_id: int
    ):
        """监控括号订单中的保护性订单"""
        try:
            db = SessionLocal()
            
            try:
                bracket_order = db.query(models.Trade).filter(
                    models.Trade.id == bracket_order_id
                ).first()
                
                if not bracket_order:
                    return
                
                # 监控订单执行条件
                symbol = bracket_order.symbol
                order_type = bracket_order.advanced_order_type
                
                while True:
                    db.refresh(bracket_order)
                    
                    if bracket_order.status == "canceled":
                        break
                    
                    # 获取当前价格
                    current_price = await self.market_service.get_real_time_price(symbol)
                    if not current_price:
                        await asyncio.sleep(10)
                        continue
                    
                    should_execute = False
                    
                    # 检查执行条件
                    if order_type == "STOP_LOSS":
                        stop_price = bracket_order.stop_price
                        if current_price <= stop_price:
                            should_execute = True
                            
                            # 记录止损触发
                            await self._log_trading_action(
                                db=db,
                                user_id=bracket_order.user_id,
                                action=models.TradingAction.STOP_LOSS_TRIGGERED,
                                portfolio_id=bracket_order.portfolio_id,
                                trade_id=bracket_order.id,
                                symbol=symbol,
                                quantity=bracket_order.quantity,
                                price=current_price,
                                message=f"止损订单触发，当前价格: ${current_price:.2f}, 止损价: ${stop_price:.2f}",
                                extra_data={
                                    "trigger_price": current_price,
                                    "stop_price": stop_price,
                                    "parent_order_id": parent_order_id
                                }
                            )
                    
                    elif order_type == "TAKE_PROFIT":
                        take_profit_price = bracket_order.take_profit_price
                        if current_price >= take_profit_price:
                            should_execute = True
                            
                            # 记录止盈触发
                            await self._log_trading_action(
                                db=db,
                                user_id=bracket_order.user_id,
                                action=models.TradingAction.TAKE_PROFIT_TRIGGERED,
                                portfolio_id=bracket_order.portfolio_id,
                                trade_id=bracket_order.id,
                                symbol=symbol,
                                quantity=bracket_order.quantity,
                                price=current_price,
                                message=f"止盈订单触发，当前价格: ${current_price:.2f}, 止盈价: ${take_profit_price:.2f}",
                                extra_data={
                                    "trigger_price": current_price,
                                    "take_profit_price": take_profit_price,
                                    "parent_order_id": parent_order_id
                                }
                            )
                    
                    if should_execute:
                        # 执行订单
                        execution_result = await self._execute_trade(
                            db, bracket_order, current_price, bracket_order.quantity
                        )
                        
                        if execution_result["success"]:
                            bracket_order.status = "executed"
                            bracket_order.executed_at = datetime.utcnow()
                            bracket_order.price = current_price
                            bracket_order.profit_loss = execution_result.get("profit_loss", 0)
                            db.commit()
                            
                            # 取消同组的其他保护性订单（OCO逻辑）
                            await self._cancel_other_bracket_orders(
                                db, parent_order_id, bracket_order_id
                            )
                            
                            logger.info(f"括号订单 {bracket_order_id} 执行成功")
                        else:
                            bracket_order.status = "failed"
                            db.commit()
                            logger.error(f"括号订单 {bracket_order_id} 执行失败: {execution_result['message']}")
                        
                        break
                    
                    await asyncio.sleep(5)
                    
            finally:
                db.close()
                if bracket_order_id in self.running_orders:
                    del self.running_orders[bracket_order_id]
                    
        except Exception as e:
            logger.error(f"监控括号订单异常: {e}")
    
    async def _cancel_other_bracket_orders(
        self,
        db: Session,
        parent_order_id: int,
        executed_order_id: int
    ):
        """取消同组的其他保护性订单（OCO逻辑）"""
        try:
            # 查找同组的其他保护性订单
            other_orders = db.query(models.Trade).filter(
                models.Trade.notes.like(f"%关联主订单 {parent_order_id}%"),
                models.Trade.id != executed_order_id,
                models.Trade.status == "pending"
            ).all()
            
            for order in other_orders:
                order.status = "canceled"
                order.updated_at = datetime.utcnow()
                order.notes = f"{order.notes} - 因同组订单执行而自动取消"
                
                # 记录自动取消
                await self._log_trading_action(
                    db=db,
                    user_id=order.user_id,
                    action=models.TradingAction.ORDER_CANCELED,
                    portfolio_id=order.portfolio_id,
                    trade_id=order.id,
                    symbol=order.symbol,
                    quantity=order.quantity,
                    price=order.price,
                    message=f"因同组订单 {executed_order_id} 执行而自动取消",
                    extra_data={
                        "cancellation_reason": "bracket_order_oco",
                        "executed_order_id": executed_order_id,
                        "parent_order_id": parent_order_id
                    }
                )
                
                # 取消监控任务
                if order.id in self.running_orders:
                    self.running_orders[order.id].cancel()
                    del self.running_orders[order.id]
            
            db.commit()
            logger.info(f"因订单 {executed_order_id} 执行，取消了 {len(other_orders)} 个同组订单")
            
        except Exception as e:
            logger.error(f"取消同组订单失败: {e}")
            db.rollback()
    
    async def submit_order(
        self, 
        user_id: int,
        portfolio_id: int,
        symbol: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        time_in_force: str = "DAY",
        strategy_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        提交订单
        
        Args:
            user_id: 用户ID
            portfolio_id: 投资组合ID
            symbol: 股票代码
            order_type: 订单类型 (MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT, STOP_LIMIT)
            quantity: 数量（正数买入，负数卖出）
            price: 限价单价格
            stop_price: 止损价格
            take_profit_price: 止盈价格
            time_in_force: 有效期类型 (DAY, GTC, IOC, FOK)
            strategy_id: 策略ID
            
        Returns:
            订单提交结果
        """
        await self._initialize_services()
        
        try:
            db = SessionLocal()
            
            try:
                # 风险检查
                risk_check = await self._risk_check(
                    db, user_id, portfolio_id, symbol, quantity, price or 0
                )
                if not risk_check["passed"]:
                    # 记录风险事件
                    await self._log_risk_event(
                        db=db,
                        user_id=user_id,
                        portfolio_id=portfolio_id,
                        risk_type="order_risk_check",
                        risk_level=models.RiskLevel.HIGH,
                        current_value=abs(quantity) * (price or 0),
                        limit_value=risk_check.get("limit_value", 0),
                        message=f"订单风险检查失败: {risk_check['reason']}",
                        symbol=symbol,
                        actions_taken={"action": "order_rejected"}
                    )
                    
                    return {
                        "success": False,
                        "message": f"风险检查失败: {risk_check['reason']}",
                        "order_id": None
                    }
                
                # 创建订单记录
                order_data = {
                    "user_id": user_id,
                    "portfolio_id": portfolio_id,
                    "symbol": symbol,
                    "order_type": "buy" if quantity > 0 else "sell",
                    "advanced_order_type": order_type,
                    "quantity": abs(quantity),
                    "price": price,
                    "stop_price": stop_price,
                    "take_profit_price": take_profit_price,
                    "time_in_force": time_in_force,
                    "status": "pending",
                    "strategy_id": strategy_id,
                    "created_at": datetime.utcnow()
                }
                
                # 保存到数据库
                new_trade = models.Trade(
                    user_id=user_id,
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    order_type=order_data["order_type"],
                    quantity=order_data["quantity"],
                    price=price or 0,
                    status="pending",
                    strategy_id=strategy_id
                )
                
                db.add(new_trade)
                db.commit()
                db.refresh(new_trade)
                
                # 记录订单提交审计日志
                await self._log_trading_action(
                    db=db,
                    user_id=user_id,
                    action=models.TradingAction.ORDER_SUBMITTED,
                    portfolio_id=portfolio_id,
                    trade_id=new_trade.id,
                    symbol=symbol,
                    quantity=abs(quantity),
                    price=price,
                    amount=abs(quantity) * (price or 0),
                    message=f"{order_type}订单已提交",
                    extra_data={
                        "order_type": order_type,
                        "time_in_force": time_in_force,
                        "stop_price": stop_price,
                        "take_profit_price": take_profit_price,
                        "strategy_id": strategy_id
                    }
                )
                
                # 记录初始订单状态
                await self._log_order_state_change(
                    db=db,
                    trade_id=new_trade.id,
                    previous_status=None,
                    new_status=models.OrderStatus.PENDING,
                    remaining_quantity=abs(quantity),
                    reason="订单已提交"
                )
                
                # 根据订单类型处理
                if order_type == "MARKET":
                    # 市价单立即执行
                    execution_result = await self._execute_market_order(db, new_trade)
                elif order_type == "BRACKET":
                    # 对于括号订单，根据是否有价格确定主订单类型
                    if price and price > 0:
                        # 有价格的话，主订单是限价单
                        new_trade.advanced_order_type = "LIMIT"
                        db.commit()
                        db.refresh(new_trade)
                    else:
                        # 没有价格的话，主订单是市价单
                        new_trade.advanced_order_type = "MARKET"
                        db.commit()
                        db.refresh(new_trade)
                    
                    # 创建括号订单组合
                    bracket_result = await self._create_bracket_order(
                        db, new_trade, order_data
                    )
                    execution_result = bracket_result
                else:
                    # 其他订单类型启动监控任务
                    task = asyncio.create_task(
                        self._monitor_order_with_new_session(new_trade.id, order_data)
                    )
                    self.running_orders[new_trade.id] = task
                    execution_result = {
                        "success": True,
                        "message": f"{order_type}订单已提交，等待执行条件触发"
                    }
                
            finally:
                db.close()
            
            return {
                "success": execution_result["success"],
                "message": execution_result["message"],
                "order_id": new_trade.id,
                "order_details": {
                    "symbol": symbol,
                    "type": order_type,
                    "quantity": abs(quantity),
                    "side": "buy" if quantity > 0 else "sell",
                    "price": price,
                    "stop_price": stop_price,
                    "take_profit_price": take_profit_price
                }
            }
            
        except Exception as e:
            logger.error(f"订单提交失败: {e}")
            return {
                "success": False,
                "message": f"订单提交失败: {str(e)}",
                "order_id": None
            }
    
    async def _risk_check(
        self, 
        db: Session, 
        user_id: int, 
        portfolio_id: int, 
        symbol: str, 
        quantity: float, 
        price: float
    ) -> Dict[str, Any]:
        """风险检查"""
        try:
            # 获取投资组合信息
            portfolio = crud.get_portfolio(db, portfolio_id)
            if not portfolio or portfolio.user_id != user_id:
                return {"passed": False, "reason": "投资组合不存在或权限不足"}
            
            # 检查现金余额（买入时）
            if quantity > 0:
                order_value = abs(quantity) * price
                
                # 合规检查：现金余额
                await self._log_compliance_check(
                    db=db,
                    user_id=user_id,
                    check_type="cash_balance",
                    check_result="passed" if portfolio.cash_balance >= order_value else "failed",
                    rule_name="现金余额检查",
                    rule_description="确保有足够现金执行买入订单",
                    violation_details={
                        "required_cash": order_value,
                        "available_cash": portfolio.cash_balance
                    } if portfolio.cash_balance < order_value else None
                )
                
                if portfolio.cash_balance < order_value:
                    return {"passed": False, "reason": "现金余额不足", "limit_value": portfolio.cash_balance}
                
                # 合规检查：订单金额限制
                await self._log_compliance_check(
                    db=db,
                    user_id=user_id,
                    check_type="order_value_limit",
                    check_result="passed" if order_value <= self.execution_rules["max_order_value"] else "failed",
                    rule_name="单笔订单金额限制",
                    rule_description=f"单笔订单不得超过${self.execution_rules['max_order_value']:,.2f}",
                    violation_details={
                        "order_value": order_value,
                        "limit": self.execution_rules["max_order_value"]
                    } if order_value > self.execution_rules["max_order_value"] else None
                )
                
                if order_value > self.execution_rules["max_order_value"]:
                    return {"passed": False, "reason": "单笔订单金额超限", "limit_value": self.execution_rules["max_order_value"]}
                
                # 合规检查：现金比例
                remaining_cash = portfolio.cash_balance - order_value
                cash_ratio = remaining_cash / (portfolio.total_value + portfolio.cash_balance)
                
                await self._log_compliance_check(
                    db=db,
                    user_id=user_id,
                    check_type="cash_ratio",
                    check_result="passed" if cash_ratio >= self.execution_rules["min_cash_ratio"] else "failed",
                    rule_name="最小现金比例检查",
                    rule_description=f"必须保持至少{self.execution_rules['min_cash_ratio']:.1%}的现金比例",
                    violation_details={
                        "resulting_cash_ratio": cash_ratio,
                        "minimum_ratio": self.execution_rules["min_cash_ratio"]
                    } if cash_ratio < self.execution_rules["min_cash_ratio"] else None
                )
                
                if cash_ratio < self.execution_rules["min_cash_ratio"]:
                    return {"passed": False, "reason": "现金比例过低", "limit_value": self.execution_rules["min_cash_ratio"]}
            
            # 检查持仓（卖出时）
            else:
                asset = db.query(models.PortfolioAsset).filter(
                    models.PortfolioAsset.portfolio_id == portfolio_id,
                    models.PortfolioAsset.symbol == symbol
                ).first()
                
                if not asset or asset.quantity < abs(quantity):
                    return {"passed": False, "reason": "持仓数量不足"}
            
            # 检查单个标的仓位比例（买入时）
            if quantity > 0:
                current_position_value = 0
                existing_asset = db.query(models.PortfolioAsset).filter(
                    models.PortfolioAsset.portfolio_id == portfolio_id,
                    models.PortfolioAsset.symbol == symbol
                ).first()
                
                if existing_asset:
                    current_position_value = existing_asset.quantity * existing_asset.average_price
                
                new_position_value = current_position_value + (abs(quantity) * price)
                total_value = portfolio.total_value + portfolio.cash_balance
                position_ratio = new_position_value / total_value
                
                if position_ratio > self.execution_rules["max_position_ratio"]:
                    return {"passed": False, "reason": "单个标的仓位比例超限"}
            
            return {"passed": True, "reason": "风险检查通过"}
            
        except Exception as e:
            logger.error(f"风险检查失败: {e}")
            return {"passed": False, "reason": f"风险检查异常: {str(e)}"}
    
    async def _execute_market_order(
        self, 
        db: Session, 
        order: models.Trade
    ) -> Dict[str, Any]:
        """执行市价单"""
        try:
            # 获取当前市价
            current_price = await self.market_service.get_real_time_price(order.symbol)
            if not current_price:
                # 更新订单状态为失败
                order.status = "failed"
                db.commit()
                return {"success": False, "message": "无法获取市场价格"}
            
            # 检查价格偏差（如果有参考价格）
            if order.price > 0:
                price_deviation = abs(current_price - order.price) / order.price
                if price_deviation > self.execution_rules["price_deviation_limit"]:
                    order.status = "failed"
                    db.commit()
                    return {
                        "success": False, 
                        "message": f"市场价格偏差过大: {price_deviation:.2%}"
                    }
            
            # 执行订单
            execution_result = await self._execute_trade(
                db, order, current_price, order.quantity
            )
            
            if execution_result["success"]:
                old_status = order.status
                order.status = "executed"
                order.executed_at = datetime.utcnow()
                order.price = current_price
                order.profit_loss = execution_result.get("profit_loss", 0)
                db.commit()
                
                # 记录订单执行审计日志
                await self._log_trading_action(
                    db=db,
                    user_id=order.user_id,
                    action=models.TradingAction.ORDER_FILLED,
                    portfolio_id=order.portfolio_id,
                    trade_id=order.id,
                    symbol=order.symbol,
                    quantity=order.quantity,
                    price=current_price,
                    amount=order.quantity * current_price,
                    message=f"市价单执行成功，价格: ${current_price:.2f}",
                    extra_data={
                        "execution_type": "market_order",
                        "profit_loss": execution_result.get("profit_loss", 0)
                    }
                )
                
                # 记录订单状态变更
                await self._log_order_state_change(
                    db=db,
                    trade_id=order.id,
                    previous_status=models.OrderStatus.PENDING,
                    new_status=models.OrderStatus.FILLED,
                    filled_quantity=order.quantity,
                    remaining_quantity=0.0,
                    fill_price=current_price,
                    reason="市价单立即执行"
                )
                
                return {
                    "success": True,
                    "message": f"市价单执行成功，价格: ${current_price:.2f}",
                    "execution_price": current_price,
                    "execution_time": order.executed_at
                }
            else:
                order.status = "failed"
                db.commit()
                
                # 记录订单失败审计日志
                await self._log_trading_action(
                    db=db,
                    user_id=order.user_id,
                    action=models.TradingAction.ORDER_REJECTED,
                    portfolio_id=order.portfolio_id,
                    trade_id=order.id,
                    symbol=order.symbol,
                    quantity=order.quantity,
                    price=current_price,
                    message=f"市价单执行失败: {execution_result['message']}",
                    extra_data={"failure_reason": execution_result["message"]}
                )
                
                # 记录订单状态变更
                await self._log_order_state_change(
                    db=db,
                    trade_id=order.id,
                    previous_status=models.OrderStatus.PENDING,
                    new_status=models.OrderStatus.REJECTED,
                    reason=execution_result["message"]
                )
                
                return execution_result
                
        except Exception as e:
            logger.error(f"市价单执行失败: {e}")
            order.status = "failed"
            db.commit()
            return {"success": False, "message": f"执行失败: {str(e)}"}
    
    async def _monitor_order(
        self, 
        db: Session, 
        order: models.Trade, 
        order_data: Dict[str, Any]
    ):
        """监控订单执行条件"""
        order_type = order_data["advanced_order_type"]
        symbol = order.symbol
        
        try:
            while True:
                # 检查订单是否已取消
                db.refresh(order)
                if order.status == "canceled":
                    break
                
                # 检查时间限制
                if order_data["time_in_force"] == "DAY":
                    # 检查是否超过当天
                    if datetime.utcnow().date() > order.created_at.date():
                        order.status = "canceled"
                        db.commit()
                        logger.info(f"订单 {order.id} 因DAY限制过期")
                        break
                
                # 获取当前价格
                current_price = await self.market_service.get_real_time_price(symbol)
                if not current_price:
                    await asyncio.sleep(10)  # 等待10秒后重试
                    continue
                
                should_execute = False
                execution_price = current_price
                
                # 根据订单类型检查执行条件
                if order_type == "LIMIT":
                    if order.order_type == "buy" and current_price <= order.price:
                        should_execute = True
                        execution_price = order.price
                    elif order.order_type == "sell" and current_price >= order.price:
                        should_execute = True
                        execution_price = order.price
                
                elif order_type == "STOP_LOSS":
                    stop_price = order_data["stop_price"]
                    if order.order_type == "sell" and current_price <= stop_price:
                        should_execute = True
                        execution_price = current_price  # 市价执行
                
                elif order_type == "TAKE_PROFIT":
                    take_profit_price = order_data["take_profit_price"]
                    if order.order_type == "sell" and current_price >= take_profit_price:
                        should_execute = True
                        execution_price = current_price  # 市价执行
                
                elif order_type == "STOP_LIMIT":
                    stop_price = order_data["stop_price"]
                    limit_price = order.price
                    
                    if order.order_type == "buy":
                        if current_price >= stop_price and current_price <= limit_price:
                            should_execute = True
                            execution_price = limit_price
                    else:  # sell
                        if current_price <= stop_price and current_price >= limit_price:
                            should_execute = True
                            execution_price = limit_price
                
                # 执行订单
                if should_execute:
                    execution_result = await self._execute_trade(
                        db, order, execution_price, order.quantity
                    )
                    
                    if execution_result["success"]:
                        order.status = "executed"
                        order.executed_at = datetime.utcnow()
                        order.price = execution_price
                        order.profit_loss = execution_result.get("profit_loss", 0)
                        db.commit()
                        
                        # 记录订单执行审计日志
                        await self._log_trading_action(
                            db=db,
                            user_id=order.user_id,
                            action=models.TradingAction.ORDER_FILLED,
                            portfolio_id=order.portfolio_id,
                            trade_id=order.id,
                            symbol=order.symbol,
                            quantity=order.quantity,
                            price=execution_price,
                            amount=order.quantity * execution_price,
                            message=f"{order_type}订单触发执行，价格: ${execution_price:.2f}",
                            extra_data={
                                "execution_type": order_type.lower(),
                                "trigger_price": current_price,
                                "profit_loss": execution_result.get("profit_loss", 0)
                            }
                        )
                        
                        # 记录订单状态变更
                        await self._log_order_state_change(
                            db=db,
                            trade_id=order.id,
                            previous_status=models.OrderStatus.PENDING,
                            new_status=models.OrderStatus.FILLED,
                            filled_quantity=order.quantity,
                            remaining_quantity=0.0,
                            fill_price=execution_price,
                            reason=f"{order_type}订单条件触发"
                        )
                        
                        logger.info(f"订单 {order.id} 执行成功，价格: ${execution_price:.2f}")
                    else:
                        order.status = "failed"
                        db.commit()
                        
                        # 记录订单失败审计日志
                        await self._log_trading_action(
                            db=db,
                            user_id=order.user_id,
                            action=models.TradingAction.ORDER_REJECTED,
                            portfolio_id=order.portfolio_id,
                            trade_id=order.id,
                            symbol=order.symbol,
                            quantity=order.quantity,
                            price=execution_price,
                            message=f"{order_type}订单执行失败: {execution_result['message']}",
                            extra_data={"failure_reason": execution_result["message"]}
                        )
                        
                        # 记录订单状态变更
                        await self._log_order_state_change(
                            db=db,
                            trade_id=order.id,
                            previous_status=models.OrderStatus.PENDING,
                            new_status=models.OrderStatus.REJECTED,
                            reason=execution_result["message"]
                        )
                        
                        logger.error(f"订单 {order.id} 执行失败: {execution_result['message']}")
                    
                    break
                
                # 等待5秒后再次检查
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info(f"订单 {order.id} 监控任务被取消")
        except Exception as e:
            logger.error(f"订单监控异常: {e}")
            order.status = "failed"
            db.commit()
        finally:
            # 清理任务引用
            if order.id in self.running_orders:
                del self.running_orders[order.id]
    
    async def _monitor_order_with_new_session(
        self,
        order_id: int,
        order_data: Dict[str, Any]
    ):
        """使用新数据库会话监控订单"""
        try:
            db = SessionLocal()
            
            try:
                order = db.query(models.Trade).filter(models.Trade.id == order_id).first()
                if not order:
                    return
                
                await self._monitor_order(db, order, order_data)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"订单监控会话异常: {e}")
            # 清理任务引用
            if order_id in self.running_orders:
                del self.running_orders[order_id]
    
    async def _execute_trade(
        self, 
        db: Session, 
        order: models.Trade, 
        execution_price: float, 
        quantity: float
    ) -> Dict[str, Any]:
        """执行交易并更新持仓"""
        try:
            portfolio = crud.get_portfolio(db, order.portfolio_id)
            if not portfolio:
                return {"success": False, "message": "投资组合不存在"}
            
            trade_value = quantity * execution_price
            
            if order.order_type == "buy":
                # 买入操作
                # 检查现金余额
                if portfolio.cash_balance < trade_value:
                    return {"success": False, "message": "现金余额不足"}
                
                # 更新现金余额
                portfolio.cash_balance -= trade_value
                
                # 更新持仓
                asset = db.query(models.PortfolioAsset).filter(
                    models.PortfolioAsset.portfolio_id == order.portfolio_id,
                    models.PortfolioAsset.symbol == order.symbol
                ).first()
                
                if asset:
                    # 更新现有持仓
                    total_cost = (asset.quantity * asset.average_price) + trade_value
                    asset.quantity += quantity
                    asset.average_price = total_cost / asset.quantity
                    asset.updated_at = datetime.utcnow()
                else:
                    # 创建新持仓
                    new_asset = models.PortfolioAsset(
                        portfolio_id=order.portfolio_id,
                        symbol=order.symbol,
                        quantity=quantity,
                        average_price=execution_price,
                        updated_at=datetime.utcnow()
                    )
                    db.add(new_asset)
                
                profit_loss = 0  # 买入时盈亏为0
                
            else:
                # 卖出操作
                asset = db.query(models.PortfolioAsset).filter(
                    models.PortfolioAsset.portfolio_id == order.portfolio_id,
                    models.PortfolioAsset.symbol == order.symbol
                ).first()
                
                if not asset or asset.quantity < quantity:
                    return {"success": False, "message": "持仓数量不足"}
                
                # 计算盈亏
                cost_basis = quantity * asset.average_price
                profit_loss = trade_value - cost_basis
                
                # 更新持仓
                asset.quantity -= quantity
                if asset.quantity <= 0:
                    db.delete(asset)  # 清空持仓
                else:
                    asset.updated_at = datetime.utcnow()
                
                # 更新现金余额
                portfolio.cash_balance += trade_value
            
            # 重新计算投资组合总价值
            total_asset_value = 0
            assets = db.query(models.PortfolioAsset).filter(
                models.PortfolioAsset.portfolio_id == order.portfolio_id
            ).all()
            
            for asset in assets:
                # 获取当前价格估算
                current_price = await self.market_service.get_real_time_price(asset.symbol)
                if current_price:
                    total_asset_value += asset.quantity * current_price
                else:
                    total_asset_value += asset.quantity * asset.average_price
            
            portfolio.total_value = total_asset_value
            portfolio.updated_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "message": "交易执行成功",
                "profit_loss": profit_loss,
                "new_cash_balance": portfolio.cash_balance,
                "new_total_value": portfolio.total_value + portfolio.cash_balance
            }
            
        except Exception as e:
            logger.error(f"交易执行失败: {e}")
            db.rollback()
            return {"success": False, "message": f"交易执行失败: {str(e)}"}
    
    async def cancel_order(self, user_id: int, order_id: int) -> Dict[str, Any]:
        """取消订单"""
        try:
            db = SessionLocal()
            
            order = db.query(models.Trade).filter(
                models.Trade.id == order_id,
                models.Trade.user_id == user_id
            ).first()
            
            if not order:
                db.close()
                return {"success": False, "message": "订单不存在"}
            
            if order.status not in ["pending"]:
                db.close()
                return {"success": False, "message": f"无法取消状态为 {order.status} 的订单"}
            
            # 更新订单状态
            old_status = order.status
            order.status = "canceled"
            order.updated_at = datetime.utcnow()
            db.commit()
            
            # 记录订单取消审计日志
            await self._log_trading_action(
                db=db,
                user_id=user_id,
                action=models.TradingAction.ORDER_CANCELED,
                portfolio_id=order.portfolio_id,
                trade_id=order.id,
                symbol=order.symbol,
                quantity=order.quantity,
                price=order.price,
                message="订单被用户手动取消",
                extra_data={"cancellation_reason": "user_request"}
            )
            
            # 记录订单状态变更
            await self._log_order_state_change(
                db=db,
                trade_id=order.id,
                previous_status=models.OrderStatus.PENDING,
                new_status=models.OrderStatus.CANCELED,
                reason="用户手动取消"
            )
            
            # 取消监控任务
            if order_id in self.running_orders:
                self.running_orders[order_id].cancel()
                del self.running_orders[order_id]
            
            db.close()
            
            return {
                "success": True,
                "message": "订单已取消",
                "order_id": order_id
            }
            
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return {"success": False, "message": f"取消订单失败: {str(e)}"}
    
    async def get_order_status(self, user_id: int, order_id: int) -> Dict[str, Any]:
        """获取订单状态"""
        try:
            db = SessionLocal()
            
            order = db.query(models.Trade).filter(
                models.Trade.id == order_id,
                models.Trade.user_id == user_id
            ).first()
            
            if not order:
                db.close()
                return {"success": False, "message": "订单不存在"}
            
            db.close()
            
            return {
                "success": True,
                "order": {
                    "id": order.id,
                    "symbol": order.symbol,
                    "order_type": order.order_type,
                    "quantity": order.quantity,
                    "price": order.price,
                    "status": order.status,
                    "created_at": order.created_at,
                    "executed_at": order.executed_at,
                    "profit_loss": order.profit_loss
                }
            }
            
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {"success": False, "message": f"获取订单状态失败: {str(e)}"}
    
    async def get_active_orders(self, user_id: int) -> List[Dict[str, Any]]:
        """获取活跃订单列表"""
        try:
            db = SessionLocal()
            
            orders = db.query(models.Trade).filter(
                models.Trade.user_id == user_id,
                models.Trade.status == "pending"
            ).all()
            
            db.close()
            
            return [
                {
                    "id": order.id,
                    "symbol": order.symbol,
                    "order_type": order.order_type,
                    "quantity": order.quantity,
                    "price": order.price,
                    "status": order.status,
                    "created_at": order.created_at
                }
                for order in orders
            ]
            
        except Exception as e:
            logger.error(f"获取活跃订单失败: {e}")
            return []


# 全局订单引擎实例
order_engine = OrderExecutionEngine()


async def get_order_engine() -> OrderExecutionEngine:
    """获取订单执行引擎实例"""
    return order_engine