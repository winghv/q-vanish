from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import json
import traceback

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

# 获取回测列表
@router.get("/", response_model=List[schemas.Backtest])
async def read_backtests(
    skip: int = 0, 
    limit: int = 100,
    strategy_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return crud.get_backtests(
        db, 
        user_id=current_user.id, 
        strategy_id=strategy_id,
        skip=skip, 
        limit=limit
    )

# 创建新回测
@router.post("/", response_model=schemas.Backtest, status_code=status.HTTP_201_CREATED)
async def create_backtest(
    backtest: schemas.BacktestCreate,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 检查策略是否存在
    strategy = crud.get_strategy(db, strategy_id=backtest.strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 检查用户是否有权访问此策略
    if strategy.owner_id != current_user.id and not strategy.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限使用此策略"
        )
    
    # 创建回测记录
    db_backtest = crud.create_backtest(db=db, backtest=backtest, user_id=current_user.id)
    
    # 在后台运行回测
    background_tasks.add_task(
        run_backtest_task,
        db=db,
        backtest_id=db_backtest.id,
        strategy=strategy,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        initial_capital=backtest.initial_capital
    )
    
    return db_backtest

# 获取指定回测
@router.get("/{backtest_id}", response_model=schemas.Backtest)
async def read_backtest(
    backtest_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_backtest = crud.get_backtest(db, backtest_id=backtest_id)
    if db_backtest is None:
        raise HTTPException(status_code=404, detail="回测不存在")
    
    # 检查用户是否有权访问此回测
    if db_backtest.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限访问此回测"
        )
    
    return db_backtest

# 删除回测
@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(
    backtest_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 检查回测是否存在
    db_backtest = crud.get_backtest(db, backtest_id=backtest_id)
    if db_backtest is None:
        raise HTTPException(status_code=404, detail="回测不存在")
    
    # 检查用户是否有权删除此回测
    if db_backtest.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限删除此回测"
        )
    
    crud.delete_backtest(db, backtest_id=backtest_id, user_id=current_user.id)
    return None

# 后台任务：运行回测
def run_backtest_task(
    db: Session,
    backtest_id: int,
    strategy: models.Strategy,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float
):
    try:
        # 更新回测状态为运行中
        crud.update_backtest(
            db,
            backtest_id=backtest_id,
            backtest_update=schemas.BacktestUpdate(status="running"),
            user_id=strategy.owner_id
        )
        
        # 从策略代码中提取交易符号
        # 这里假设策略参数中包含symbol字段
        symbols = []
        if strategy.parameters and "symbols" in strategy.parameters:
            symbols = strategy.parameters["symbols"]
        elif strategy.parameters and "symbol" in strategy.parameters:
            symbols = [strategy.parameters["symbol"]]
        else:
            # 默认使用一些常见股票
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        # 获取市场数据
        market_data = {}
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            if not data.empty:
                market_data[symbol] = data
        
        if not market_data:
            raise ValueError("无法获取市场数据")
        
        # 准备回测环境
        # 在实际应用中，这里应该有更复杂的回测逻辑
        # 这里我们使用一个简化版的回测框架
        
        # 解析并执行策略代码
        # 注意：在生产环境中，应该使用更安全的方法来执行用户代码
        strategy_code = strategy.code
        strategy_parameters = strategy.parameters or {}
        
        # 创建简单的回测引擎
        results = simple_backtest_engine(
            market_data=market_data,
            strategy_code=strategy_code,
            parameters=strategy_parameters,
            initial_capital=initial_capital,
            start_date=start_date,
            end_date=end_date
        )
        
        # 更新回测结果
        final_capital = results.get("final_capital", initial_capital)
        profit_loss = final_capital - initial_capital
        
        backtest_update = schemas.BacktestUpdate(
            status="completed",
            final_capital=final_capital,
            profit_loss=profit_loss,
            sharpe_ratio=results.get("sharpe_ratio", 0),
            max_drawdown=results.get("max_drawdown", 0),
            win_rate=results.get("win_rate", 0),
            results=results
        )
        
        crud.update_backtest(
            db,
            backtest_id=backtest_id,
            backtest_update=backtest_update,
            user_id=strategy.owner_id
        )
    
    except Exception as e:
        # 记录错误并更新回测状态
        error_message = str(e)
        traceback_str = traceback.format_exc()
        
        backtest_update = schemas.BacktestUpdate(
            status="failed",
            results={"error": error_message, "traceback": traceback_str}
        )
        
        crud.update_backtest(
            db,
            backtest_id=backtest_id,
            backtest_update=backtest_update,
            user_id=strategy.owner_id
        )

# 简单回测引擎（模拟实现）
def simple_backtest_engine(
    market_data: Dict[str, pd.DataFrame],
    strategy_code: str,
    parameters: Dict[str, Any],
    initial_capital: float,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """
    一个非常简化的回测引擎实现，仅用于演示。
    实际应用中应该使用更完善的回测框架。
    """
    # 创建回测环境
    portfolio = {
        "cash": initial_capital,
        "positions": {},
        "trades": [],
        "equity_curve": []
    }
    
    # 创建交易函数
    def buy(symbol, shares, price):
        cost = shares * price
        if portfolio["cash"] >= cost:
            portfolio["cash"] -= cost
            if symbol in portfolio["positions"]:
                portfolio["positions"][symbol] += shares
            else:
                portfolio["positions"][symbol] = shares
            
            portfolio["trades"].append({
                "type": "buy",
                "symbol": symbol,
                "shares": shares,
                "price": price,
                "timestamp": current_date.strftime("%Y-%m-%d")
            })
            return True
        return False
    
    def sell(symbol, shares, price):
        if symbol in portfolio["positions"] and portfolio["positions"][symbol] >= shares:
            portfolio["positions"][symbol] -= shares
            portfolio["cash"] += shares * price
            
            if portfolio["positions"][symbol] == 0:
                del portfolio["positions"][symbol]
            
            portfolio["trades"].append({
                "type": "sell",
                "symbol": symbol,
                "shares": shares,
                "price": price,
                "timestamp": current_date.strftime("%Y-%m-%d")
            })
            return True
        return False
    
    # 准备执行环境
    # 注意：在生产环境中应该使用更安全的方法
    strategy_globals = {
        "market_data": market_data,
        "parameters": parameters,
        "buy": buy,
        "sell": sell,
        "np": np,
        "pd": pd
    }
    
    # 编译策略代码
    try:
        strategy_compiled = compile(strategy_code, "<string>", "exec")
    except Exception as e:
        return {
            "error": f"策略代码编译错误: {str(e)}",
            "final_capital": initial_capital,
            "trades": []
        }
    
    # 执行策略
    try:
        # 设置回测开始日期
        all_dates = set()
        for symbol, data in market_data.items():
            all_dates.update(data.index.date)
        
        all_dates = sorted(all_dates)
        
        # 主回测循环
        for date in all_dates:
            current_date = datetime.combine(date, datetime.min.time())
            if current_date < start_date or current_date > end_date:
                continue
            
            # 更新当前日期
            strategy_globals["current_date"] = current_date
            
            # 准备当日数据
            for symbol, data in market_data.items():
                if date in data.index.date:
                    current_data = data.loc[data.index.date == date]
                    strategy_globals[f"{symbol}_data"] = current_data
                    strategy_globals[f"{symbol}_price"] = current_data["Close"].iloc[-1]
            
            # 执行策略
            exec(strategy_compiled, strategy_globals)
            
            # 计算当前持仓价值
            portfolio_value = portfolio["cash"]
            for symbol, shares in portfolio["positions"].items():
                if symbol in market_data and date in market_data[symbol].index.date:
                    price = market_data[symbol].loc[market_data[symbol].index.date == date, "Close"].iloc[-1]
                    portfolio_value += shares * price
            
            # 记录权益曲线
            portfolio["equity_curve"].append({
                "date": current_date.strftime("%Y-%m-%d"),
                "value": portfolio_value
            })
    
    except Exception as e:
        return {
            "error": f"策略执行错误: {str(e)}",
            "final_capital": initial_capital,
            "trades": portfolio["trades"]
        }
    
    # 计算回测指标
    final_capital = portfolio["cash"]
    for symbol, shares in portfolio["positions"].items():
        if symbol in market_data:
            final_price = market_data[symbol]["Close"].iloc[-1]
            final_capital += shares * final_price
    
    # 计算收益率
    returns = []
    if len(portfolio["equity_curve"]) > 1:
        for i in range(1, len(portfolio["equity_curve"])):
            prev_value = portfolio["equity_curve"][i-1]["value"]
            curr_value = portfolio["equity_curve"][i]["value"]
            returns.append((curr_value - prev_value) / prev_value)
    
    # 计算Sharpe比率（假设无风险利率为0）
    sharpe_ratio = 0
    if returns:
        daily_returns = np.array(returns)
        if np.std(daily_returns) > 0:
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)  # 年化
    
    # 计算最大回撤
    max_drawdown = 0
    if portfolio["equity_curve"]:
        equity_values = [point["value"] for point in portfolio["equity_curve"]]
        peak = equity_values[0]
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    # 计算胜率
    win_trades = 0
    total_trades = len(portfolio["trades"])
    if total_trades > 0:
        buy_trades = {}
        for trade in portfolio["trades"]:
            if trade["type"] == "buy":
                key = f"{trade['symbol']}_{trade['timestamp']}"
                buy_trades[key] = trade
            elif trade["type"] == "sell":
                key = f"{trade['symbol']}_{trade['timestamp']}"
                if key in buy_trades:
                    buy_trade = buy_trades[key]
                    if trade["price"] > buy_trade["price"]:
                        win_trades += 1
        
        win_rate = win_trades / total_trades if total_trades > 0 else 0
    else:
        win_rate = 0
    
    # 返回回测结果
    return {
        "final_capital": final_capital,
        "profit_loss": final_capital - initial_capital,
        "profit_loss_pct": (final_capital - initial_capital) / initial_capital * 100,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "total_trades": total_trades,
        "trades": portfolio["trades"],
        "equity_curve": portfolio["equity_curve"],
        "final_positions": [
            {"symbol": symbol, "shares": shares}
            for symbol, shares in portfolio["positions"].items()
        ]
    } 