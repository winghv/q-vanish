from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

# 获取策略列表
@router.get("/", response_model=List[schemas.Strategy])
async def read_strategies(
    skip: int = 0, 
    limit: int = 100, 
    include_public: bool = True,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    strategies = crud.get_strategies(
        db, 
        user_id=current_user.id, 
        skip=skip, 
        limit=limit, 
        include_public=include_public
    )
    return strategies

# 创建新策略
@router.post("/", response_model=schemas.Strategy, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy: schemas.StrategyCreate, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return crud.create_strategy(db=db, strategy=strategy, user_id=current_user.id)

# 获取指定策略
@router.get("/{strategy_id}", response_model=schemas.Strategy)
async def read_strategy(
    strategy_id: int, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 检查访问权限：用户只能访问自己的策略或公开策略
    if db_strategy.owner_id != current_user.id and not db_strategy.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限访问此策略"
        )
    
    return db_strategy

# 更新策略
@router.put("/{strategy_id}", response_model=schemas.Strategy)
async def update_strategy(
    strategy_id: int, 
    strategy: schemas.StrategyUpdate, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 首先检查策略是否存在
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 检查用户是否有权修改此策略
    if db_strategy.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限修改此策略"
        )
    
    return crud.update_strategy(db, strategy_id=strategy_id, strategy=strategy, user_id=current_user.id)

# 删除策略
@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 首先检查策略是否存在
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 检查用户是否有权删除此策略
    if db_strategy.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限删除此策略"
        )
    
    if not crud.delete_strategy(db, strategy_id=strategy_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="策略不存在")
    
    return None

# 获取我的策略列表
@router.get("/me/", response_model=List[schemas.Strategy])
async def read_my_strategies(
    skip: int = 0, 
    limit: int = 100, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return crud.get_strategies(db, user_id=current_user.id, skip=skip, limit=limit, include_public=False)

# 获取公开策略列表
@router.get("/public/", response_model=List[schemas.Strategy])
async def read_public_strategies(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    return crud.get_strategies(db, user_id=None, skip=skip, limit=limit, include_public=True) 