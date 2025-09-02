"""
安全工具模块
包含认证、授权和安全相关的工具函数
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
import ipaddress
import re

from .. import models, config


def is_account_locked(user: models.User) -> bool:
    """检查账户是否被锁定"""
    if user.locked_until is None:
        return False
    
    return datetime.utcnow() < user.locked_until


def should_lock_account(user: models.User) -> bool:
    """判断是否应该锁定账户"""
    return user.failed_login_attempts >= config.MAX_LOGIN_ATTEMPTS


def lock_user_account(db: Session, user: models.User):
    """锁定用户账户"""
    user.locked_until = datetime.utcnow() + timedelta(seconds=config.LOGIN_ATTEMPT_TIMEOUT)
    user.failed_login_attempts = 0  # 重置失败次数
    db.commit()


def increment_failed_login(db: Session, user: models.User):
    """增加失败登录次数"""
    user.failed_login_attempts += 1
    db.commit()
    
    if should_lock_account(user):
        lock_user_account(db, user)


def reset_failed_login(db: Session, user: models.User):
    """重置失败登录次数"""
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


def update_login_info(db: Session, user: models.User, request: Request):
    """更新用户登录信息"""
    user.last_login = datetime.utcnow()
    user.last_login_ip = get_client_ip(request)
    db.commit()


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    # 检查代理头
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 取第一个IP（最原始的客户端IP）
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # fallback到直接连接IP
    return request.client.host


def validate_password_strength(password: str) -> bool:
    """验证密码强度"""
    if len(password) < 8:
        return False
    
    # 至少包含一个小写字母
    if not re.search(r'[a-z]', password):
        return False
    
    # 至少包含一个大写字母
    if not re.search(r'[A-Z]', password):
        return False
    
    # 至少包含一个数字
    if not re.search(r'\d', password):
        return False
    
    # 至少包含一个特殊字符
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True


def validate_email_format(email: str) -> bool:
    """验证邮箱格式"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def is_suspicious_ip(ip: str) -> bool:
    """检查是否为可疑IP（简单示例）"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        # 检查是否为私有IP
        if ip_obj.is_private:
            return False
            
        # 这里可以添加更多的IP黑名单检查
        # 例如：检查已知的恶意IP数据库
        
        return False
    except ValueError:
        # 无效IP格式
        return True


class SecurityException(HTTPException):
    """安全相关异常"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )