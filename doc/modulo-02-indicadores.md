# Módulo 2: Cálculo de indicadores

## 1.2 Indicadores y Métricas Clave
- Indicadores principales: EMA200, HMA, MACD, RSI, volumen, OBV, VWAP.
- Métricas de robustez: profit factor, drawdown máximo, ratio de Sharpe, win rate, tiempos de permanencia.
- Métricas de confirmación: divergencias de OBV, confirmaciones de VWAP, relación precio/EMA200.

## Cálculo y actualización de indicadores técnicos
- Calcular y actualizar todos los indicadores clave para cada timeframe relevante (1m, 5m, 1h, 1d).
- Implementar lógica para el cálculo incremental y eficiente (solo sobre nuevas velas).
- Almacenar los resultados en tablas agregadas/cache para acceso rápido por otros módulos.
- Garantizar la consistencia temporal (timestamp) y la actualización atómica de los valores.

## Integración en la estrategia
- `populate_indicators` debe consumir los valores desde la cache/tablas agregadas, no recalcular todo en cada ciclo.
- Lógica de invalidación/actualización: al cerrarse cada nueva vela, invalidar solo los valores afectados y recalcular lo necesario.
- Permitir la extensión sencilla para añadir nuevos indicadores o métricas desde la configuración.

## Buenas prácticas y extensibilidad
- Documentar la fórmula y el propósito de cada indicador en el código y/o documentación técnica.
- Validar la integridad de los datos antes de calcular indicadores (valores nulos, gaps, etc.).
- Permitir la configuración de parámetros (periodos, umbrales) desde archivos externos o la UI.
- Facilitar la exportación de los indicadores calculados para análisis externo o backtesting avanzado.
