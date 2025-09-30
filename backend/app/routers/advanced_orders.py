"""
高级订单管理API路由
支持各种复杂订单类型：市价单、限价单、止损单、止盈单、止损限价单等
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..services.order_engine import get_order_engine, OrderExecutionEngine

router = APIRouter()


@router.post("/submit")
async def submit_order(
    order_data: schemas.AdvancedOrderCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    order_engine: OrderExecutionEngine = Depends(get_order_engine)
) -> Dict[str, Any]:
    """
    提交高级订单
    
    支持的订单类型：
    - MARKET: 市价单（立即按市场价格执行）
    - LIMIT: 限价单（达到指定价格时执行）
    - STOP_LOSS: 止损单（价格跌破止损价时按市价卖出）
    - TAKE_PROFIT: 止盈单（价格上涨到目标价时按市价卖出）
    - STOP_LIMIT: 止损限价单（价格触发后按限价执行）
    """
    try:
        # 获取用户的默认投资组合
        portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
        if not portfolios:
            # 创建默认投资组合
            portfolio_create = schemas.PortfolioCreate(
                name="默认投资组合",
                description="系统自动创建的默认投资组合",
                cash_balance=100000.0,
                total_value=100000.0
            )
            portfolio = crud.create_portfolio(db, portfolio=portfolio_create, user_id=current_user.id)
        else:
            portfolio = portfolios[0]
        
        # 验证订单参数
        if order_data.order_type == schemas.AdvancedOrderType.LIMIT and not order_data.price:
            raise HTTPException(status_code=400, detail="限价单必须指定价格")
        
        if order_data.order_type == schemas.AdvancedOrderType.STOP_LOSS and not order_data.stop_price:
            raise HTTPException(status_code=400, detail="止损单必须指定止损价格")
        
        if order_data.order_type == schemas.AdvancedOrderType.TAKE_PROFIT and not order_data.take_profit_price:
            raise HTTPException(status_code=400, detail="止盈单必须指定止盈价格")
        
        if order_data.order_type == schemas.AdvancedOrderType.STOP_LIMIT:
            if not order_data.stop_price or not order_data.price:
                raise HTTPException(status_code=400, detail="止损限价单必须指定止损价格和限价价格")
        
        # 提交订单到订单引擎
        result = await order_engine.submit_order(
            user_id=current_user.id,
            portfolio_id=portfolio.id,
            symbol=order_data.symbol.upper(),
            order_type=order_data.order_type.value,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_price=order_data.stop_price,
            take_profit_price=order_data.take_profit_price,
            time_in_force=order_data.time_in_force.value,
            strategy_id=order_data.strategy_id
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "order_id": result["order_id"],
                "order_details": result["order_details"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"订单提交失败: {str(e)}")


@router.get("/active")
async def get_active_orders(
    current_user: models.User = Depends(get_current_active_user),
    order_engine: OrderExecutionEngine = Depends(get_order_engine)
) -> List[Dict[str, Any]]:
    """获取用户的活跃订单列表"""
    try:
        active_orders = await order_engine.get_active_orders(current_user.id)
        return active_orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取活跃订单失败: {str(e)}")


@router.get("/{order_id}")
async def get_order_status(
    order_id: int,
    current_user: models.User = Depends(get_current_active_user),
    order_engine: OrderExecutionEngine = Depends(get_order_engine)
) -> Dict[str, Any]:
    """获取特定订单的状态"""
    try:
        result = await order_engine.get_order_status(current_user.id, order_id)
        
        if result["success"]:
            return result["order"]
        else:
            raise HTTPException(status_code=404, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单状态失败: {str(e)}")


@router.delete("/{order_id}")
async def cancel_order(
    order_id: int,
    current_user: models.User = Depends(get_current_active_user),
    order_engine: OrderExecutionEngine = Depends(get_order_engine)
) -> Dict[str, Any]:
    """取消订单"""
    try:
        result = await order_engine.cancel_order(current_user.id, order_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "order_id": result["order_id"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消订单失败: {str(e)}")


@router.get("/history/all")
async def get_order_history(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    symbol: str = None,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取订单历史记录
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        status: 订单状态过滤器
        symbol: 股票代码过滤器
    """
    try:
        # 构建查询
        query = db.query(models.Trade).filter(models.Trade.user_id == current_user.id)
        
        if status:
            query = query.filter(models.Trade.status == status)
        if symbol:
            query = query.filter(models.Trade.symbol == symbol.upper())
        
        # 按创建时间倒序排列
        trades = query.order_by(models.Trade.created_at.desc()).offset(skip).limit(limit).all()
        
        # 转换为API响应格式
        order_history = []
        for trade in trades:
            order_history.append({
                "id": trade.id,
                "symbol": trade.symbol,
                "order_type": trade.order_type,
                "advanced_order_type": getattr(trade, 'advanced_order_type', 'MARKET'),
                "quantity": trade.quantity,
                "price": trade.price,
                "stop_price": getattr(trade, 'stop_price', None),
                "take_profit_price": getattr(trade, 'take_profit_price', None),
                "status": trade.status,
                "filled_quantity": getattr(trade, 'filled_quantity', 0),
                "average_fill_price": getattr(trade, 'average_fill_price', None),
                "profit_loss": trade.profit_loss,
                "commission": getattr(trade, 'commission', 0),
                "created_at": trade.created_at,
                "executed_at": trade.executed_at,
                "notes": getattr(trade, 'notes', None)
            })
        
        return order_history
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单历史失败: {str(e)}")


@router.post("/batch")
async def submit_batch_orders(
    orders: List[schemas.AdvancedOrderCreate],
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    order_engine: OrderExecutionEngine = Depends(get_order_engine)
) -> Dict[str, Any]:
    """
    批量提交订单
    
    Args:
        orders: 订单列表
        
    Returns:
        批量提交结果，包含成功和失败的订单
    """
    try:
        # 获取用户的默认投资组合
        portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
        if not portfolios:
            portfolio_create = schemas.PortfolioCreate(
                name="默认投资组合",
                description="系统自动创建的默认投资组合",
                cash_balance=100000.0,
                total_value=100000.0
            )
            portfolio = crud.create_portfolio(db, portfolio=portfolio_create, user_id=current_user.id)
        else:
            portfolio = portfolios[0]
        
        successful_orders = []
        failed_orders = []
        
        for i, order_data in enumerate(orders):
            try:
                # 提交单个订单
                result = await order_engine.submit_order(
                    user_id=current_user.id,
                    portfolio_id=portfolio.id,
                    symbol=order_data.symbol.upper(),
                    order_type=order_data.order_type.value,
                    quantity=order_data.quantity,
                    price=order_data.price,
                    stop_price=order_data.stop_price,
                    take_profit_price=order_data.take_profit_price,
                    time_in_force=order_data.time_in_force.value,
                    strategy_id=order_data.strategy_id
                )
                
                if result["success"]:
                    successful_orders.append({
                        "index": i,
                        "order_id": result["order_id"],
                        "symbol": order_data.symbol,
                        "message": result["message"]
                    })
                else:
                    failed_orders.append({
                        "index": i,
                        "symbol": order_data.symbol,
                        "error": result["message"]
                    })
                    
            except Exception as e:
                failed_orders.append({
                    "index": i,
                    "symbol": order_data.symbol,
                    "error": str(e)
                })
        
        return {
            "total_submitted": len(orders),
            "successful_count": len(successful_orders),
            "failed_count": len(failed_orders),
            "successful_orders": successful_orders,
            "failed_orders": failed_orders
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量订单提交失败: {str(e)}")


@router.get("/stats/summary")
async def get_order_statistics(
    days: int = 30,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取订单统计信息
    
    Args:
        days: 统计天数，默认30天
    """
    try:
        from datetime import datetime, timedelta
        
        # 计算日期范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 查询指定时间范围内的订单
        trades = db.query(models.Trade).filter(
            models.Trade.user_id == current_user.id,
            models.Trade.created_at >= start_date,
            models.Trade.created_at <= end_date
        ).all()
        
        # 统计数据
        total_orders = len(trades)
        executed_orders = len([t for t in trades if t.status == "executed"])
        pending_orders = len([t for t in trades if t.status == "pending"])
        canceled_orders = len([t for t in trades if t.status == "canceled"])
        failed_orders = len([t for t in trades if t.status == "failed"])
        
        # 计算总盈亏
        total_profit_loss = sum(t.profit_loss or 0 for t in trades if t.status == "executed")
        
        # 统计按订单类型分组
        buy_orders = len([t for t in trades if t.order_type == "buy"])
        sell_orders = len([t for t in trades if t.order_type == "sell"])
        
        # 统计最活跃的股票
        symbol_counts = {}
        for trade in trades:
            symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1
        
        top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "period_days": days,
            "total_orders": total_orders,
            "order_status": {
                "executed": executed_orders,
                "pending": pending_orders,
                "canceled": canceled_orders,
                "failed": failed_orders
            },
            "order_types": {
                "buy_orders": buy_orders,
                "sell_orders": sell_orders
            },
            "financial_summary": {
                "total_profit_loss": round(total_profit_loss, 2),
                "execution_rate": round(executed_orders / total_orders * 100, 2) if total_orders > 0 else 0
            },
            "top_symbols": [{"symbol": symbol, "count": count} for symbol, count in top_symbols]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单统计失败: {str(e)}")