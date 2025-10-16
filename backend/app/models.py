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
    is_verified = Column(Boolean, default=False)  # 邮箱验证状态
    failed_login_attempts = Column(Integer, default=0)  # 失败登录次数
    locked_until = Column(DateTime, nullable=True)  # 账户锁定到期时间
    last_login = Column(DateTime, nullable=True)  # 最后登录时间
    last_login_ip = Column(String, nullable=True)  # 最后登录IP
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

class BacktestResult(Base):
    """回测结果模型"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), index=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    initial_capital = Column(Float)
    final_capital = Column(Float)
    total_return = Column(Float)  # 总回报率
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    total_trades = Column(Integer, default=0)
    metrics = Column(JSON, nullable=True)  # 其他绩效指标
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    order_type = Column(String)  # "buy", "sell"
    advanced_order_type = Column(String, default="MARKET")  # "MARKET", "LIMIT", "STOP_LOSS", "TAKE_PROFIT", "STOP_LIMIT"
    price = Column(Float)
    quantity = Column(Float)
    stop_price = Column(Float)  # 止损价格
    take_profit_price = Column(Float)  # 止盈价格
    time_in_force = Column(String, default="DAY")  # "DAY", "GTC", "IOC", "FOK"
    status = Column(String)  # "pending", "executed", "canceled", "failed", "partial_filled"
    filled_quantity = Column(Float, default=0.0)  # 已成交数量
    average_fill_price = Column(Float)  # 平均成交价格
    executed_at = Column(DateTime)
    profit_loss = Column(Float)
    commission = Column(Float, default=0.0)  # 佣金
    notes = Column(Text)  # 订单备注
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

# Trading Audit and Risk Management Models

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"

class TradingAction(str, enum.Enum):
    ORDER_SUBMITTED = "order_submitted"
    ORDER_MODIFIED = "order_modified"
    ORDER_CANCELED = "order_canceled"
    ORDER_FILLED = "order_filled"
    ORDER_PARTIAL_FILLED = "order_partial_filled"
    ORDER_REJECTED = "order_rejected"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_MODIFIED = "position_modified"
    RISK_ALERT_TRIGGERED = "risk_alert_triggered"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"

class TradingAuditLog(Base):
    """交易审计日志"""
    __tablename__ = "trading_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    action = Column(Enum(TradingAction), index=True)
    symbol = Column(String, index=True, nullable=True)
    quantity = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    old_values = Column(JSON, nullable=True)  # 修改前的值
    new_values = Column(JSON, nullable=True)  # 修改后的值
    extra_data = Column(JSON, nullable=True)  # 额外的元数据
    message = Column(Text, nullable=True)  # 详细信息
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关系
    user = relationship("User", backref="audit_logs")
    portfolio = relationship("Portfolio", backref="audit_logs")
    trade = relationship("Trade", backref="audit_logs")

class OrderStateLog(Base):
    """订单状态变更日志"""
    __tablename__ = "order_state_logs"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), index=True)
    previous_status = Column(Enum(OrderStatus), nullable=True)
    new_status = Column(Enum(OrderStatus))
    filled_quantity = Column(Float, default=0.0)
    remaining_quantity = Column(Float, default=0.0)
    fill_price = Column(Float, nullable=True)
    commission = Column(Float, default=0.0)
    reason = Column(String, nullable=True)  # 状态变更原因
    broker_order_id = Column(String, nullable=True)  # 券商订单ID
    extra_data = Column(JSON, nullable=True)  # 额外信息
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    trade = relationship("Trade", backref="state_logs")

class RiskEvent(Base):
    """风险事件记录"""
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    risk_type = Column(String, index=True)  # concentration, drawdown, volatility, leverage, etc.
    risk_level = Column(Enum(RiskLevel))
    current_value = Column(Float)
    limit_value = Column(Float)
    threshold_exceeded = Column(Boolean, default=True)
    symbol = Column(String, nullable=True)
    message = Column(Text)
    actions_taken = Column(JSON, nullable=True)  # 采取的措施
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关系
    user = relationship("User", backref="risk_events")
    portfolio = relationship("Portfolio", backref="risk_events")
    trade = relationship("Trade", backref="risk_events")

class TradingSession(Base):
    """交易会话记录"""
    __tablename__ = "trading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_start = Column(DateTime, default=datetime.utcnow)
    session_end = Column(DateTime, nullable=True)
    total_trades = Column(Integer, default=0)
    total_volume = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    ip_address = Column(String)
    user_agent = Column(String)
    session_metadata = Column(JSON, nullable=True)  # 会话额外信息
    is_active = Column(Boolean, default=True)

    # 关系
    user = relationship("User", backref="trading_sessions")

class ComplianceCheck(Base):
    """合规检查记录"""
    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    check_type = Column(String, index=True)  # risk_limit, concentration, day_trading, etc.
    check_result = Column(String)  # passed, failed, warning
    rule_name = Column(String)
    rule_description = Column(Text)
    violation_details = Column(JSON, nullable=True)
    action_required = Column(String, nullable=True)  # block, warn, log
    action_taken = Column(String, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", backref="compliance_checks")
    trade = relationship("Trade", backref="compliance_checks")

class PerformanceMetrics(Base):
    """性能指标记录"""
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True, index=True)
    date = Column(DateTime, index=True)
    total_value = Column(Float)
    cash_balance = Column(Float)
    invested_amount = Column(Float)
    daily_pnl = Column(Float)
    daily_pnl_percent = Column(Float)
    cumulative_pnl = Column(Float)
    cumulative_pnl_percent = Column(Float)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    var_95 = Column(Float, nullable=True)  # 95% Value at Risk
    beta = Column(Float, nullable=True)  # 相对市场的Beta
    alpha = Column(Float, nullable=True)  # Alpha值
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    positions_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", backref="performance_metrics")
    portfolio = relationship("Portfolio", backref="performance_metrics")