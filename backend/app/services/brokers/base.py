"""
抽象券商接口定义
定义所有券商实现必须遵循的基础接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import uuid


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """订单类型枚举"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"
    BRACKET = "bracket"
    OCO = "oco"  # One-Cancels-Other


class OrderSide(Enum):
    """订单方向枚举"""
    BUY = "buy"
    SELL = "sell"


class TimeInForce(Enum):
    """订单有效期枚举"""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill


@dataclass
class OrderRequest:
    """订单请求数据结构"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    client_order_id: Optional[str] = None
    
    # 高级订单参数
    parent_order_id: Optional[str] = None  # 用于括号订单
    oco_group_id: Optional[str] = None     # 用于OCO订单
    
    def __post_init__(self):
        if not self.client_order_id:
            self.client_order_id = str(uuid.uuid4())


@dataclass
class OrderResponse:
    """订单响应数据结构"""
    broker_order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    filled_quantity: float
    remaining_quantity: float
    price: Optional[float]
    average_fill_price: Optional[float]
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    commission: float = 0.0
    message: Optional[str] = None


@dataclass
class Position:
    """持仓数据结构"""
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    side: str  # "long" or "short"


@dataclass
class AccountInfo:
    """账户信息数据结构"""
    account_id: str
    cash_balance: float
    total_value: float
    buying_power: float
    day_trading_buying_power: float
    maintenance_margin: float
    currency: str = "USD"


class BrokerInterface(ABC):
    """抽象券商接口"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化券商接口
        
        Args:
            config: 券商配置参数
        """
        self.config = config
        self.is_connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        连接到券商
        
        Returns:
            是否连接成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """断开券商连接"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """
        获取账户信息
        
        Returns:
            账户信息
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        获取持仓信息
        
        Returns:
            持仓列表
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        获取特定股票的持仓信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            持仓信息，如果没有持仓则返回None
        """
        pass
    
    @abstractmethod
    async def submit_order(self, order_request: OrderRequest) -> OrderResponse:
        """
        提交订单
        
        Args:
            order_request: 订单请求
            
        Returns:
            订单响应
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """
        取消订单
        
        Args:
            broker_order_id: 券商订单ID
            
        Returns:
            是否取消成功
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> Optional[OrderResponse]:
        """
        获取订单状态
        
        Args:
            broker_order_id: 券商订单ID
            
        Returns:
            订单信息，如果订单不存在则返回None
        """
        pass
    
    @abstractmethod
    async def get_orders(
        self, 
        status: Optional[OrderStatus] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[OrderResponse]:
        """
        获取订单列表
        
        Args:
            status: 订单状态过滤器
            symbol: 股票代码过滤器
            limit: 最大返回数量
            
        Returns:
            订单列表
        """
        pass
    
    @abstractmethod
    async def get_market_price(self, symbol: str) -> Optional[float]:
        """
        获取市场价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            当前价格，如果获取失败则返回None
        """
        pass
    
    async def validate_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """
        验证订单有效性
        
        Args:
            order_request: 订单请求
            
        Returns:
            验证结果，包含是否有效和错误信息
        """
        # 基础验证逻辑
        if order_request.quantity <= 0:
            return {"valid": False, "error": "订单数量必须大于0"}
        
        if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if not order_request.price or order_request.price <= 0:
                return {"valid": False, "error": "限价单必须指定有效价格"}
        
        if order_request.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT]:
            if not order_request.stop_price or order_request.stop_price <= 0:
                return {"valid": False, "error": "止损单必须指定有效止损价格"}
        
        return {"valid": True, "error": None}
    
    async def calculate_commission(self, order_request: OrderRequest, fill_price: float) -> float:
        """
        计算佣金
        
        Args:
            order_request: 订单请求
            fill_price: 成交价格
            
        Returns:
            佣金金额
        """
        # 默认佣金计算，可被子类重写
        trade_value = order_request.quantity * fill_price
        commission_rate = self.config.get("commission_rate", 0.001)  # 默认0.1%
        min_commission = self.config.get("min_commission", 1.0)      # 最低1美元
        
        commission = max(trade_value * commission_rate, min_commission)
        return round(commission, 2)
    
    def is_market_open(self) -> bool:
        """
        检查市场是否开放
        
        Returns:
            市场是否开放
        """
        # 简化实现，实际应该检查交易所时间
        from datetime import datetime, time
        now = datetime.now().time()
        market_open = time(9, 30)  # 9:30 AM
        market_close = time(16, 0)  # 4:00 PM
        
        return market_open <= now <= market_close
    
    def get_broker_name(self) -> str:
        """获取券商名称"""
        return self.__class__.__name__
    
    def get_broker_config(self) -> Dict[str, Any]:
        """获取券商配置（隐藏敏感信息）"""
        safe_config = self.config.copy()
        
        # 隐藏敏感信息
        sensitive_keys = ['api_key', 'secret_key', 'password', 'token']
        for key in sensitive_keys:
            if key in safe_config:
                safe_config[key] = "*" * 8
        
        return safe_config


class BrokerError(Exception):
    """券商操作异常"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class OrderRejectedException(BrokerError):
    """订单被拒绝异常"""
    pass


class InsufficientFundsException(BrokerError):
    """资金不足异常"""
    pass


class MarketClosedException(BrokerError):
    """市场关闭异常"""
    pass