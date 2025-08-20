from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import uuid
import random

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

@router.get("/")
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取订单列表"""
    # 从trades表获取用户的交易记录，转换为订单格式
    trades = crud.get_trades(db, user_id=current_user.id, skip=skip, limit=limit)
    
    orders = []
    for trade in trades:
        # 将Trade转换为前端期望的TradeOrder格式
        orders.append({
            "id": str(trade.id),
            "symbol": trade.symbol,
            "type": trade.order_type,  # "buy" or "sell"
            "status": _convert_trade_status(trade.status),
            "quantity": trade.quantity,
            "price": trade.price,
            "total": trade.quantity * trade.price,
            "timestamp": trade.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return orders

@router.post("/")
async def place_order(
    order_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """下单"""
    try:
        # 验证订单数据
        symbol = order_data.get("symbol", "").upper()
        order_type = order_data.get("type")  # "buy" or "sell"
        quantity = float(order_data.get("quantity", 0))
        order_style = order_data.get("order_type", "market")  # "market" or "limit"
        price = float(order_data.get("price", 0)) if order_data.get("price") else None
        
        if not symbol or not order_type or quantity <= 0:
            raise HTTPException(status_code=400, detail="订单参数无效")
        
        if order_type not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="订单类型必须是 buy 或 sell")
        
        # 获取用户的默认投资组合
        portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
        portfolio = portfolios[0] if portfolios else None
        
        # 如果没有投资组合，创建一个默认的
        if not portfolio:
            portfolio_create = schemas.PortfolioCreate(
                name="默认投资组合",
                description="自动创建的默认投资组合",
                cash_balance=100000.0,  # 10万美元起始资金
                total_value=100000.0
            )
            portfolio = crud.create_portfolio(db, portfolio=portfolio_create, user_id=current_user.id)
        
        # 模拟获取当前市场价格
        if not price or order_style == "market":
            price = _get_mock_market_price(symbol)
        
        # 创建交易记录
        trade_create = schemas.TradeCreate(
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            price=price,
            portfolio_id=portfolio.id,
            strategy_id=None  # 手动交易没有策略ID
        )
        
        trade = crud.create_trade(db, trade=trade_create, user_id=current_user.id)
        
        # 在后台处理订单执行
        background_tasks.add_task(
            process_order_execution,
            db=db,
            trade_id=trade.id,
            user_id=current_user.id
        )
        
        # 返回订单确认
        return {
            "id": str(trade.id),
            "symbol": symbol,
            "type": order_type,
            "status": "pending",
            "quantity": quantity,
            "price": price,
            "total": quantity * price,
            "timestamp": trade.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="数值参数格式错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下单失败: {str(e)}")

def _convert_trade_status(trade_status: str) -> str:
    """转换交易状态为前端期望的格式"""
    status_map = {
        "pending": "pending",
        "executed": "filled",
        "canceled": "canceled",
        "failed": "canceled"
    }
    return status_map.get(trade_status, "pending")

def _get_mock_market_price(symbol: str) -> float:
    """获取模拟市场价格"""
    # 模拟不同股票的价格范围
    price_ranges = {
        "AAPL": (170, 180),
        "GOOGL": (130, 145),
        "MSFT": (370, 385),
        "TSLA": (240, 260),
        "AMZN": (140, 155),
        "META": (320, 340),
        "NVDA": (450, 480),
        "NFLX": (420, 450)
    }
    
    if symbol in price_ranges:
        min_price, max_price = price_ranges[symbol]
        return round(random.uniform(min_price, max_price), 2)
    else:
        # 对于未知股票，返回随机价格
        return round(random.uniform(50, 200), 2)

async def process_order_execution(db: Session, trade_id: int, user_id: int):
    """后台处理订单执行"""
    try:
        # 获取交易记录
        trade = crud.get_trade(db, trade_id=trade_id)
        if not trade or trade.status != "pending":
            return
        
        # 模拟订单执行延迟
        import asyncio
        await asyncio.sleep(random.uniform(1, 3))  # 1-3秒随机延迟
        
        # 模拟执行成功率（95%成功率）
        if random.random() < 0.95:
            # 订单执行成功
            execution_price = trade.price * (1 + random.uniform(-0.001, 0.001))  # 轻微滑点
            
            trade_update = schemas.TradeUpdate(
                status="executed",
                price=execution_price,
                executed_at=datetime.now()
            )
            
            # 更新投资组合
            if trade.portfolio_id:
                await _update_portfolio_from_trade(db, trade, execution_price)
                
        else:
            # 订单执行失败
            trade_update = schemas.TradeUpdate(
                status="failed",
                executed_at=datetime.now()
            )
        
        # 更新交易状态
        crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=user_id)
        
    except Exception as e:
        # 处理执行过程中的错误
        trade_update = schemas.TradeUpdate(
            status="failed",
            executed_at=datetime.now()
        )
        crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=user_id)

async def _update_portfolio_from_trade(db: Session, trade: models.Trade, execution_price: float):
    """根据交易更新投资组合"""
    try:
        portfolio = crud.get_portfolio(db, portfolio_id=trade.portfolio_id)
        if not portfolio:
            return
        
        if trade.order_type == "buy":
            # 买入操作
            cost = trade.quantity * execution_price
            
            # 检查现金余额
            if portfolio.cash_balance >= cost:
                # 减少现金
                new_cash_balance = portfolio.cash_balance - cost
                
                # 更新或创建资产
                existing_asset = crud.get_asset_by_symbol(db, portfolio_id=portfolio.id, symbol=trade.symbol)
                
                if existing_asset:
                    # 更新现有资产
                    new_quantity = existing_asset.quantity + trade.quantity
                    new_avg_price = ((existing_asset.average_price * existing_asset.quantity) + 
                                   (execution_price * trade.quantity)) / new_quantity
                    
                    asset_update = schemas.AssetUpdate(
                        quantity=new_quantity,
                        average_price=new_avg_price,
                        current_price=execution_price,
                        market_value=new_quantity * execution_price
                    )
                    crud.update_asset(db, asset_id=existing_asset.id, asset_update=asset_update)
                else:
                    # 创建新资产
                    asset_create = schemas.AssetCreate(
                        symbol=trade.symbol,
                        quantity=trade.quantity,
                        average_price=execution_price,
                        current_price=execution_price,
                        market_value=trade.quantity * execution_price,
                        portfolio_id=portfolio.id
                    )
                    crud.create_asset(db, asset=asset_create)
                
                # 更新投资组合
                portfolio_update = schemas.PortfolioUpdate(
                    cash_balance=new_cash_balance,
                    total_value=portfolio.total_value  # 总价值保持不变（现金变股票）
                )
                crud.update_portfolio(db, portfolio_id=portfolio.id, portfolio_update=portfolio_update, user_id=trade.user_id)
        
        elif trade.order_type == "sell":
            # 卖出操作
            existing_asset = crud.get_asset_by_symbol(db, portfolio_id=portfolio.id, symbol=trade.symbol)
            
            if existing_asset and existing_asset.quantity >= trade.quantity:
                # 增加现金
                revenue = trade.quantity * execution_price
                new_cash_balance = portfolio.cash_balance + revenue
                
                # 更新资产
                new_quantity = existing_asset.quantity - trade.quantity
                
                if new_quantity > 0:
                    # 还有剩余持仓
                    asset_update = schemas.AssetUpdate(
                        quantity=new_quantity,
                        current_price=execution_price,
                        market_value=new_quantity * execution_price
                    )
                    crud.update_asset(db, asset_id=existing_asset.id, asset_update=asset_update)
                else:
                    # 完全卖出，删除资产记录
                    crud.delete_asset(db, asset_id=existing_asset.id)
                
                # 计算盈亏
                profit_loss = (execution_price - existing_asset.average_price) * trade.quantity
                
                # 更新交易盈亏
                trade_update = schemas.TradeUpdate(profit_loss=profit_loss)
                crud.update_trade(db, trade_id=trade.id, trade_update=trade_update, user_id=trade.user_id)
                
                # 更新投资组合
                portfolio_update = schemas.PortfolioUpdate(
                    cash_balance=new_cash_balance,
                    total_value=portfolio.total_value  # 总价值保持不变（股票变现金）
                )
                crud.update_portfolio(db, portfolio_id=portfolio.id, portfolio_update=portfolio_update, user_id=trade.user_id)
                
    except Exception as e:
        # 记录错误但不抛出异常，避免影响交易状态更新
        print(f"更新投资组合失败: {str(e)}")