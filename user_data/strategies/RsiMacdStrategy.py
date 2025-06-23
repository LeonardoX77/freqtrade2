import logging
import subprocess
from datetime import datetime

import talib.abstract as ta
from pandas import DataFrame
from technical.indicators import hull_moving_average

from freqtrade.persistence import Trade
from freqtrade.strategy import IntParameter, IStrategy


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
        "0": 0.05,  # 5% de beneficio mínimo
        "30": 0.025,  # 2.5% después de 30 minutos
        "60": 0.015,  # 1.5% después de 1 hora
        "120": 0.01,  # 1% después de 2 horas
    }

    # Stoploss - protección contra pérdidas
    stoploss = -0.1  # -10% stoploss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01  # 1%
    trailing_stop_positive_offset = 0.02  # 2%
    trailing_only_offset_is_reached = True

    # Configuración general
    timeframe = "1m"  # Timeframe principal de 1 minuto
    informative_timeframes = {"5m": ["*"], "1h": ["*"], "1d": ["*"]}
    process_only_new_candles = True
    startup_candle_count = 30  # Número de velas necesarias para iniciar
    use_exit_signal = True

    # Configuración de órdenes
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata.get("pair", "N/A")
        logger.info(
            f"[{pair}] Calculando indicadores para nuevo dataframe ({len(dataframe)} velas)..."
        )
        # --- Indicadores en 1m ---
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        macd_1m = ta.MACD(dataframe)
        dataframe["macd"] = macd_1m["macd"]
        dataframe["macdsignal"] = macd_1m["macdsignal"]
        dataframe["macdhist"] = macd_1m["macdhist"]
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe["bb_upperband"] = bollinger["upperband"]
        dataframe["bb_midband"] = bollinger["middleband"]
        dataframe["bb_lowerband"] = bollinger["lowerband"]
        dataframe["hma"] = hull_moving_average(dataframe, 14)

        # --- Multi-timeframe: 5m, 1h y 1d ---
        for tf in ["5m", "1h", "1d"]:
            try:
                inf_df = self.dp.get_pair_dataframe(pair=pair, timeframe=tf)
                dataframe[f"rsi_{tf}"] = (
                    inf_df["rsi"] if "rsi" in inf_df else ta.RSI(inf_df, timeperiod=14)
                )
                macd_inf = ta.MACD(inf_df)
                dataframe[f"macd_{tf}"] = macd_inf["macd"]
                dataframe[f"macdsignal_{tf}"] = macd_inf["macdsignal"]
                dataframe[f"macdhist_{tf}"] = macd_inf["macdhist"]
                # Sincronizar con el índice del dataframe principal
                dataframe[f"rsi_{tf}"] = dataframe[f"rsi_{tf}"].reindex(
                    dataframe.index, method="ffill"
                )
                dataframe[f"macd_{tf}"] = dataframe[f"macd_{tf}"].reindex(
                    dataframe.index, method="ffill"
                )
                dataframe[f"macdsignal_{tf}"] = dataframe[f"macdsignal_{tf}"].reindex(
                    dataframe.index, method="ffill"
                )
                dataframe[f"macdhist_{tf}"] = dataframe[f"macdhist_{tf}"].reindex(
                    dataframe.index, method="ffill"
                )
                last_rsi = dataframe[f"rsi_{tf}"].iloc[-1]
                last_macd = dataframe[f"macd_{tf}"].iloc[-1]
                last_hist = dataframe[f"macdhist_{tf}"].iloc[-1]
                logger.info(
                    f"[{pair}] Última vela {tf}: "
                    f"RSI={last_rsi:.2f}, MACD={last_macd:.4f}, "
                    f"MACDHIST={last_hist:.4f}"
                )
            except Exception as e:
                logger.warning(f"[{pair}] No se pudo calcular indicadores para timeframe {tf}: {e}")

        # Mostrar los últimos 30 intervalos de 1m (última media hora)
        ultimos_30min = dataframe.tail(30)
        resumen = ultimos_30min[["date", "close", "rsi", "macd", "macdhist"]].to_string(index=False)
        logger.info(f"[{pair}] Últimos 30min (30 velas):\n{resumen}")
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define las condiciones de entrada."""
        pair = metadata.get("pair", "N/A")
        logger.info(f"[{pair}] Analizando condiciones de entrada...")
        signals = (
            (dataframe["rsi"] < self.buy_rsi.value)
            & (dataframe["macdhist"] > 0)
            & (dataframe["macdhist"].shift(1) < 0)
            & (dataframe["close"] <= dataframe["bb_lowerband"])
            & (dataframe["hma"] > dataframe["hma"].shift(1))
            & (dataframe["volume"] > 0)
        )
        n_signals = signals.sum()
        if n_signals > 0:
            logger.info(f"[{pair}] Señales de COMPRA detectadas: {n_signals}")
        dataframe.loc[signals, ["enter_long", "enter_tag"]] = (1, "buy_signal")

        llm_signal = self._get_llm_signal(pair, dataframe)
        last_idx = dataframe.index[-1]
        if llm_signal == "BUY":
            dataframe.loc[last_idx, ["enter_long", "enter_tag"]] = (1, "llm_buy")
        elif llm_signal == "SELL":
            dataframe.loc[last_idx, ["exit_long", "exit_tag"]] = (1, "llm_sell")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define las condiciones de salida."""
        pair = metadata.get("pair", "N/A")
        logger.info(f"[{pair}] Analizando condiciones de salida...")
        signals = (
            (dataframe["rsi"] > self.sell_rsi.value)
            & (dataframe["macdhist"] < 0)
            & (dataframe["macdhist"].shift(1) > 0)
            & (dataframe["close"] >= dataframe["bb_upperband"])
            & (dataframe["hma"] < dataframe["hma"].shift(1))
            & (dataframe["volume"] > 0)
        )
        n_signals = signals.sum()
        if n_signals > 0:
            logger.info(f"[{pair}] Señales de VENTA detectadas: {n_signals}")
        dataframe.loc[signals, ["exit_long", "exit_tag"]] = (1, "sell_signal")

        llm_signal = self._get_llm_signal(pair, dataframe)
        last_idx = dataframe.index[-1]
        if llm_signal == "SELL":
            dataframe.loc[last_idx, ["exit_long", "exit_tag"]] = (1, "llm_sell")
        elif llm_signal == "BUY":
            dataframe.loc[last_idx, ["enter_long", "enter_tag"]] = (1, "llm_buy")
        return dataframe

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        logger.info(
            f"[{pair}] Confirmando entrada: side={side}, rate={rate}, entry_tag={entry_tag}"
        )
        # Obtener los datos del par
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        # Verificar si el precio de entrada es razonable
        if side == "long":
            # Para compras, asegurarse que el precio no está muy alejado de la banda media
            if rate > last_candle["bb_midband"] * 1.02:  # Max 2% sobre la banda media
                return False

        return True

    def confirm_trade_exit(
        self,
        pair: str,
        trade: Trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs,
    ) -> bool:
        logger.info(f"[{pair}] Confirmando salida: exit_reason={exit_reason}, rate={rate}")
        # Obtener los datos del par
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        # Si la tendencia sigue siendo fuertemente alcista, mantener la posición
        if (
            last_candle["rsi"] < 65  # RSI aún no en sobrecompra extrema
            and last_candle["macd"] > last_candle["macdsignal"]  # MACD alcista
            and last_candle["close"] < last_candle["bb_upperband"]
        ):  # Precio bajo banda superior
            return False

        return True

    def _get_llm_signal(self, pair: str, dataframe: DataFrame) -> str:
        """Analiza los indicadores con un modelo local a través de ollama."""
        last_idx = dataframe.index[-1]
        indicators = {
            "rsi_1m": dataframe.loc[last_idx, "rsi"],
            "macd_1m": dataframe.loc[last_idx, "macd"],
            "macdhist_1m": dataframe.loc[last_idx, "macdhist"],
            "rsi_5m": dataframe.loc[last_idx, "rsi_5m"],
            "macd_5m": dataframe.loc[last_idx, "macd_5m"],
            "macdhist_5m": dataframe.loc[last_idx, "macdhist_5m"],
            "rsi_1h": dataframe.loc[last_idx, "rsi_1h"],
            "macd_1h": dataframe.loc[last_idx, "macd_1h"],
            "macdhist_1h": dataframe.loc[last_idx, "macdhist_1h"],
            "rsi_1d": dataframe.loc[last_idx, "rsi_1d"],
            "macd_1d": dataframe.loc[last_idx, "macd_1d"],
            "macdhist_1d": dataframe.loc[last_idx, "macdhist_1d"],
        }

        prompt = (
            f"Analiza los siguientes indicadores para {pair} y responde SOLO BUY, SELL o HOLD:\n"
            f"1m -> RSI {indicators['rsi_1m']:.2f}, MACDHIST {indicators['macdhist_1m']:.4f}\n"
            f"5m -> RSI {indicators['rsi_5m']:.2f}, MACDHIST {indicators['macdhist_5m']:.4f}\n"
            f"1h -> RSI {indicators['rsi_1h']:.2f}, MACDHIST {indicators['macdhist_1h']:.4f}\n"
            f"1d -> RSI {indicators['rsi_1d']:.2f}, MACDHIST {indicators['macdhist_1d']:.4f}"
        )
        try:
            result = subprocess.run(
                ["ollama", "run", "claude", prompt],
                capture_output=True,
                text=True,
                timeout=30,
            )
            response = result.stdout.strip().upper()
            if "BUY" in response:
                return "BUY"
            if "SELL" in response:
                return "SELL"
        except Exception as exc:  # pragma: no cover - depends on external tool
            logger.error(f"[{pair}] Error al ejecutar ollama: {exc}")
        return "HOLD"
