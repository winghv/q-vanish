from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# 用户相关模式
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserInDB(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class User(UserInDB):
    pass

# 策略相关模式
class StrategyType(str, Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    PAIRS_TRADING = "pairs_trading"
    CUSTOM = "custom"

class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: StrategyType = StrategyType.CUSTOM
    parameters: Optional[Dict[str, Any]] = None
    code: Optional[str] = None
    is_active: bool = True
    is_public: bool = False

class StrategyCreate(StrategyBase):
    pass

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[StrategyType] = None
    parameters: Optional[Dict[str, Any]] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None

class StrategyInDB(StrategyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    owner_id: int

    class Config:
        from_attributes = True

class Strategy(StrategyInDB):
    pass

# 回测相关模式
class BacktestBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    strategy_id: int

class BacktestCreate(BacktestBase):
    pass

class BacktestUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    final_capital: Optional[float] = None
    profit_loss: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    results: Optional[Dict[str, Any]] = None

class BacktestInDB(BacktestBase):
    id: int
    final_capital: Optional[float] = None
    profit_loss: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    results: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    user_id: int

    class Config:
        from_attributes = True

class Backtest(BacktestInDB):
    pass

# 交易相关模式
class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELED = "canceled"
    FAILED = "failed"

class TradeBase(BaseModel):
    symbol: str
    order_type: OrderType
    price: float
    quantity: float
    strategy_id: Optional[int] = None
    portfolio_id: Optional[int] = None

class TradeCreate(TradeBase):
    pass

class TradeUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    executed_at: Optional[datetime] = None
    profit_loss: Optional[float] = None

class TradeInDB(TradeBase):
    id: int
    status: OrderStatus
    executed_at: Optional[datetime] = None
    profit_loss: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    user_id: int

    class Config:
        from_attributes = True

class Trade(TradeInDB):
    pass

# 资产组合相关模式
class PortfolioBase(BaseModel):
    name: str
    description: Optional[str] = None
    cash_balance: float = 0.0

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cash_balance: Optional[float] = None
    total_value: Optional[float] = None

class PortfolioInDB(PortfolioBase):
    id: int
    total_value: float
    created_at: datetime
    updated_at: datetime
    user_id: int

    class Config:
        from_attributes = True

class Portfolio(PortfolioInDB):
    pass

# 资产相关模式
class AssetBase(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    portfolio_id: int

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    quantity: Optional[float] = None
    average_price: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percentage: Optional[float] = None

class AssetInDB(AssetBase):
    id: int
    current_price: float
    market_value: float
    profit_loss: float
    profit_loss_percentage: float
    updated_at: datetime

    class Config:
        from_attributes = True

class Asset(AssetInDB):
    pass

# AI助手相关模式
class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    context: Optional[Dict[str, Any]] = None

# 认证相关模式
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# 市场数据相关模式
class MarketDataCreate(BaseModel):
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class MarketData(MarketDataCreate):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

class MarketDataFilter(BaseModel):
    symbol: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = 100 