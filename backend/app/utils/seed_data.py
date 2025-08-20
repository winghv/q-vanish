#!/usr/bin/env python3
"""
数据库种子数据生成脚本
用于初始化数据库并生成测试数据
"""

import sys
import os
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Base
from app import crud, models
from app.schemas import (
    UserCreate, PortfolioCreate, AssetCreate, StrategyCreate, 
    TradeCreate, OrderType
)

def create_database_tables():
    """创建数据库表"""
    print("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")

def create_test_users(db: Session):
    """创建测试用户"""
    print("创建测试用户...")
    
    users_data = [
        {"username": "demo_user", "email": "demo@qvanish.com", "password": "demo123"},
        {"username": "trader1", "email": "trader1@qvanish.com", "password": "trader123"},
        {"username": "investor", "email": "investor@qvanish.com", "password": "invest123"}
    ]
    
    created_users = []
    for user_data in users_data:
        user_create = UserCreate(**user_data)
        try:
            user = crud.create_user(db, user_create)
            created_users.append(user)
            print(f"  ✅ 创建用户: {user.username}")
        except Exception as e:
            print(f"  ⚠️ 用户 {user_data['username']} 可能已存在: {e}")
            # 尝试获取现有用户
            existing_user = crud.get_user_by_username(db, user_data['username'])
            if existing_user:
                created_users.append(existing_user)
    
    return created_users

def create_test_portfolios(db: Session, users):
    """创建测试投资组合"""
    print("创建测试投资组合...")
    
    portfolios = []
    for user in users:
        portfolio_data = {
            "name": f"{user.username}的投资组合",
            "description": f"用户{user.username}的默认投资组合",
            "cash_balance": random.uniform(50000, 200000)
        }
        
        portfolio_create = PortfolioCreate(**portfolio_data)
        portfolio = crud.create_portfolio(db, portfolio_create, user.id)
        portfolios.append(portfolio)
        print(f"  ✅ 创建投资组合: {portfolio.name}")
    
    return portfolios

def create_test_assets(db: Session, portfolios):
    """创建测试资产"""
    print("创建测试资产...")
    
    # 模拟股票数据
    stocks = [
        {"symbol": "AAPL", "price_range": (170, 180)},
        {"symbol": "GOOGL", "price_range": (130, 145)},
        {"symbol": "MSFT", "price_range": (370, 385)},
        {"symbol": "TSLA", "price_range": (240, 260)},
        {"symbol": "AMZN", "price_range": (140, 155)},
        {"symbol": "META", "price_range": (320, 340)},
        {"symbol": "NVDA", "price_range": (450, 480)},
        {"symbol": "NFLX", "price_range": (420, 450)},
    ]
    
    assets = []
    for portfolio in portfolios:
        # 为每个投资组合随机分配3-6只股票
        selected_stocks = random.sample(stocks, random.randint(3, 6))
        
        for stock in selected_stocks:
            quantity = random.randint(10, 100)
            avg_price = random.uniform(*stock["price_range"])
            current_price = avg_price * (1 + random.uniform(-0.1, 0.1))  # ±10%波动
            
            asset_data = {
                "symbol": stock["symbol"],
                "quantity": quantity,
                "average_price": avg_price,
                "current_price": current_price,
                "market_value": quantity * current_price,
                "portfolio_id": portfolio.id
            }
            
            asset_create = AssetCreate(**asset_data)
            asset = crud.create_asset(db, asset_create)
            assets.append(asset)
            print(f"  ✅ 创建资产: {asset.symbol} x{asset.quantity} @ ${avg_price:.2f}")
    
    return assets

def create_test_strategies(db: Session, users):
    """创建测试策略"""
    print("创建测试策略...")
    
    strategies_data = [
        {
            "name": "均线交叉策略",
            "description": "基于移动平均线交叉的趋势跟踪策略",
            "type": "trend_following",
            "is_active": True,
            "is_public": False
        },
        {
            "name": "RSI反转策略", 
            "description": "基于RSI指标的反转交易策略",
            "type": "mean_reversion",
            "is_active": True,
            "is_public": False
        },
        {
            "name": "布林带突破策略",
            "description": "基于布林带突破的交易策略",
            "type": "breakout",
            "is_active": False,
            "is_public": True
        },
        {
            "name": "动量策略",
            "description": "基于价格动量的交易策略",
            "type": "momentum",
            "is_active": True,
            "is_public": False
        }
    ]
    
    strategies = []
    for user in users[:2]:  # 只为前两个用户创建策略
        for strategy_data in strategies_data[:2]:  # 每个用户创建2个策略
            strategy_create = StrategyCreate(**strategy_data)
            strategy = crud.create_strategy(db, strategy_create, user.id)
            strategies.append(strategy)
            print(f"  ✅ 创建策略: {strategy.name} (用户: {user.username})")
    
    return strategies

def create_test_trades(db: Session, users, portfolios, strategies):
    """创建测试交易记录"""
    print("创建测试交易记录...")
    
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "META"]
    
    trades = []
    for i in range(30):  # 创建30笔交易
        user = random.choice(users)
        portfolio = next((p for p in portfolios if p.user_id == user.id), None)
        strategy = random.choice(strategies) if random.random() > 0.3 else None  # 70%概率有策略
        
        trade_data = {
            "symbol": random.choice(symbols),
            "order_type": random.choice([OrderType.BUY, OrderType.SELL]),
            "quantity": random.randint(10, 100),
            "price": random.uniform(100, 500),
            "strategy_id": strategy.id if strategy else None,
            "portfolio_id": portfolio.id if portfolio else None
        }
        
        trade_create = TradeCreate(**trade_data)
        trade = crud.create_trade(db, trade_create, user.id)
        
        # 随机设置一些交易为已执行状态
        if random.random() > 0.3:
            trade.status = "executed"
            trade.executed_at = datetime.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            # 设置盈亏
            trade.profit_loss = random.uniform(-1000, 2000)
            db.commit()
        
        trades.append(trade)
        
    print(f"  ✅ 创建了 {len(trades)} 笔交易记录")
    return trades

def update_portfolio_values(db: Session, portfolios):
    """更新投资组合总价值"""
    print("更新投资组合总价值...")
    
    for portfolio in portfolios:
        # 计算总价值 = 现金 + 所有资产市值
        assets = db.query(models.PortfolioAsset).filter(
            models.PortfolioAsset.portfolio_id == portfolio.id
        ).all()
        
        total_assets_value = sum(asset.market_value for asset in assets)
        portfolio.total_value = portfolio.cash_balance + total_assets_value
        
        db.commit()
        print(f"  ✅ 更新投资组合 {portfolio.name}: ${portfolio.total_value:.2f}")

def main():
    """主函数"""
    print("🚀 开始初始化数据库和生成测试数据...\n")
    
    # 创建数据库表
    create_database_tables()
    
    # 获取数据库会话
    db = SessionLocal()
    
    try:
        # 创建测试数据
        users = create_test_users(db)
        portfolios = create_test_portfolios(db, users)
        assets = create_test_assets(db, portfolios)
        strategies = create_test_strategies(db, users)
        trades = create_test_trades(db, users, portfolios, strategies)
        
        # 更新投资组合价值
        update_portfolio_values(db, portfolios)
        
        print("\n✅ 数据库初始化完成!")
        print("\n📊 生成的测试数据:")
        print(f"  - 用户: {len(users)}")
        print(f"  - 投资组合: {len(portfolios)}")
        print(f"  - 资产持仓: {len(assets)}")
        print(f"  - 策略: {len(strategies)}")
        print(f"  - 交易记录: {len(trades)}")
        
        print("\n🔑 测试用户登录信息:")
        print("  用户名: demo_user, 密码: demo123")
        print("  用户名: trader1, 密码: trader123")
        print("  用户名: investor, 密码: invest123")
        
    except Exception as e:
        print(f"❌ 生成测试数据时出错: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()