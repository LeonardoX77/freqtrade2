from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class AltSeasonRotationStrategy(IStrategy):
    
    # --- CONFIGURACIÓN GENERAL ---
    timeframe = '1h'                      # Se opera en velas de 1 hora
    minimal_roi = {"0": 0.10}            # ROI mínimo de 10%
    stoploss = -0.15                      # Stoploss máximo de 15%
    trailing_stop = True                  # Activar trailing stop
    trailing_stop_positive = 0.05         # Empieza a moverse a partir de 5%
    trailing_stop_positive_offset = 0.08  # Solo activa si ganancia > 8%

    # --- INDICADORES ---
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Media Móvil Exponencial de 20 y 50 periodos
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)

        # Índice de Fuerza Relativa (RSI)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Media móvil de volumen (24h)
        dataframe['vol_mean'] = dataframe['volume'].rolling(window=24).mean()

        return dataframe

    # --- CONDICIÓN DE COMPRA ---
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema20'] > dataframe['ema50']) &             # Tendencia alcista
            (dataframe['rsi'] < 70) &                                # Aún sin sobrecompra
            (dataframe['close'] > dataframe['ema20']) &             # Confirmación de impulso
            (dataframe['volume'] > 1.2 * dataframe['vol_mean']),    # Confirmación de volumen
            'buy'] = 1
        return dataframe

    # --- CONDICIÓN DE VENTA ---
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['rsi'] > 80) |                                # Condición de sobrecompra
            (dataframe['close'] < dataframe['ema20']),              # Ruptura bajista de soporte dinámico
            'sell'] = 1
        return dataframe
