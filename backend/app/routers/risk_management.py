"""
风险管理API路由
提供投资组合风险评估和管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel

from .. import models
from ..database import get_db
from .auth import get_current_active_user
from ..services.risk_management import get_risk_manager, RiskManager
from ..utils.rate_limit import general_rate_limit

router = APIRouter()


class RiskLimitsUpdate(BaseModel):
    """风险限制更新请求"""
    limits: Dict[str, float]


class OrderRiskCheck(BaseModel):
    """订单风险检查请求"""
    portfolio_id: int
    symbol: str
    quantity: float
    price: float
    order_type: str


@router.get("/assessment", dependencies=[Depends(general_rate_limit)])
async def assess_portfolio_risk(
    portfolio_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_active_user),
    risk_manager: RiskManager = Depends(get_risk_manager)
) -> Dict[str, Any]:
    """
    评估投资组合风险
    
    Args:
        portfolio_id: 投资组合ID，为None时评估所有投资组合
    """
    try:
        assessment = await risk_manager.assess_portfolio_risk(
            user_id=current_user.id,
            portfolio_id=portfolio_id
        )
        
        if "error" in assessment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=assessment["error"]
            )
        
        return assessment
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"风险评估失败: {str(e)}"
        )


@router.post("/check-order", dependencies=[Depends(general_rate_limit)])
async def check_order_risk(
    order_check: OrderRiskCheck,
    current_user: models.User = Depends(get_current_active_user),
    risk_manager: RiskManager = Depends(get_risk_manager)
) -> Dict[str, Any]:
    """
    检查订单风险
    
    Args:
        order_check: 订单风险检查参数
    """
    try:
        risk_result = await risk_manager.check_order_risk(
            user_id=current_user.id,
            portfolio_id=order_check.portfolio_id,
            symbol=order_check.symbol.upper(),
            quantity=order_check.quantity,
            price=order_check.price,
            order_type=order_check.order_type
        )
        
        return {
            "risk_check_passed": risk_result["passed"],
            "reason": risk_result["reason"],
            "order_details": {
                "symbol": order_check.symbol.upper(),
                "quantity": order_check.quantity,
                "price": order_check.price,
                "order_value": abs(order_check.quantity) * order_check.price,
                "side": "buy" if order_check.quantity > 0 else "sell"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"订单风险检查失败: {str(e)}"
        )


@router.get("/limits", dependencies=[Depends(general_rate_limit)])
async def get_risk_limits(
    current_user: models.User = Depends(get_current_active_user),
    risk_manager: RiskManager = Depends(get_risk_manager)
) -> Dict[str, Any]:
    """获取用户的风险限制配置"""
    try:
        limits = await risk_manager.get_risk_limits(current_user.id)
        return limits
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取风险限制失败: {str(e)}"
        )


@router.put("/limits", dependencies=[Depends(general_rate_limit)])
async def update_risk_limits(
    limits_update: RiskLimitsUpdate,
    current_user: models.User = Depends(get_current_active_user),
    risk_manager: RiskManager = Depends(get_risk_manager)
) -> Dict[str, Any]:
    """
    更新用户的风险限制配置
    
    Args:
        limits_update: 风险限制更新数据
    """
    try:
        result = await risk_manager.update_risk_limits(
            user_id=current_user.id,
            limits=limits_update.limits
        )
        
        return {
            "success": True,
            "message": result["message"],
            "updated_limits": result["updated_limits"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新风险限制失败: {str(e)}"
        )


@router.get("/alerts", dependencies=[Depends(general_rate_limit)])
async def get_risk_alerts(
    portfolio_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_active_user),
    risk_manager: RiskManager = Depends(get_risk_manager)
) -> Dict[str, Any]:
    """
    获取风险警报
    
    Args:
        portfolio_id: 投资组合ID，为None时获取所有警报
    """
    try:
        # 进行风险评估以获取最新警报
        assessment = await risk_manager.assess_portfolio_risk(
            user_id=current_user.id,
            portfolio_id=portfolio_id
        )
        
        if "error" in assessment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=assessment["error"]
            )
        
        # 提取警报信息
        alerts = []
        for alert in assessment.get("alerts", []):
            if hasattr(alert, '__dict__'):
                # 如果是RiskAlert对象，转换为字典
                alert_dict = {
                    "risk_type": alert.risk_type,
                    "level": alert.level.value,
                    "message": alert.message,
                    "current_value": alert.current_value,
                    "limit_value": alert.limit_value,
                    "timestamp": alert.timestamp.isoformat(),
                    "portfolio_id": alert.portfolio_id,
                    "symbol": alert.symbol
                }
            else:
                # 如果已经是字典，直接使用
                alert_dict = alert
            
            alerts.append(alert_dict)
        
        # 按风险等级和时间排序
        risk_level_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        alerts.sort(
            key=lambda x: (
                risk_level_order.get(x.get("level", "low"), 1),
                x.get("timestamp", "")
            ),
            reverse=True
        )
        
        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a.get("level") == "critical"]),
            "high_alerts": len([a for a in alerts if a.get("level") == "high"]),
            "medium_alerts": len([a for a in alerts if a.get("level") == "medium"]),
            "assessment_time": assessment.get("assessment_time")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取风险警报失败: {str(e)}"
        )


@router.get("/metrics/{portfolio_id}", dependencies=[Depends(general_rate_limit)])
async def get_portfolio_risk_metrics(
    portfolio_id: int,
    current_user: models.User = Depends(get_current_active_user),
    risk_manager: RiskManager = Depends(get_risk_manager)
) -> Dict[str, Any]:
    """
    获取特定投资组合的详细风险指标
    
    Args:
        portfolio_id: 投资组合ID
    """
    try:
        assessment = await risk_manager.assess_portfolio_risk(
            user_id=current_user.id,
            portfolio_id=portfolio_id
        )
        
        if "error" in assessment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=assessment["error"]
            )
        
        # 找到目标投资组合的评估结果
        portfolio_data = None
        for portfolio in assessment.get("portfolios", []):
            if portfolio["portfolio_id"] == portfolio_id:
                portfolio_data = portfolio
                break
        
        if not portfolio_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到投资组合评估数据"
            )
        
        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio_data["portfolio_name"],
            "risk_score": portfolio_data["risk_score"],
            "risk_level": portfolio_data["risk_level"].value if hasattr(portfolio_data["risk_level"], 'value') else portfolio_data["risk_level"],
            "total_value": portfolio_data["total_value"],
            "cash_ratio": portfolio_data["cash_ratio"],
            "metrics": portfolio_data["metrics"],
            "position_count": len(portfolio_data["positions"]),
            "positions": portfolio_data["positions"],
            "alerts": [
                {
                    "risk_type": alert.risk_type if hasattr(alert, 'risk_type') else alert.get("risk_type"),
                    "level": alert.level.value if hasattr(alert, 'level') and hasattr(alert.level, 'value') else alert.get("level"),
                    "message": alert.message if hasattr(alert, 'message') else alert.get("message"),
                    "current_value": alert.current_value if hasattr(alert, 'current_value') else alert.get("current_value"),
                    "limit_value": alert.limit_value if hasattr(alert, 'limit_value') else alert.get("limit_value")
                }
                for alert in portfolio_data["alerts"]
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取风险指标失败: {str(e)}"
        )


@router.get("/summary", dependencies=[Depends(general_rate_limit)])
async def get_risk_summary(
    current_user: models.User = Depends(get_current_active_user),
    risk_manager: RiskManager = Depends(get_risk_manager)
) -> Dict[str, Any]:
    """获取用户的风险管理摘要"""
    try:
        # 获取完整的风险评估
        assessment = await risk_manager.assess_portfolio_risk(
            user_id=current_user.id
        )
        
        if "error" in assessment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=assessment["error"]
            )
        
        # 计算摘要统计
        total_portfolios = len(assessment.get("portfolios", []))
        total_alerts = len(assessment.get("alerts", []))
        
        alert_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for alert in assessment.get("alerts", []):
            level = alert.level.value if hasattr(alert, 'level') and hasattr(alert.level, 'value') else alert.get("level", "low")
            if level in alert_counts:
                alert_counts[level] += 1
        
        # 计算总价值和风险敞口
        total_value = sum(p["total_value"] for p in assessment.get("portfolios", []))
        total_cash = sum(p["cash_balance"] for p in assessment.get("portfolios", []))
        total_invested = total_value - total_cash
        
        return {
            "overall_risk_score": assessment.get("overall_risk_score", 0.0),
            "risk_level": assessment.get("risk_level").value if hasattr(assessment.get("risk_level"), 'value') else assessment.get("risk_level", "low"),
            "total_portfolios": total_portfolios,
            "total_value": total_value,
            "total_cash": total_cash,
            "total_invested": total_invested,
            "cash_ratio": total_cash / total_value if total_value > 0 else 0,
            "total_alerts": total_alerts,
            "alert_breakdown": alert_counts,
            "recommendations": assessment.get("recommendations", []),
            "assessment_time": assessment.get("assessment_time")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取风险摘要失败: {str(e)}"
        )