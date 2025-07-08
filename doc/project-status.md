# Estado actual del proyecto CryptoFreqtrade

**Fecha de actualización:** 8 de julio de 2025

---

## Resumen general

El proyecto se encuentra en una fase avanzada de diseño arquitectónico y documentación, con una estructura modular clara y documentación detallada para cada componente principal del bot de trading. Se han definido los módulos clave, su integración, flujos de datos y mejores prácticas, y se ha comenzado a preparar el entorno para la implementación y despliegue.

---

## Estado por módulos

### Módulo 1: Ingesta y almacenamiento de datos
- [ ] Pendiente de implementación.
- Objetivo: recolectar, limpiar y almacenar velas e indicadores en la base de datos/cache (TimescaleDB o QuestDB).
- Tareas próximas: definir esquema de tablas, scripts de ingestión histórica y streaming.

### Módulo 2: Cálculo de indicadores
- [ ] Pendiente de implementación.
- Objetivo: calcular y actualizar indicadores técnicos (EMA200, HMA, MACD, RSI, volumen, OBV, VWAP) y almacenarlos para consumo eficiente.
- Tareas próximas: implementar funciones de cálculo y actualización incremental.

### Módulo 3: Núcleo de tendencia y orquestación
- [ ] Pendiente de implementación.
- Objetivo: implementar la función principal `get_trend(df)` que, usando los indicadores, determine el estado del mercado (`"up"`, `"down"`, `"sideways"`).
- Observación: la lógica de la estrategia `RsiMacdStrategy` es suficiente para esta función si se incluyen EMA200 y volumen.

### Módulo 4: Estrategias y ejecución
- [x] Parcialmente implementado.
- Estado: existe la estrategia `RsiMacdStrategy.py` que cubre señales multi-indicador y multi-timeframe, e integra LLM para señales avanzadas.
- Pendiente: adaptar la estrategia para consumir indicadores desde la base de datos/cache y coordinar con el módulo de tendencia.

### Módulo 5: Monitorización, control y mejoras operativas
- [ ] Pendiente de implementación.
- Objetivo: alertas, dashboards, CLI y bots de control (Telegram, Prometheus, Grafana).

### Módulo 6: Aprendizaje, optimización y adaptabilidad
- [ ] Pendiente de implementación.
- Objetivo: integrar procesos de auto-optimización, aprendizaje automático y mejora continua del bot.
- Tareas próximas: definir el ciclo de optimización y los criterios de éxito.

---

## Próximos pasos

1. Diseñar e implementar el esquema de la base de datos y el pipeline de ingestión histórica (Módulo 1).
2. Desarrollar el cálculo incremental de indicadores y su almacenamiento (Módulo 2).
3. Implementar el núcleo de tendencia y conectar con la estrategia (Módulo 3 y 4).
4. Añadir monitorización, control y aprendizaje automático (Módulo 5 y 6).

---

## Notas
- El proyecto está preparado para escalar y adaptarse a nuevas funcionalidades.
- Se prioriza la trazabilidad, extensibilidad y robustez en cada etapa.
- Este archivo `project-status.md` se actualiza en paralelo con cada avance.
- El estado de cada módulo se revisa y documenta tras cada cambio relevante.