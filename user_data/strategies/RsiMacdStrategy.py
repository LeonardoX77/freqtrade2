import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from technical.indicators import hull_moving_average

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, IntParameter


logger = logging.getLogger(__name__)


class RsiMacdStrategy(IStrategy):
    """
    Estrategia que combina RSI, MACD y Bollinger Bands para generar señales de trading.
    
    Se basa en:
    * RSI para identificar condiciones de sobrecompra/sobreventa
    * MACD para confirmación de tendencia
    * Bollinger Bands como filtro adicional
    """

    # Parámetros de estrategia
    INTERFACE_VERSION = 3

    # Parámetros para optimización (hyperopt)
    buy_rsi = IntParameter(10, 40, default=30, space="buy")
    sell_rsi = IntParameter(60, 90, default=70, space="sell")
    
    # Parámetros ROI - gestión de beneficios
    minimal_roi = {
        "0": 0.05,     # 5% de beneficio mínimo
        "30": 0.025,   # 2.5% después de 30 minutos
        "60": 0.015,   # 1.5% después de 1 hora
        "120": 0.01    # 1% después de 2 horas
    }

    # Stoploss - protección contra pérdidas
    stoploss = -0.1  # -10% stoploss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01  # 1%
    trailing_stop_positive_offset = 0.02  # 2%
    trailing_only_offset_is_reached = True

    # Configuración general
    timeframe = "5m"  # Timeframe de 5 minutos
    informative_timeframes = {
        "1h": ["*"],
        "1d": ["*"],
        "1M": ["*"]
    }
    process_only_new_candles = True
    startup_candle_count = 30  # Número de velas necesarias para iniciar
    use_exit_signal = True

    # Configuración de órdenes
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata.get('pair', 'N/A')
        logger.info(f"[{pair}] Calculando indicadores para nuevo dataframe ({len(dataframe)} velas)...")
        # --- Indicadores en 5m ---
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        macd_5m = ta.MACD(dataframe)
        dataframe["macd"] = macd_5m["macd"]
        dataframe["macdsignal"] = macd_5m["macdsignal"]
        dataframe["macdhist"] = macd_5m["macdhist"]
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe["bb_upperband"] = bollinger["upperband"]
        dataframe["bb_midband"] = bollinger["middleband"]
        dataframe["bb_lowerband"] = bollinger["lowerband"]
        dataframe["hma"] = hull_moving_average(dataframe, 14)

        # --- Multi-timeframe: 1h, 1d, 1M ---
        for tf in ["1h", "1d", "1M"]:
            try:
                inf_df = self.dp.get_pair_dataframe(pair=pair, timeframe=tf)
                dataframe[f"rsi_{tf}"] = inf_df["rsi"] if "rsi" in inf_df else ta.RSI(inf_df, timeperiod=14)
                macd_inf = ta.MACD(inf_df)
                dataframe[f"macd_{tf}"] = macd_inf["macd"]
                dataframe[f"macdsignal_{tf}"] = macd_inf["macdsignal"]
                dataframe[f"macdhist_{tf}"] = macd_inf["macdhist"]
                # Sincronizar con el índice del dataframe principal
                dataframe[f"rsi_{tf}"] = dataframe[f"rsi_{tf}"].reindex(dataframe.index, method="ffill")
                dataframe[f"macd_{tf}"] = dataframe[f"macd_{tf}"].reindex(dataframe.index, method="ffill")
                dataframe[f"macdsignal_{tf}"] = dataframe[f"macdsignal_{tf}"].reindex(dataframe.index, method="ffill")
                dataframe[f"macdhist_{tf}"] = dataframe[f"macdhist_{tf}"].reindex(dataframe.index, method="ffill")
                logger.info(f"[{pair}] Última vela {tf}: RSI={dataframe[f'rsi_{tf}'].iloc[-1]:.2f}, MACD={dataframe[f'macd_{tf}'].iloc[-1]:.4f}, MACDHIST={dataframe[f'macdhist_{tf}'].iloc[-1]:.4f}")
            except Exception as e:
                logger.warning(f"[{pair}] No se pudo calcular indicadores para timeframe {tf}: {e}")

        # Mostrar los últimos 6 intervalos de 5m (última media hora)
        ultimos_30min = dataframe.tail(6)
        logger.info(f"[{pair}] Últimos 30min (6 velas):\n{ultimos_30min[['date','close','rsi','macd','macdhist']].to_string(index=False)}")
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define las condiciones de entrada."""
        pair = metadata.get('pair', 'N/A')
        logger.info(f"[{pair}] Analizando condiciones de entrada...")
        signals = (
            (dataframe["rsi"] < self.buy_rsi.value) &
            (dataframe["macdhist"] > 0) &
            (dataframe["macdhist"].shift(1) < 0) &
            (dataframe["close"] <= dataframe["bb_lowerband"]) &
            (dataframe["hma"] > dataframe["hma"].shift(1)) &
            (dataframe["volume"] > 0)
        )
        n_signals = signals.sum()
        if n_signals > 0:
            logger.info(f"[{pair}] Señales de COMPRA detectadas: {n_signals}")
        dataframe.loc[signals, ["enter_long", "enter_tag"]] = (1, "buy_signal")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define las condiciones de salida."""
        pair = metadata.get('pair', 'N/A')
        logger.info(f"[{pair}] Analizando condiciones de salida...")
        signals = (
            (dataframe["rsi"] > self.sell_rsi.value) &
            (dataframe["macdhist"] < 0) &
            (dataframe["macdhist"].shift(1) > 0) &
            (dataframe["close"] >= dataframe["bb_upperband"]) &
            (dataframe["hma"] < dataframe["hma"].shift(1)) &
            (dataframe["volume"] > 0)
        )
        n_signals = signals.sum()
        if n_signals > 0:
            logger.info(f"[{pair}] Señales de VENTA detectadas: {n_signals}")
        dataframe.loc[signals, ["exit_long", "exit_tag"]] = (1, "sell_signal")
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                          time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                          side: str, **kwargs) -> bool:
        logger.info(f"[{pair}] Confirmando entrada: side={side}, rate={rate}, entry_tag={entry_tag}")
        # Obtener los datos del par
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        # Verificar si el precio de entrada es razonable
        if side == "long":
            # Para compras, asegurarse que el precio no está muy alejado de la banda media
            if rate > last_candle["bb_midband"] * 1.02:  # Max 2% sobre la banda media
                return False
        
        return True

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                         rate: float, time_in_force: str, exit_reason: str,
                         current_time: datetime, **kwargs) -> bool:
        logger.info(f"[{pair}] Confirmando salida: exit_reason={exit_reason}, rate={rate}")
        # Obtener los datos del par
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        # Si la tendencia sigue siendo fuertemente alcista, mantener la posición
        if (last_candle["rsi"] < 65 and  # RSI aún no en sobrecompra extrema
            last_candle["macd"] > last_candle["macdsignal"] and  # MACD alcista
            last_candle["close"] < last_candle["bb_upperband"]):  # Precio bajo banda superior
            return False
            
        return True
