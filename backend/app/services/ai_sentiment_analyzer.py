"""
AI市场情绪分析服务
分析市场情绪、新闻情绪和社交媒体趋势
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import yfinance as yf

from .. import models, crud
from .ai_service_manager import get_ai_service_manager
from .market_data import get_market_service

logger = logging.getLogger(__name__)


class AISentimentAnalyzer:
    """AI市场情绪分析类"""

    def __init__(self):
        self.ai_manager = get_ai_service_manager()
        self.market_service = None

    async def _get_market_service(self):
        """获取市场数据服务"""
        if self.market_service is None:
            self.market_service = await get_market_service()
        return self.market_service

    async def analyze_market_sentiment(
        self,
        symbols: Optional[List[str]] = None,
        include_news: bool = True
    ) -> Dict[str, Any]:
        """
        分析市场整体情绪

        Args:
            symbols: 要分析的股票列表，None表示分析大盘
            include_news: 是否包含新闻情绪分析
        """
        try:
            market_service = await self._get_market_service()

            # 默认分析主要指数
            if not symbols:
                symbols = ['SPY', 'QQQ', 'DIA']  # S&P 500, NASDAQ, Dow Jones

            # 获取市场数据
            prices = await market_service.get_multiple_prices(symbols)

            # 获取历史数据分析趋势
            market_data_summary = {}
            for symbol in symbols:
                hist = await market_service.get_historical_data(symbol, period="1mo", interval="1d")
                if hist is not None and not hist.empty:
                    recent_close = hist['Close'].iloc[-1]
                    month_ago_close = hist['Close'].iloc[0]
                    change_pct = ((recent_close - month_ago_close) / month_ago_close * 100)

                    # 简单的波动率计算
                    returns = hist['Close'].pct_change().dropna()
                    volatility = returns.std() * (252 ** 0.5) * 100  # 年化波动率

                    market_data_summary[symbol] = {
                        "current_price": float(recent_close),
                        "month_change_pct": round(change_pct, 2),
                        "volatility": round(volatility, 2),
                        "trend": "上涨" if change_pct > 0 else "下跌"
                    }

            # 获取新闻（如果需要）
            news_summary = ""
            if include_news:
                news_summary = await self._fetch_market_news(symbols)

            # 构建分析提示词
            prompt = f"""请分析当前市场情绪：

市场数据摘要：
"""
            for symbol, data in market_data_summary.items():
                prompt += f"""
{symbol}:
- 当前价格: ${data['current_price']:.2f}
- 月度涨跌: {data['month_change_pct']:.2f}%
- 波动率: {data['volatility']:.2f}% (年化)
- 趋势: {data['trend']}
"""

            if news_summary:
                prompt += f"\n最近市场新闻:\n{news_summary}\n"

            prompt += """
请提供：
1. **整体情绪评分**: 0-100分，0表示极度恐慌，100表示极度贪婪，50表示中性
2. **主要驱动因素**: 影响当前情绪的3-5个关键因素
3. **行业板块情绪**: 哪些板块强势，哪些板块弱势
4. **短期展望**: 未来1-2周的市场情绪预期
5. **风险提示**: 需要注意的潜在风险

使用markdown格式，简洁专业。每个部分都要有具体的数据支持。
"""

            analysis = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["sentiment_analyst"],
                temperature=0.7,
                max_tokens=2000,
                cache_key=f"market_sentiment_{datetime.utcnow().strftime('%Y%m%d%H')}"  # 按小时缓存
            )

            # 尝试从分析中提取情绪评分
            sentiment_score = self._extract_sentiment_score(analysis)

            return {
                "success": True,
                "analysis": analysis,
                "sentiment_score": sentiment_score,
                "market_data": market_data_summary,
                "symbols_analyzed": symbols,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error analyzing market sentiment: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_symbol_sentiment(
        self,
        symbol: str,
        include_news: bool = True
    ) -> Dict[str, Any]:
        """
        分析单个股票的情绪

        Args:
            symbol: 股票代码
            include_news: 是否包含新闻分析
        """
        try:
            market_service = await self._get_market_service()

            # 获取股票信息
            stock_info = await market_service.get_stock_info(symbol)
            if not stock_info:
                return {
                    "success": False,
                    "error": f"Unable to fetch info for {symbol}"
                }

            # 获取历史数据
            hist = await market_service.get_historical_data(symbol, period="3mo", interval="1d")
            if hist is None or hist.empty:
                return {
                    "success": False,
                    "error": f"No historical data for {symbol}"
                }

            # 计算技术指标
            recent_close = hist['Close'].iloc[-1]
            week_ago_close = hist['Close'].iloc[-5] if len(hist) >= 5 else hist['Close'].iloc[0]
            month_ago_close = hist['Close'].iloc[-20] if len(hist) >= 20 else hist['Close'].iloc[0]

            week_change = ((recent_close - week_ago_close) / week_ago_close * 100)
            month_change = ((recent_close - month_ago_close) / month_ago_close * 100)

            # 简单的移动平均线
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['MA50'] = hist['Close'].rolling(window=50).mean()

            ma20 = hist['MA20'].iloc[-1] if len(hist) >= 20 else None
            ma50 = hist['MA50'].iloc[-1] if len(hist) >= 50 else None

            # 获取新闻
            news_summary = ""
            if include_news:
                try:
                    ticker = yf.Ticker(symbol)
                    news = ticker.news[:5]  # 最近5条新闻
                    if news:
                        news_summary = "最近新闻:\n"
                        for item in news:
                            news_summary += f"- {item.get('title', 'N/A')}\n"
                except Exception as e:
                    logger.warning(f"Unable to fetch news for {symbol}: {e}")

            # 构建提示词
            prompt = f"""请分析 {symbol} ({stock_info['name']}) 的市场情绪：

基本信息:
- 行业: {stock_info.get('industry', 'N/A')}
- 板块: {stock_info.get('sector', 'N/A')}
- 市值: ${stock_info.get('market_cap', 0):,.0f}
- 当前价格: ${recent_close:.2f}

技术指标:
- 周度涨跌: {week_change:.2f}%
- 月度涨跌: {month_change:.2f}%
"""

            if ma20:
                prompt += f"- 20日均线: ${ma20:.2f} ({'上方' if recent_close > ma20 else '下方'})\n"
            if ma50:
                prompt += f"- 50日均线: ${ma50:.2f} ({'上方' if recent_close > ma50 else '下方'})\n"

            if news_summary:
                prompt += f"\n{news_summary}"

            prompt += """
请提供：
1. **情绪评分**: 0-100分，评估市场对这只股票的情绪
2. **情绪驱动因素**: 影响情绪的主要因素（基本面、技术面、新闻等）
3. **强度评级**: 看涨强度或看跌强度（强/中/弱）
4. **关注要点**: 投资者应该关注的关键指标或事件
5. **短期预期**: 未来1-2周的情绪走向预测

简洁专业，使用markdown格式。
"""

            analysis = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["sentiment_analyst"],
                temperature=0.7,
                max_tokens=1500,
                cache_key=f"sentiment_{symbol}_{datetime.utcnow().strftime('%Y%m%d')}"  # 按天缓存
            )

            sentiment_score = self._extract_sentiment_score(analysis)

            return {
                "success": True,
                "symbol": symbol,
                "name": stock_info['name'],
                "analysis": analysis,
                "sentiment_score": sentiment_score,
                "price_data": {
                    "current": float(recent_close),
                    "week_change": round(week_change, 2),
                    "month_change": round(month_change, 2)
                },
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_sector_sentiment(self) -> Dict[str, Any]:
        """获取行业板块情绪分析"""
        try:
            # 主要行业ETF代表
            sector_etfs = {
                "Technology": "XLK",
                "Financial": "XLF",
                "Healthcare": "XLV",
                "Energy": "XLE",
                "Consumer": "XLY",
                "Industrial": "XLI",
                "Real Estate": "XLRE",
                "Utilities": "XLU",
                "Materials": "XLB",
                "Communication": "XLC"
            }

            market_service = await self._get_market_service()
            sector_data = {}

            for sector, etf_symbol in sector_etfs.items():
                try:
                    hist = await market_service.get_historical_data(etf_symbol, period="1mo", interval="1d")
                    if hist is not None and not hist.empty:
                        recent_close = hist['Close'].iloc[-1]
                        month_ago_close = hist['Close'].iloc[0]
                        change_pct = ((recent_close - month_ago_close) / month_ago_close * 100)

                        sector_data[sector] = {
                            "symbol": etf_symbol,
                            "change_pct": round(change_pct, 2),
                            "trend": "强势" if change_pct > 3 else "平稳" if change_pct > -3 else "弱势"
                        }
                except Exception as e:
                    logger.warning(f"Error fetching data for {sector} ({etf_symbol}): {e}")

            # 排序
            sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1]['change_pct'], reverse=True)

            # 生成分析
            prompt = f"""请分析当前各行业板块的相对强弱和情绪：

月度表现排名:
"""
            for i, (sector, data) in enumerate(sorted_sectors, 1):
                prompt += f"{i}. {sector} ({data['symbol']}): {data['change_pct']:+.2f}% - {data['trend']}\n"

            prompt += """
请提供：
1. **强势板块分析**: 表现最好的3个板块及原因
2. **弱势板块分析**: 表现最差的3个板块及原因
3. **板块轮动观察**: 资金流向和板块轮动趋势
4. **投资建议**: 基于板块情绪的配置建议

简洁明了，使用markdown格式。
"""

            analysis = await self.ai_manager.simple_prompt(
                prompt=prompt,
                system_prompt=self.ai_manager.system_prompts["sentiment_analyst"],
                temperature=0.7,
                max_tokens=1500,
                cache_key=f"sector_sentiment_{datetime.utcnow().strftime('%Y%m%d')}"
            )

            return {
                "success": True,
                "analysis": analysis,
                "sector_rankings": [
                    {
                        "sector": sector,
                        "symbol": data["symbol"],
                        "change_pct": data["change_pct"],
                        "trend": data["trend"]
                    }
                    for sector, data in sorted_sectors
                ],
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error analyzing sector sentiment: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _fetch_market_news(self, symbols: List[str]) -> str:
        """获取市场新闻摘要"""
        try:
            news_items = []
            for symbol in symbols[:2]:  # 只取前2个symbol的新闻
                try:
                    ticker = yf.Ticker(symbol)
                    news = ticker.news[:3]  # 每个symbol取3条新闻
                    for item in news:
                        title = item.get('title', '')
                        if title:
                            news_items.append(f"- {title}")
                except:
                    continue

            return "\n".join(news_items) if news_items else "暂无相关新闻"

        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return "暂无相关新闻"

    def _extract_sentiment_score(self, analysis: str) -> Optional[int]:
        """从分析文本中提取情绪评分"""
        try:
            # 简单的正则匹配尝试提取0-100的数字
            import re
            patterns = [
                r'情绪评分.*?(\d{1,3})\s*分',
                r'评分.*?(\d{1,3})',
                r'得分.*?(\d{1,3})',
                r'(\d{1,3})\s*/\s*100'
            ]

            for pattern in patterns:
                match = re.search(pattern, analysis)
                if match:
                    score = int(match.group(1))
                    if 0 <= score <= 100:
                        return score

            # 如果没有明确分数，尝试通过关键词推断
            if any(word in analysis for word in ['极度贪婪', '非常乐观', '强烈看涨']):
                return 80
            elif any(word in analysis for word in ['贪婪', '乐观', '看涨']):
                return 65
            elif any(word in analysis for word in ['中性', '平衡', '观望']):
                return 50
            elif any(word in analysis for word in ['谨慎', '担忧', '看跌']):
                return 35
            elif any(word in analysis for word in ['恐慌', '极度悲观', '强烈看跌']):
                return 20

            # 默认中性
            return 50

        except Exception as e:
            logger.error(f"Error extracting sentiment score: {e}")
            return None


# 全局实例
_sentiment_analyzer: Optional[AISentimentAnalyzer] = None


def get_sentiment_analyzer() -> AISentimentAnalyzer:
    """获取情绪分析器实例"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = AISentimentAnalyzer()
    return _sentiment_analyzer
