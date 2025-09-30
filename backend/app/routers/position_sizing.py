"""
持仓大小计算API路由
提供动态持仓大小计算和建议功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from .. import models
from ..database import get_db
from .auth import get_current_active_user
from ..services.position_sizing import get_position_sizer, PositionSizer, PositionSizingMethod
from ..utils.rate_limit import general_rate_limit

router = APIRouter()


class PositionSizeRequest(BaseModel):
    """持仓大小计算请求"""
    portfolio_id: int
    symbol: str
    entry_price: float
    method: str = "volatility_target"
    custom_params: Optional[Dict[str, Any]] = None


class BatchPositionSizeRequest(BaseModel):
    """批量持仓大小计算请求"""
    portfolio_id: int
    positions: List[Dict[str, Any]]  # [{"symbol": "AAPL", "entry_price": 150.0}, ...]
    method: str = "volatility_target"
    custom_params: Optional[Dict[str, Any]] = None


@router.get("/methods", dependencies=[Depends(general_rate_limit)])
async def get_sizing_methods(
    current_user: models.User = Depends(get_current_active_user),
    position_sizer: PositionSizer = Depends(get_position_sizer)
) -> List[Dict[str, Any]]:
    """获取支持的持仓大小计算方法"""
    try:
        methods = await position_sizer.get_sizing_methods()
        return methods
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取计算方法失败: {str(e)}"
        )


@router.post("/calculate", dependencies=[Depends(general_rate_limit)])
async def calculate_position_size(
    request: PositionSizeRequest,
    current_user: models.User = Depends(get_current_active_user),
    position_sizer: PositionSizer = Depends(get_position_sizer)
) -> Dict[str, Any]:
    """
    计算建议的持仓大小
    
    Args:
        request: 持仓大小计算请求参数
    """
    try:
        # 验证计算方法
        try:
            method = PositionSizingMethod(request.method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的计算方法: {request.method}"
            )
        
        # 计算持仓大小
        result = await position_sizer.calculate_position_size(
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            symbol=request.symbol.upper(),
            entry_price=request.entry_price,
            method=method,
            custom_params=request.custom_params
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "symbol": request.symbol.upper(),
            "entry_price": request.entry_price,
            "calculation_result": result,
            "calculation_time": "now"  # 可以添加实际时间戳
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"持仓大小计算失败: {str(e)}"
        )


@router.post("/calculate-batch", dependencies=[Depends(general_rate_limit)])
async def calculate_batch_position_sizes(
    request: BatchPositionSizeRequest,
    current_user: models.User = Depends(get_current_active_user),
    position_sizer: PositionSizer = Depends(get_position_sizer)
) -> Dict[str, Any]:
    """
    批量计算多个股票的建议持仓大小
    
    Args:
        request: 批量计算请求参数
    """
    try:
        # 验证计算方法
        try:
            method = PositionSizingMethod(request.method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的计算方法: {request.method}"
            )
        
        results = []
        total_suggested_amount = 0
        successful_calculations = 0
        failed_calculations = 0
        
        for position in request.positions:
            try:
                symbol = position.get("symbol", "").upper()
                entry_price = position.get("entry_price", 0)
                
                if not symbol or entry_price <= 0:
                    results.append({
                        "symbol": symbol,
                        "entry_price": entry_price,
                        "error": "无效的股票代码或价格"
                    })
                    failed_calculations += 1
                    continue
                
                # 计算持仓大小
                result = await position_sizer.calculate_position_size(
                    user_id=current_user.id,
                    portfolio_id=request.portfolio_id,
                    symbol=symbol,
                    entry_price=entry_price,
                    method=method,
                    custom_params=request.custom_params
                )
                
                if "error" in result:
                    results.append({
                        "symbol": symbol,
                        "entry_price": entry_price,
                        "error": result["error"]
                    })
                    failed_calculations += 1
                else:
                    results.append({
                        "symbol": symbol,
                        "entry_price": entry_price,
                        "calculation_result": result
                    })
                    total_suggested_amount += result.get("suggested_amount", 0)
                    successful_calculations += 1
                
            except Exception as e:
                results.append({
                    "symbol": position.get("symbol", ""),
                    "entry_price": position.get("entry_price", 0),
                    "error": str(e)
                })
                failed_calculations += 1
        
        return {
            "method": request.method,
            "portfolio_id": request.portfolio_id,
            "results": results,
            "summary": {
                "total_positions": len(request.positions),
                "successful_calculations": successful_calculations,
                "failed_calculations": failed_calculations,
                "total_suggested_amount": total_suggested_amount,
                "average_suggested_amount": total_suggested_amount / successful_calculations if successful_calculations > 0 else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量持仓大小计算失败: {str(e)}"
        )


@router.get("/portfolio-analysis/{portfolio_id}", dependencies=[Depends(general_rate_limit)])
async def analyze_portfolio_sizing(
    portfolio_id: int,
    method: str = "volatility_target",
    current_user: models.User = Depends(get_current_active_user),
    position_sizer: PositionSizer = Depends(get_position_sizer),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    分析投资组合的持仓大小配置
    
    Args:
        portfolio_id: 投资组合ID
        method: 计算方法
    """
    try:
        # 验证投资组合权限
        from .. import crud
        portfolio = crud.get_portfolio(db, portfolio_id)
        if not portfolio or portfolio.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="投资组合不存在或权限不足"
            )
        
        # 验证计算方法
        try:
            sizing_method = PositionSizingMethod(method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的计算方法: {method}"
            )
        
        # 获取当前持仓
        assets = crud.get_portfolio_assets(db, portfolio_id)
        
        analysis_results = {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "total_value": portfolio.total_value + portfolio.cash_balance,
            "cash_balance": portfolio.cash_balance,
            "method": method,
            "current_positions": [],
            "sizing_recommendations": [],
            "summary": {
                "total_positions": len(assets),
                "total_market_value": portfolio.total_value,
                "cash_ratio": portfolio.cash_balance / (portfolio.total_value + portfolio.cash_balance) if (portfolio.total_value + portfolio.cash_balance) > 0 else 0,
                "avg_position_weight": 0,
                "largest_position_weight": 0,
                "position_concentration_risk": "low"
            }
        }
        
        total_value = portfolio.total_value + portfolio.cash_balance
        position_weights = []
        
        # 分析当前持仓
        for asset in assets:
            current_price = asset.current_price or asset.average_price
            current_weight = (asset.market_value or 0) / total_value if total_value > 0 else 0
            position_weights.append(current_weight)
            
            # 计算基于当前价格的建议持仓大小
            recommended_result = await position_sizer.calculate_position_size(
                user_id=current_user.id,
                portfolio_id=portfolio_id,
                symbol=asset.symbol,
                entry_price=current_price,
                method=sizing_method
            )
            
            position_analysis = {
                "symbol": asset.symbol,
                "current_quantity": asset.quantity,
                "current_price": current_price,
                "current_market_value": asset.market_value or 0,
                "current_weight": current_weight,
                "unrealized_pnl": asset.profit_loss or 0,
                "unrealized_pnl_percent": asset.profit_loss_percentage or 0
            }
            
            if "error" not in recommended_result:
                recommended_weight = recommended_result.get("portfolio_weight", 0)
                weight_diff = recommended_weight - current_weight
                
                position_analysis.update({
                    "recommended_weight": recommended_weight,
                    "recommended_amount": recommended_result.get("suggested_amount", 0),
                    "weight_difference": weight_diff,
                    "sizing_action": "increase" if weight_diff > 0.01 else "decrease" if weight_diff < -0.01 else "hold",
                    "confidence": recommended_result.get("confidence", 0),
                    "risk_level": recommended_result.get("risk_level", "medium")
                })
            else:
                position_analysis["sizing_error"] = recommended_result["error"]
            
            analysis_results["current_positions"].append(position_analysis)
        
        # 计算汇总统计
        if position_weights:
            analysis_results["summary"]["avg_position_weight"] = sum(position_weights) / len(position_weights)
            analysis_results["summary"]["largest_position_weight"] = max(position_weights)
            
            # 评估集中度风险
            if max(position_weights) > 0.3:
                analysis_results["summary"]["position_concentration_risk"] = "high"
            elif max(position_weights) > 0.2:
                analysis_results["summary"]["position_concentration_risk"] = "medium"
            else:
                analysis_results["summary"]["position_concentration_risk"] = "low"
        
        # 生成整体建议
        recommendations = []
        
        if analysis_results["summary"]["cash_ratio"] < 0.05:
            recommendations.append("现金比例过低，建议增加现金头寸")
        elif analysis_results["summary"]["cash_ratio"] > 0.3:
            recommendations.append("现金比例较高，可考虑增加投资")
        
        if analysis_results["summary"]["position_concentration_risk"] == "high":
            recommendations.append("持仓集中度过高，建议分散投资")
        
        over_weighted = [p for p in analysis_results["current_positions"] 
                        if p.get("weight_difference", 0) < -0.05]
        under_weighted = [p for p in analysis_results["current_positions"] 
                         if p.get("weight_difference", 0) > 0.05]
        
        if over_weighted:
            symbols = [p["symbol"] for p in over_weighted[:3]]
            recommendations.append(f"建议减持: {', '.join(symbols)}")
        
        if under_weighted:
            symbols = [p["symbol"] for p in under_weighted[:3]]
            recommendations.append(f"建议增持: {', '.join(symbols)}")
        
        analysis_results["sizing_recommendations"] = recommendations
        
        return analysis_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"投资组合持仓分析失败: {str(e)}"
        )


@router.get("/optimization/{portfolio_id}", dependencies=[Depends(general_rate_limit)])
async def optimize_portfolio_sizing(
    portfolio_id: int,
    target_risk: float = 0.15,  # 15%目标风险
    max_position_weight: float = 0.25,  # 25%最大单个持仓
    current_user: models.User = Depends(get_current_active_user),
    position_sizer: PositionSizer = Depends(get_position_sizer),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    优化投资组合的持仓大小配置
    
    Args:
        portfolio_id: 投资组合ID
        target_risk: 目标风险水平
        max_position_weight: 最大单个持仓权重
    """
    try:
        # 验证投资组合权限
        from .. import crud
        portfolio = crud.get_portfolio(db, portfolio_id)
        if not portfolio or portfolio.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="投资组合不存在或权限不足"
            )
        
        # 获取当前持仓
        assets = crud.get_portfolio_assets(db, portfolio_id)
        
        if not assets:
            return {
                "portfolio_id": portfolio_id,
                "message": "投资组合无持仓，无需优化",
                "optimized_weights": [],
                "execution_plan": []
            }
        
        optimization_result = {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "target_risk": target_risk,
            "max_position_weight": max_position_weight,
            "current_allocation": [],
            "optimized_allocation": [],
            "execution_plan": [],
            "expected_improvement": {}
        }
        
        total_value = portfolio.total_value + portfolio.cash_balance
        
        # 分析当前配置
        current_weights = []
        symbols = []
        
        for asset in assets:
            current_weight = (asset.market_value or 0) / total_value if total_value > 0 else 0
            current_weights.append(current_weight)
            symbols.append(asset.symbol)
            
            optimization_result["current_allocation"].append({
                "symbol": asset.symbol,
                "current_weight": current_weight,
                "current_amount": asset.market_value or 0
            })
        
        # 简化的优化算法（等权重分配，受最大权重约束）
        num_positions = len(assets)
        if num_positions > 0:
            # 计算理想等权重
            equal_weight = 1.0 / num_positions
            
            # 应用最大权重约束
            optimized_weight = min(equal_weight, max_position_weight)
            
            # 如果等权重超过最大权重，重新分配
            if equal_weight > max_position_weight:
                # 受约束的持仓使用最大权重
                constrained_positions = num_positions
                remaining_weight = 1.0 - (constrained_positions * max_position_weight)
                
                # 如果剩余权重为负，说明无法满足约束
                if remaining_weight < 0:
                    # 所有持仓都使用最大权重
                    optimized_weight = max_position_weight
                    remaining_weight = 0
        
        # 生成优化后的配置
        for i, asset in enumerate(assets):
            current_weight = current_weights[i]
            
            # 简化：使用风险平价方法计算建议权重
            risk_parity_result = await position_sizer.calculate_position_size(
                user_id=current_user.id,
                portfolio_id=portfolio_id,
                symbol=asset.symbol,
                entry_price=asset.current_price or asset.average_price,
                method=PositionSizingMethod.RISK_PARITY,
                custom_params={"target_risk_contribution": target_risk / num_positions}
            )
            
            if "error" not in risk_parity_result:
                optimized_weight = min(
                    risk_parity_result.get("portfolio_weight", current_weight),
                    max_position_weight
                )
            else:
                optimized_weight = min(current_weight, max_position_weight)
            
            optimized_amount = total_value * optimized_weight
            weight_change = optimized_weight - current_weight
            amount_change = optimized_amount - (asset.market_value or 0)
            
            optimization_result["optimized_allocation"].append({
                "symbol": asset.symbol,
                "optimized_weight": optimized_weight,
                "optimized_amount": optimized_amount,
                "weight_change": weight_change,
                "amount_change": amount_change
            })
            
            # 生成执行计划
            if abs(weight_change) > 0.01:  # 权重变化超过1%才执行
                action = "增持" if weight_change > 0 else "减持"
                optimization_result["execution_plan"].append({
                    "symbol": asset.symbol,
                    "action": action,
                    "target_weight": optimized_weight,
                    "weight_change": weight_change,
                    "amount_change": amount_change,
                    "priority": "high" if abs(weight_change) > 0.05 else "medium"
                })
        
        # 计算预期改进
        current_concentration = max(current_weights) if current_weights else 0
        optimized_concentration = max([pos["optimized_weight"] for pos in optimization_result["optimized_allocation"]])
        
        optimization_result["expected_improvement"] = {
            "concentration_reduction": current_concentration - optimized_concentration,
            "risk_reduction_estimate": max(0, (current_concentration - optimized_concentration) * 0.5),
            "diversification_improvement": len([p for p in optimization_result["execution_plan"] if p["weight_change"] > 0]),
            "total_adjustments": len(optimization_result["execution_plan"])
        }
        
        return optimization_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"投资组合优化失败: {str(e)}"
        )