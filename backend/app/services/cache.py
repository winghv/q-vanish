"""
缓存服务模块
提供Redis缓存功能，用于缓存市场数据和用户数据
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import redis
import logging
from contextlib import asynccontextmanager

from .. import config

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务类"""
    
    def __init__(self, redis_url: str = None):
        """
        初始化缓存服务
        
        Args:
            redis_url: Redis连接URL，如果为None则使用内存缓存
        """
        self.redis_url = redis_url or getattr(config, 'REDIS_URL', None)
        self.redis_client = None
        self.memory_cache = {}  # 内存缓存作为fallback
        
        if self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url, 
                    decode_responses=False,  # 保持二进制数据
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # 测试连接
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}, falling back to memory cache")
                self.redis_client = None
        else:
            logger.info("Using memory cache (Redis not configured)")
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        """生成缓存键"""
        return f"qvanish:{prefix}:{identifier}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """序列化数据"""
        try:
            # 对于简单的JSON可序列化数据，使用JSON
            if isinstance(data, (dict, list, str, int, float, bool)) or data is None:
                return json.dumps(data, default=str).encode('utf-8')
        except (TypeError, ValueError):
            pass
        
        # 对于复杂对象，使用pickle
        return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """反序列化数据"""
        try:
            # 尝试JSON反序列化
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # 使用pickle反序列化
            return pickle.loads(data)
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire_seconds: int = 300
    ) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            expire_seconds: 过期时间（秒）
            
        Returns:
            是否设置成功
        """
        try:
            serialized_data = self._serialize_data(value)
            
            if self.redis_client:
                result = self.redis_client.setex(
                    key, 
                    expire_seconds, 
                    serialized_data
                )
                return bool(result)
            else:
                # 内存缓存
                expire_time = datetime.now() + timedelta(seconds=expire_seconds)
                self.memory_cache[key] = {
                    'data': serialized_data,
                    'expire_time': expire_time
                }
                return True
                
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或过期则返回None
        """
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                if data is None:
                    return None
                return self._deserialize_data(data)
            else:
                # 内存缓存
                if key not in self.memory_cache:
                    return None
                
                cache_item = self.memory_cache[key]
                if datetime.now() > cache_item['expire_time']:
                    del self.memory_cache[key]
                    return None
                
                return self._deserialize_data(cache_item['data'])
                
        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        try:
            if self.redis_client:
                result = self.redis_client.delete(key)
                return bool(result)
            else:
                # 内存缓存
                if key in self.memory_cache:
                    del self.memory_cache[key]
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            else:
                # 内存缓存
                if key not in self.memory_cache:
                    return False
                
                cache_item = self.memory_cache[key]
                if datetime.now() > cache_item['expire_time']:
                    del self.memory_cache[key]
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to check cache existence for key {key}: {e}")
            return False
    
    async def set_market_price(
        self, 
        symbol: str, 
        price: float, 
        expire_seconds: int = 300
    ) -> bool:
        """
        缓存股票价格
        
        Args:
            symbol: 股票代码
            price: 价格
            expire_seconds: 过期时间（秒），默认5分钟
            
        Returns:
            是否设置成功
        """
        key = self._get_key("price", symbol)
        price_data = {
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.now().isoformat()
        }
        return await self.set(key, price_data, expire_seconds)
    
    async def get_market_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的股票价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            价格数据字典或None
        """
        key = self._get_key("price", symbol)
        return await self.get(key)
    
    async def set_portfolio_data(
        self, 
        user_id: int, 
        portfolio_data: Any, 
        expire_seconds: int = 600
    ) -> bool:
        """
        缓存投资组合数据
        
        Args:
            user_id: 用户ID
            portfolio_data: 投资组合数据
            expire_seconds: 过期时间（秒），默认10分钟
            
        Returns:
            是否设置成功
        """
        key = self._get_key("portfolio", str(user_id))
        return await self.set(key, portfolio_data, expire_seconds)
    
    async def get_portfolio_data(self, user_id: int) -> Optional[Any]:
        """
        获取缓存的投资组合数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            投资组合数据或None
        """
        key = self._get_key("portfolio", str(user_id))
        return await self.get(key)
    
    async def set_user_session(
        self, 
        user_id: int, 
        session_data: Dict[str, Any], 
        expire_seconds: int = 1800
    ) -> bool:
        """
        缓存用户会话数据
        
        Args:
            user_id: 用户ID
            session_data: 会话数据
            expire_seconds: 过期时间（秒），默认30分钟
            
        Returns:
            是否设置成功
        """
        key = self._get_key("session", str(user_id))
        return await self.set(key, session_data, expire_seconds)
    
    async def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取缓存的用户会话数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话数据或None
        """
        key = self._get_key("session", str(user_id))
        return await self.get(key)
    
    async def clear_user_cache(self, user_id: int) -> bool:
        """
        清除用户相关的所有缓存
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否清除成功
        """
        try:
            user_id_str = str(user_id)
            keys_to_delete = []
            
            if self.redis_client:
                # Redis模式：查找所有用户相关的键
                pattern = f"qvanish:*:{user_id_str}"
                keys_to_delete = self.redis_client.keys(pattern)
                if keys_to_delete:
                    self.redis_client.delete(*keys_to_delete)
            else:
                # 内存缓存模式
                keys_to_delete = [
                    key for key in self.memory_cache.keys() 
                    if key.endswith(f":{user_id_str}")
                ]
                for key in keys_to_delete:
                    del self.memory_cache[key]
            
            logger.info(f"Cleared {len(keys_to_delete)} cache entries for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear user cache for user {user_id}: {e}")
            return False
    
    async def clear_expired_cache(self):
        """清理过期的内存缓存项"""
        if not self.redis_client:  # 只在使用内存缓存时需要
            current_time = datetime.now()
            expired_keys = [
                key for key, item in self.memory_cache.items()
                if current_time > item['expire_time']
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
            
            if expired_keys:
                logger.info(f"Cleared {len(expired_keys)} expired cache entries")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计数据
        """
        try:
            if self.redis_client:
                info = self.redis_client.info()
                return {
                    "type": "redis",
                    "connected": True,
                    "used_memory": info.get('used_memory_human', 'N/A'),
                    "connected_clients": info.get('connected_clients', 0),
                    "total_commands_processed": info.get('total_commands_processed', 0)
                }
            else:
                # 清理过期项
                await self.clear_expired_cache()
                return {
                    "type": "memory",
                    "connected": True,
                    "cache_size": len(self.memory_cache),
                    "memory_usage": "N/A"
                }
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "type": "unknown",
                "connected": False,
                "error": str(e)
            }


# 全局缓存服务实例
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """获取缓存服务实例"""
    return cache_service