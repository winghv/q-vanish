"""
AI助手API路由（重构版）
整合所有AI功能：聊天、投资建议、情绪分析、风险提醒、策略推荐
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging

from .. import models
from ..database import get_db
from .auth import get_current_active_user
from ..services.ai_service_manager import get_ai_service_manager
from ..services.ai_investment_advisor import get_investment_advisor
from ..services.ai_sentiment_analyzer import get_sentiment_analyzer
from ..services.ai_risk_alerter import get_risk_alerter
from ..services.ai_strategy_recommender import get_strategy_recommender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


# ========== Request/Response Models ==========

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    context: Optional[Dict[str, Any]] = None


class InvestmentAdviceRequest(BaseModel):
    portfolio_id: int
    focus_areas: Optional[List[str]] = Field(default=None, description="关注领域：rebalancing, diversification, risk, tax")


class RebalancingRequest(BaseModel):
    portfolio_id: int
    target_allocations: Optional[Dict[str, float]] = None


class AssetRecommendationRequest(BaseModel):
    risk_tolerance: str = Field(..., description="风险承受能力：low, moderate, high")
    investment_amount: float
    investment_horizon: str = Field(..., description="投资期限：short, medium, long")
    preferences: Optional[Dict[str, Any]] = None


class SentimentRequest(BaseModel):
    symbols: Optional[List[str]] = None
    include_news: bool = True


class SymbolSentimentRequest(BaseModel):
    symbol: str
    include_news: bool = True


class RiskScanRequest(BaseModel):
    portfolio_id: int


class StrategyRecommendRequest(BaseModel):
    portfolio_id: Optional[int] = None
    market_condition: Optional[str] = None


class StrategyOptimizationRequest(BaseModel):
    strategy_id: int


class StrategyComparisonRequest(BaseModel):
    strategy_ids: List[int]


# ========== 聊天功能 ==========

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """基础聊天功能"""
    try:
        ai_manager = get_ai_service_manager()

        # 准备消息
        messages = []
        context = request.context or {}

        if "messages" in context:
            messages = context["messages"]
        else:
            messages.append({
                "role": "system",
                "content": ai_manager.system_prompts["default"]
            })

        messages.append({"role": "user", "content": request.message})

        # 调用AI
        if request.stream:
            # 流式响应（这里简化处理）
            response = await ai_manager.chat_completion(
                messages=messages,
                stream=False  # 简化：暂不支持流式
            )
        else:
            response = await ai_manager.chat_completion(messages=messages)

        # 提取响应
        ai_message = response.choices[0].message.content if hasattr(response, 'choices') else ""

        # 更新上下文
        messages.append({"role": "assistant", "content": ai_message})
        if len(messages) > 12:
            messages = [messages[0]] + messages[-10:]

        return {
            "response": ai_message,
            "context": {"messages": messages}
        }

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"AI服务错误: {str(e)}")


# ========== 投资建议功能 ==========

@router.post("/investment-advice")
async def get_investment_advice(
    request: InvestmentAdviceRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取投资组合建议"""
    try:
        advisor = get_investment_advisor()
        result = await advisor.get_portfolio_advice(
            db=db,
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            focus_areas=request.focus_areas
        )
        return result
    except Exception as e:
        logger.error(f"Investment advice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebalancing-advice")
async def get_rebalancing_advice(
    request: RebalancingRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取再平衡建议"""
    try:
        advisor = get_investment_advisor()
        result = await advisor.get_rebalancing_advice(
            db=db,
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            target_allocations=request.target_allocations
        )
        return result
    except Exception as e:
        logger.error(f"Rebalancing advice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/asset-recommendations")
async def get_asset_recommendations(
    request: AssetRecommendationRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取资产推荐"""
    try:
        advisor = get_investment_advisor()
        result = await advisor.get_asset_recommendation(
            db=db,
            user_id=current_user.id,
            risk_tolerance=request.risk_tolerance,
            investment_amount=request.investment_amount,
            investment_horizon=request.investment_horizon,
            preferences=request.preferences
        )
        return result
    except Exception as e:
        logger.error(f"Asset recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 市场情绪分析功能 ==========

@router.post("/sentiment/market")
async def analyze_market_sentiment(
    request: SentimentRequest,
    current_user: models.User = Depends(get_current_active_user)
):
    """分析市场整体情绪"""
    try:
        analyzer = get_sentiment_analyzer()
        result = await analyzer.analyze_market_sentiment(
            symbols=request.symbols,
            include_news=request.include_news
        )
        return result
    except Exception as e:
        logger.error(f"Market sentiment analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentiment/symbol")
async def analyze_symbol_sentiment(
    request: SymbolSentimentRequest,
    current_user: models.User = Depends(get_current_active_user)
):
    """分析单个股票情绪"""
    try:
        analyzer = get_sentiment_analyzer()
        result = await analyzer.analyze_symbol_sentiment(
            symbol=request.symbol,
            include_news=request.include_news
        )
        return result
    except Exception as e:
        logger.error(f"Symbol sentiment analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/sectors")
async def get_sector_sentiment(
    current_user: models.User = Depends(get_current_active_user)
):
    """获取行业板块情绪"""
    try:
        analyzer = get_sentiment_analyzer()
        result = await analyzer.get_sector_sentiment()
        return result
    except Exception as e:
        logger.error(f"Sector sentiment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 风险提醒功能 ==========

@router.post("/risk/scan")
async def scan_portfolio_risks(
    request: RiskScanRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """扫描投资组合风险"""
    try:
        alerter = get_risk_alerter()
        result = await alerter.scan_portfolio_risks(
            db=db,
            user_id=current_user.id,
            portfolio_id=request.portfolio_id
        )
        return result
    except Exception as e:
        logger.error(f"Risk scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/alerts")
async def get_user_risk_alerts(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户的风险提醒列表"""
    try:
        # 从数据库获取未解决的风险提醒
        alerts = db.query(models.AIRiskAlert).filter(
            models.AIRiskAlert.user_id == current_user.id,
            models.AIRiskAlert.is_resolved == False
        ).order_by(models.AIRiskAlert.created_at.desc()).limit(50).all()

        return {
            "success": True,
            "alerts": [
                {
                    "id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "symbol": alert.symbol,
                    "message": alert.alert_message,
                    "is_read": alert.is_read,
                    "created_at": alert.created_at.isoformat()
                }
                for alert in alerts
            ],
            "total_count": len(alerts)
        }
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 策略推荐功能 ==========

@router.post("/strategy/recommend")
async def recommend_strategies(
    request: StrategyRecommendRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """推荐交易策略"""
    try:
        recommender = get_strategy_recommender()
        result = await recommender.recommend_strategies(
            db=db,
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            market_condition=request.market_condition
        )
        return result
    except Exception as e:
        logger.error(f"Strategy recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy/optimize")
async def optimize_strategy(
    request: StrategyOptimizationRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """优化策略参数"""
    try:
        recommender = get_strategy_recommender()
        result = await recommender.optimize_strategy_parameters(
            db=db,
            user_id=current_user.id,
            strategy_id=request.strategy_id
        )
        return result
    except Exception as e:
        logger.error(f"Strategy optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy/compare")
async def compare_strategies(
    request: StrategyComparisonRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """比较多个策略"""
    try:
        recommender = get_strategy_recommender()
        result = await recommender.compare_strategies(
            db=db,
            user_id=current_user.id,
            strategy_ids=request.strategy_ids
        )
        return result
    except Exception as e:
        logger.error(f"Strategy comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 统计和健康检查 ==========

@router.get("/stats")
async def get_ai_usage_stats(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取AI使用统计"""
    try:
        ai_manager = get_ai_service_manager()
        stats = ai_manager.get_usage_stats()

        # 获取用户的历史使用统计
        user_stats = db.query(models.AIUsageStats).filter(
            models.AIUsageStats.user_id == current_user.id
        ).all()

        return {
            "success": True,
            "current_session": stats,
            "user_history": {
                "total_requests": sum(s.request_count for s in user_stats),
                "total_tokens": sum(s.total_tokens for s in user_stats),
                "total_cost": sum(s.total_cost for s in user_stats)
            }
        }
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ai_health_check(
    current_user: models.User = Depends(get_current_active_user)
):
    """AI服务健康检查"""
    try:
        ai_manager = get_ai_service_manager()
        is_healthy = await ai_manager.health_check()

        return {
            "success": True,
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "success": False,
            "status": "error",
            "error": str(e)
        }


@router.get("/history")
async def get_ai_advice_history(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    advice_type: Optional[str] = None
):
    """获取AI建议历史"""
    try:
        query = db.query(models.AIAdviceHistory).filter(
            models.AIAdviceHistory.user_id == current_user.id
        )

        if advice_type:
            query = query.filter(models.AIAdviceHistory.advice_type == advice_type)

        history = query.order_by(
            models.AIAdviceHistory.created_at.desc()
        ).limit(limit).all()

        return {
            "success": True,
            "history": [
                {
                    "id": item.id,
                    "advice_type": item.advice_type,
                    "created_at": item.created_at.isoformat(),
                    "was_helpful": item.was_helpful,
                    "metadata": item.extra_metadata
                }
                for item in history
            ]
        }
    except Exception as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
