# Setup y uso básico del bot CryptoFreqtrade

Esta guía resume los pasos y comandos esenciales para desplegar, reiniciar y operar el bot en contenedores Docker, así como la estructura básica del proyecto.

---

## Comandos Docker principales

- **Reiniciar contenedor:**
  ```bash
  docker-compose down
  docker-compose up -d
  ```
- **Ejecutar Freqtrade en modo simulación (dry-run):**
  ```bash
  docker-compose exec freqtrade freqtrade trade --strategy RsiMacdStrategy --dry-run --logfile -
  ```
- **Ver logs en tiempo real:**
  ```bash
  docker-compose logs -f freqtrade
  ```

---

## Modificaciones y configuración
- Elimina o corrige `"margin_mode": "none"` en `config.json` si da error.
- Asegúrate de que el parámetro `--strategy` esté correctamente especificado en los comandos o en `docker-compose.yml`.

---

## Monitorización y control
- Usa logs en tiempo real con `docker-compose logs -f freqtrade`.
- Activa y configura el bot de Telegram desde `config.json`.
- Utiliza la API REST disponible en http://localhost:8080.

---

## Estructura relevante del proyecto
- `user_data/strategies/RsiMacdStrategy.py`: Estrategia personalizada.
- `user_data/config.json`: Configuración principal del bot.


## Problema común: Conflicto de nombre de contenedor Docker
Si al iniciar el contenedor aparece un error como:
```
Conflict. The container name "/freqtrade" is already in use by container "<container_id>".
```
Solución:
1. Detén el contenedor en ejecución:
   ```bash
   docker stop <container_id>
   ```
2. Elimínalo:
   ```bash
   docker rm <container_id>
   ```
   O fuerza la eliminación:
   ```bash
   docker rm -f <container_id>
   ```

---