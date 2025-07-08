# Módulo 1: Ingesta y almacenamiento de datos

## 1. Validación, Métricas y Gestión de Datos Históricos

**1.1 Backtesting Multi-Nivel**
- Ejecutar en **1m, 5m, 1h** y aplicar un **filtro macro** (diario/semanal, por ejemplo, EMA200₁d o MACD₁w) para comparar señales intradía contra la tendencia general.
- Incluir **indicadores de volumen** (media móvil de volumen 20, OBV, VWAP) y **EMA200** en las métricas de robustez. Estos indicadores ayudan a filtrar señales falsas y a operar a favor de la tendencia principal.

## 1.3 Base de Datos de Series Temporales
- Usar **TimescaleDB** o **QuestDB** para almacenar 6 meses de velas (1m–1d), con `vol_ma20`, `OBV`, `VWAP`, y **EMA200** precomputados mediante agregados continuos o vistas materializadas.
- **Pipeline de ingesta**: al iniciar o cada noche, comprobar el último timestamp almacenado, ajustar el rango de descarga para obtener solo las velas faltantes hasta el cierre de ayer vía API + **UPSERT**; programar limpieza (`DELETE` < now() – INTERVAL '6 months').

## 2. Arquitectura modular de datos e ingestión

1. **Módulo 1 – Ingestión histórica (batch)**: al arrancar o en job nocturno, comprobar la base de datos para determinar la última vela almacenada y descargar únicamente los datos faltantes hasta el cierre de ayer; bulk‐insert inicial + cálculo incremental de indicadores en DB.
2. **Módulo 2 – Ingestión en tiempo real (streaming)**: recoger velas en tiempo real vía WebSocket/REST, realizar UPSERT en la tabla de candles y actualizar solo la última vela con los indicadores (ATR, VWAP, OBV); mantener un cache local de las últimas N velas para lecturas ultra-rápidas.
3. **Módulo 3 – Capa de consumo de datos**: el bot Freqtrade lee siempre desde la DB o el cache, unificando históricos preprocesados y datos en tiempo real obtenidos directamente con la API del exchange.

## 3. Almacenamiento de métricas e indicadores recientes

1. **Cache de indicadores**
   - Mantener en la base de datos (o en Redis/Memory Cache) tablas/vistas con los últimos N valores de indicadores clave (ATR, EMA, RSI, MACD, OBV, VWAP, etc.), actualizadas en cada ingestión de vela.
   - Crear continuous aggregates o triggers que actualicen únicamente la ventana móvil (e.g. últimos 1 000 registros) para lecturas rápidas.
2. **Tablas de métricas resumidas**
   - Definir tablas con métricas agregadas de corto plazo (p.ej. media, desviación estándar, percentiles) calculadas cada vela o cada bloque de tiempo (5 m, 1 h).
   - Estas tablas alimentan las estrategias evitando recalcular series completas.
3. **Integración en estrategia**
   - Modificar `populate_indicators` para leer directamente estas tablas caché para los valores actuales de los indicadores y métricas, en lugar de computarlos desde cero.
   - Garantizar consistencia con un timestamp y lógica de invalidación/actualización al cerrarse cada nueva vela.
