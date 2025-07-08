### Plan bot CryptoFreqtrade&#x20;

docker-compose exec freqtrade freqtrade trade --strategy RsiMacdStrategy --dry-run --logfile -

---

## 1. Validación, Métricas y Gestión de Datos Históricos

**1.1 Backtesting Multi-Nivel**

- Ejecutar en **1m, 5m, 1h** y aplicar un **filtro macro** (diario/semanal, por ejemplo, EMA200₁d o MACD₁w) para comparar señales intradía contra la tendencia general.
- Incluir **indicadores de volumen** (media móvil de volumen 20, OBV, VWAP) y **EMA200** en las métricas de robustez. Estos indicadores ayudan a filtrar señales falsas y a operar a favor de la tendencia principal.

**1.2 Indicadores y Métricas Clave**

- Profit factor, drawdown máximo, ratio de Sharpe, win rate y tiempos de permanencia.
- Analizar divergencias de OBV, confirmaciones de VWAP y relación precio/EMA200.

**1.3 Base de Datos de Series Temporales**

- Usar **TimescaleDB** o **QuestDB** para almacenar 6 meses de velas (1m–1d), con `vol_ma20`, `OBV`, `VWAP`, y **EMA200** precomputados mediante agregados continuos o vistas materializadas.
- **Pipeline de ingesta**: al iniciar o cada noche, comprobar el último timestamp almacenado, ajustar el rango de descarga para obtener solo las velas faltantes hasta el cierre de ayer vía API + **UPSERT**; programar limpieza (`DELETE` < now() – INTERVAL '6 months').

---

## 2. Función Unificada de Detección de Tendencia (Multi-Timeframe + Volumen + EMA200)

```python
def get_trend(df: DataFrame) -> Literal["up","down","sideways"]:
    # 1. Macro tendencia: EMA200 diaria vs. cierre diario
    macro_up = df['ema200_1d'].iloc[-1] < df['close_1d'].iloc[-1]

    # 2. Intradía: HMA(14) vs. MA200
    trend_hma = df['hma'].iloc[-1] > df['close'].rolling(200).mean().iloc[-1]

    # 3. Intradía: MACD
    trend_macd = df['macd'].iloc[-1] > df['macdsignal'].iloc[-1]

    # 4. Multi-timeframe RSI
    rsi_ok = (df['rsi_1h'].iloc[-1] > 50) and (df['rsi_1d'].iloc[-1] > 50)

    # 5. Confirmación por volumen
    vol_ok = df['volume'].iloc[-1] > df['vol_ma20'].iloc[-1] * 1.2
    vwap_ok = df['close'].iloc[-1] > df['vwap'].iloc[-1]
    obv_ok = df['obv'].iloc[-1] > df['obv'].rolling(20).mean().iloc[-1]

    if macro_up and trend_hma and trend_macd and rsi_ok and vol_ok and vwap_ok and obv_ok:
        return "up"
    if not (macro_up or trend_hma or trend_macd) and df['rsi'].iloc[-1] < 50:
        return "down"
    return "sideways"
```

---

## 3. Selección dinámica de estrategia según estado de mercado

| Estado       | Lógica principal                                   | Timeframes                             |
| ------------ | -------------------------------------------------- | -------------------------------------- |
| **Up**       | Momentum: cruce MACD > signal + precio > EMA20     | 10 m–1 h (confirmación), 1 m (entrada) |
| **Sideways** | Mean-reversion: RSI < buy\_rsi + BB inferior       | 5 m–15 m para puntos de entrada        |
| **Down**     | Opción A: cortos (si admite); Opción B: stablecoin | 1 h–4 h: cerrar posiciones intradía    |

- **Triple Pantalla**: siempre filtrar intradía con tendencia semanal/diaria antes de abrir.
- **Reversión de estado**: al detectar cambio (`up→sideways`), cerrar y reoptimizar lógica.

---

## 4. Gestión avanzada de riesgos y capital

1. **Position sizing dinámico**

   ```python
   risk_amount = capital * riesgo_pct  # 1–2 %
   risk_dist   = abs(entry_price - stop_price)  # 2×ATR
   size        = risk_amount / risk_dist
   ```

   - Ajustar `riesgo_pct`: 2 % en tendencias fuertes, 1 % en moderadas, 0.5 % en ruido.

2. **Stop-loss y trailing**

   - Stop inicial: **2×ATR(14)**; trailing: **1×ATR** tras +0.5×ATR.

3. **Time-stop**

   - En 1 m: máximo **240–480 velas** (4–8 h).
   - En diario: máximo **10–20 velas** (10–20 días).

4. **Reserva en stablecoins**

   - Mantener 10–20 % en USDT/USDC como buffer.

5. **Diversificación y hedge**

   - Máximo **3–4 pares** correlacionados.
   - Usar futuros inversos o cortos para cubrir parte de la exposición.

6. **Rebalanceo periódico**

   - Cada 4 h (intradía) y cada semana (swing), recalcular tendencias y reasignar capital.

---

## 5. Gestión de posiciones abiertas y reequilibrio al inicio/reinicio

Al iniciar el bot por primera vez o tras un reinicio debido a un error de sistema, es crítico asegurar que el estado de las posiciones y la asignación de capital sean consistentes:

1. **Reconstrucción del estado de posiciones**

   - Al arrancar, leer todas las órdenes abiertas y posiciones desde el exchange y la base de datos local (TimescaleDB/QuestDB).
   - Validar cada posición:
     - Verificar que el **precio de entrada**, **stop-loss**, **trailing stop** y **tamaño** coincidan con el último estado conocido.
     - Si hay discrepancias, registrar alerta y/o ajustar stop-loss al valor más conservador entre local y remoto.

2. **Rebalanceo de capital cripto/fiat/stablecoin**

   - Calcular el porcentaje actual de capital en:
     - Criptodivisas (posiciones abiertas y disponibles)
     - Fiat (cash libre para trading)
     - Stablecoins (buffer de 10–20 %)
   - Si tras reinicio el buffer de stablecoins está por debajo del rango objetivo, convertir automáticamente parte de las criptos/dólar devolviendo el buffer al 10–20 %.
   - Si el buffer excede el 20 %, reubicar el exceso en criptomonedas según la clasificación de tendencias (solo en `trend == "up"`).

3. **Reaplicación de lógica de entrada/salida**

   - Una vez reconstruido el estado y reequilibrado el capital, llamar a `populate_entry_trend` y `populate_exit_trend` para generar las señales actuales.
   - Confirmar operaciones pendientes (entry/exit) con `confirm_trade_entry` / `confirm_trade_exit` para evitar órdenes huérfanas o duplicadas.

4. **Fallback y alertas**

   - Si no se puede reconstruir completamente el estado de una posición (por ejemplo, datos faltantes), marcarla para **cierre manual** con alerta enviada al canal de notificaciones.
   - Registrar un **snapshot** del balance y posiciones al inicio para auditoría y análisis de fallos.

---

## 6. Histórico de operaciones y monitorización

1. **Registro completo de operaciones**

   - Mantener una tabla o colección en la base de datos para cada trade ejecutado, con campos: `trade_id`, `pair`, `side`, `entry_price`, `exit_price`, `entry_time`, `exit_time`, `profit_loss_pct`, `reason_tag`, `stop_loss_level`, `take_profit_level`, `max_drawdown`, `notes`.
   - Guardar snapshots de indicadores al momento de entrada y salida para análisis de condiciones de mercado.

2. **Análisis estadístico periódico**

   - Implementar jobs cron (p.ej. diario o semanal) para:
     - Calcular métricas agregadas: profit factor, drawdown medio, time-in-trade medio, tasa de aciertos por estrategia o tag.
     - Identificar estrategias o parámetros con performance por debajo de un umbral y marcar para reoptimización.
   - Generar reportes automatizados (CSV o dashboards) para facilitar la toma de decisiones sobre ajustes de `buy_rsi`, `sell_rsi`, ROI y stops.

3. **Monitorización en tiempo real**

   - **Alertas**: enviar notificaciones (Telegram, Slack o Email) al detectar errores críticos, discrepancias en posiciones o sobrepaso de drawdown en una sola señal.
   - **Dashboard sencillo**:
     - Usar herramientas ligeras como **Grafana** o **Prometheus+Alertmanager** para visualizar:
       - Balance en cripto/fiat/stablecoin.
       - Número de operaciones activas.
       - Utilización de capital (%) y riesgo pendiente.
       - Gráficos de equity curve, drawdown y distribución de ganancias.
   - **Logs estructurados** (JSON) para facilitar búsquedas e integración con sistemas de observabilidad (ELK, Loki).

---

## 7. Arquitectura modular de datos e ingestión

1. **Módulo 1 – Ingestión histórica (batch)**: al arrancar o en job nocturno, comprobar la base de datos para determinar la última vela almacenada y descargar únicamente los datos faltantes hasta el cierre de ayer; bulk‐insert inicial + cálculo incremental de indicadores en DB.
2. **Módulo 2 – Ingestión en tiempo real (streaming)**: recoger velas en tiempo real vía WebSocket/REST, realizar UPSERT en la tabla de candles y actualizar solo la última vela con los indicadores (ATR, VWAP, OBV); mantener un cache local de las últimas N velas para lecturas ultra-rápidas.
3. **Módulo 3 – Capa de consumo de datos**: el bot Freqtrade lee siempre desde la DB o el cache, unificando históricos preprocesados y datos en tiempo real, sin acceder directamente a la API del exchange.

---

## 8. Almacenamiento de métricas e indicadores recientes

1. **Cache de indicadores**

   - Mantener en la base de datos (o en Redis/Memory Cache) tablas/vistas con los últimos N valores de indicadores clave (ATR, EMA, RSI, MACD, OBV, VWAP, etc.), actualizadas en cada ingestión de vela.
   - Crear continuous aggregates o triggers que actualicen únicamente la ventana móvil (e.g. últimos 1 000 registros) para lecturas rápidas.

2. **Tablas de métricas resumidas**

   - Definir tablas con métricas agregadas de corto plazo (p.ej. media, desviación estándar, percentiles) calculadas cada vela o cada bloque de tiempo (5 m, 1 h).
   - Estas tablas alimentan las estrategias evitando recalcular series completas.

3. **Integración en estrategia**

   - Modificar `populate_indicators` para leer directamente estas tablas caché para los valores actuales de los indicadores y métricas, en lugar de computarlos desde cero.
   - Garantizar consistencia con un timestamp y lógica de invalidación/actualización al cerrarse cada nueva vela.

---

## 9. Dockerización de módulos

Para facilitar la implementación, despliegue y escalabilidad, contenedorizaremos cada componente del sistema:

1. **Contenedor Batch (Ingestión histórica)**
   - Imagen Docker con script de ingestión histórica y dependencias (Python, CCXT, librerías de DB).
   - Variables de entorno para credenciales API y configuración DB.
   - Montaje de volúmenes para logs y snapshots.

2. **Contenedor Streaming (Ingestión en tiempo real)**
   - Imagen Docker que levanta el listener WebSocket/REST.
   - Incluye Redis/Cache en un contenedor separado o como servicio dentro de Docker Compose.
   - Healthchecks para asegurar reconexión automática en fallos.

3. **Contenedor Strategy (Bot Freqtrade)**
   - Imagen basada en la oficial de Freqtrade, con la estrategia y configuración adaptativa.
   - Conexión a la DB y al cache definidos vía variables de entorno.
   - Política de reinicio automática en caso de crash.

4. **Contenedor Monitoring**
   - Grafana y Prometheus en contenedores separados para métricas y dashboard.
   - Exporters (DB y aplicación) para exponer métricas via HTTP.

5. **Orquestación con Docker Compose/Kubernetes**
   - Definir `docker-compose.yml` con redes dedicadas, volúmenes y dependencias de servicio (DB, Redis, Prometheus).
   - Configurar reinicios (`restart: always`), límites de recursos y variables de entorno.
   - Opcionalmente empaquetar con Helm charts si se despliega en Kubernetes.

---

## 10. Menú de control (CLI) y Bot de Telegram

Para facilitar la intervención manual y recibir alertas en tiempo real, añadimos dos capas de control:

1. **Estado general**  
   - Mostrar balance cripto/fiat/stablecoins, posiciones abiertas con PnL, capital en riesgo y equity curve.
2. **Gestión de posiciones**  
   - Listar operaciones activas (entrada, stop-loss, trailing-stop).  
   - Comandos para **cancelar** posiciones (market exit) o **ajustar** stop-loss / take-profit sobre un trade específico.
3. **Ajuste de parámetros en caliente**  
   - Modificar `riesgo_pct`, umbral de volumen, objetivos ROI o activar/desactivar filtros (volumen, streaming, batch) sin reiniciar.
4. **Control de flujo**  
   - **Pausar/reanudar** módulos enteros (batch, streaming o strategy) o un par concreto.  
   - Forzar recarga de datos históricos o de indicadores cacheados.
5. **Tests y validaciones**  
   - Ejecutar un backtest rápido sobre los últimos N minutos/horas y visualizar métricas antes y después de un cambio.

---

## 11. Integración de modelos Ollama para análisis técnico avanzado

Para ventanas de tiempo más grandes (diario, semanal, mensual) donde la latencia no sea crítica, podemos emplear modelos locales especializados en Ollama para generar indicadores e insights adicionales:

1. **Selección de modelos**  
   - Usar modelos de gran capacidad (p.ej. LLaMA-2-70B, Mistral-Instruct) o adaptaciones financieras (finetuned) disponibles en Ollama.  
   - Asegurar licencia y recursos de hardware (GPU, RAM) adecuados.

2. **Flujo batch de análisis**  
   - Cada periodo (diario/semanal) un job batch recopila datos históricos ampliados (todos los timeframes).  
   - Prepara un prompt estructurado con series de indicadores (cierre, volumen, BB, MACD, RSI) y pregunta al modelo por:  
     - Predicción de fuerza de tendencia en el próximo periodo.  
     - Scores de convicción (0–1) para estrategias momentum, mean-reversion o breakout.
   - Parsear la respuesta alfanumérica y convertirla en nuevos campos en la DB (`llm_momentum_score`, `llm_volatility_forecast`, `llm_trend_strength`).

3. **Almacenamiento y consumo**  
   - Guardar outputs en tablas de indicadores cacheados para lecturas en `get_trend()` y `populate_*`.  
   - Ajustar lógicas de entrada/salida: p.ej. ignorar señales intradía si `llm_trend_strength < 0.3`.

4. **Ventajas y consideraciones**  
   - **Ventaja**: modelar relaciones no lineales y aprendizaje contextual de patrones complejos.  
   - **Riesgo**: dependemos de la calidad del prompt y la robustez del modelo — es clave backtestear estas señales LLM de forma independiente.

---

**Bot de Telegram**  
- Exponer comandos `/status`, `/sell <pair>`, `/set risk <pct>`, `/pause`, `/resume` para controlar el bot desde el móvil o escritorio.  
- Envío de alertas automáticas (errores críticos, drawdowns, posición abierta/cerrada) al canal de Telegram.

---

> Con este plan, integrarás volumen, gestión de datos eficiente y un filtro macro-micro en todos los niveles, junto con sizing adaptativo y uso de stablecoins, logrando un bot Freqtrade verdaderamente robusto y adaptable.

---

## 12. Arquitectura modular y función principal de tendencia

Para garantizar flexibilidad y mantenibilidad, la arquitectura debe organizarse en módulos independientes, con un **módulo principal** encargado de la detección de tendencia y la orquestación de la lógica de trading:

### Estructura recomendada:

- **Módulo 1: Ingesta y almacenamiento de datos**
  - Encargado de recolectar, limpiar y almacenar velas e indicadores en la base de datos/cache.
- **Módulo 2: Cálculo de indicadores**
  - Calcula y actualiza los indicadores técnicos (incluyendo EMA200, HMA, MACD, RSI, volumen, OBV, VWAP) y los deja listos para consumo.
- **Módulo 3: Detección de tendencia (core)**
  - Implementa la función principal `get_trend(df)` que, usando los indicadores calculados, determina el estado del mercado: `"up"`, `"down"` o `"sideways"`.
  - Este módulo es el punto de entrada para la lógica de selección de estrategia y gestión de capital.
- **Módulo 4: Estrategias y ejecución**
  - Define las reglas de entrada/salida y ejecuta las órdenes según el estado de tendencia y los parámetros de riesgo.
- **Módulo 5: Monitorización y control**
  - Gestiona alertas, dashboards, CLI y bots de control.

### Sobre la función `get_trend` y la estrategia actual

La lógica de la estrategia `RsiMacdStrategy` (con los indicadores propuestos: EMA200, HMA, MACD, RSI, volumen, OBV, VWAP) es suficiente para implementar la función `get_trend` y distinguir entre `"up"`, `"down"` y `"sideways"`, siempre que se incluyan los indicadores de volumen y EMA200 en el cálculo.

No es necesario implementar una estrategia adicional para la detección de tendencia, pero sí es fundamental que la función `get_trend`:
- Consuma los indicadores desde el módulo de datos/cache.
- Aplique las condiciones multi-nivel y de confirmación descritas (macro, intradía, volumen).
- Permita ser llamada desde el módulo principal para decidir la lógica de trading y gestión de capital.

**Resumen:**  
La arquitectura modular debe tener un módulo principal donde se defina y ejecute `get_trend`. Si la estrategia implementa todos los indicadores clave (EMA200, volumen, etc.), es suficiente para calcular las tendencias. Si falta algún indicador, debe añadirse en el módulo de cálculo de indicadores.
