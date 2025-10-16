"""
策略系统API路由
提供回测、性能分析、模板和实盘执行的完整API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from decimal import Decimal

from ..database import get_db
from .auth import get_current_user
from ..schemas import User
from ..services.backtest_engine import BacktestEngine
from ..services.strategy_performance import StrategyPerformanceAnalyzer
from ..services.strategy_templates import StrategyTemplates
from ..services.live_strategy_engine import LiveStrategyEngine
from ..services.strategy_risk_assessment import StrategyRiskAssessor
from ..services.market_data import MarketDataService
from ..services.order_engine import OrderExecutionEngine as OrderEngine
from ..services.risk_management import RiskManager as RiskManagementService

router = APIRouter(prefix="/api/strategy-system", tags=["Strategy System"])

# 依赖注入
def get_market_data_service():
    return MarketDataService()

def get_order_engine():
    return OrderEngine()

def get_risk_service():
    return RiskManagementService()

def get_backtest_engine(market_data: MarketDataService = Depends(get_market_data_service)):
    return BacktestEngine(market_data)

def get_live_engine(
    market_data: MarketDataService = Depends(get_market_data_service),
    order_engine: OrderEngine = Depends(get_order_engine),
    risk_service: RiskManagementService = Depends(get_risk_service)
):
    return LiveStrategyEngine(market_data, order_engine, risk_service)


# ==================== 请求模型 ====================

class BacktestRequest(BaseModel):
    strategy_id: int
    start_date: datetime
    end_date: datetime
    initial_capital: Optional[Decimal] = Decimal("100000")
    commission_rate: Optional[Decimal] = Decimal("0.001")
    slippage_rate: Optional[Decimal] = Decimal("0.0005")


class StartLiveStrategyRequest(BaseModel):
    strategy_id: int
    portfolio_id: int


class CompareStrategiesRequest(BaseModel):
    strategy_ids: List[int]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class PortfolioPerformanceRequest(BaseModel):
    portfolio_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ==================== 回测相关API ====================

@router.post("/backtest/run")
async def run_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    backtest_engine: BacktestEngine = Depends(get_backtest_engine)
):
    """运行策略回测"""
    try:
        result = await backtest_engine.run_backtest(
            db=db,
            strategy_id=request.strategy_id,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            slippage_rate=request.slippage_rate
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/backtest/{backtest_id}/analysis")
async def get_backtest_analysis(
    backtest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取回测结果分析"""
    try:
        analysis = StrategyPerformanceAnalyzer.analyze_backtest(backtest_id, db)
        return analysis
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== 策略性能分析API ====================

@router.post("/performance/compare")
async def compare_strategies(
    request: CompareStrategiesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """比较多个策略的性能"""
    comparison = StrategyPerformanceAnalyzer.compare_strategies(
        request.strategy_ids,
        db,
        request.start_date,
        request.end_date
    )
    return comparison


@router.post("/performance/portfolio")
async def get_portfolio_performance(
    request: PortfolioPerformanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """计算投资组合性能"""
    performance = StrategyPerformanceAnalyzer.calculate_portfolio_performance(
        request.portfolio_id,
        db,
        request.start_date,
        request.end_date
    )
    return performance


# ==================== 策略模板API ====================

@router.get("/templates")
async def get_all_templates(current_user: User = Depends(get_current_user)):
    """获取所有策略模板"""
    templates = StrategyTemplates.get_all_templates()
    return {"templates": templates}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取特定策略模板"""
    template = StrategyTemplates.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


# ==================== 实盘策略执行API ====================

@router.post("/live/start")
async def start_live_strategy(
    request: StartLiveStrategyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    live_engine: LiveStrategyEngine = Depends(get_live_engine)
):
    """启动实盘策略"""
    result = await live_engine.start_strategy(
        db=db,
        strategy_id=request.strategy_id,
        portfolio_id=request.portfolio_id,
        user_id=current_user.id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/live/stop/{strategy_id}")
async def stop_live_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    live_engine: LiveStrategyEngine = Depends(get_live_engine)
):
    """停止实盘策略"""
    result = await live_engine.stop_strategy(strategy_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@router.get("/live/running")
async def get_running_strategies(
    current_user: User = Depends(get_current_user),
    live_engine: LiveStrategyEngine = Depends(get_live_engine)
):
    """获取所有运行中的策略"""
    strategies = live_engine.get_running_strategies()
    return {"running_strategies": strategies}


@router.get("/live/status/{strategy_id}")
async def get_strategy_status(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    live_engine: LiveStrategyEngine = Depends(get_live_engine)
):
    """获取策略运行状态"""
    status = live_engine.get_strategy_status(strategy_id)

    if not status:
        raise HTTPException(status_code=404, detail="Strategy not running")

    return status


# ==================== 策略风险评估API ====================

@router.get("/risk/assess/{strategy_id}")
async def assess_strategy_risk(
    strategy_id: int,
    portfolio_value: Optional[Decimal] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """评估策略风险"""
    try:
        assessment = StrategyRiskAssessor.assess_strategy_risk(
            strategy_id, db, portfolio_value
        )
        return assessment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/risk/compare")
async def compare_strategy_risks(
    request: CompareStrategiesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """比较多个策略的风险"""
    comparison = StrategyRiskAssessor.compare_strategy_risks(
        request.strategy_ids, db
    )
    return comparison


@router.get("/risk/stress-test/{strategy_id}")
async def stress_test_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """策略压力测试"""
    result = StrategyRiskAssessor.stress_test_strategy(strategy_id, db)
    return result


# ==================== 综合报告API ====================

@router.get("/report/comprehensive/{strategy_id}")
async def get_comprehensive_report(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取策略综合报告（包含性能、风险等所有信息）"""
    try:
        # 获取最新回测
        from ..models import BacktestResult
        backtest = db.query(BacktestResult).filter(
            BacktestResult.strategy_id == strategy_id
        ).order_by(BacktestResult.created_at.desc()).first()

        if not backtest:
            raise HTTPException(
                status_code=404,
                detail="No backtest results found for this strategy"
            )

        # 性能分析
        performance = StrategyPerformanceAnalyzer.analyze_backtest(backtest.id, db)

        # 风险评估
        risk = StrategyRiskAssessor.assess_strategy_risk(strategy_id, db)

        # 压力测试
        stress_test = StrategyRiskAssessor.stress_test_strategy(strategy_id, db)

        return {
            "strategy_id": strategy_id,
            "performance": performance,
            "risk_assessment": risk,
            "stress_test": stress_test,
            "generated_at": datetime.now().isoformat()
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
