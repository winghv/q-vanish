from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

# 获取用户列表
@router.get("/", response_model=List[schemas.User])
async def read_users(
    skip: int = 0, 
    limit: int = 100, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 只有管理员可以查看所有用户
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限执行此操作"
        )
    
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

# 获取指定用户
@router.get("/{user_id}", response_model=schemas.User)
async def read_user(
    user_id: int, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 用户只能查看自己的信息，管理员可以查看所有用户
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限执行此操作"
        )
    
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return db_user

# 更新用户
@router.put("/{user_id}", response_model=schemas.User)
async def update_user(
    user_id: int, 
    user: schemas.UserUpdate, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 用户只能更新自己的信息，管理员可以更新所有用户
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限执行此操作"
        )
    
    # 如果要更新角色，确保只有管理员才能执行
    if hasattr(user, "role") and user.role and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限更改用户角色"
        )
    
    db_user = crud.update_user(db, user_id=user_id, user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return db_user

# 删除用户
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 只有管理员可以删除用户
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限执行此操作"
        )
    
    if not crud.delete_user(db, user_id=user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return None 