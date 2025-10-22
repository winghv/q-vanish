"""
AI服务管理器
统一管理所有AI服务，包括API密钥管理、请求限流、成本控制、缓存等
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from decimal import Decimal
from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletion
import asyncio
from collections import defaultdict

from ..config import OPENAI_API_KEY
from .cache import get_cache_service

logger = logging.getLogger(__name__)


class AIServiceManager:
    """AI服务管理器类"""

    def __init__(self):
        """初始化AI服务管理器"""
        self.api_key = OPENAI_API_KEY
        self.client = None
        self.async_client = None
        self.cache_service = None

        # 请求统计
        self.request_counts = defaultdict(int)
        self.token_usage = defaultdict(int)
        self.cost_tracking = defaultdict(float)

        # 限流配置
        self.rate_limits = {
            "requests_per_minute": 60,
            "tokens_per_minute": 90000,
            "max_retries": 3,
            "retry_delay": 1.0
        }

        # 成本配置 (USD per 1K tokens)
        self.pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006}
        }

        # 默认模型
        self.default_model = "gpt-4o-mini"

        # 系统提示词
        self.system_prompts = {
            "default": """你是Q-Vanish量化交易平台的AI助手。你的任务是帮助用户进行市场分析、策略开发和投资决策。

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

记住，所有投资决策最终都应该由用户自己做出，你的建议仅供参考。""",

            "investment_advisor": """你是一位专业的投资顾问AI。基于用户的持仓、风险偏好和市场数据，提供个性化的投资建议。
重点关注：资产配置、风险分散、再平衡策略、税收优化。始终提供多种选择方案，并解释每种方案的优缺点。""",

            "sentiment_analyst": """你是市场情绪分析专家。分析新闻、市场数据和社交媒体情绪，评估市场情绪指标。
提供简洁的情绪评分（0-100）、主要驱动因素和潜在影响。使用数据支持你的分析。""",

            "risk_assessor": """你是风险管理专家。识别投资组合中的潜在风险，包括集中度风险、市场风险、流动性风险等。
提供具体的风险指标、可能的损失场景和建议的缓解措施。""",

            "strategy_expert": """你是量化交易策略专家。基于用户的交易历史和市场条件，推荐合适的交易策略。
评估策略的历史表现、适用市场环境、风险收益特征。提供参数优化建议。"""
        }

    def initialize(self):
        """初始化OpenAI客户端"""
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return False

        try:
            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
            logger.info("OpenAI clients initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI clients: {e}")
            return False

    async def get_cache_service(self):
        """获取缓存服务"""
        if self.cache_service is None:
            self.cache_service = await get_cache_service()
        return self.cache_service

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        functions: Optional[List[Dict]] = None,
        function_call: Optional[str] = None,
        cache_key: Optional[str] = None,
        cache_ttl: int = 300
    ) -> Any:
        """
        通用聊天完成方法

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式响应
            functions: 函数列表（function calling）
            function_call: 函数调用模式
            cache_key: 缓存键
            cache_ttl: 缓存过期时间（秒）
        """
        if not self.async_client:
            self.initialize()

        if not self.async_client:
            raise ValueError("OpenAI client not initialized. Check your API key.")

        model = model or self.default_model

        # 检查缓存
        if cache_key and not stream:
            cache_service = await self.get_cache_service()
            cached_response = await cache_service.get(f"ai_response:{cache_key}")
            if cached_response:
                logger.info(f"Using cached AI response for key: {cache_key}")
                return json.loads(cached_response)

        # 构建请求参数
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if functions:
            params["functions"] = functions
        if function_call:
            params["function_call"] = function_call

        # 执行请求（带重试）
        for attempt in range(self.rate_limits["max_retries"]):
            try:
                response = await self.async_client.chat.completions.create(**params)

                # 记录使用情况
                if not stream and hasattr(response, 'usage'):
                    self._track_usage(model, response.usage)

                # 缓存响应
                if cache_key and not stream:
                    cache_service = await self.get_cache_service()
                    response_dict = response.model_dump() if hasattr(response, 'model_dump') else response.dict()
                    await cache_service.set(
                        f"ai_response:{cache_key}",
                        json.dumps(response_dict),
                        expire=cache_ttl
                    )

                return response

            except Exception as e:
                logger.error(f"AI request attempt {attempt + 1} failed: {e}")
                if attempt < self.rate_limits["max_retries"] - 1:
                    await asyncio.sleep(self.rate_limits["retry_delay"] * (attempt + 1))
                else:
                    raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """流式聊天完成"""
        return await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

    async def simple_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        cache_key: Optional[str] = None
    ) -> str:
        """
        简单提示词方法，返回纯文本响应

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            cache_key: 缓存键
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        elif "default" in self.system_prompts:
            messages.append({"role": "system", "content": self.system_prompts["default"]})

        messages.append({"role": "user", "content": prompt})

        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            cache_key=cache_key
        )

        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content

        return ""

    async def structured_prompt(
        self,
        prompt: str,
        context: Dict[str, Any],
        system_prompt_type: str = "default",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        结构化提示词方法，包含上下文信息

        Args:
            prompt: 基础提示词
            context: 上下文数据（会被格式化注入提示词）
            system_prompt_type: 系统提示词类型
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
        """
        # 格式化上下文
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        full_prompt = f"{prompt}\n\n上下文信息:\n{context_str}"

        system_prompt = self.system_prompts.get(system_prompt_type, self.system_prompts["default"])

        return await self.simple_prompt(
            prompt=full_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

    def _track_usage(self, model: str, usage: Any):
        """跟踪API使用情况和成本"""
        try:
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # 更新token统计
            self.token_usage[model] += total_tokens
            self.request_counts[model] += 1

            # 计算成本
            if model in self.pricing:
                input_cost = (prompt_tokens / 1000) * self.pricing[model]["input"]
                output_cost = (completion_tokens / 1000) * self.pricing[model]["output"]
                total_cost = input_cost + output_cost
                self.cost_tracking[model] += total_cost

                logger.info(
                    f"AI Request: model={model}, tokens={total_tokens} "
                    f"(prompt={prompt_tokens}, completion={completion_tokens}), "
                    f"cost=${total_cost:.6f}"
                )
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "request_counts": dict(self.request_counts),
            "token_usage": dict(self.token_usage),
            "cost_tracking": dict(self.cost_tracking),
            "total_cost": sum(self.cost_tracking.values())
        }

    def reset_usage_stats(self):
        """重置使用统计"""
        self.request_counts.clear()
        self.token_usage.clear()
        self.cost_tracking.clear()
        logger.info("AI usage stats reset")

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self.simple_prompt(
                prompt="Say 'OK' if you're working.",
                max_tokens=10
            )
            return bool(response and len(response) > 0)
        except Exception as e:
            logger.error(f"AI health check failed: {e}")
            return False


# 全局AI服务管理器实例
_ai_service_manager: Optional[AIServiceManager] = None


def get_ai_service_manager() -> AIServiceManager:
    """获取AI服务管理器实例（单例）"""
    global _ai_service_manager
    if _ai_service_manager is None:
        _ai_service_manager = AIServiceManager()
        _ai_service_manager.initialize()
    return _ai_service_manager


async def get_ai_service() -> AIServiceManager:
    """异步获取AI服务管理器实例（用于FastAPI依赖注入）"""
    return get_ai_service_manager()
