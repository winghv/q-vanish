"""
持仓分析API路由
提供详细的持仓计算、盈亏分析和风险评估功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from .. import models
from ..database import get_db
from .auth import get_current_active_user
from ..services.position_analytics import get_position_analytics, PositionAnalytics

router = APIRouter()


@router.get("/portfolio/analysis")
async def get_portfolio_analysis(
    portfolio_id: Optional[int] = Query(None, description="投资组合ID，不指定则分析所有投资组合"),
    current_user: models.User = Depends(get_current_active_user),
    analytics: PositionAnalytics = Depends(get_position_analytics)
) -> Dict[str, Any]:
    """
    获取投资组合持仓分析
    
    包含：
    - 总体持仓概况
    - 各个持仓的详细信息
    - 盈亏分析
    - 资产配置分析
    """
    try:
        result = await analytics.analyze_portfolio_positions(
            user_id=current_user.id,
            portfolio_id=portfolio_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取持仓分析失败: {str(e)}")


@router.get("/position/{symbol}/performance")
async def get_position_performance(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="分析天数，1-365天"),
    current_user: models.User = Depends(get_current_active_user),
    analytics: PositionAnalytics = Depends(get_position_analytics)
) -> Dict[str, Any]:
    """
    分析特定股票的持仓表现
    
    包含：
    - 持仓概况
    - 盈亏分析
    - 交易历史
    - 成本基础分析
    """
    try:
        result = await analytics.analyze_position_performance(
            user_id=current_user.id,
            symbol=symbol,
            days=days
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取持仓表现分析失败: {str(e)}")


@router.get("/risk/metrics")
async def get_risk_metrics(
    current_user: models.User = Depends(get_current_active_user),
    analytics: PositionAnalytics = Depends(get_position_analytics)
) -> Dict[str, Any]:
    """
    获取投资组合风险指标
    
    包含：
    - 集中度风险
    - 流动性风险
    - 行业集中度
    - 波动率指标
    - 综合风险评估
    """
    try:
        result = await analytics.get_portfolio_risk_metrics(current_user.id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取风险指标失败: {str(e)}")


@router.get("/summary/pnl")
async def get_pnl_summary(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取盈亏汇总
    
    Args:
        days: 统计天数
        
    Returns:
        盈亏汇总数据
    """
    try:
        from datetime import datetime, timedelta
        
        # 计算日期范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 获取已实现盈亏（卖出交易）
        realized_trades = db.query(models.Trade).filter(
            models.Trade.user_id == current_user.id,
            models.Trade.order_type == "sell",
            models.Trade.status == "executed",
            models.Trade.executed_at >= start_date,
            models.Trade.profit_loss.isnot(None)
        ).all()
        
        realized_pnl = sum(trade.profit_loss for trade in realized_trades)
        
        # 获取未实现盈亏（需要调用持仓分析服务）
        analytics = await get_position_analytics()
        portfolio_analysis = await analytics.analyze_portfolio_positions(current_user.id)
        
        if "error" not in portfolio_analysis:
            unrealized_pnl = portfolio_analysis.get("total_unrealized_pnl", 0)
            total_cost_basis = portfolio_analysis.get("total_cost_basis", 0)
        else:
            unrealized_pnl = 0
            total_cost_basis = 0
        
        # 计算总盈亏
        total_pnl = realized_pnl + unrealized_pnl
        
        # 计算收益率
        if total_cost_basis > 0:
            total_return_rate = (total_pnl / total_cost_basis) * 100
        else:
            total_return_rate = 0
        
        # 按股票分组统计
        symbol_pnl = {}
        for trade in realized_trades:
            symbol = trade.symbol
            if symbol not in symbol_pnl:
                symbol_pnl[symbol] = {
                    "symbol": symbol,
                    "realized_pnl": 0,
                    "trade_count": 0,
                    "total_sold": 0
                }
            
            symbol_pnl[symbol]["realized_pnl"] += trade.profit_loss or 0
            symbol_pnl[symbol]["trade_count"] += 1
            symbol_pnl[symbol]["total_sold"] += trade.quantity * trade.price
        
        # 转换为列表并排序
        symbol_performance = list(symbol_pnl.values())
        symbol_performance.sort(key=lambda x: x["realized_pnl"], reverse=True)
        
        return {
            "period_days": days,
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "total_return_rate": round(total_return_rate, 2),
            "total_cost_basis": round(total_cost_basis, 2),
            "realized_trade_count": len(realized_trades),
            "top_performers": symbol_performance[:5],  # 前5名表现最好的
            "worst_performers": symbol_performance[-5:] if len(symbol_performance) > 5 else []  # 后5名表现最差的
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取盈亏汇总失败: {str(e)}")


@router.get("/allocation/analysis")
async def get_allocation_analysis(
    current_user: models.User = Depends(get_current_active_user),
    analytics: PositionAnalytics = Depends(get_position_analytics)
) -> Dict[str, Any]:
    """
    获取资产配置分析
    
    Returns:
        详细的资产配置分析结果
    """
    try:
        # 获取投资组合分析
        portfolio_analysis = await analytics.analyze_portfolio_positions(current_user.id)
        
        if "error" in portfolio_analysis:
            raise HTTPException(status_code=400, detail=portfolio_analysis["error"])
        
        # 提取资产配置信息
        asset_allocation = portfolio_analysis.get("asset_allocation", {})
        
        # 计算配置建议
        allocations = asset_allocation.get("asset_allocations", [])
        total_value = asset_allocation.get("total_value", 0)
        cash_percentage = asset_allocation.get("cash_percentage", 0)
        
        # 分析配置风险
        concentration_alerts = []
        for allocation in allocations:
            if allocation["percentage"] > 30:
                concentration_alerts.append({
                    "type": "high_concentration",
                    "symbol": allocation["symbol"],
                    "percentage": allocation["percentage"],
                    "message": f"{allocation['symbol']} 占比过高 ({allocation['percentage']:.1f}%)，建议控制在30%以下"
                })
        
        if cash_percentage < 5:
            concentration_alerts.append({
                "type": "low_cash",
                "percentage": cash_percentage,
                "message": f"现金比例过低 ({cash_percentage:.1f}%)，建议保持5%以上现金储备"
            })
        elif cash_percentage > 20:
            concentration_alerts.append({
                "type": "high_cash",
                "percentage": cash_percentage,
                "message": f"现金比例较高 ({cash_percentage:.1f}%)，可考虑增加投资"
            })
        
        # 生成配置建议
        recommendations = []
        if len(allocations) < 3:
            recommendations.append("建议增加持仓多样化，分散投资风险")
        
        if any(a["percentage"] > 25 for a in allocations):
            recommendations.append("建议降低大仓位股票比例，平衡投资组合")
        
        if cash_percentage < 10:
            recommendations.append("建议增加现金储备，应对市场波动")
        
        return {
            "total_portfolio_value": total_value,
            "cash_percentage": cash_percentage,
            "position_count": len(allocations),
            "asset_allocations": allocations,
            "concentration_alerts": concentration_alerts,
            "recommendations": recommendations,
            "diversification_score": min(100, len(allocations) * 20)  # 简单的多样化评分
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产配置分析失败: {str(e)}")