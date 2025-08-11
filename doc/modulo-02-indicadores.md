# Módulo 2: Cálculo y Gestión de Indicadores Técnicos

## Rol y objetivo
Este módulo es responsable de calcular, actualizar y gestionar todos los indicadores y métricas técnicas necesarios para la toma de decisiones del bot. Su objetivo es proveer datos derivados robustos, consistentes y fácilmente accesibles para los módulos de tendencia, estrategias y monitorización.

## Flujo de cálculo y actualización
1. **Recepción de datos:** Obtiene velas y datos brutos del Módulo 1 (ingesta).
2. **Cálculo incremental:** Calcula solo los indicadores de las nuevas velas o de las que han cambiado, evitando recalcular todo el histórico.
3. **Almacenamiento eficiente:** Guarda los resultados en tablas agregadas o cache para acceso rápido y consistente.
4. **Consistencia temporal:** Garantiza que cada valor de indicador esté alineado con el timestamp de la vela correspondiente.
5. **Invalidación y actualización:** Al cerrarse una nueva vela, solo se invalidan y recalculan los valores afectados.

## Indicadores y métricas clave
- **Indicadores principales:**
  - EMA200: tendencia de largo plazo.
  - HMA: suavizado rápido para señales intradía.
  - MACD: momentum y cruces de tendencia.
  - RSI: sobrecompra/sobreventa.
  - Volumen: confirmación de movimientos.
  - OBV: divergencias volumen/precio.
  - VWAP: precio medio ponderado por volumen.
- **Métricas de robustez:**
  - Profit factor, drawdown máximo, ratio de Sharpe, win rate, tiempo de permanencia.
- **Métricas de confirmación:**
  - Divergencias de OBV, confirmaciones de VWAP, relación precio/EMA200.

## Estrategias de eficiencia y consistencia
- Calcular indicadores para cada timeframe relevante (1m, 5m, 1h, 1d).
- Usar funciones vectorizadas y cálculos en batch para optimizar el rendimiento.
- Almacenar los resultados en tablas/vistas agregadas o cache para acceso rápido.
- Validar la integridad de los datos antes de calcular (valores nulos, gaps, duplicados).
- Permitir la configuración dinámica de parámetros (periodos, umbrales) desde archivos externos o UI.

## Integración con otros módulos
- Provee indicadores calculados al Módulo 3 (núcleo de tendencia), Módulo 4 (estrategias) y Módulo 5 (monitorización).
- Expone API o interfaz de consulta para el resto del sistema.
- Permite la extensión sencilla para añadir nuevos indicadores o métricas desde la configuración.

## Extensibilidad y mejores prácticas
- Documentar la fórmula y el propósito de cada indicador en el código y/o documentación técnica.
- Facilitar la exportación de los indicadores calculados para análisis externo o backtesting avanzado.
- Diseñar el módulo para ser desacoplado y fácilmente testeable.
- Registrar todos los eventos y errores para trazabilidad.

## Ejemplo de flujo de cálculo y consumo
```mermaid
graph TD;
    A[Datos brutos (Módulo 1)] --> B[Cálculo de indicadores];
    B --> C[Almacenamiento en cache/tablas];
    C --> D[Consumo por tendencia, estrategias y monitorización];
```

---

Este módulo es esencial para dotar al sistema de señales técnicas robustas, eficientes y fácilmente integrables en cualquier lógica de trading algorítmico.
