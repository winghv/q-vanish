from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..services.market_data import get_market_service, MarketDataService
from ..services.cache import get_cache_service, CacheService

router = APIRouter()

@router.get("/positions")
async def get_positions(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取投资组合持仓"""
    portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
    
    if not portfolios:
        return []
    
    positions = []
    # 获取所有投资组合的资产
    for portfolio in portfolios:
        assets = crud.get_portfolio_assets(db, portfolio_id=portfolio.id)
        
        for asset in assets:
            # 模拟当前价格更新
            current_price = asset.current_price * (1 + random.uniform(-0.05, 0.05))
            value = asset.quantity * current_price
            profit_loss = value - (asset.quantity * asset.average_price)
            profit_loss_percent = (profit_loss / (asset.quantity * asset.average_price)) * 100
            
            positions.append({
                "symbol": asset.symbol,
                "quantity": asset.quantity,
                "avg_cost": asset.average_price,
                "current_price": round(current_price, 2),
                "value": round(value, 2),
                "profit_loss": round(profit_loss, 2),
                "profit_loss_percent": round(profit_loss_percent, 2)
            })
    
    return positions

@router.get("/assets")
async def get_assets(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取资产配置信息"""
    portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
    
    if not portfolios:
        # 返回模拟数据
        return _generate_mock_assets()
    
    assets = []
    total_portfolio_value = sum(p.total_value for p in portfolios)
    
    for portfolio in portfolios:
        portfolio_assets = crud.get_portfolio_assets(db, portfolio_id=portfolio.id)
        
        for asset in portfolio_assets:
            current_price = asset.current_price * (1 + random.uniform(-0.03, 0.03))
            value = asset.quantity * current_price
            allocation = (value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            
            # 模拟日涨跌和总收益
            day_change = random.uniform(-5.0, 5.0)
            total_return = ((current_price - asset.average_price) / asset.average_price) * 100
            
            assets.append({
                "symbol": asset.symbol,
                "name": _get_stock_name(asset.symbol),
                "shares": asset.quantity,
                "price": round(current_price, 2),
                "value": round(value, 2),
                "allocation": round(allocation, 1),
                "day_change": round(day_change, 2),
                "total_return": round(total_return, 2)
            })
    
    return assets

@router.get("/performance")
async def get_performance(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    cache_service: CacheService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """获取投资组合表现"""
    # 先尝试从缓存获取
    cached_performance = await cache_service.get_portfolio_data(current_user.id)
    if cached_performance:
        return cached_performance
    
    portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
    
    if not portfolios:
        performance_data = _generate_mock_performance()
    else:
        # 计算总资产
        total_balance = sum(p.total_value + p.cash_balance for p in portfolios)
        
        # 模拟各种收益率
        day_change = random.uniform(-3.0, 3.0)
        week_change = random.uniform(-8.0, 8.0)
        month_change = random.uniform(-15.0, 15.0)
        year_change = random.uniform(-30.0, 40.0)
        total_return = random.uniform(-20.0, 60.0)
        
        # 生成历史净值数据
        history = []
        base_date = datetime.now() - timedelta(days=30)
        for i in range(30):
            date = base_date + timedelta(days=i)
            # 基于总资产计算历史净值
            value = total_balance * (1 + random.uniform(-0.03, 0.03))
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "value": round(value, 2)
            })
        
        performance_data = {
            "balance": round(total_balance, 2),
            "day_change": round(day_change, 2),
            "week_change": round(week_change, 2),
            "month_change": round(month_change, 2),
            "year_change": round(year_change, 2),
            "total_return": round(total_return, 2),
            "history": history
        }
    
    # 缓存结果（缓存5分钟）
    await cache_service.set_portfolio_data(current_user.id, performance_data, 300)
    
    return performance_data

def _generate_mock_assets() -> List[Dict[str, Any]]:
    """生成模拟资产数据"""
    mock_assets = [
        {
            "symbol": "AAPL",
            "name": "苹果公司",
            "shares": 50,
            "price": 175.25,
            "value": 8762.50,
            "allocation": 35.2,
            "day_change": 2.1,
            "total_return": 15.4
        },
        {
            "symbol": "GOOGL",
            "name": "字母公司",
            "shares": 25,
            "price": 138.45,
            "value": 3461.25,
            "allocation": 13.9,
            "day_change": -1.3,
            "total_return": 8.7
        },
        {
            "symbol": "MSFT",
            "name": "微软公司",
            "shares": 30,
            "price": 378.85,
            "value": 11365.50,
            "allocation": 45.7,
            "day_change": 0.8,
            "total_return": 22.1
        },
        {
            "symbol": "TSLA",
            "name": "特斯拉公司",
            "shares": 10,
            "price": 248.50,
            "value": 2485.00,
            "allocation": 10.0,
            "day_change": -3.2,
            "total_return": -5.8
        }
    ]
    return mock_assets

def _generate_mock_performance() -> Dict[str, Any]:
    """生成模拟表现数据"""
    balance = 125000.0
    
    # 生成历史数据
    history = []
    base_date = datetime.now() - timedelta(days=30)
    current_value = balance
    
    for i in range(30):
        date = base_date + timedelta(days=i)
        daily_change = random.uniform(-0.02, 0.02)
        current_value *= (1 + daily_change)
        
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(current_value, 2)
        })
    
    return {
        "balance": balance,
        "day_change": 1.25,
        "week_change": -2.15,
        "month_change": 4.68,
        "year_change": 18.42,
        "total_return": 25.0,
        "history": history
    }

def _get_stock_name(symbol: str) -> str:
    """根据股票代码获取公司名称"""
    stock_names = {
        "AAPL": "苹果公司",
        "GOOGL": "字母公司", 
        "MSFT": "微软公司",
        "TSLA": "特斯拉公司",
        "AMZN": "亚马逊公司",
        "META": "Meta公司",
        "NVDA": "英伟达公司",
        "NFLX": "Netflix公司"
    }
    return stock_names.get(symbol, f"{symbol} 公司")

# 新增：实时更新投资组合价格
@router.post("/refresh-prices")
async def refresh_portfolio_prices(
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    market_service: MarketDataService = Depends(get_market_service)
):
    """刷新用户所有投资组合的价格"""
    try:
        portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
        
        if not portfolios:
            return {"message": "没有找到投资组合"}
        
        # 为每个投资组合启动后台价格更新任务
        for portfolio in portfolios:
            background_tasks.add_task(
                market_service.update_portfolio_prices,
                db, portfolio.id
            )
        
        return {
            "message": f"已启动 {len(portfolios)} 个投资组合的价格更新任务",
            "portfolio_count": len(portfolios)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"刷新价格失败: {str(e)}"
        )

# 新增：获取投资组合实时价格信息
@router.get("/positions-realtime")
async def get_positions_realtime(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    market_service: MarketDataService = Depends(get_market_service)
):
    """获取包含实时价格的投资组合持仓"""
    try:
        portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
        
        if not portfolios:
            return []
        
        all_positions = []
        all_symbols = set()
        
        # 收集所有股票代码
        for portfolio in portfolios:
            assets = crud.get_portfolio_assets(db, portfolio_id=portfolio.id)
            for asset in assets:
                all_symbols.add(asset.symbol)
        
        # 批量获取实时价格
        real_prices = await market_service.get_multiple_prices(list(all_symbols))
        
        # 构建持仓数据
        for portfolio in portfolios:
            assets = crud.get_portfolio_assets(db, portfolio_id=portfolio.id)
            
            for asset in assets:
                current_price = real_prices.get(asset.symbol, asset.current_price)
                value = asset.quantity * current_price
                profit_loss = value - (asset.quantity * asset.average_price)
                profit_loss_percent = (profit_loss / (asset.quantity * asset.average_price)) * 100 if asset.average_price > 0 else 0
                
                all_positions.append({
                    "symbol": asset.symbol,
                    "quantity": asset.quantity,
                    "avg_cost": asset.average_price,
                    "current_price": round(current_price, 2),
                    "value": round(value, 2),
                    "profit_loss": round(profit_loss, 2),
                    "profit_loss_percent": round(profit_loss_percent, 2),
                    "last_updated": datetime.now().isoformat()
                })
        
        return all_positions
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取实时持仓失败: {str(e)}"
        )