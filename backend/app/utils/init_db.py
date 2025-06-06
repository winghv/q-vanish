"""
数据库初始化工具
"""
import sys
import os
import logging
from datetime import datetime, timedelta

# 添加父目录到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import models, crud, schemas
from app.database import SessionLocal, engine
from app.utils.sample_strategies import get_all_sample_strategies

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """初始化数据库，创建必要的表和初始数据"""
    # 创建数据库表
    models.Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 检查数据库中是否已存在用户
        existing_users = db.query(models.User).count()
        if existing_users == 0:
            # 创建管理员用户
            admin_user = schemas.UserCreate(
                username="admin",
                email="admin@example.com",
                password="admin123"
            )
            db_admin = crud.create_user(db, admin_user)
            db_admin.role = "admin"
            db.commit()
            logger.info(f"创建管理员用户: {admin_user.username}")
            
            # 创建普通用户
            user = schemas.UserCreate(
                username="user",
                email="user@example.com",
                password="user123"
            )
            db_user = crud.create_user(db, user)
            logger.info(f"创建普通用户: {user.username}")
            
            # 导入示例策略
            sample_strategies = get_all_sample_strategies()
            for key, strategy_data in sample_strategies.items():
                strategy = schemas.StrategyCreate(
                    name=strategy_data["name"],
                    description=strategy_data["description"],
                    type=strategy_data["type"],
                    parameters=strategy_data["parameters"],
                    code=strategy_data["code"],
                    is_active=True,
                    is_public=True
                )
                
                # 为两个用户创建策略
                crud.create_strategy(db, strategy, db_admin.id)
                logger.info(f"为管理员创建示例策略: {strategy.name}")
                
                # 修改一下参数，为普通用户也创建
                if "symbol" in strategy.parameters:
                    strategy.parameters["symbol"] = "TSLA"  # 改变一下股票代码
                elif "symbols" in strategy.parameters:
                    strategy.parameters["symbols"] = ["TSLA", "AMZN", "FB", "NFLX"]
                
                crud.create_strategy(db, strategy, db_user.id)
                logger.info(f"为普通用户创建示例策略: {strategy.name}")
            
            # 创建示例投资组合
            portfolio = schemas.PortfolioCreate(
                name="主要投资组合",
                description="包含多种资产类型的平衡投资组合",
                cash_balance=100000.0
            )
            db_portfolio = crud.create_portfolio(db, portfolio, db_user.id)
            logger.info(f"为用户创建投资组合: {portfolio.name}")
            
            # 创建示例资产
            assets = [
                {"symbol": "AAPL", "quantity": 50, "average_price": 150.0},
                {"symbol": "MSFT", "quantity": 30, "average_price": 280.0},
                {"symbol": "GOOGL", "quantity": 10, "average_price": 2800.0},
                {"symbol": "AMZN", "quantity": 5, "average_price": 3300.0}
            ]
            
            for asset_data in assets:
                asset = schemas.AssetCreate(
                    symbol=asset_data["symbol"],
                    quantity=asset_data["quantity"],
                    average_price=asset_data["average_price"],
                    portfolio_id=db_portfolio.id
                )
                db_asset = crud.create_asset(db, asset)
                logger.info(f"为投资组合添加资产: {asset.symbol}")
            
            # 更新投资组合总价值
            total_value = db_portfolio.cash_balance
            for asset_data in assets:
                total_value += asset_data["quantity"] * asset_data["average_price"]
            
            portfolio_update = schemas.PortfolioUpdate(total_value=total_value)
            crud.update_portfolio(db, db_portfolio.id, portfolio_update, db_user.id)
            
            # 创建示例回测
            backtest = schemas.BacktestCreate(
                name="双均线策略回测",
                description="测试双均线策略在不同市场条件下的表现",
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now(),
                initial_capital=100000.0,
                strategy_id=1  # 假设ID为1的策略是双均线策略
            )
            db_backtest = crud.create_backtest(db, backtest, db_user.id)
            
            # 模拟回测完成
            backtest_update = schemas.BacktestUpdate(
                status="completed",
                final_capital=120000.0,
                profit_loss=20000.0,
                sharpe_ratio=1.2,
                max_drawdown=0.15,
                win_rate=0.65,
                results={
                    "total_trades": 24,
                    "profit_loss_pct": 20.0,
                    "annualized_return": 18.5,
                    "trades": [
                        {"type": "buy", "symbol": "AAPL", "shares": 100, "price": 150.0, "timestamp": "2023-01-15"},
                        {"type": "sell", "symbol": "AAPL", "shares": 100, "price": 170.0, "timestamp": "2023-03-20"}
                    ],
                    "equity_curve": [
                        {"date": "2023-01-01", "value": 100000.0},
                        {"date": "2023-06-01", "value": 110000.0},
                        {"date": "2023-12-01", "value": 120000.0}
                    ]
                }
            )
            crud.update_backtest(db, db_backtest.id, backtest_update, db_user.id)
            logger.info(f"创建示例回测: {backtest.name}")
            
            # 创建示例交易
            trades = [
                {"symbol": "AAPL", "order_type": "buy", "price": 150.0, "quantity": 10},
                {"symbol": "MSFT", "order_type": "buy", "price": 280.0, "quantity": 5},
                {"symbol": "AAPL", "order_type": "sell", "price": 170.0, "quantity": 5}
            ]
            
            for i, trade_data in enumerate(trades):
                trade = schemas.TradeCreate(
                    symbol=trade_data["symbol"],
                    order_type=trade_data["order_type"],
                    price=trade_data["price"],
                    quantity=trade_data["quantity"],
                    portfolio_id=db_portfolio.id
                )
                db_trade = crud.create_trade(db, trade, db_user.id)
                
                # 模拟交易完成
                executed_time = datetime.now() - timedelta(days=30-i)
                trade_update = schemas.TradeUpdate(
                    status="executed",
                    executed_at=executed_time
                )
                
                if trade_data["order_type"] == "sell":
                    # 计算卖出利润
                    buy_price = trades[0]["price"]  # 假设是第一笔交易的买入价
                    profit = (trade_data["price"] - buy_price) * trade_data["quantity"]
                    trade_update.profit_loss = profit
                
                crud.update_trade(db, db_trade.id, trade_update, db_user.id)
                logger.info(f"创建示例交易: {trade.symbol} {trade.order_type}")
        
        else:
            logger.info("数据库已存在用户，跳过初始化数据")
    
    except Exception as e:
        logger.error(f"初始化数据时出错: {str(e)}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("开始初始化数据库...")
    init_db()
    logger.info("数据库初始化完成!") 