"""
示例策略模块，提供一些预定义的交易策略示例
"""

SAMPLE_STRATEGIES = {
    "dual_moving_average": {
        "name": "双均线交叉策略",
        "type": "trend_following",
        "description": "使用短期均线和长期均线的交叉信号来决定买入和卖出的时机。当短期均线向上穿过长期均线时买入，当短期均线向下穿过长期均线时卖出。",
        "parameters": {
            "symbol": "AAPL",
            "short_window": 5,
            "long_window": 20,
            "initial_position": 0,
        },
        "code": """
# 双均线交叉策略
import pandas as pd
import numpy as np

# 获取参数
symbol = parameters.get('symbol', 'AAPL')
short_window = parameters.get('short_window', 5)
long_window = parameters.get('long_window', 20)
initial_position = parameters.get('initial_position', 0)

# 访问市场数据
if symbol in market_data and len(market_data[symbol]) > long_window:
    data = market_data[symbol]
    
    # 计算移动平均线
    if 'short_mavg' not in data.columns:
        data['short_mavg'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
    
    if 'long_mavg' not in data.columns:
        data['long_mavg'] = data['Close'].rolling(window=long_window, min_periods=1).mean()
    
    # 获取当前日期的数据点
    current_idx = data.index[-1]
    current_price = data.loc[current_idx, 'Close']
    
    # 检查均线交叉
    current_short_mavg = data.loc[current_idx, 'short_mavg']
    current_long_mavg = data.loc[current_idx, 'long_mavg']
    
    # 如果有前一天的数据
    if len(data) > 1:
        prev_idx = data.index[-2]
        prev_short_mavg = data.loc[prev_idx, 'short_mavg']
        prev_long_mavg = data.loc[prev_idx, 'long_mavg']
        
        # 检查买入信号：短期均线从下方穿过长期均线
        if prev_short_mavg < prev_long_mavg and current_short_mavg > current_long_mavg:
            # 假设每次交易买入10股
            buy(symbol, 10, current_price)
            print(f"买入信号: {symbol} @ {current_price}")
        
        # 检查卖出信号：短期均线从上方穿过长期均线
        elif prev_short_mavg > prev_long_mavg and current_short_mavg < current_long_mavg:
            # 假设每次交易卖出10股（如果持有）
            sell(symbol, 10, current_price)
            print(f"卖出信号: {symbol} @ {current_price}")
"""
    },
    
    "rsi_strategy": {
        "name": "RSI超买超卖策略",
        "type": "mean_reversion",
        "description": "使用相对强弱指数(RSI)来检测超买和超卖条件。当RSI低于30时买入(超卖)，当RSI高于70时卖出(超买)。",
        "parameters": {
            "symbol": "MSFT",
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
        },
        "code": """
# RSI超买超卖策略
import pandas as pd
import numpy as np

# 获取参数
symbol = parameters.get('symbol', 'MSFT')
rsi_period = parameters.get('rsi_period', 14)
oversold_threshold = parameters.get('oversold_threshold', 30)
overbought_threshold = parameters.get('overbought_threshold', 70)

# 计算RSI的函数
def calculate_rsi(data, period=14):
    # 计算价格变化
    delta = data['Close'].diff()
    
    # 分离上涨和下跌
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    loss = abs(loss)
    
    # 计算平均上涨和下跌
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    
    # 计算相对强度
    rs = avg_gain / avg_loss
    
    # 计算RSI
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 访问市场数据
if symbol in market_data and len(market_data[symbol]) > rsi_period:
    data = market_data[symbol]
    
    # 计算RSI
    if 'RSI' not in data.columns:
        data['RSI'] = calculate_rsi(data, rsi_period)
    
    # 获取当前RSI值
    current_idx = data.index[-1]
    current_price = data.loc[current_idx, 'Close']
    current_rsi = data.loc[current_idx, 'RSI']
    
    # 交易逻辑
    if current_rsi < oversold_threshold:
        # RSI低于超卖阈值，买入信号
        buy(symbol, 10, current_price)
        print(f"超卖信号: {symbol} @ {current_price}, RSI={current_rsi}")
    
    elif current_rsi > overbought_threshold:
        # RSI高于超买阈值，卖出信号
        sell(symbol, 10, current_price)
        print(f"超买信号: {symbol} @ {current_price}, RSI={current_rsi}")
"""
    },
    
    "bollinger_bands_strategy": {
        "name": "布林带策略",
        "type": "mean_reversion",
        "description": "使用布林带指标来识别价格波动。当价格触及下轨时买入，当价格触及上轨时卖出。",
        "parameters": {
            "symbol": "GOOGL",
            "bb_period": 20,
            "bb_std": 2,
        },
        "code": """
# 布林带策略
import pandas as pd
import numpy as np

# 获取参数
symbol = parameters.get('symbol', 'GOOGL')
bb_period = parameters.get('bb_period', 20)
bb_std = parameters.get('bb_std', 2)

# 访问市场数据
if symbol in market_data and len(market_data[symbol]) > bb_period:
    data = market_data[symbol]
    
    # 计算布林带
    if 'SMA' not in data.columns:
        data['SMA'] = data['Close'].rolling(window=bb_period).mean()
        rolling_std = data['Close'].rolling(window=bb_period).std()
        data['UpperBand'] = data['SMA'] + (rolling_std * bb_std)
        data['LowerBand'] = data['SMA'] - (rolling_std * bb_std)
    
    # 获取当前数据
    current_idx = data.index[-1]
    current_price = data.loc[current_idx, 'Close']
    current_upper = data.loc[current_idx, 'UpperBand']
    current_lower = data.loc[current_idx, 'LowerBand']
    
    # 交易逻辑
    if current_price <= current_lower:
        # 价格触及下轨，买入信号
        buy(symbol, 10, current_price)
        print(f"价格触及下轨: {symbol} @ {current_price}")
    
    elif current_price >= current_upper:
        # 价格触及上轨，卖出信号
        sell(symbol, 10, current_price)
        print(f"价格触及上轨: {symbol} @ {current_price}")
"""
    },
    
    "breakout_strategy": {
        "name": "突破策略",
        "type": "breakout",
        "description": "寻找价格突破前期高点或低点的情况。当价格突破前N日最高价时买入，当价格跌破前N日最低价时卖出。",
        "parameters": {
            "symbol": "TSLA",
            "period": 20,
        },
        "code": """
# 突破策略
import pandas as pd
import numpy as np

# 获取参数
symbol = parameters.get('symbol', 'TSLA')
period = parameters.get('period', 20)

# 访问市场数据
if symbol in market_data and len(market_data[symbol]) > period:
    data = market_data[symbol]
    
    # 获取当前数据
    current_idx = data.index[-1]
    current_price = data.loc[current_idx, 'Close']
    
    # 计算前N日的最高价和最低价（不包括当天）
    if len(data) > period + 1:
        price_history = data.iloc[-(period+1):-1]
        highest_high = price_history['High'].max()
        lowest_low = price_history['Low'].min()
        
        # 交易逻辑
        if current_price > highest_high:
            # 价格突破前期高点，买入信号
            buy(symbol, 10, current_price)
            print(f"向上突破: {symbol} @ {current_price}")
        
        elif current_price < lowest_low:
            # 价格跌破前期低点，卖出信号
            sell(symbol, 10, current_price)
            print(f"向下突破: {symbol} @ {current_price}")
"""
    },
    
    "portfolio_rebalance_strategy": {
        "name": "投资组合再平衡策略",
        "type": "custom",
        "description": "定期调整投资组合中各资产的权重，保持目标分配比例。",
        "parameters": {
            "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN"],
            "weights": [0.25, 0.25, 0.25, 0.25],
            "rebalance_days": [1, 15],  # 每月1日和15日再平衡
        },
        "code": """
# 投资组合再平衡策略
import pandas as pd
import numpy as np
from datetime import datetime

# 获取参数
symbols = parameters.get('symbols', ['AAPL', 'MSFT', 'GOOGL', 'AMZN'])
weights = parameters.get('weights', [0.25, 0.25, 0.25, 0.25])
rebalance_days = parameters.get('rebalance_days', [1, 15])

# 检查当前日期是否为再平衡日
current_day = current_date.day
if current_day in rebalance_days:
    print(f"执行投资组合再平衡 - 日期: {current_date.strftime('%Y-%m-%d')}")
    
    # 获取各资产当前价格
    prices = {}
    for symbol in symbols:
        if symbol in market_data and not market_data[symbol].empty:
            current_price = market_data[symbol]['Close'].iloc[-1]
            prices[symbol] = current_price
    
    # 计算目标持仓量
    portfolio_value = 0
    for symbol, weight in zip(symbols, weights):
        if symbol in prices:
            # 为简化计算，我们假设每个资产有10股作为基准
            portfolio_value += prices[symbol] * 10
    
    # 执行再平衡交易
    for i, symbol in enumerate(symbols):
        if symbol in prices:
            target_value = portfolio_value * weights[i]
            target_shares = round(target_value / prices[symbol])
            
            # 假设当前持有10股
            current_shares = 10
            
            # 计算需要调整的股数
            delta_shares = target_shares - current_shares
            
            if delta_shares > 0:
                # 需要买入
                buy(symbol, delta_shares, prices[symbol])
                print(f"再平衡买入: {symbol}, {delta_shares}股 @ {prices[symbol]}")
            elif delta_shares < 0:
                # 需要卖出
                sell(symbol, abs(delta_shares), prices[symbol])
                print(f"再平衡卖出: {symbol}, {abs(delta_shares)}股 @ {prices[symbol]}")
"""
    }
}

def get_sample_strategy(strategy_key):
    """获取指定的示例策略"""
    return SAMPLE_STRATEGIES.get(strategy_key)

def get_all_sample_strategies():
    """获取所有示例策略"""
    return SAMPLE_STRATEGIES 