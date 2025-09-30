"""
券商管理API路由
提供券商配置、连接、管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from .. import models
from ..database import get_db
from .auth import get_current_active_user
from ..services.brokers.broker_manager import get_broker_manager, BrokerManager, BrokerType
from ..utils.rate_limit import general_rate_limit

router = APIRouter()


class BrokerConfigRequest(BaseModel):
    """券商配置请求"""
    broker_type: str
    config: Dict[str, Any]


class BrokerCreateRequest(BaseModel):
    """创建券商请求"""
    broker_id: str
    broker_type: str
    config: Optional[Dict[str, Any]] = None


@router.get("/types", dependencies=[Depends(general_rate_limit)])
async def get_supported_broker_types(
    current_user: models.User = Depends(get_current_active_user),
    broker_manager: BrokerManager = Depends(get_broker_manager)
) -> List[Dict[str, str]]:
    """获取支持的券商类型列表"""
    broker_types = broker_manager.get_supported_broker_types()
    
    return [
        {
            "type": broker_type.value,
            "name": broker_type.value.replace("_", " ").title(),
            "description": _get_broker_description(broker_type)
        }
        for broker_type in broker_types
    ]


def _get_broker_description(broker_type: BrokerType) -> str:
    """获取券商类型描述"""
    descriptions = {
        BrokerType.PAPER_TRADING: "模拟交易 - 用于测试和学习，使用虚拟资金",
        BrokerType.ALPACA: "Alpaca - 美股免佣金交易平台",
        BrokerType.INTERACTIVE_BROKERS: "Interactive Brokers - 专业交易平台",
        BrokerType.TD_AMERITRADE: "TD Ameritrade - 美国知名券商"
    }
    return descriptions.get(broker_type, "未知券商类型")


@router.post("/validate-config", dependencies=[Depends(general_rate_limit)])
async def validate_broker_config(
    config_request: BrokerConfigRequest,
    current_user: models.User = Depends(get_current_active_user),
    broker_manager: BrokerManager = Depends(get_broker_manager)
) -> Dict[str, Any]:
    """验证券商配置"""
    try:
        broker_type = BrokerType(config_request.broker_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported broker type: {config_request.broker_type}"
        )
    
    validation_result = broker_manager.validate_broker_config(
        broker_type, 
        config_request.config
    )
    
    return validation_result


@router.post("/create", dependencies=[Depends(general_rate_limit)])
async def create_broker(
    create_request: BrokerCreateRequest,
    current_user: models.User = Depends(get_current_active_user),
    broker_manager: BrokerManager = Depends(get_broker_manager)
) -> Dict[str, Any]:
    """创建券商实例"""
    # 检查权限（只有管理员可以创建券商实例）
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以创建券商实例"
        )
    
    try:
        broker_type = BrokerType(create_request.broker_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported broker type: {create_request.broker_type}"
        )
    
    try:
        # 验证配置
        if create_request.config:
            validation_result = broker_manager.validate_broker_config(
                broker_type, 
                create_request.config
            )
            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid configuration: {validation_result['error']}"
                )
        
        # 创建券商实例
        broker = await broker_manager.create_broker(
            create_request.broker_id,
            broker_type,
            create_request.config
        )
        
        # 获取账户信息
        account_info = await broker.get_account_info()
        
        return {
            "success": True,
            "message": f"券商实例创建成功: {create_request.broker_id}",
            "broker_id": create_request.broker_id,
            "broker_type": broker_type.value,
            "is_connected": broker.is_connected,
            "account_info": {
                "account_id": account_info.account_id,
                "cash_balance": account_info.cash_balance,
                "total_value": account_info.total_value,
                "buying_power": account_info.buying_power
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建券商实例失败: {str(e)}"
        )


@router.get("/list", dependencies=[Depends(general_rate_limit)])
async def list_brokers(
    current_user: models.User = Depends(get_current_active_user),
    broker_manager: BrokerManager = Depends(get_broker_manager)
) -> List[Dict[str, Any]]:
    """列出所有券商实例"""
    try:
        brokers = await broker_manager.list_brokers()
        return brokers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取券商列表失败: {str(e)}"
        )


@router.get("/default", dependencies=[Depends(general_rate_limit)])
async def get_default_broker_info(
    current_user: models.User = Depends(get_current_active_user),
    broker_manager: BrokerManager = Depends(get_broker_manager)
) -> Dict[str, Any]:
    """获取默认券商信息"""
    try:
        broker = await broker_manager.get_default_broker()
        
        if not broker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有可用的券商实例"
            )
        
        account_info = await broker.get_account_info()
        positions = await broker.get_positions()
        
        result = {
            "broker_name": broker.get_broker_name(),
            "is_connected": broker.is_connected,
            "account_info": {
                "account_id": account_info.account_id,
                "cash_balance": account_info.cash_balance,
                "total_value": account_info.total_value,
                "buying_power": account_info.buying_power,
                "currency": account_info.currency
            },
            "positions_count": len(positions),
            "total_position_value": sum(pos.market_value for pos in positions)
        }
        
        # 如果是模拟交易，添加性能信息
        from ..services.brokers.paper_trading import PaperTradingBroker
        if isinstance(broker, PaperTradingBroker):
            result["performance"] = broker.get_performance_summary()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取默认券商信息失败: {str(e)}"
        )


@router.delete("/{broker_id}", dependencies=[Depends(general_rate_limit)])
async def remove_broker(
    broker_id: str,
    current_user: models.User = Depends(get_current_active_user),
    broker_manager: BrokerManager = Depends(get_broker_manager)
) -> Dict[str, Any]:
    """移除券商实例"""
    # 检查权限（只有管理员可以移除券商实例）
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以移除券商实例"
        )
    
    try:
        success = await broker_manager.remove_broker(broker_id)
        
        if success:
            return {
                "success": True,
                "message": f"券商实例已移除: {broker_id}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"券商实例不存在: {broker_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除券商实例失败: {str(e)}"
        )


@router.get("/{broker_id}/account", dependencies=[Depends(general_rate_limit)])
async def get_broker_account_info(
    broker_id: str,
    current_user: models.User = Depends(get_current_active_user),
    broker_manager: BrokerManager = Depends(get_broker_manager)
) -> Dict[str, Any]:
    """获取特定券商的账户信息"""
    try:
        broker = await broker_manager.get_broker(broker_id)
        
        if not broker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"券商实例不存在: {broker_id}"
            )
        
        if not broker.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"券商实例未连接: {broker_id}"
            )
        
        account_info = await broker.get_account_info()
        positions = await broker.get_positions()
        
        return {
            "broker_id": broker_id,
            "broker_name": broker.get_broker_name(),
            "account_info": {
                "account_id": account_info.account_id,
                "cash_balance": account_info.cash_balance,
                "total_value": account_info.total_value,
                "buying_power": account_info.buying_power,
                "maintenance_margin": account_info.maintenance_margin,
                "currency": account_info.currency
            },
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "average_price": pos.average_price,
                    "current_price": pos.current_price,
                    "market_value": pos.market_value,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "unrealized_pnl_percent": pos.unrealized_pnl_percent,
                    "side": pos.side
                }
                for pos in positions
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取账户信息失败: {str(e)}"
        )


@router.get("/{broker_id}/performance", dependencies=[Depends(general_rate_limit)])
async def get_broker_performance(
    broker_id: str,
    current_user: models.User = Depends(get_current_active_user),
    broker_manager: BrokerManager = Depends(get_broker_manager)
) -> Dict[str, Any]:
    """获取券商表现信息（仅限模拟交易）"""
    try:
        broker = await broker_manager.get_broker(broker_id)
        
        if not broker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"券商实例不存在: {broker_id}"
            )
        
        # 检查是否为模拟交易
        from ..services.brokers.paper_trading import PaperTradingBroker
        if not isinstance(broker, PaperTradingBroker):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="性能信息仅适用于模拟交易券商"
            )
        
        performance = broker.get_performance_summary()
        trade_history = broker.get_trade_history(50)  # 最近50笔交易
        
        return {
            "broker_id": broker_id,
            "performance": performance,
            "recent_trades": trade_history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能信息失败: {str(e)}"
        )