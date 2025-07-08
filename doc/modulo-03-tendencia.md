# Módulo 3: Núcleo de Detección de Tendencia y Orquestación

## Rol y Responsabilidad Central
Este módulo es el **cerebro** y punto de control principal del sistema. Su función es recibir los datos e indicadores procesados, ejecutar la lógica de detección de tendencia y orquestar el flujo de decisiones y acciones del bot. Es responsable de coordinar la interacción entre los módulos de indicadores, estrategias, gestión de capital y monitorización, asegurando la coherencia y adaptabilidad del sistema.

## Funciones Clave
- Ejecutar la función principal `get_trend(df)` para determinar el estado del mercado (`"up"`, `"down"`, `"sideways"`) usando todos los indicadores y métricas relevantes.
- Orquestar la lógica de selección de estrategia y gestión de capital según la tendencia detectada.
- Coordinar la gestión de riesgos y reglas globales del bot.
- Integrar señales de control y eventos externos (pausas, rebalanceos, cambios de modo).
- Servir como punto de integración para la extensión de lógica y nuevas reglas.

## Flujo de Datos y Orquestación
1. **Recepción de datos**: Recibe los indicadores y métricas calculados por el Módulo 2.
2. **Análisis de tendencia**: Ejecuta la función de tendencia sobre los datos recibidos.
3. **Decisión y orquestación**:
   - Determina el estado de mercado y selecciona la estrategia adecuada.
   - Informa al Módulo 4 para ejecutar la lógica de trading correspondiente.
   - Ajusta la gestión de capital y riesgo según el contexto.
4. **Control y feedback**:
   - Recibe señales del Módulo 5 (monitorización) para pausar, modificar o reoptimizar el bot.
   - Registra eventos y cambios de estado para auditoría y análisis.

## Ejemplo de función de tendencia
```python
def get_trend(df: DataFrame) -> Literal["up","down","sideways"]:
    # Macro tendencia: EMA200 diaria vs. cierre diario
    macro_up = df['ema200_1d'].iloc[-1] < df['close_1d'].iloc[-1]
    # Intradía: HMA(14) vs. MA200
    trend_hma = df['hma'].iloc[-1] > df['close'].rolling(200).mean().iloc[-1]
    # Intradía: MACD
    trend_macd = df['macd'].iloc[-1] > df['macdsignal'].iloc[-1]
    # Multi-timeframe RSI
    rsi_ok = (df['rsi_1h'].iloc[-1] > 50) and (df['rsi_1d'].iloc[-1] > 50)
    # Confirmación por volumen
    vol_ok = df['volume'].iloc[-1] > df['vol_ma20'].iloc[-1] * 1.2
    vwap_ok = df['close'].iloc[-1] > df['vwap'].iloc[-1]
    obv_ok = df['obv'].iloc[-1] > df['obv'].rolling(20).mean().iloc[-1]
    if macro_up and trend_hma and trend_macd and rsi_ok and vol_ok and vwap_ok and obv_ok:
        return "up"
    if not (macro_up or trend_hma or trend_macd) and df['rsi'].iloc[-1] < 50:
        return "down"
    return "sideways"
```

## Selección Dinámica de Estrategia
- **Momentum (up)**: MACD > signal y precio > EMA20
- **Mean-reversion (sideways)**: RSI < buy_rsi y precio en banda inferior de Bollinger
- **Down**: Estrategias de cortos o migración a stablecoin
- **Triple pantalla**: Filtrado de señales intradía por tendencia semanal/diaria
- **Reversión de estado**: Cierre de posiciones y reoptimización

## Integración y Dependencias
- **Entrada**: Recibe indicadores y métricas del Módulo 2.
- **Salida**: Informa al Módulo 4 sobre el estado de tendencia y la lógica a aplicar.
- **Monitorización**: El Módulo 5 recibe tanto los datos/indicadores (Módulo 2) como las decisiones y estados generados por este módulo (Módulo 3), para auditar, alertar y registrar el funcionamiento del bot.
- **Control**: Solo en casos especiales (alertas críticas, límites de riesgo, errores graves), el Módulo 5 puede enviar señales de control a este módulo para pausar, modificar o reoptimizar el bot.
- **Extensibilidad**: Permite la incorporación de nuevos indicadores, reglas y fuentes de datos desde configuración o plugins.

## Extensibilidad y Mejores Prácticas
- Diseñar la función de tendencia para ser fácilmente ampliable y configurable.
- Registrar el estado de tendencia y los cambios para auditoría y análisis posterior.
- Mantener el módulo desacoplado y testeable, facilitando la integración de nuevas estrategias o reglas.
- Documentar claramente los puntos de integración y dependencias con otros módulos.
- Permitir la inyección de lógica personalizada mediante hooks o callbacks.

## Ejemplo de flujo de orquestación
```mermaid
graph TD;
    A[Datos e Indicadores (Módulo 2)] --> B[Núcleo de Tendencia (Módulo 3)];
    B --> C[Estrategias y Ejecución (Módulo 4)];
    B --> D[Gestión de Capital y Riesgo];
    E[Monitorización y Control (Módulo 5)] --> B;
    B --> F[Registro y Auditoría];
```

---

Este módulo debe ser el punto de referencia para cualquier lógica de decisión global, asegurando la robustez, adaptabilidad y trazabilidad del bot.
