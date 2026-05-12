# Diccionario de Datos — Dataset Sintético BioCatch para Detección de Vishing

## Información General

| Concepto | Detalle |
|---|---|
| Total de sesiones | 50,000 |
| Sesiones de vishing | 2,500 (5.0%) |
| Sesiones legítimas | 47,500 (95.0%) |
| Período simulado | Junio 2024 – Mayo 2025 |
| Columnas | 61 |

---

## 1. Identificadores y Contexto de Sesión

| Columna | Tipo | Descripción |
|---|---|---|
| `session_id` | string | ID único de sesión (SES-XXXXXX) |
| `customer_id` | string | ID del cliente (CUS-XXXXX). Un cliente puede tener múltiples sesiones |
| `session_timestamp` | datetime | Fecha y hora de inicio de la sesión |
| `device_type` | string | Tipo de dispositivo: `mobile` (85%) o `web` (15%) |
| `os_type` | string | Sistema operativo: Android, iOS, Windows, macOS |
| `app_version` | string | Versión de la app MiBancolombia simulada |

---

## 2. Keystroke Dynamics (Comportamiento Físico - Tecleo)

Simulan las señales que BioCatch recopila sobre cómo el usuario teclea. En sesiones de vishing, el tecleo es más lento, más variable y muestra patrones de dictado.

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `avg_keyhold_ms` | float | milisegundos | Duración promedio que una tecla se mantiene presionada |
| `avg_interkey_latency_ms` | float | milisegundos | Tiempo promedio entre presionar una tecla y la siguiente |
| `typing_speed_cps` | float | caracteres/seg | Velocidad de tecleo en caracteres por segundo |
| `keystroke_variability` | float | ratio (0-1) | Variabilidad en el ritmo de tecleo. Valores altos = tecleo irregular |
| `segmented_typing_ratio` | float | ratio (0-1) | Proporción de tecleo segmentado (patrón de dictado). **Señal clave de vishing**: el estafador dicta datos al cliente |

---

## 3. Touch Dynamics (Comportamiento Físico - Pantalla Táctil)

Señales capturadas por el SDK de BioCatch sobre cómo el usuario toca y desliza en la pantalla.

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `avg_touch_pressure` | float | ratio (0-1) | Presión promedio del dedo en pantalla |
| `avg_touch_size_px` | float | píxeles | Tamaño promedio del área de contacto del dedo |
| `swipe_speed_px_s` | float | píxeles/seg | Velocidad promedio de gestos de deslizamiento |
| `swipe_directional_variance` | float | ratio (0-1) | Variabilidad en la dirección de swipes. Alto = deslizamientos erráticos |
| `scroll_speed_avg` | float | píxeles/seg | Velocidad promedio de scroll |

---

## 4. Acelerómetro y Giroscopio (Sensores del Dispositivo)

BioCatch captura datos de los sensores del teléfono para perfilar cómo el usuario sostiene y mueve el dispositivo.

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `device_tilt_angle_mean` | float | grados (0-90) | Ángulo promedio de inclinación del dispositivo |
| `device_tilt_variability` | float | grados | Variabilidad en el ángulo de inclinación. Alto = movimiento nervioso |
| `gyro_rotation_rate_mean` | float | rad/s | Tasa promedio de rotación del dispositivo |
| `accelerometer_jerk_mean` | float | m/s³ | Cambio promedio de aceleración (sacudidas del teléfono) |
| `phone_motion_events` | int | conteo | Número de eventos de movimiento significativo del teléfono |

---

## 5. Señales Cognitivas — Hesitación

Indicadores de estados de duda, confusión o espera de instrucciones. **Centrales para detección de vishing.**

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `hesitation_count` | int | conteo | Número de pausas significativas (>1s) durante la sesión |
| `avg_hesitation_duration_s` | float | segundos | Duración promedio de cada hesitación |
| `max_hesitation_duration_s` | float | segundos | Hesitación más larga en la sesión |

---

## 6. Señales Cognitivas — Dead Time (Inactividad)

Períodos sin actividad en la sesión. En vishing, el cliente tiene largos períodos de inactividad mientras escucha instrucciones por teléfono.

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `dead_time_periods` | int | conteo | Número de períodos sin actividad (>3 segundos) |
| `total_dead_time_s` | float | segundos | Tiempo total de inactividad en la sesión |
| `dead_time_ratio` | float | ratio (0-1) | Proporción de la sesión en inactividad |

---

## 7. Señales Cognitivas — Navegación en la App

Cómo el usuario navega dentro de MiBancolombia. En vishing, el cliente navega erráticamente siguiendo instrucciones.

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `screens_visited` | int | conteo | Total de pantallas visitadas (incluye repeticiones) |
| `unique_screens_visited` | int | conteo | Pantallas únicas visitadas |
| `unusual_screen_visits` | int | conteo | Visitas a secciones que el usuario normalmente no accede |
| `navigation_back_count` | int | conteo | Número de veces que el usuario retrocede en la navegación |
| `screen_transition_time_avg_s` | float | segundos | Tiempo promedio entre cambio de pantalla |

---

## 8. Señales Cognitivas — Errores y Correcciones

Indicadores de que el usuario no está seguro de lo que ingresa. **Clave para vishing**: el cliente comete errores al ingresar datos dictados.

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `input_error_count` | int | conteo | Total de errores de entrada durante la sesión |
| `input_correction_count` | int | conteo | Total de correcciones realizadas |
| `amount_field_corrections` | int | conteo | Correcciones específicas en campos de monto |
| `beneficiary_field_corrections` | int | conteo | Correcciones en campos del beneficiario |
| `copy_paste_events` | int | conteo | Eventos de copiar/pegar durante la sesión |

---

## 9. Señales Cognitivas — Familiaridad y Doodling

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `data_familiarity_score` | float | ratio (0-1) | Score de familiaridad con los datos ingresados. Bajo = datos desconocidos para el usuario (dictados) |
| `doodling_events` | int | conteo | Movimientos de toque sin propósito (touch/mouse doodling), indica ansiedad o espera |

---

## 10. Contexto de Sesión

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `session_duration_s` | float | segundos | Duración total de la sesión |
| `hour_of_day` | int | hora (0-23) | Hora del día en que inició la sesión |
| `is_atypical_hour` | int | binario | 1 si la sesión fue en horario atípico (22:00–05:00) |
| `phone_call_active` | int | binario | **1 si había llamada telefónica activa durante la sesión.** Señal más fuerte de vishing (85% de sesiones vishing) |
| `call_overlap_duration_s` | float | segundos | Duración de la llamada superpuesta con la sesión bancaria |
| `remote_access_tool_detected` | int | binario | 1 si se detectó herramienta de acceso remoto (RAT) |
| `suspicious_app_detected` | int | binario | 1 si se detectó app sospechosa activa |

---

## 11. Datos de Transacción

| Columna | Tipo | Unidad | Descripción |
|---|---|---|---|
| `transaction_attempted` | int | binario | 1 si se intentó una transacción en la sesión |
| `transaction_amount_cop` | int | COP | Monto de la transacción en pesos colombianos |
| `is_new_beneficiary` | int | binario | 1 si el beneficiario de la transacción era nuevo |
| `time_to_transaction_s` | float | segundos | Tiempo desde inicio de sesión hasta la transacción |

---

## 12. Scores BioCatch Simulados

Simulan los outputs que BioCatch devuelve vía API al banco.

| Columna | Tipo | Rango | Descripción |
|---|---|---|---|
| `biocatch_risk_score` | int | 0–1000 | Score de riesgo general de la sesión |
| `biocatch_genuine_score` | int | 0–1000 | Score de confianza de que el usuario es genuino |
| `biocatch_ato_indicator` | int | binario | Indicador de Account Takeover |
| `biocatch_social_eng_indicator` | int | binario | Indicador de ingeniería social detectada |
| `biocatch_bot_indicator` | int | binario | Indicador de actividad de bot |

---

## 13. Features Derivadas

| Columna | Tipo | Descripción |
|---|---|---|
| `errors_per_minute` | float | Tasa de errores por minuto de sesión |
| `interactions_per_s` | float | Interacciones por segundo (flujo general) |
| `hesitation_composite` | float | Score compuesto: (hesitation_count × avg_duration) / session_duration |

---

## 14. Labels (Variable Objetivo + Metadata de Reclamo)

| Columna | Tipo | Descripción |
|---|---|---|
| `is_vishing` | int | **Variable objetivo**: 1 = sesión de vishing confirmado, 0 = sesión legítima |
| `days_to_claim` | int | Días entre la sesión y el reclamo del cliente (-1 si no aplica) |
| `claim_category` | string | Categoría del reclamo: `vishing`, `ingenieria_social_telefonica`, `fraude_telefono`, `none` |

---

## Notas sobre el Diseño del Dataset

1. **Distribuciones diferenciadas**: Cada feature fue generada con distribuciones distintas para sesiones legítimas vs. vishing, basadas en lo que la literatura de BioCatch documenta como indicadores de manipulación por ingeniería social.

2. **Correlaciones realistas simuladas**: Por ejemplo, sesiones de vishing tienden a tener simultáneamente llamada activa + tecleo segmentado + alta hesitación + sesión larga + beneficiario nuevo.

3. **Ruido intencional**: No todas las sesiones de vishing tienen todos los indicadores activos (hay overlap con sesiones legítimas), para simular la complejidad real del problema.

4. **Uso sugerido**: El campo `is_vishing` es la variable objetivo para entrenamiento supervisado. Los campos `biocatch_*_score` e `*_indicator` simulan los outputs actuales de BioCatch y pueden excluirse del feature set del modelo propio para evitar data leakage, o incluirse como features complementarios si el objetivo es construir un modelo que combine señales propias con las de BioCatch.
