"""
API 速率限制工具模块
提供基于用户的API请求频率限制功能
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from typing import Optional
import logging

from .. import models

logger = logging.getLogger(__name__)

# 创建限制器实例
limiter = Limiter(key_func=get_remote_address)

def get_user_id_from_request(request: Request) -> str:
    """从请求中获取用户ID作为限制键"""
    try:
        # 从请求状态中获取当前用户（需要在认证中间件中设置）
        if hasattr(request.state, 'user') and request.state.user:
            return f"user:{request.state.user.id}"
        
        # 如果没有用户信息，使用IP地址
        return get_remote_address(request)
    except Exception:
        return get_remote_address(request)

def get_user_role_from_request(request: Request) -> str:
    """从请求中获取用户角色"""
    try:
        if hasattr(request.state, 'user') and request.state.user:
            return request.state.user.role
        return "anonymous"
    except Exception:
        return "anonymous"

# 创建基于用户的限制器
user_limiter = Limiter(key_func=get_user_id_from_request)

# 定义不同用户角色的限制规则
RATE_LIMITS = {
    "admin": {
        "general": "1000/minute",      # 管理员：每分钟1000次请求
        "market_data": "500/minute",   # 市场数据：每分钟500次
        "trading": "200/minute",       # 交易相关：每分钟200次
    },
    "user": {
        "general": "100/minute",       # 普通用户：每分钟100次请求
        "market_data": "50/minute",    # 市场数据：每分钟50次
        "trading": "20/minute",        # 交易相关：每分钟20次
    },
    "anonymous": {
        "general": "10/minute",        # 匿名用户：每分钟10次请求
        "market_data": "5/minute",     # 市场数据：每分钟5次
        "trading": "0/minute",         # 交易相关：不允许
    }
}

def get_rate_limit_for_user(request: Request, endpoint_type: str = "general") -> str:
    """根据用户角色获取相应的速率限制"""
    user_role = get_user_role_from_request(request)
    
    if user_role in RATE_LIMITS and endpoint_type in RATE_LIMITS[user_role]:
        return RATE_LIMITS[user_role][endpoint_type]
    
    # 默认使用最严格的限制
    return RATE_LIMITS["anonymous"]["general"]

def create_rate_limit_dependency(endpoint_type: str = "general"):
    """创建特定类型端点的速率限制依赖"""
    def rate_limit_dependency(request: Request):
        try:
            # 获取适当的速率限制
            rate_limit = get_rate_limit_for_user(request, endpoint_type)
            
            # 检查速率限制
            user_limiter.limit(rate_limit)(lambda: None)()
            
        except RateLimitExceeded as e:
            user_role = get_user_role_from_request(request)
            logger.warning(f"Rate limit exceeded for {user_role} user on {endpoint_type} endpoint")
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "速率限制超出",
                    "message": f"您的请求频率过高，请稍后再试",
                    "retry_after": e.retry_after,
                    "limit": rate_limit,
                    "endpoint_type": endpoint_type
                }
            )
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # 如果速率限制出错，不阻塞请求
            pass
    
    return rate_limit_dependency

# 预定义的速率限制依赖
general_rate_limit = create_rate_limit_dependency("general")
market_data_rate_limit = create_rate_limit_dependency("market_data") 
trading_rate_limit = create_rate_limit_dependency("trading")

def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """自定义速率限制超出处理器"""
    user_role = get_user_role_from_request(request)
    
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "请求频率限制",
            "message": "您的请求过于频繁，请稍后重试",
            "retry_after": exc.retry_after,
            "user_type": user_role
        }
    )

# 速率限制统计
class RateLimitStats:
    """速率限制统计类"""
    
    def __init__(self):
        self.request_counts = {}
        self.blocked_counts = {}
    
    def record_request(self, user_id: str, endpoint_type: str):
        """记录请求"""
        key = f"{user_id}:{endpoint_type}"
        self.request_counts[key] = self.request_counts.get(key, 0) + 1
    
    def record_blocked(self, user_id: str, endpoint_type: str):
        """记录被阻塞的请求"""
        key = f"{user_id}:{endpoint_type}"
        self.blocked_counts[key] = self.blocked_counts.get(key, 0) + 1
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_requests": sum(self.request_counts.values()),
            "total_blocked": sum(self.blocked_counts.values()),
            "by_endpoint": {
                "requests": self.request_counts.copy(),
                "blocked": self.blocked_counts.copy()
            }
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.request_counts.clear()
        self.blocked_counts.clear()

# 全局统计实例
rate_limit_stats = RateLimitStats()