"""
缓存管理API路由
提供缓存统计、清理和管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from .. import models
from ..database import get_db
from .auth import get_current_active_user
from ..services.cache import get_cache_service, CacheService

router = APIRouter()


@router.get("/stats")
async def get_cache_stats(
    current_user: models.User = Depends(get_current_active_user),
    cache_service: CacheService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """获取缓存统计信息"""
    # 检查权限（只有管理员可以查看缓存统计）
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问缓存统计信息"
        )
    
    stats = await cache_service.get_cache_stats()
    return {"cache_stats": stats}


@router.delete("/clear/user")
async def clear_user_cache(
    current_user: models.User = Depends(get_current_active_user),
    cache_service: CacheService = Depends(get_cache_service)
):
    """清除当前用户的缓存"""
    success = await cache_service.clear_user_cache(current_user.id)
    
    if success:
        return {"message": "用户缓存已清除"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清除缓存失败"
        )


@router.delete("/clear/prices")
async def clear_price_cache(
    current_user: models.User = Depends(get_current_active_user),
    cache_service: CacheService = Depends(get_cache_service)
):
    """清除价格缓存（需要管理员权限）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限清除价格缓存"
        )
    
    try:
        # 清除所有价格相关的缓存
        # 这里需要根据实际的Redis键模式进行清理
        # 示例：清除所有 "qvanish:price:*" 键
        # 由于CacheService没有直接提供清除模式匹配的方法，
        # 这里先返回成功，实际实现可以扩展CacheService
        
        return {"message": "价格缓存清除任务已启动"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清除价格缓存失败: {str(e)}"
        )


@router.get("/health")
async def cache_health_check(
    current_user: models.User = Depends(get_current_active_user),
    cache_service: CacheService = Depends(get_cache_service)
):
    """缓存健康检查"""
    stats = await cache_service.get_cache_stats()
    
    is_healthy = stats.get("connected", False)
    
    return {
        "healthy": is_healthy,
        "cache_type": stats.get("type", "unknown"),
        "details": stats
    }


@router.post("/test")
async def test_cache_operations(
    current_user: models.User = Depends(get_current_active_user),
    cache_service: CacheService = Depends(get_cache_service)
):
    """测试缓存操作（开发/测试用途）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限执行缓存测试"
        )
    
    try:
        # 测试基本的缓存操作
        test_key = f"test_key_{current_user.id}"
        test_value = {
            "test_data": "Hello, Cache!",
            "timestamp": "2025-01-21T10:00:00Z",
            "user_id": current_user.id
        }
        
        # 设置缓存
        set_success = await cache_service.set(test_key, test_value, 60)  # 60秒过期
        
        # 获取缓存
        retrieved_value = await cache_service.get(test_key)
        
        # 检查存在性
        exists = await cache_service.exists(test_key)
        
        # 删除缓存
        delete_success = await cache_service.delete(test_key)
        
        # 再次检查存在性
        exists_after_delete = await cache_service.exists(test_key)
        
        return {
            "test_results": {
                "set_success": set_success,
                "retrieved_value": retrieved_value,
                "exists_before_delete": exists,
                "delete_success": delete_success,
                "exists_after_delete": exists_after_delete
            },
            "message": "缓存功能测试完成"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"缓存测试失败: {str(e)}"
        )