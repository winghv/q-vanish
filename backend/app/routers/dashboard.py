from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

@router.get("/performance")
async def get_dashboard_performance(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取仪表盘性能数据"""
    # 获取用户的主要投资组合
    portfolios = crud.get_user_portfolios(db, user_id=current_user.id)
    
    if not portfolios:
        # 如果没有投资组合，返回模拟数据
        return _generate_mock_performance_data()
    
    # 计算投资组合历史表现
    performance_data = []
    base_date = datetime.now() - timedelta(days=90)  # 3个月数据
    
    for i in range(90):
        date = base_date + timedelta(days=i)
        # 这里应该从实际的历史数据计算，现在使用模拟数据
        total_value = sum(p.total_value for p in portfolios) * (1 + random.uniform(-0.02, 0.02))
        performance_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(total_value, 2)
        })
    
    return performance_data

@router.get("/active_strategies")
async def get_active_strategies(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取活跃策略"""
    strategies = crud.get_user_strategies(db, user_id=current_user.id, is_active=True)
    
    active_strategies = []
    for strategy in strategies:
        # 计算策略统计信息
        trades = crud.get_trades_by_strategy(db, strategy_id=strategy.id)
        
        total_profit = sum(trade.profit_loss or 0 for trade in trades if trade.profit_loss)
        profit_str = f"+{total_profit:.2f}" if total_profit >= 0 else f"{total_profit:.2f}"
        
        active_strategies.append({
            "id": strategy.id,
            "name": strategy.name,
            "profit": profit_str,
            "trades": len(trades),
            "status": "running" if strategy.is_active else "paused"
        })
    
    return active_strategies

@router.get("/recent_trades")
async def get_recent_trades(
    limit: int = 10,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取最近交易"""
    trades = crud.get_user_recent_trades(db, user_id=current_user.id, limit=limit)
    
    recent_trades = []
    for trade in trades:
        strategy_name = trade.strategy.name if trade.strategy else "手动交易"
        
        recent_trades.append({
            "id": trade.id,
            "strategy": strategy_name,
            "symbol": trade.symbol,
            "type": trade.order_type,
            "price": trade.price,
            "amount": trade.quantity,
            "time": trade.created_at.strftime("%m-%d %H:%M")
        })
    
    return recent_trades

@router.get("/notifications")
async def get_notifications(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取通知"""
    # 这里应该从通知表获取，暂时返回模拟数据
    notifications = [
        {
            "id": 1,
            "message": "策略 'RSI反转策略' 触发买入信号",
            "time": "2分钟前"
        },
        {
            "id": 2, 
            "message": "AAPL股票价格突破阻力位",
            "time": "15分钟前"
        },
        {
            "id": 3,
            "message": "账户资金变动：+$1,234.56",
            "time": "1小时前"
        },
        {
            "id": 4,
            "message": "策略回测完成：均线交叉策略",
            "time": "2小时前"
        }
    ]
    
    return notifications

def _generate_mock_performance_data() -> List[Dict[str, Any]]:
    """生成模拟性能数据"""
    data = []
    base_value = 100000.0  # 10万美元起始
    base_date = datetime.now() - timedelta(days=90)
    
    current_value = base_value
    for i in range(90):
        # 模拟市场波动
        daily_change = random.uniform(-0.03, 0.03)  # ±3%的日波动
        current_value *= (1 + daily_change)
        
        date = base_date + timedelta(days=i)
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(current_value, 2)
        })
    
    return data