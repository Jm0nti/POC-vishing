# Arquitectura PoC Detección de Vishing en Tiempo Real — Documentación de Componentes


## 1. Visión General

### 1.1 Problema

El vishing (voice phishing) representa aproximadamente el 50% de los casos de fraude transaccional del banco. Un estafador llama al cliente haciéndose pasar por el banco, lo convence de abrir la app bancaria y ejecutar una transferencia "de seguridad". El cliente está autenticado, usa su propio dispositivo y sus propias credenciales, por lo que los sistemas de detección de fraude tradicionales (basados en identidad, dispositivo o ubicación) no lo detectan.

### 1.2 Hipótesis

Aunque la identidad del usuario es legítima, su **comportamiento durante la sesión** cambia cuando está siendo manipulado telefónicamente. Un cliente bajo vishing teclea más lento (le dictan datos), hace pausas frecuentes (escucha instrucciones), comete más errores (no conoce los datos que ingresa), y tiene una llamada activa todo el tiempo. Estas señales comportamentales, capturadas en tiempo real, pueden alimentar un modelo de clasificación que detecte vishing antes de que la transacción se complete.

### 1.3 Qué hace esta PoC

Simula el flujo completo de detección en tiempo real: un **simulador** genera eventos de sesión bancaria (legítimos y de vishing), un **pipeline serverless en AWS** procesa los eventos, acumula el comportamiento de cada sesión, y cuando se intenta una transacción, un **modelo de Machine Learning** evalúa la sesión y genera un score de riesgo. Según el score, el sistema decide qué nivel de intervención aplicar (desde monitoreo silencioso hasta bloqueo de la transacción).

---

## 2. Arquitectura de Componentes

### 2.1 Diagrama de componentes

```
                                    ┌─────────────────────────────────┐
                                    │         AWS CLOUD               │
                                    │                                 │
┌──────────────┐    HTTPS/POST      │  ┌────────────┐                 │
│  EC2         │───────────────────────▶│ API Gateway │                │
│  Simulador   │    + API Key       │  │ REST       │                 │
│  t3.micro    │                    │  └──────┬─────┘                 │
└──────────────┘                    │         │                       │
                                    │         ▼                       │
                                    │  ┌──────────────┐              │
                                    │  │   Lambda      │              │
                                    │  │   Ingestor    │              │
                                    │  └──────┬───────┘              │
                                    │         │ SQS SendMessage       │
                                    │         ▼                       │
                                    │  ┌──────────────┐              │
                                    │  │  SQS FIFO    │              │
                                    │  │  (cola)      │              │
                                    │  └──────┬───────┘              │
                                    │         │ Trigger (batch=1)     │
                                    │         ▼                       │
                                    │  ┌──────────────┐   ┌────────┐ │
                                    │  │   Lambda      │──▶│DynamoDB│ │
                                    │  │   Procesador  │◀──│session │ │
                                    │  └──────┬───────┘   │_state  │ │
                                    │         │            └────────┘ │
                                    │         │ HTTP POST              │
                                    │         │ + API Key              │
                                    │         ▼                       │
                                    │  ┌──────────────┐              │
                                    │  │  EC2 Model   │              │
                                    │  │  Server      │              │
                                    │  │  t3.small    │              │
                                    │  │  (FastAPI)   │              │
                                    │  └──────┬───────┘              │
                                    │         │ Score + Label         │
                                    │         ▼                       │
                                    │  ┌──────────────┐   ┌────────┐ │
                                    │  │   Lambda      │──▶│DynamoDB│ │
                                    │  │   Decisor     │   │fraud_  │ │
                                    │  └──────┬───────┘   │alerts  │ │
                                    │         │            └────────┘ │
                                    │         ├──▶ CloudWatch Metrics  │
                                    │         └──▶ WebSocket (opcional)│
                                    │                                 │
                                    └─────────────────────────────────┘
```

### 2.2 Flujo de datos

1. El **Simulador** genera eventos JSON que representan la telemetría comportamental de una sesión bancaria (keystroke dynamics, touch, sensores, contexto)
2. Los eventos se envían por HTTPS al **API Gateway REST**, que los rutea al **Lambda Ingestor**
3. El Lambda Ingestor valida el evento y lo publica en una **cola SQS FIFO** (agrupado por session_id para mantener orden)
4. La cola dispara el **Lambda Procesador**, que lee el estado acumulado de la sesión desde **DynamoDB**, incorpora el nuevo evento, y guarda el estado actualizado
5. Cuando llega un evento de tipo `transaction_intent`, el Lambda Procesador construye un vector de **44 features** comportamentales y lo envía al **Model Server** en EC2
6. El Model Server ejecuta el **VishingModelWrapper** (XGBoost) y retorna la probabilidad de vishing, la predicción y el umbral usado
7. El Lambda Procesador invoca asincrónicamente al **Lambda Decisor** con el resultado
8. El Lambda Decisor determina el nivel de intervención, guarda la alerta en **DynamoDB**, emite una métrica a **CloudWatch**, y opcionalmente notifica vía **WebSocket**

---

## 3. Componentes Detallados

### 3.1 EC2 Simulador

| Atributo | Valor |
|---|---|
| Instancia | t3.micro (2 vCPU, 1 GB RAM) |
| Rol | Generar sesiones bancarias simuladas (legítimas y de vishing) |
| Tecnología | Python 3 + requests + threading |

**Qué hace:** Ejecuta sesiones concurrentes, cada una representando un cliente que navega la app bancaria. Cada sesión envía entre 5-8 eventos (`screen_view`) que simulan la navegación por las pantallas, y finalmente un evento `transaction_intent` cuando el cliente intenta transferir dinero.

**Cómo diferencia sesiones legítimas de vishing:** Los parámetros de generación son distintos. En una sesión legítima, el tecleo es rápido y fluido (μ=130ms entre teclas), sin pausas largas, sin llamada activa. En una sesión de vishing, el tecleo es lento y segmentado (μ=250ms), con pausas de 10-30 segundos (escucha instrucciones), llamada activa en el 85% de los eventos, más errores de tecleo, y montos transaccionales más altos.

**Los valores de generación están calibrados a las distribuciones del dataset sintético original**, asegurando que las sesiones simuladas caen dentro de los rangos que el modelo aprendió durante el entrenamiento.

**Archivos:**
- `session_base.py` — Función utilitaria `send_event()` que construye el JSON y lo envía al API Gateway
- `legitimate.py` — Generador de sesiones legítimas con 5 pantallas
- `vishing.py` — Generador de sesiones de vishing con 8 pantallas, pausas largas y navegación errática
- `orchestrator.py` — Orquestador que lanza N sesiones concurrentes con un ratio configurable de vishing

### 3.2 API Gateway REST

| Atributo | Valor |
|---|---|
| Endpoint | `POST /poc/session/event` |
| Autenticación | API Key en header `x-api-key` |
| Throttling | 100 req/seg, burst 200 |

**Qué hace:** Recibe los eventos HTTP del simulador, valida la API Key, y rutea el request al Lambda Ingestor. Es el punto de entrada público de la arquitectura.

**Por qué REST y no HTTP API:** REST API permite configurar API Keys y Usage Plans nativamente, lo cual es importante para controlar el acceso desde el simulador.

### 3.3 Lambda Ingestor

| Atributo | Valor |
|---|---|
| Runtime | Python 3.11 |
| Memoria | 256 MB |
| Timeout | 10 segundos |
| Función | Validar y enrutar eventos a SQS |

**Qué hace:** Recibe el body JSON del API Gateway, valida que contenga los campos requeridos (`session_id`, `customer_id`, `timestamp`, `event_type`), y lo publica en la cola SQS FIFO. Genera un `MessageDeduplicationId` basado en hash del session_id + timestamp para evitar duplicados.

**Por qué existe como componente separado:** Desacopla la validación/ingesta de la lógica de procesamiento. Si la cola está saturada o el procesador falla, los eventos no se pierden. El simulador recibe un 200 inmediatamente sin esperar procesamiento.

### 3.4 SQS FIFO

| Atributo | Valor |
|---|---|
| Tipo | FIFO (First In, First Out) |
| MessageGroupId | `session_id` |
| Deduplicación | MessageDeduplicationId explícito |
| Visibility timeout | 30 segundos |

**Qué hace:** Buffer ordenado entre la ingesta y el procesamiento. Garantiza que los eventos de una misma sesión se procesen en orden (critical para calcular hesitaciones y dead time basados en deltas de timestamps).

**Por qué FIFO y no Standard:** El orden importa. Si dos eventos de la misma sesión llegan desordenados, el cálculo de gaps temporales (hesitación, dead time) sería incorrecto. El `MessageGroupId = session_id` garantiza orden dentro de cada sesión sin bloquear sesiones entre sí.

**Por qué SQS y no Kinesis:** Para el volumen de la PoC (decenas de sesiones), Kinesis es sobredimensionado y más caro. SQS FIFO es serverless, escala automáticamente, y no tiene costo fijo.

### 3.5 Lambda Procesador

| Atributo | Valor |
|---|---|
| Runtime | Python 3.11 |
| Memoria | 512 MB |
| Timeout | 30 segundos |
| Trigger | SQS FIFO, batch size = 1 |
| Función | Acumular estado + feature engineering + invocar modelo |

**Este es el componente más complejo de la arquitectura.** Realiza tres funciones:

**Función 1 — Acumulación de estado (`update_state`):** Cada evento contribuye a contadores y acumuladores almacenados en DynamoDB. Por ejemplo, cada evento con `keyhold_ms > 0` suma al acumulador `sum_keyhold_ms` e incrementa `typing_event_count`. Los timestamps se usan para detectar hesitaciones (gap > 1.5s entre eventos) y dead time (gap > 3s). El estado acumulado tiene ~40 campos.

**Función 2 — Feature engineering (`build_feature_vector`):** Cuando llega un `transaction_intent`, transforma los acumuladores en 44 features numéricas alineadas al modelo. Por ejemplo, `avg_keyhold_ms = sum_keyhold_ms / typing_event_count`, o `segmented_typing_ratio = segment_pause_count / typing_event_count`. También calcula features derivadas como `data_familiarity_score` (compuesto de segmented typing, correction rate y typing speed) y `hesitation_composite`.

**Función 3 — Invocación del modelo:** Envía el vector de 44 features por HTTP POST al Model Server en EC2 con la API key en el header. Recibe la respuesta e invoca asincrónicamente al Lambda Decisor.

**Las 44 features que construye** corresponden exactamente a las que el VishingModelWrapper espera, definidas por el `cols_to_drop` del Notebook 7 de entrenamiento.

### 3.6 DynamoDB — session_state

| Atributo | Valor |
|---|---|
| Partition key | `session_id` (String) |
| TTL | `ttl` (Unix timestamp + 3600s) |
| Billing | On-demand |

**Qué hace:** Almacena el estado acumulado de cada sesión activa. Cada invocación del Lambda Procesador hace un read-update-write sobre el item de la sesión. El TTL de 60 minutos limpia automáticamente sesiones expiradas.

**Por qué DynamoDB y no Redis/ElastiCache:** Para la PoC, DynamoDB on-demand es más simple (serverless, sin instancias que gestionar) y más barato (costo por operación, no por hora). La latencia de ~5ms por operación es aceptable para el volumen de la PoC.

### 3.7 EC2 Model Server

| Atributo | Valor |
|---|---|
| Instancia | t3.small (2 vCPU, 2 GB RAM) |
| Tecnología | FastAPI + uvicorn |
| Modelo | VishingModelWrapper (XGBoost) cargado desde S3 |
| Autenticación | API key en header `X-API-Key` |
| Servicio | systemd (se reinicia automáticamente) |

**Qué hace:** Sirve el modelo de ML como un endpoint HTTP. Al iniciar, descarga el VishingModelWrapper serializado desde S3, lo carga en memoria, y queda listo para recibir requests en el puerto 8000.

**Endpoint `/predict`:** Recibe un dict de 44 features, valida la API key, y llama `wrapper.predict_full(features)`. El wrapper maneja internamente el ordenamiento de features, el scaling (si aplica), y aplica el umbral óptimo de decisión. Retorna la predicción (0/1), la etiqueta ("legitimate"/"vishing"), las probabilidades de ambas clases, y el umbral usado.

**Endpoint `/health`:** Retorna el estado del servidor, el nombre del modelo cargado, la técnica de balanceo, el ratio, el threshold, y la lista de features. No requiere API key (para health checks).

**El VishingModelWrapper** encapsula en un solo archivo `.pkl` el modelo entrenado, el scaler (si se usó), la lista ordenada de features, el umbral óptimo por F1, y metadata (nombre del modelo, técnica, ratio). Fue creado en el Notebook 7 de modelado.

**Seguridad:** El Security Group de la EC2 permite tráfico entrante en el puerto 8000, y la API key en el header actúa como autenticación. El endpoint `/predict` rechaza con HTTP 403 cualquier request sin la API key correcta.

### 3.8 Lambda Decisor

| Atributo | Valor |
|---|---|
| Runtime | Python 3.11 |
| Memoria | 256 MB |
| Timeout | 10 segundos |
| Invocación | Asincrónica (desde Lambda Procesador) |

**Qué hace:** Recibe el score del modelo y decide qué acción tomar. Implementa 5 niveles de intervención progresiva:

| Nivel | Score | Acción | Descripción |
|---|---|---|---|
| 0 — Monitor | < 0.3 | Ninguna | Sesión normal, solo logging |
| 1 — Alerta silenciosa | 0.3 – 0.5 | Log interno | Se registra la alerta pero no se notifica al cliente |
| 2 — Fricción | 0.5 – 0.7 | Mensaje al cliente | "¿Estás hablando por teléfono con alguien que te guía?" |
| 4 — Cooling-off | 0.7 – 0.9 | Delay de 30 min | La transferencia se retiene y se confirma por SMS |
| 5 — Bloqueo | ≥ 0.9 | Transacción bloqueada | Un agente de seguridad contacta al cliente |

**Acciones que ejecuta:**
1. Guarda la alerta completa en DynamoDB (`fraud_alerts`) con el score, el label del modelo, el threshold usado, y las features de la sesión
2. Emite una métrica custom a CloudWatch (`VishingPoC/VishingScore`) con la dimensión del nivel
3. Si el nivel requiere intervención y hay WebSocket configurado, envía la notificación push

### 3.9 DynamoDB — fraud_alerts

| Atributo | Valor |
|---|---|
| Partition key | `alert_id` (String UUID) |
| Sort key | `timestamp` (String ISO) |
| Billing | On-demand |

**Qué hace:** Registro histórico de todas las evaluaciones del modelo. Cada item contiene el session_id, customer_id, score, label, threshold, nivel de intervención, y el vector completo de 44 features. Permite auditoría posterior y análisis de falsos positivos/negativos.

### 3.10 CloudWatch Dashboard

**Qué hace:** Panel de observabilidad de la PoC con tres widgets principales:

1. **Logs de intervenciones** — Tabla con las últimas 20 decisiones del Lambda Decisor, mostrando timestamp, session_id, score y nivel
2. **Distribución de scores** — Gráfica de la métrica custom `VishingScore` agrupada por nivel de intervención
3. **Latencia del pipeline** — Duración de ejecución de cada Lambda para monitorear performance

### 3.11 API Gateway WebSocket (opcional)

| Atributo | Valor |
|---|---|
| Rutas | `$connect`, `$disconnect`, `$default` |
| Tabla de conexiones | `ws_connections` en DynamoDB |

**Qué hace:** Canal de notificación push en tiempo real. Cuando el Lambda Decisor decide intervenir, envía un mensaje JSON al dispositivo conectado con el score, nivel, mensaje de intervención y las features que más contribuyeron al score. En la PoC actual, este componente es opcional — toda la información de detección está disponible en CloudWatch y en la tabla `fraud_alerts`.

---

## 4. Modelo de Machine Learning

### 4.1 Datos de entrenamiento

El modelo fue entrenado sobre un **dataset sintético de 50,000 sesiones** que simula los datos comportamentales que BioCatch recopila durante sesiones bancarias. El dataset fue aumentado y balanceado con técnicas de SMOTE para abordar el desbalance de clases.

### 4.2 Features

El modelo usa **44 features** agrupadas en 10 categorías: keystroke dynamics (5), touch dynamics (5), sensores del dispositivo (5), hesitación (6), navegación (3), errores y correcciones (5), cognitivo (2), sesión (4), contexto de riesgo (5), y transacción (4).

Las features más discriminativas según el EDA y el feature importance del modelo son:
- `phone_call_active` — Si hay llamada telefónica activa durante la sesión bancaria
- `segmented_typing_ratio` — Proporción de tecleo fragmentado (patrón de dictado)
- `hesitation_count` — Número de pausas significativas en la sesión
- `data_familiarity_score` — Score compuesto de familiaridad con los datos ingresados
- `session_duration_s` — Duración total de la sesión (vishing toma ~3.5x más)

### 4.3 Variables excluidas del modelo

Se excluyeron del entrenamiento las siguientes variables para evitar data leakage:
- Scores de BioCatch (`biocatch_risk_score`, `biocatch_genuine_score`, indicadores) — son outputs de otro modelo, no inputs
- Metadata post-evento (`days_to_claim`, `claim_category`) — información que no existiría en tiempo real
- Variables redundantes o de bajo valor (`screens_visited`, `unusual_screen_visits`, `interactions_per_s`, `is_synthetic`)

### 4.4 Wrapper

El modelo se distribuye como un `VishingModelWrapper` que encapsula modelo + scaler + features + umbral en un solo archivo `.pkl`, almacenado en S3.

---

## 5. Seguridad

| Capa | Mecanismo | Protege |
|---|---|---|
| Simulador → API Gateway | API Key en header `x-api-key` | Acceso no autorizado al endpoint de ingesta |
| API Gateway | Usage Plan con throttling (100 req/s) | Abuso / DDoS |
| Lambda Procesador → Model Server | API Key en header `X-API-Key` | Acceso no autorizado al modelo |
| Model Server EC2 | Security Group (puerto 8000) | Exposición de red |
| DynamoDB | IAM Role (solo Lambdas autorizadas) | Acceso a datos de sesión y alertas |
| S3 (modelos) | IAM Role EC2 (read-only) | Acceso al wrapper del modelo |
| Session state | TTL 60 minutos | Retención innecesaria de datos |

---

## 6. Costos

| Componente | Costo 24/7 | Costo testing (~20h/mes) |
|---|---|---|
| EC2 t3.small (model server) | $15.18/mes | ~$0.42/mes |
| EC2 t3.micro (simulador) | $7.59/mes | ~$0.21/mes |
| API Gateway | ~$2.00/mes | ~$0.50/mes |
| Lambda (4 funciones) | ~$3.00/mes | ~$0.50/mes |
| SQS FIFO | ~$0.00/mes | ~$0.00/mes |
| DynamoDB (3 tablas) | ~$3.00/mes | ~$0.50/mes |
| CloudWatch | ~$5.00/mes | ~$2.00/mes |
| S3 | ~$0.05/mes | ~$0.05/mes |
| **Total** | **~$36/mes** | **~$4/mes** |

---

*Área de Innovación · Arquitectura de Innovación · 2025*
