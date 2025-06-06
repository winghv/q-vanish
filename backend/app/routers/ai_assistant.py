from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import openai
import os
from datetime import datetime
import json

from .. import crud, models, schemas
from ..database import get_db
from .auth import get_current_active_user

router = APIRouter()

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key")
openai.api_key = OPENAI_API_KEY

# 默认的AI模型
DEFAULT_MODEL = "gpt-3.5-turbo"

# 定义AI助手系统提示
SYSTEM_PROMPT = """你是一个专业的量化交易助手，你的任务是帮助用户进行市场分析、策略开发和投资决策。
你应该：
1. 提供客观、基于数据的建议
2. 解释交易概念和策略逻辑
3. 帮助用户优化交易策略
4. 分析市场趋势和潜在风险
5. 介绍量化交易的最佳实践

你不应该：
1. 提供确定性的投资建议（如"一定买入XX股票"）
2. 做出保证收益的承诺
3. 忽视风险管理的重要性
4. 提供违反法律法规的建议

记住，所有投资决策最终都应该由用户自己做出，你的建议仅供参考。
"""

@router.post("/chat", response_model=schemas.ChatResponse)
async def chat_with_ai(
    chat_message: schemas.ChatMessage,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 准备对话历史
    context = chat_message.context or {}
    messages = context.get("messages", [])
    
    # 如果是新对话，添加系统提示
    if not messages:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    
    # 添加用户消息
    messages.append({"role": "user", "content": chat_message.message})
    
    try:
        # 调用OpenAI API
        response = openai.ChatCompletion.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        
        # 提取AI回复
        ai_message = response.choices[0].message["content"]
        
        # 更新对话历史
        messages.append({"role": "assistant", "content": ai_message})
        
        # 将历史限制为最近10条消息，以控制上下文长度
        if len(messages) > 12:  # 系统提示 + 最多10轮对话
            messages = [messages[0]] + messages[-10:]
        
        # 更新上下文
        updated_context = {"messages": messages}
        
        # 保存对话记录到数据库
        crud.create_ai_chat(
            db=db,
            user_id=current_user.id,
            message=chat_message.message,
            response=ai_message,
            context=updated_context
        )
        
        return {
            "response": ai_message,
            "context": updated_context
        }
    
    except Exception as e:
        # 处理API调用错误
        error_message = f"AI服务错误: {str(e)}"
        
        # 记录错误但仍返回一个应急响应
        fallback_message = "抱歉，AI服务暂时无法使用。请稍后再试。"
        
        # 记录错误到数据库
        crud.create_ai_chat(
            db=db,
            user_id=current_user.id,
            message=chat_message.message,
            response=fallback_message,
            context={"error": error_message}
        )
        
        return {
            "response": fallback_message,
            "context": context
        }

@router.post("/analyze-strategy", response_model=schemas.ChatResponse)
async def analyze_strategy(
    strategy_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 获取策略信息
    strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 检查访问权限
    if strategy.owner_id != current_user.id and not strategy.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有足够的权限访问此策略"
        )
    
    # 准备策略分析提示
    prompt = f"""
    请分析以下量化交易策略并提供优化建议：
    
    策略名称: {strategy.name}
    策略类型: {strategy.type}
    策略描述: {strategy.description}
    
    策略参数:
    {json.dumps(strategy.parameters, indent=2, ensure_ascii=False) if strategy.parameters else "无参数"}
    
    策略代码:
    ```python
    {strategy.code}
    ```
    
    请分析以下几个方面：
    1. 策略逻辑是否合理
    2. 潜在的风险和弱点
    3. 性能优化建议
    4. 参数调整建议
    5. 可能的改进方向
    """
    
    try:
        # 调用OpenAI API
        response = openai.ChatCompletion.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        
        # 提取AI回复
        analysis = response.choices[0].message["content"]
        
        # 保存分析记录到数据库
        crud.create_ai_chat(
            db=db,
            user_id=current_user.id,
            message=f"分析策略: {strategy.name}",
            response=analysis,
            context={"strategy_id": strategy_id}
        )
        
        return {
            "response": analysis,
            "context": {"strategy_id": strategy_id}
        }
    
    except Exception as e:
        # 处理API调用错误
        error_message = f"AI服务错误: {str(e)}"
        fallback_message = "抱歉，无法完成策略分析。请稍后再试。"
        
        return {
            "response": fallback_message,
            "context": {"error": error_message}
        }

@router.post("/market-analysis", response_model=schemas.ChatResponse)
async def market_analysis(
    symbols: List[str],
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 将股票代码转换为逗号分隔的字符串
    symbols_str = ", ".join(symbols)
    
    # 准备市场分析提示
    prompt = f"""
    请对以下股票进行市场分析，包括技术面和基本面分析：
    
    股票代码: {symbols_str}
    
    请提供以下分析：
    1. 当前市场趋势分析
    2. 每只股票的技术指标分析（如均线、RSI、MACD等）
    3. 潜在的支撑位和阻力位
    4. 交易量分析
    5. 相关的市场新闻和事件影响
    6. 简要的交易建议（买入/卖出/持有）及风险提示
    """
    
    try:
        # 调用OpenAI API
        response = openai.ChatCompletion.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        
        # 提取AI回复
        analysis = response.choices[0].message["content"]
        
        # 保存分析记录到数据库
        crud.create_ai_chat(
            db=db,
            user_id=current_user.id,
            message=f"市场分析: {symbols_str}",
            response=analysis,
            context={"symbols": symbols}
        )
        
        return {
            "response": analysis,
            "context": {"symbols": symbols}
        }
    
    except Exception as e:
        # 处理API调用错误
        error_message = f"AI服务错误: {str(e)}"
        fallback_message = "抱歉，无法完成市场分析。请稍后再试。"
        
        return {
            "response": fallback_message,
            "context": {"error": error_message}
        } 