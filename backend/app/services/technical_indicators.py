"""
技术指标计算库
提供常用的技术分析指标计算功能
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional


class TechnicalIndicators:
    """技术指标计算工具类"""

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """
        简单移动平均线 (Simple Moving Average)

        Args:
            data: 价格数据序列
            period: 周期

        Returns:
            SMA序列
        """
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """
        指数移动平均线 (Exponential Moving Average)

        Args:
            data: 价格数据序列
            period: 周期

        Returns:
            EMA序列
        """
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        相对强弱指标 (Relative Strength Index)

        Args:
            data: 价格数据序列
            period: 周期，默认14

        Returns:
            RSI序列 (0-100)
        """
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def macd(
        data: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD指标 (Moving Average Convergence Divergence)

        Args:
            data: 价格数据序列
            fast_period: 快速EMA周期，默认12
            slow_period: 慢速EMA周期，默认26
            signal_period: 信号线周期，默认9

        Returns:
            (MACD线, 信号线, MACD柱)
        """
        ema_fast = TechnicalIndicators.ema(data, fast_period)
        ema_slow = TechnicalIndicators.ema(data, slow_period)

        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)
        macd_histogram = macd_line - signal_line

        return macd_line, signal_line, macd_histogram

    @staticmethod
    def bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        布林带 (Bollinger Bands)

        Args:
            data: 价格数据序列
            period: 周期，默认20
            std_dev: 标准差倍数，默认2.0

        Returns:
            (上轨, 中轨, 下轨)
        """
        middle_band = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()

        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)

        return upper_band, middle_band, lower_band

    @staticmethod
    def stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        随机指标 (Stochastic Oscillator)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            k_period: K线周期，默认14
            d_period: D线周期，默认3

        Returns:
            (%K线, %D线)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d_line = k_line.rolling(window=d_period).mean()

        return k_line, d_line

    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        平均真实波幅 (Average True Range)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期，默认14

        Returns:
            ATR序列
        """
        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    @staticmethod
    def adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        平均趋向指标 (Average Directional Index)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期，默认14

        Returns:
            ADX序列
        """
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = TechnicalIndicators.atr(high, low, close, 1)

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        能量潮指标 (On Balance Volume)

        Args:
            close: 收盘价序列
            volume: 成交量序列

        Returns:
            OBV序列
        """
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]

        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]

        return obv

    @staticmethod
    def cci(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        顺势指标 (Commodity Channel Index)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期，默认20

        Returns:
            CCI序列
        """
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
        )

        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)

        return cci

    @staticmethod
    def williams_r(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        威廉指标 (Williams %R)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期，默认14

        Returns:
            Williams %R序列 (-100 到 0)
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)

        return williams_r

    @staticmethod
    def vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        成交量加权平均价 (Volume Weighted Average Price)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            volume: 成交量序列

        Returns:
            VWAP序列
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()

        return vwap

    @staticmethod
    def pivot_points(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> dict:
        """
        枢轴点 (Pivot Points)

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列

        Returns:
            包含P, R1, R2, R3, S1, S2, S3的字典
        """
        pivot = (high + low + close) / 3

        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)

        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)

        return {
            'P': pivot,
            'R1': r1,
            'R2': r2,
            'R3': r3,
            'S1': s1,
            'S2': s2,
            'S3': s3
        }

    @staticmethod
    def ichimoku_cloud(
        high: pd.Series,
        low: pd.Series,
        conversion_period: int = 9,
        base_period: int = 26,
        span_b_period: int = 52,
        displacement: int = 26
    ) -> dict:
        """
        一目均衡表 (Ichimoku Cloud)

        Args:
            high: 最高价序列
            low: 最低价序列
            conversion_period: 转换线周期，默认9
            base_period: 基准线周期，默认26
            span_b_period: 先行带B周期，默认52
            displacement: 位移，默认26

        Returns:
            包含转换线、基准线、先行带A、先行带B、延迟线的字典
        """
        # 转换线 (Tenkan-sen)
        conversion_line = (
            high.rolling(window=conversion_period).max() +
            low.rolling(window=conversion_period).min()
        ) / 2

        # 基准线 (Kijun-sen)
        base_line = (
            high.rolling(window=base_period).max() +
            low.rolling(window=base_period).min()
        ) / 2

        # 先行带A (Senkou Span A)
        span_a = ((conversion_line + base_line) / 2).shift(displacement)

        # 先行带B (Senkou Span B)
        span_b = (
            (high.rolling(window=span_b_period).max() +
             low.rolling(window=span_b_period).min()) / 2
        ).shift(displacement)

        # 延迟线 (Chikou Span)
        lagging_span = low.shift(-displacement)

        return {
            'conversion_line': conversion_line,
            'base_line': base_line,
            'span_a': span_a,
            'span_b': span_b,
            'lagging_span': lagging_span
        }
