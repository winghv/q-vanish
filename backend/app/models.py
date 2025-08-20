from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class StrategyType(str, enum.Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    PAIRS_TRADING = "pairs_trading"
    CUSTOM = "custom"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    strategies = relationship("Strategy", back_populates="owner")
    backtests = relationship("Backtest", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    portfolios = relationship("Portfolio", back_populates="user")

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    type = Column(String, default=StrategyType.CUSTOM)
    parameters = Column(JSON)
    code = Column(Text)
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))

    # 关系
    owner = relationship("User", back_populates="strategies")
    backtests = relationship("Backtest", back_populates="strategy")
    trades = relationship("Trade", back_populates="strategy")

class Backtest(Base):
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    initial_capital = Column(Float)
    final_capital = Column(Float)
    profit_loss = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    results = Column(JSON)
    status = Column(String)  # "pending", "running", "completed", "failed"
    created_at = Column(DateTime, default=datetime.utcnow)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    # 关系
    strategy = relationship("Strategy", back_populates="backtests")
    user = relationship("User", back_populates="backtests")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    order_type = Column(String)  # "buy", "sell"
    price = Column(Float)
    quantity = Column(Float)
    status = Column(String)  # "pending", "executed", "canceled", "failed"
    executed_at = Column(DateTime)
    profit_loss = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))

    # 关系
    strategy = relationship("Strategy", back_populates="trades")
    user = relationship("User", back_populates="trades")
    portfolio = relationship("Portfolio", back_populates="trades")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    total_value = Column(Float)
    cash_balance = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

    # 关系
    user = relationship("User", back_populates="portfolios")
    trades = relationship("Trade", back_populates="portfolio")
    assets = relationship("PortfolioAsset", back_populates="portfolio")

class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    quantity = Column(Float)
    average_price = Column(Float)
    current_price = Column(Float)
    market_value = Column(Float)
    profit_loss = Column(Float)
    profit_loss_percentage = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))

    # 关系
    portfolio = relationship("Portfolio", back_populates="assets")

class AIAssistantChat(Base):
    __tablename__ = "ai_assistant_chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    response = Column(Text)
    context = Column(JSON) # 存储对话的上下文信息
    created_at = Column(DateTime, default=datetime.utcnow)

class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    date = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class Config:
        table_name = "market_data"
        indexes = [
            ("symbol", "date", "unique"),
        ]

class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String, index=True)  # openai, alpaca, binance, etc.
    key_hash = Column(String)  # 加密存储的密钥
    key_preview = Column(String)  # 用于显示的密钥预览 (如: sk-...abc123)
    status = Column(String, default="active")  # active, inactive
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", backref="api_keys")

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    notification_settings = Column(JSON)  # 存储通知设置
    trading_preferences = Column(JSON)  # 存储交易偏好设置
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", backref="settings") 