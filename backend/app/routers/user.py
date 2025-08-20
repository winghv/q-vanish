from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

@router.get("/profile")
async def get_user_profile(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取用户配置文件"""
    return {
        "name": current_user.username,
        "email": current_user.email,
        "avatar": f"https://ui-avatars.com/api/?name={current_user.username}&background=6366f1&color=fff"
    }

@router.put("/profile")
async def update_user_profile(
    profile_data: Dict[str, Any],
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """更新用户配置文件"""
    try:
        # 提取更新数据
        name = profile_data.get("name", current_user.username)
        email = profile_data.get("email", current_user.email)
        
        # 验证email格式
        if "@" not in email:
            raise HTTPException(status_code=400, detail="邮箱格式无效")
        
        # 检查email是否已被其他用户使用
        if email != current_user.email:
            existing_user = crud.get_user_by_email(db, email=email)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(status_code=400, detail="该邮箱已被使用")
        
        # 更新用户信息
        user_update = schemas.UserUpdate(
            username=name,
            email=email
        )
        updated_user = crud.update_user(db, user_id=current_user.id, user_update=user_update)
        
        return {
            "name": updated_user.username,
            "email": updated_user.email,
            "avatar": f"https://ui-avatars.com/api/?name={updated_user.username}&background=6366f1&color=fff"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新用户信息失败: {str(e)}")

@router.get("/notifications")
async def get_notification_settings(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, bool]:
    """获取通知设置"""
    # 从用户配置或数据库获取通知设置，这里使用默认值
    user_settings = crud.get_user_settings(db, user_id=current_user.id)
    
    if user_settings and user_settings.notification_settings:
        try:
            settings = json.loads(user_settings.notification_settings)
        except:
            settings = {}
    else:
        settings = {}
    
    return {
        "email_alerts": settings.get("email_alerts", True),
        "trading_alerts": settings.get("trading_alerts", True),
        "market_updates": settings.get("market_updates", False),
        "weekly_reports": settings.get("weekly_reports", True)
    }

@router.put("/notifications")
async def update_notification_settings(
    settings_data: Dict[str, bool],
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, bool]:
    """更新通知设置"""
    try:
        # 验证设置数据
        valid_keys = ["email_alerts", "trading_alerts", "market_updates", "weekly_reports"]
        filtered_settings = {k: v for k, v in settings_data.items() if k in valid_keys and isinstance(v, bool)}
        
        if not filtered_settings:
            raise HTTPException(status_code=400, detail="无效的通知设置")
        
        # 保存设置
        settings_json = json.dumps(filtered_settings)
        crud.update_user_notification_settings(db, user_id=current_user.id, settings_json=settings_json)
        
        return filtered_settings
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新通知设置失败: {str(e)}")

@router.get("/api_keys")
async def get_api_keys(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取API密钥列表"""
    # 从数据库获取用户的API密钥
    api_keys = crud.get_user_api_keys(db, user_id=current_user.id)
    
    result = []
    for key_record in api_keys:
        result.append({
            "provider": key_record.provider,
            "key": key_record.key_preview,  # 只显示前几位和后几位
            "status": key_record.status,
            "last_used": key_record.last_used.strftime("%Y-%m-%d %H:%M:%S") if key_record.last_used else "从未使用"
        })
    
    return result

@router.post("/api_keys")
async def add_api_key(
    key_data: Dict[str, str],
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """添加API密钥"""
    try:
        provider = key_data.get("provider", "").strip()
        key = key_data.get("key", "").strip()
        
        if not provider or not key:
            raise HTTPException(status_code=400, detail="提供商和密钥不能为空")
        
        # 验证提供商
        valid_providers = ["openai", "alpaca", "binance", "coinbase", "polygon"]
        if provider.lower() not in valid_providers:
            raise HTTPException(status_code=400, detail="不支持的API提供商")
        
        # 检查是否已存在该提供商的密钥
        existing_key = crud.get_user_api_key_by_provider(db, user_id=current_user.id, provider=provider)
        if existing_key:
            raise HTTPException(status_code=400, detail="该提供商的API密钥已存在")
        
        # 创建API密钥记录
        api_key_create = schemas.ApiKeyCreate(
            provider=provider.lower(),
            key=key,  # 在实际应用中应该加密存储
            status="active"
        )
        
        api_key = crud.create_user_api_key(db, api_key=api_key_create, user_id=current_user.id)
        
        return {
            "provider": api_key.provider,
            "key": api_key.key_preview,
            "status": api_key.status,
            "last_used": "从未使用"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加API密钥失败: {str(e)}")

@router.delete("/api_keys/{provider}")
async def delete_api_key(
    provider: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除API密钥"""
    try:
        # 查找API密钥
        api_key = crud.get_user_api_key_by_provider(db, user_id=current_user.id, provider=provider.lower())
        
        if not api_key:
            raise HTTPException(status_code=404, detail="API密钥不存在")
        
        # 删除API密钥
        crud.delete_user_api_key(db, api_key_id=api_key.id, user_id=current_user.id)
        
        return {"message": "API密钥删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除API密钥失败: {str(e)}")