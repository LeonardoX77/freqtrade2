# Estrategia diseñada para aprovechar tendencias alcistas en altcoins durante ciclos de expansión cripto (bull runs).
# Utiliza cruces de medias móviles y RSI para confirmar entradas, con trailing stop para capturar ganancias extendidas.
# Añade un filtro dinámico basado en volumen para operar únicamente cuando hay liquidez significativa.

import ccxt
import pandas as pd
from datetime import datetime, timedelta


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


    # --- CATEGORÍAS MANUALES DE TOKENS ---
    CATEGORIAS = {
        'layer1': ['SOL/USDT', 'AVAX/USDT', 'ADA/USDT'],
        'defi': ['UNI/USDT', 'AAVE/USDT', 'COMP/USDT'],
        'ai': ['FET/USDT', 'AGIX/USDT', 'OCEAN/USDT']
    }


# Script para rotar grupos de pares según rendimiento semanal
# Este script evalúa rendimiento semanal y selecciona sectores calientes

    # --- PARÁMETROS ---
    THRESHOLD_TOP = 0.15   # % mínimo semanal para activar grupo
    EXCHANGE = ccxt.binance()

    # --- OBTIENE RENDIMIENTO SEMANAL DE UN PAR ---
    def get_weekly_performance(symbol):
        try:
            ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe='1d', limit=7)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            perf = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
            return perf
        except:
            return None

    # --- FILTRA CATEGORÍAS ACTIVAS ---
    def detectar_grupos_activos():
        activos = {}
        for sector, pares in CATEGORIAS.items():
            rendimientos = [get_weekly_performance(par) for par in pares]
            rendimientos = [r for r in rendimientos if r is not None]
            if rendimientos:
                promedio = sum(rendimientos) / len(rendimientos)
                if promedio > THRESHOLD_TOP:
                    activos[sector] = promedio
        return activos

    # --- EJECUCIÓN ---
    if __name__ == '__main__':
        activos = detectar_grupos_activos()
        if activos:
            print("Grupos calientes:")
            for sector, score in activos.items():
                print(f" - {sector.upper()}: {score*100:.2f}%")
        else:
            print("Ningún grupo supera el umbral.")


