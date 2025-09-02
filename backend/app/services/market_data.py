"""
市场数据服务模块
集成外部数据源，提供实时和历史市场数据
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import asyncio
import aiohttp
import logging

from .. import models, schemas, crud
from ..database import SessionLocal
from .cache import get_cache_service, CacheService

logger = logging.getLogger(__name__)

class MarketDataService:
    """市场数据服务类"""
    
    def __init__(self):
        self.cache_duration = timedelta(minutes=5)  # 数据缓存时间
        self.supported_symbols = [
            'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 
            'NVDA', 'NFLX', 'SPY', 'QQQ', 'ARKK'
        ]
        self.cache_service = None
    
    async def get_real_time_price(self, symbol: str) -> Optional[float]:
        """获取实时股价"""
        # 初始化缓存服务
        if self.cache_service is None:
            self.cache_service = await get_cache_service()
        
        try:
            # 先从缓存获取
            cached_price = await self.cache_service.get_market_price(symbol)
            if cached_price:
                logger.info(f"Using cached price for {symbol}: ${cached_price['price']}")
                return cached_price['price']
            
            # 缓存中没有，从API获取
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                logger.warning(f"No data found for symbol: {symbol}")
                return None
            
            current_price = float(hist['Close'].iloc[-1])
            logger.info(f"Real-time price for {symbol}: ${current_price}")
            
            # 缓存价格数据
            await self.cache_service.set_market_price(symbol, current_price, 300)  # 缓存5分钟
            
            return current_price
            
        except Exception as e:
            logger.error(f"Error fetching real-time price for {symbol}: {e}")
            return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """批量获取多只股票的实时价格"""
        # 初始化缓存服务
        if self.cache_service is None:
            self.cache_service = await get_cache_service()
            
        prices = {}
        uncached_symbols = []
        
        # 首先检查缓存
        for symbol in symbols:
            cached_price = await self.cache_service.get_market_price(symbol)
            if cached_price:
                prices[symbol] = cached_price['price']
                logger.info(f"Using cached price for {symbol}: ${cached_price['price']}")
            else:
                uncached_symbols.append(symbol)
        
        # 对未缓存的股票进行API调用
        if uncached_symbols:
            try:
                # 使用yfinance的批量下载功能
                tickers_str = " ".join(uncached_symbols)
                data = yf.download(tickers_str, period="1d", interval="5m", group_by='ticker', progress=False)
                
                for symbol in uncached_symbols:
                    try:
                        current_price = None
                        if len(uncached_symbols) == 1:
                            # 单个股票的情况
                            if not data.empty and 'Close' in data.columns:
                                current_price = float(data['Close'].iloc[-1])
                        else:
                            # 多个股票的情况
                            if symbol in data.columns.get_level_values(0):
                                symbol_data = data[symbol]
                                if not symbol_data.empty and 'Close' in symbol_data.columns:
                                    current_price = float(symbol_data['Close'].iloc[-1])
                        
                        if current_price:
                            prices[symbol] = current_price
                            # 缓存价格
                            await self.cache_service.set_market_price(symbol, current_price, 300)
                            logger.info(f"Fetched and cached price for {symbol}: ${current_price}")
                            
                    except Exception as e:
                        logger.error(f"Error processing price for {symbol}: {e}")
                        continue
            
            except Exception as e:
                logger.error(f"Error in batch price fetch: {e}")
                
                # 如果批量获取失败，逐个获取
                for symbol in uncached_symbols:
                    price = await self.get_real_time_price(symbol)
                    if price:
                        prices[symbol] = price
        
        return prices
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """获取历史数据"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                logger.warning(f"No historical data found for symbol: {symbol}")
                return None
            
            # 重置索引，将日期作为列
            hist = hist.reset_index()
            logger.info(f"Retrieved {len(hist)} records for {symbol}")
            return hist
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """获取股票基本信息"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 提取关键信息
            stock_info = {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', symbol)),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 0),
                'price': info.get('currentPrice', 0),
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0),
            }
            
            return stock_info
            
        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            return None
    
    async def update_portfolio_prices(self, db: Session, portfolio_id: int):
        """更新投资组合中所有股票的价格"""
        try:
            # 获取投资组合中的所有股票
            assets = crud.get_portfolio_assets(db, portfolio_id)
            if not assets:
                return
            
            symbols = [asset.symbol for asset in assets]
            prices = await self.get_multiple_prices(symbols)
            
            # 更新每个资产的当前价格
            for asset in assets:
                if asset.symbol in prices:
                    current_price = prices[asset.symbol]
                    market_value = asset.quantity * current_price
                    profit_loss = market_value - (asset.quantity * asset.average_price)
                    profit_loss_percentage = (profit_loss / (asset.quantity * asset.average_price)) * 100 if asset.average_price > 0 else 0
                    
                    # 更新资产信息
                    asset_update = schemas.AssetUpdate(
                        current_price=current_price,
                        market_value=market_value,
                        profit_loss=profit_loss,
                        profit_loss_percentage=profit_loss_percentage
                    )
                    crud.update_asset(db, asset_id=asset.id, asset_update=asset_update)
            
            logger.info(f"Updated prices for portfolio {portfolio_id}: {len(prices)} assets")
            
        except Exception as e:
            logger.error(f"Error updating portfolio prices: {e}")
    
    async def store_historical_data(self, db: Session, symbol: str, period: str = "1y"):
        """将历史数据存储到数据库"""
        try:
            hist_data = await self.get_historical_data(symbol, period)
            if hist_data is None:
                return
            
            # 转换数据格式并存储
            for _, row in hist_data.iterrows():
                market_data = schemas.MarketDataCreate(
                    symbol=symbol,
                    date=row['Date'].to_pydatetime() if hasattr(row['Date'], 'to_pydatetime') else row['Date'],
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume'])
                )
                
                # 使用upsert操作（创建或更新）
                crud.create_market_data(db, market_data)
            
            logger.info(f"Stored historical data for {symbol}: {len(hist_data)} records")
            
        except Exception as e:
            logger.error(f"Error storing historical data for {symbol}: {e}")
    
    def get_supported_symbols(self) -> List[str]:
        """获取支持的股票代码列表"""
        return self.supported_symbols.copy()
    
    async def validate_symbol(self, symbol: str) -> bool:
        """验证股票代码是否有效"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return 'symbol' in info or 'shortName' in info
        except:
            return False


# 全局市场数据服务实例
market_service = MarketDataService()


async def get_market_service() -> MarketDataService:
    """获取市场数据服务实例"""
    return market_service


# 后台任务：定期更新所有投资组合的价格
async def update_all_portfolio_prices():
    """定期更新所有投资组合的价格"""
    db = SessionLocal()
    try:
        # 获取所有投资组合
        portfolios = db.query(models.Portfolio).all()
        
        for portfolio in portfolios:
            await market_service.update_portfolio_prices(db, portfolio.id)
            # 添加短暂延迟避免API限制
            await asyncio.sleep(1)
            
        logger.info(f"Updated prices for {len(portfolios)} portfolios")
        
    except Exception as e:
        logger.error(f"Error in background price update: {e}")
    finally:
        db.close()


# 后台任务：存储历史数据
async def store_daily_market_data():
    """每日存储市场数据"""
    db = SessionLocal()
    try:
        for symbol in market_service.get_supported_symbols():
            await market_service.store_historical_data(db, symbol, "5d")  # 存储最近5天的数据
            await asyncio.sleep(2)  # 避免API限制
            
        logger.info("Daily market data storage completed")
        
    except Exception as e:
        logger.error(f"Error in daily data storage: {e}")
    finally:
        db.close()