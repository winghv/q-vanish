from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_
from typing import List, Optional, Dict, Any, Union, TypeVar, Generic, Type
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

from . import models, schemas

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
SECRET_KEY = "YOUR_SECRET_KEY_HERE"  # 在生产环境中应该使用安全的密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 用户相关CRUD操作
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        update_data = user.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = pwd_context.hash(update_data["password"])
            del update_data["password"]
        
        for key, value in update_data.items():
            setattr(db_user, key, value)
        
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 策略相关CRUD操作
def get_strategy(db: Session, strategy_id: int):
    return db.query(models.Strategy).filter(models.Strategy.id == strategy_id).first()

def get_strategies(
    db: Session, 
    user_id: Optional[int] = None, 
    skip: int = 0, 
    limit: int = 100, 
    include_public: bool = False
):
    query = db.query(models.Strategy)
    if user_id is not None:
        if include_public:
            query = query.filter(
                (models.Strategy.owner_id == user_id) | (models.Strategy.is_public == True)
            )
        else:
            query = query.filter(models.Strategy.owner_id == user_id)
    elif not include_public:
        return []
    else:
        query = query.filter(models.Strategy.is_public == True)
    
    return query.offset(skip).limit(limit).all()

def create_strategy(db: Session, strategy: schemas.StrategyCreate, user_id: int):
    db_strategy = models.Strategy(**strategy.model_dump(), owner_id=user_id)
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

def update_strategy(db: Session, strategy_id: int, strategy: schemas.StrategyUpdate, user_id: int):
    db_strategy = db.query(models.Strategy).filter(
        models.Strategy.id == strategy_id,
        models.Strategy.owner_id == user_id
    ).first()
    
    if db_strategy:
        update_data = strategy.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_strategy, key, value)
        
        db.commit()
        db.refresh(db_strategy)
    
    return db_strategy

def delete_strategy(db: Session, strategy_id: int, user_id: int):
    db_strategy = db.query(models.Strategy).filter(
        models.Strategy.id == strategy_id,
        models.Strategy.owner_id == user_id
    ).first()
    
    if db_strategy:
        db.delete(db_strategy)
        db.commit()
        return True
    
    return False

# 回测相关CRUD操作
def get_backtest(db: Session, backtest_id: int):
    return db.query(models.Backtest).filter(models.Backtest.id == backtest_id).first()

def get_backtests(
    db: Session, 
    user_id: int, 
    strategy_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100
):
    query = db.query(models.Backtest).filter(models.Backtest.user_id == user_id)
    if strategy_id:
        query = query.filter(models.Backtest.strategy_id == strategy_id)
    
    return query.order_by(desc(models.Backtest.created_at)).offset(skip).limit(limit).all()

def create_backtest(db: Session, backtest: schemas.BacktestCreate, user_id: int):
    db_backtest = models.Backtest(
        **backtest.model_dump(),
        user_id=user_id,
        status="pending"
    )
    db.add(db_backtest)
    db.commit()
    db.refresh(db_backtest)
    return db_backtest

def update_backtest(db: Session, backtest_id: int, backtest_update: schemas.BacktestUpdate, user_id: int):
    db_backtest = db.query(models.Backtest).filter(
        models.Backtest.id == backtest_id,
        models.Backtest.user_id == user_id
    ).first()
    
    if db_backtest:
        update_data = backtest_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_backtest, key, value)
        
        db.commit()
        db.refresh(db_backtest)
    
    return db_backtest

def delete_backtest(db: Session, backtest_id: int, user_id: int):
    db_backtest = db.query(models.Backtest).filter(
        models.Backtest.id == backtest_id,
        models.Backtest.user_id == user_id
    ).first()
    
    if db_backtest:
        db.delete(db_backtest)
        db.commit()
        return True
    
    return False

# 交易相关CRUD操作
def get_trade(db: Session, trade_id: int):
    return db.query(models.Trade).filter(models.Trade.id == trade_id).first()

def get_trades(
    db: Session, 
    user_id: int, 
    strategy_id: Optional[int] = None,
    portfolio_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100
):
    query = db.query(models.Trade).filter(models.Trade.user_id == user_id)
    
    if strategy_id:
        query = query.filter(models.Trade.strategy_id == strategy_id)
    
    if portfolio_id:
        query = query.filter(models.Trade.portfolio_id == portfolio_id)
    
    return query.order_by(desc(models.Trade.created_at)).offset(skip).limit(limit).all()

def create_trade(db: Session, trade: schemas.TradeCreate, user_id: int):
    db_trade = models.Trade(
        **trade.model_dump(),
        user_id=user_id,
        status="pending"
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def update_trade(db: Session, trade_id: int, trade_update: schemas.TradeUpdate, user_id: int):
    db_trade = db.query(models.Trade).filter(
        models.Trade.id == trade_id,
        models.Trade.user_id == user_id
    ).first()
    
    if db_trade:
        update_data = trade_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_trade, key, value)
        
        db.commit()
        db.refresh(db_trade)
    
    return db_trade

def delete_trade(db: Session, trade_id: int, user_id: int):
    db_trade = db.query(models.Trade).filter(
        models.Trade.id == trade_id,
        models.Trade.user_id == user_id
    ).first()
    
    if db_trade:
        db.delete(db_trade)
        db.commit()
        return True
    
    return False

# 资产组合相关CRUD操作
def get_portfolio(db: Session, portfolio_id: int):
    return db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()

def get_portfolios(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Portfolio).filter(
        models.Portfolio.user_id == user_id
    ).offset(skip).limit(limit).all()

def create_portfolio(db: Session, portfolio: schemas.PortfolioCreate, user_id: int):
    db_portfolio = models.Portfolio(
        **portfolio.model_dump(),
        total_value=portfolio.cash_balance,
        user_id=user_id
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def update_portfolio(db: Session, portfolio_id: int, portfolio_update: schemas.PortfolioUpdate, user_id: int):
    db_portfolio = db.query(models.Portfolio).filter(
        models.Portfolio.id == portfolio_id,
        models.Portfolio.user_id == user_id
    ).first()
    
    if db_portfolio:
        update_data = portfolio_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_portfolio, key, value)
        
        db.commit()
        db.refresh(db_portfolio)
    
    return db_portfolio

def delete_portfolio(db: Session, portfolio_id: int, user_id: int):
    db_portfolio = db.query(models.Portfolio).filter(
        models.Portfolio.id == portfolio_id,
        models.Portfolio.user_id == user_id
    ).first()
    
    if db_portfolio:
        db.delete(db_portfolio)
        db.commit()
        return True
    
    return False

# 资产相关CRUD操作
def get_asset(db: Session, asset_id: int):
    return db.query(models.PortfolioAsset).filter(models.PortfolioAsset.id == asset_id).first()

def get_assets_by_portfolio(db: Session, portfolio_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.PortfolioAsset).filter(
        models.PortfolioAsset.portfolio_id == portfolio_id
    ).offset(skip).limit(limit).all()

def create_asset(db: Session, asset: schemas.AssetCreate):
    market_value = asset.quantity * asset.average_price
    db_asset = models.PortfolioAsset(
        **asset.model_dump(),
        current_price=asset.average_price,
        market_value=market_value,
        profit_loss=0.0,
        profit_loss_percentage=0.0
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

def update_asset(db: Session, asset_id: int, asset_update: schemas.AssetUpdate):
    db_asset = db.query(models.PortfolioAsset).filter(models.PortfolioAsset.id == asset_id).first()
    
    if db_asset:
        update_data = asset_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_asset, key, value)
        
        # 如果价格或数量更新了，更新市值
        if "current_price" in update_data or "quantity" in update_data:
            db_asset.market_value = db_asset.current_price * db_asset.quantity
            
        # 如果当前价格或平均价格更新了，更新利润
        if "current_price" in update_data or "average_price" in update_data:
            db_asset.profit_loss = (db_asset.current_price - db_asset.average_price) * db_asset.quantity
            if db_asset.average_price > 0:
                db_asset.profit_loss_percentage = (db_asset.current_price - db_asset.average_price) / db_asset.average_price * 100
            else:
                db_asset.profit_loss_percentage = 0
        
        db.commit()
        db.refresh(db_asset)
    
    return db_asset

def delete_asset(db: Session, asset_id: int):
    db_asset = db.query(models.PortfolioAsset).filter(models.PortfolioAsset.id == asset_id).first()
    
    if db_asset:
        db.delete(db_asset)
        db.commit()
        return True
    
    return False

# AI助手相关CRUD操作
def create_ai_chat(db: Session, user_id: int, message: str, response: str, context: Optional[Dict[str, Any]] = None):
    db_chat = models.AIAssistantChat(
        user_id=user_id,
        message=message,
        response=response,
        context=context
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

def get_ai_chats_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.AIAssistantChat).filter(
        models.AIAssistantChat.user_id == user_id
    ).order_by(desc(models.AIAssistantChat.created_at)).offset(skip).limit(limit).all()

# 市场数据相关CRUD操作
def create_market_data(db: Session, market_data: schemas.MarketDataCreate):
    # 检查是否已存在相同的数据
    existing = db.query(models.MarketData).filter(
        models.MarketData.symbol == market_data.symbol,
        models.MarketData.date == market_data.date
    ).first()
    
    if existing:
        # 更新现有记录
        update_data = market_data.model_dump()
        for key, value in update_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 创建新记录
        db_market_data = models.MarketData(**market_data.model_dump())
        db.add(db_market_data)
        db.commit()
        db.refresh(db_market_data)
        return db_market_data

def get_market_data(db: Session, filter_params: schemas.MarketDataFilter):
    query = db.query(models.MarketData).filter(models.MarketData.symbol == filter_params.symbol)
    
    if filter_params.start_date:
        query = query.filter(models.MarketData.date >= filter_params.start_date)
    
    if filter_params.end_date:
        query = query.filter(models.MarketData.date <= filter_params.end_date)
    
    return query.order_by(asc(models.MarketData.date)).limit(filter_params.limit).all()

def bulk_create_market_data(db: Session, market_data_list: List[schemas.MarketDataCreate]):
    result = []
    for data in market_data_list:
        result.append(create_market_data(db, data))
    return result 