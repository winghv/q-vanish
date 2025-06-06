from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import yfinance as yf
from datetime import datetime

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

# 获取交易列表
@router.get("/", response_model=List[schemas.Trade])
async def read_trades(
    skip: int = 0, 
    limit: int = 100,
    strategy_id: Optional[int] = None,
    portfolio_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return crud.get_trades(
        db, 
        user_id=current_user.id, 
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        skip=skip, 
        limit=limit
    )

# 创建新交易
@router.post("/", response_model=schemas.Trade, status_code=status.HTTP_201_CREATED)
async def create_trade(
    trade: schemas.TradeCreate,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 检查策略是否存在（如果提供了策略ID）
    if trade.strategy_id:
        strategy = crud.get_strategy(db, strategy_id=trade.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="策略不存在")
        
        # 检查用户是否有权使用此策略
        if strategy.owner_id != current_user.id and not strategy.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有足够的权限使用此策略"
            )
    
    # 检查投资组合是否存在（如果提供了投资组合ID）
    if trade.portfolio_id:
        portfolio = crud.get_portfolio(db, portfolio_id=trade.portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="投资组合不存在")
        
        # 检查用户是否有权访问此投资组合
        if portfolio.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有足够的权限访问此投资组合"
            )
    
    # 创建交易记录
    db_trade = crud.create_trade(db=db, trade=trade, user_id=current_user.id)
    
    # 在后台执行交易
    background_tasks.add_task(
        execute_trade_task,
        db=db,
        trade_id=db_trade.id,
        user_id=current_user.id
    )
    
    return db_trade

# 获取指定交易
@router.get("/{trade_id}", response_model=schemas.Trade)
async def read_trade(
    trade_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_trade = crud.get_trade(db, trade_id=trade_id)
    if db_trade is None:
        raise HTTPException(status_code=404, detail="交易不存在")
    
    # 检查用户是否有权访问此交易
    if db_trade.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限访问此交易"
        )
    
    return db_trade

# 取消交易
@router.put("/{trade_id}/cancel", response_model=schemas.Trade)
async def cancel_trade(
    trade_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 检查交易是否存在
    db_trade = crud.get_trade(db, trade_id=trade_id)
    if db_trade is None:
        raise HTTPException(status_code=404, detail="交易不存在")
    
    # 检查用户是否有权取消此交易
    if db_trade.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限取消此交易"
        )
    
    # 检查交易是否可以取消
    if db_trade.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有待处理的交易可以取消"
        )
    
    # 更新交易状态
    trade_update = schemas.TradeUpdate(status="canceled")
    updated_trade = crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=current_user.id)
    
    return updated_trade

# 后台任务：执行交易
def execute_trade_task(db: Session, trade_id: int, user_id: int):
    try:
        # 获取交易信息
        trade = crud.get_trade(db, trade_id=trade_id)
        if not trade or trade.status != "pending":
            return
        
        # 获取当前市场价格
        ticker = yf.Ticker(trade.symbol)
        current_price = None
        
        try:
            # 获取实时价格
            hist = ticker.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
        except Exception:
            # 如果无法获取实时价格，使用交易中指定的价格
            current_price = trade.price
        
        if not current_price:
            # 更新交易状态为失败
            trade_update = schemas.TradeUpdate(
                status="failed",
                executed_at=datetime.now()
            )
            crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=user_id)
            return
        
        # 如果有投资组合，更新投资组合
        if trade.portfolio_id:
            portfolio = crud.get_portfolio(db, portfolio_id=trade.portfolio_id)
            if portfolio:
                if trade.order_type == "buy":
                    # 检查现金是否足够
                    cost = trade.quantity * current_price
                    if portfolio.cash_balance < cost:
                        # 资金不足，交易失败
                        trade_update = schemas.TradeUpdate(
                            status="failed",
                            executed_at=datetime.now()
                        )
                        crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=user_id)
                        return
                    
                    # 更新投资组合现金余额
                    portfolio_update = schemas.PortfolioUpdate(
                        cash_balance=portfolio.cash_balance - cost
                    )
                    crud.update_portfolio(db, portfolio_id=portfolio.id, portfolio_update=portfolio_update, user_id=user_id)
                    
                    # 检查是否已有此股票
                    assets = crud.get_assets_by_portfolio(db, portfolio_id=portfolio.id)
                    existing_asset = next((a for a in assets if a.symbol == trade.symbol), None)
                    
                    if existing_asset:
                        # 更新现有资产
                        new_quantity = existing_asset.quantity + trade.quantity
                        new_avg_price = (existing_asset.average_price * existing_asset.quantity + current_price * trade.quantity) / new_quantity
                        
                        asset_update = schemas.AssetUpdate(
                            quantity=new_quantity,
                            average_price=new_avg_price,
                            current_price=current_price,
                            market_value=new_quantity * current_price
                        )
                        crud.update_asset(db, asset_id=existing_asset.id, asset_update=asset_update)
                    else:
                        # 创建新资产
                        asset_create = schemas.AssetCreate(
                            symbol=trade.symbol,
                            quantity=trade.quantity,
                            average_price=current_price,
                            portfolio_id=portfolio.id
                        )
                        crud.create_asset(db, asset=asset_create)
                    
                    # 更新投资组合总价值
                    total_value = calculate_portfolio_value(db, portfolio.id)
                    portfolio_update = schemas.PortfolioUpdate(total_value=total_value)
                    crud.update_portfolio(db, portfolio_id=portfolio.id, portfolio_update=portfolio_update, user_id=user_id)
                
                elif trade.order_type == "sell":
                    # 检查是否持有足够股票
                    assets = crud.get_assets_by_portfolio(db, portfolio_id=portfolio.id)
                    asset = next((a for a in assets if a.symbol == trade.symbol), None)
                    
                    if not asset or asset.quantity < trade.quantity:
                        # 持仓不足，交易失败
                        trade_update = schemas.TradeUpdate(
                            status="failed",
                            executed_at=datetime.now()
                        )
                        crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=user_id)
                        return
                    
                    # 计算卖出价值和利润
                    sell_value = trade.quantity * current_price
                    profit = (current_price - asset.average_price) * trade.quantity
                    
                    # 更新资产
                    new_quantity = asset.quantity - trade.quantity
                    
                    if new_quantity > 0:
                        # 还有剩余持仓
                        asset_update = schemas.AssetUpdate(
                            quantity=new_quantity,
                            current_price=current_price,
                            market_value=new_quantity * current_price
                        )
                        crud.update_asset(db, asset_id=asset.id, asset_update=asset_update)
                    else:
                        # 已全部卖出
                        crud.delete_asset(db, asset_id=asset.id)
                    
                    # 更新投资组合现金余额
                    portfolio_update = schemas.PortfolioUpdate(
                        cash_balance=portfolio.cash_balance + sell_value
                    )
                    crud.update_portfolio(db, portfolio_id=portfolio.id, portfolio_update=portfolio_update, user_id=user_id)
                    
                    # 更新投资组合总价值
                    total_value = calculate_portfolio_value(db, portfolio.id)
                    portfolio_update = schemas.PortfolioUpdate(total_value=total_value)
                    crud.update_portfolio(db, portfolio_id=portfolio.id, portfolio_update=portfolio_update, user_id=user_id)
                    
                    # 更新交易利润
                    trade_update = schemas.TradeUpdate(
                        profit_loss=profit
                    )
                    crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=user_id)
        
        # 更新交易状态为已执行
        trade_update = schemas.TradeUpdate(
            status="executed",
            executed_at=datetime.now(),
            price=current_price  # 使用实际执行价格
        )
        crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=user_id)
    
    except Exception as e:
        # 处理任何异常，更新交易状态为失败
        trade_update = schemas.TradeUpdate(
            status="failed",
            executed_at=datetime.now()
        )
        crud.update_trade(db, trade_id=trade_id, trade_update=trade_update, user_id=user_id)

# 辅助函数：计算投资组合总价值
def calculate_portfolio_value(db: Session, portfolio_id: int) -> float:
    portfolio = crud.get_portfolio(db, portfolio_id=portfolio_id)
    if not portfolio:
        return 0.0
    
    # 现金价值
    total_value = portfolio.cash_balance
    
    # 加上所有资产的市值
    assets = crud.get_assets_by_portfolio(db, portfolio_id=portfolio_id)
    for asset in assets:
        total_value += asset.market_value
    
    return total_value 