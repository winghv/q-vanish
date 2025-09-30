"""
券商管理器
负责管理多个券商配置和实例
"""

import asyncio
from typing import Dict, List, Any, Optional, Type
import logging
from enum import Enum

from .base import BrokerInterface
from .paper_trading import PaperTradingBroker

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """券商类型枚举"""
    PAPER_TRADING = "paper_trading"
    ALPACA = "alpaca"
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"


class BrokerManager:
    """券商管理器"""
    
    def __init__(self):
        """初始化券商管理器"""
        self.broker_classes: Dict[BrokerType, Type[BrokerInterface]] = {
            BrokerType.PAPER_TRADING: PaperTradingBroker,
        }
        
        self.broker_instances: Dict[str, BrokerInterface] = {}
        self.default_configs: Dict[BrokerType, Dict[str, Any]] = {
            BrokerType.PAPER_TRADING: {
                "initial_cash": 100000.0,
                "commission_rate": 0.001,
                "min_commission": 1.0,
                "check_market_hours": False,
                "account_id": "PAPER_ACCOUNT"
            }
        }
        
        logger.info("Broker manager initialized")
    
    def register_broker_class(self, broker_type: BrokerType, broker_class: Type[BrokerInterface]):
        """
        注册券商类
        
        Args:
            broker_type: 券商类型
            broker_class: 券商实现类
        """
        self.broker_classes[broker_type] = broker_class
        logger.info(f"Registered broker class: {broker_type.value}")
    
    def set_default_config(self, broker_type: BrokerType, config: Dict[str, Any]):
        """
        设置默认配置
        
        Args:
            broker_type: 券商类型
            config: 默认配置
        """
        self.default_configs[broker_type] = config.copy()
        logger.info(f"Set default config for {broker_type.value}")
    
    async def create_broker(
        self, 
        broker_id: str,
        broker_type: BrokerType, 
        config: Optional[Dict[str, Any]] = None
    ) -> BrokerInterface:
        """
        创建券商实例
        
        Args:
            broker_id: 券商实例ID
            broker_type: 券商类型
            config: 券商配置，如果为None则使用默认配置
            
        Returns:
            券商实例
        """
        if broker_type not in self.broker_classes:
            raise ValueError(f"Unsupported broker type: {broker_type.value}")
        
        if broker_id in self.broker_instances:
            raise ValueError(f"Broker instance already exists: {broker_id}")
        
        # 合并配置
        final_config = self.default_configs.get(broker_type, {}).copy()
        if config:
            final_config.update(config)
        
        # 创建实例
        broker_class = self.broker_classes[broker_type]
        broker_instance = broker_class(final_config)
        
        # 尝试连接
        connected = await broker_instance.connect()
        if not connected:
            raise RuntimeError(f"Failed to connect to broker: {broker_id}")
        
        # 存储实例
        self.broker_instances[broker_id] = broker_instance
        
        logger.info(f"Created broker instance: {broker_id} ({broker_type.value})")
        return broker_instance
    
    async def get_broker(self, broker_id: str) -> Optional[BrokerInterface]:
        """
        获取券商实例
        
        Args:
            broker_id: 券商实例ID
            
        Returns:
            券商实例，如果不存在则返回None
        """
        return self.broker_instances.get(broker_id)
    
    async def remove_broker(self, broker_id: str) -> bool:
        """
        移除券商实例
        
        Args:
            broker_id: 券商实例ID
            
        Returns:
            是否移除成功
        """
        if broker_id not in self.broker_instances:
            return False
        
        broker = self.broker_instances[broker_id]
        
        # 断开连接
        await broker.disconnect()
        
        # 删除实例
        del self.broker_instances[broker_id]
        
        logger.info(f"Removed broker instance: {broker_id}")
        return True
    
    async def list_brokers(self) -> List[Dict[str, Any]]:
        """
        列出所有券商实例
        
        Returns:
            券商实例信息列表
        """
        broker_list = []
        
        for broker_id, broker in self.broker_instances.items():
            broker_info = {
                "broker_id": broker_id,
                "broker_name": broker.get_broker_name(),
                "is_connected": broker.is_connected,
                "config": broker.get_broker_config()
            }
            
            # 如果是模拟交易，添加性能摘要
            if isinstance(broker, PaperTradingBroker):
                broker_info["performance"] = broker.get_performance_summary()
            
            broker_list.append(broker_info)
        
        return broker_list
    
    async def get_default_broker(self) -> Optional[BrokerInterface]:
        """
        获取默认券商实例
        
        Returns:
            默认券商实例，如果没有则返回None
        """
        if not self.broker_instances:
            # 如果没有任何实例，创建一个默认的模拟交易实例
            try:
                return await self.create_broker(
                    "default_paper",
                    BrokerType.PAPER_TRADING
                )
            except Exception as e:
                logger.error(f"Failed to create default broker: {e}")
                return None
        
        # 返回第一个实例作为默认
        return next(iter(self.broker_instances.values()))
    
    async def shutdown_all(self):
        """关闭所有券商连接"""
        broker_ids = list(self.broker_instances.keys())
        
        for broker_id in broker_ids:
            try:
                await self.remove_broker(broker_id)
            except Exception as e:
                logger.error(f"Error shutting down broker {broker_id}: {e}")
        
        logger.info("All brokers shutdown complete")
    
    def get_supported_broker_types(self) -> List[BrokerType]:
        """获取支持的券商类型列表"""
        return list(self.broker_classes.keys())
    
    def validate_broker_config(
        self, 
        broker_type: BrokerType, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证券商配置
        
        Args:
            broker_type: 券商类型
            config: 配置参数
            
        Returns:
            验证结果
        """
        if broker_type not in self.broker_classes:
            return {"valid": False, "error": f"Unsupported broker type: {broker_type.value}"}
        
        # 根据券商类型进行特定验证
        if broker_type == BrokerType.PAPER_TRADING:
            return self._validate_paper_trading_config(config)
        
        # 默认返回有效
        return {"valid": True, "error": None}
    
    def _validate_paper_trading_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证模拟交易配置"""
        required_fields = []  # 模拟交易没有必需字段
        optional_fields = ["initial_cash", "commission_rate", "min_commission", "check_market_hours"]
        
        # 检查初始资金
        initial_cash = config.get("initial_cash")
        if initial_cash is not None:
            if not isinstance(initial_cash, (int, float)) or initial_cash <= 0:
                return {"valid": False, "error": "initial_cash must be a positive number"}
        
        # 检查佣金率
        commission_rate = config.get("commission_rate")
        if commission_rate is not None:
            if not isinstance(commission_rate, (int, float)) or commission_rate < 0:
                return {"valid": False, "error": "commission_rate must be a non-negative number"}
        
        return {"valid": True, "error": None}


# 全局券商管理器实例
broker_manager = BrokerManager()


async def get_broker_manager() -> BrokerManager:
    """获取券商管理器实例"""
    return broker_manager


async def get_default_broker() -> Optional[BrokerInterface]:
    """获取默认券商实例的便捷函数"""
    return await broker_manager.get_default_broker()


async def initialize_default_brokers():
    """初始化默认券商实例"""
    try:
        # 创建默认的模拟交易实例
        await broker_manager.create_broker(
            "default_paper",
            BrokerType.PAPER_TRADING,
            {
                "initial_cash": 100000.0,
                "commission_rate": 0.001,
                "min_commission": 1.0,
                "check_market_hours": False
            }
        )
        logger.info("Default brokers initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize default brokers: {e}")


# 在应用启动时调用
async def startup_brokers():
    """应用启动时初始化券商"""
    await initialize_default_brokers()


# 在应用关闭时调用
async def shutdown_brokers():
    """应用关闭时清理券商"""
    await broker_manager.shutdown_all()