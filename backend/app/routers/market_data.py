from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user
from ..services.market_data import get_market_service, MarketDataService
from ..utils.rate_limit import market_data_rate_limit

router = APIRouter()

# 获取历史数据
@router.get("/historical", response_model=List[schemas.MarketData])
async def get_historical_data(
    symbol: str, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 处理日期参数
    end_date_dt = datetime.now() if not end_date else datetime.strptime(end_date, "%Y-%m-%d")
    start_date_dt = end_date_dt - timedelta(days=30) if not start_date else datetime.strptime(start_date, "%Y-%m-%d")
    
    # 构建过滤参数
    filter_params = schemas.MarketDataFilter(
        symbol=symbol,
        start_date=start_date_dt,
        end_date=end_date_dt,
        limit=limit
    )
    
    # 查询数据库
    market_data = crud.get_market_data(db, filter_params=filter_params)
    
    # 如果数据库中没有数据，则从外部API获取
    if not market_data:
        try:
            data = fetch_market_data(symbol, start_date_dt, end_date_dt)
            
            # 保存数据到数据库
            market_data = []
            for index, row in data.iterrows():
                market_data_item = schemas.MarketDataCreate(
                    symbol=symbol,
                    date=index,
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row['Volume']
                )
                db_item = crud.create_market_data(db, market_data=market_data_item)
                market_data.append(db_item)
            
            # 限制返回条数
            market_data = market_data[-limit:] if len(market_data) > limit else market_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取市场数据失败: {str(e)}"
            )
    
    return market_data

# 获取多个股票的最新价格
@router.get("/prices", dependencies=[Depends(market_data_rate_limit)])
async def get_latest_prices(
    symbols: str,
    current_user: models.User = Depends(get_current_active_user)
):
    symbol_list = symbols.split(",")
    
    try:
        prices = {}
        for symbol in symbol_list:
            ticker = yf.Ticker(symbol.strip())
            hist = ticker.history(period="1d")
            if not hist.empty:
                prices[symbol] = {
                    "price": hist['Close'].iloc[-1],
                    "change": hist['Close'].iloc[-1] - hist['Open'].iloc[-1],
                    "change_percent": ((hist['Close'].iloc[-1] - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1] * 100),
                    "volume": hist['Volume'].iloc[-1],
                    "time": hist.index[-1].strftime("%Y-%m-%d %H:%M:%S")
                }
        
        return {"prices": prices}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取股票价格失败: {str(e)}"
        )

# 后台任务：定期更新市场数据
def update_market_data_background(db: Session, symbols: List[str]):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)  # 更新最近一周的数据
    
    for symbol in symbols:
        try:
            data = fetch_market_data(symbol, start_date, end_date)
            
            for index, row in data.iterrows():
                market_data_item = schemas.MarketDataCreate(
                    symbol=symbol,
                    date=index,
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row['Volume']
                )
                crud.create_market_data(db, market_data=market_data_item)
        
        except Exception as e:
            print(f"更新市场数据失败: {symbol}, 错误: {str(e)}")

# 触发数据更新
@router.post("/update")
async def trigger_data_update(
    background_tasks: BackgroundTasks,
    symbols: List[str],
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 检查用户权限
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限执行此操作"
        )
    
    # 添加后台任务
    background_tasks.add_task(update_market_data_background, db, symbols)
    
    return {"message": "数据更新任务已启动"}

# 获取股票基本信息
@router.get("/info/{symbol}")
async def get_stock_info(
    symbol: str,
    current_user: models.User = Depends(get_current_active_user)
):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 提取有用的信息
        relevant_info = {
            "symbol": symbol,
            "name": info.get("shortName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "dividend_yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
            "beta": info.get("beta", 0),
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
            "avg_volume": info.get("averageVolume", 0),
            "description": info.get("longBusinessSummary", ""),
        }
        
        return relevant_info
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取股票信息失败: {str(e)}"
        )

# 辅助函数：从Yahoo Finance获取市场数据
def fetch_market_data(symbol: str, start_date: datetime, end_date: datetime):
    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start_date, end=end_date)
    
    if data.empty:
        raise ValueError(f"无法获取股票数据: {symbol}")
    
    return data

# 新增：使用市场数据服务获取实时价格
@router.get("/realtime-price/{symbol}")
async def get_realtime_price(
    symbol: str,
    current_user: models.User = Depends(get_current_active_user),
    market_service: MarketDataService = Depends(get_market_service)
):
    """获取单只股票的实时价格"""
    try:
        price = await market_service.get_real_time_price(symbol.upper())
        if price is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"无法获取股票 {symbol} 的实时价格"
            )
        
        return {
            "symbol": symbol.upper(),
            "price": round(price, 2),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取实时价格失败: {str(e)}"
        )

# 新增：批量获取实时价格
@router.post("/realtime-prices")
async def get_realtime_prices(
    symbols: List[str],
    current_user: models.User = Depends(get_current_active_user),
    market_service: MarketDataService = Depends(get_market_service)
):
    """批量获取多只股票的实时价格"""
    try:
        # 将所有符号转换为大写
        symbols = [s.upper() for s in symbols]
        
        prices = await market_service.get_multiple_prices(symbols)
        
        result = {
            "prices": {
                symbol: {
                    "price": round(price, 2),
                    "timestamp": datetime.now().isoformat()
                }
                for symbol, price in prices.items()
            },
            "requested": len(symbols),
            "found": len(prices)
        }
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量获取价格失败: {str(e)}"
        )

# 新增：更新投资组合价格
@router.post("/update-portfolio-prices/{portfolio_id}")
async def update_portfolio_prices(
    portfolio_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    market_service: MarketDataService = Depends(get_market_service)
):
    """更新指定投资组合的所有股票价格"""
    try:
        # 检查投资组合是否存在且用户有权限
        portfolio = crud.get_portfolio(db, portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="投资组合不存在"
            )
        
        if portfolio.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此投资组合"
            )
        
        # 添加后台任务更新价格
        background_tasks.add_task(
            market_service.update_portfolio_prices,
            db, portfolio_id
        )
        
        return {"message": f"投资组合 {portfolio_id} 价格更新任务已启动"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新投资组合价格失败: {str(e)}"
        )

# 新增：获取支持的股票列表
@router.get("/supported-symbols")
async def get_supported_symbols(
    current_user: models.User = Depends(get_current_active_user),
    market_service: MarketDataService = Depends(get_market_service)
):
    """获取支持的股票代码列表"""
    return {
        "symbols": market_service.get_supported_symbols(),
        "count": len(market_service.get_supported_symbols())
    }

# 新增：验证股票代码
@router.get("/validate-symbol/{symbol}")
async def validate_symbol(
    symbol: str,
    current_user: models.User = Depends(get_current_active_user),
    market_service: MarketDataService = Depends(get_market_service)
):
    """验证股票代码是否有效"""
    try:
        is_valid = await market_service.validate_symbol(symbol.upper())
        return {
            "symbol": symbol.upper(),
            "is_valid": is_valid
        }
    except Exception as e:
        return {
            "symbol": symbol.upper(),
            "is_valid": False,
            "error": str(e)
        } 