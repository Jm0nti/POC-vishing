# Detección de Vishing con Datos Biométricos Sintéticos

## Contexto General

Este proyecto es un **pipeline de machine learning para detección de sesiones de vishing** (voice phishing) en una aplicación bancaria, usando datos biométricos de comportamiento sintéticos generados con ayuda de IA generativa.

El dataset original fue construido a partir de supuestos del proveedor **BioCatch**, especializado en datos comportamentales para detección de fraude en banca. BioCatch captura señales como dinámica de teclado, presión táctil, movimiento del dispositivo y patrones de navegación para identificar comportamientos anómalos durante sesiones bancarias.

El objetivo es detectar si un usuario está siendo víctima de vishing: una llamada telefónica en la que un atacante lo guía para realizar una transferencia fraudulenta mientras está activo en la app bancaria. La dificultad estructural del problema es que el usuario opera legítimamente su app, con su dispositivo y credenciales; lo único que difiere es **cómo** interactúa: escribe más lento, hace pausas mientras escucha instrucciones, corrige más campos y tiende a montos más altos.

---

## Dataset Original

| Característica | Valor |
|---|---|
| Fuente | Dataset sintético generado con IA generativa (Claude) |
| Sesiones totales | 50,000 |
| Sesiones legítimas | 47,500 (95%) |
| Sesiones vishing (fraude) | 2,500 (5%) |
| Clientes únicos | 19,782 |
| Sesiones por cliente (promedio) | 2.53 |
| Variables totales | 61 columnas |
| Periodo simulado | Junio 2024 – Mayo 2025 |
| Archivo | `raw_data/biocatch_sinthetic_data.csv` |

El diccionario completo de variables se encuentra en `raw_data/diccionario_datos_biocatch_sintetico.md`.

### ¿Cómo se creó el dataset?

BioCatch publica información general sobre los vectores de comportamiento que utiliza para detectar fraude en banca, pero **no divulga las variables exactas ni la forma en la que las computa**. A partir de la documentación pública sobre sus indicadores de riesgo (particularmente para vishing e ingeniería social), se diseñó un conjunto de 61 variables que cubren ocho grupos funcionales y se generó un dataset sintético en el que las sesiones simulan tanto comportamientos legítimos como fraudulentos, usando IA generativa (Claude) como asistente en la construcción.

### Grupos de Variables

1. **Dinámica de teclado (5 variables).** Velocidad de escritura, latencia entre teclas, variabilidad y ratio de escritura segmentada. En sesiones de vishing el usuario escribe más despacio y de forma segmentada porque está dictando lo que le indica el atacante por teléfono.

2. **Dinámica táctil (5 variables).** Presión, tamaño de toque, velocidad y varianza de swipes. En vishing suelen ser más erráticos.

3. **Movimiento del dispositivo (5 variables).** Ángulo de inclinación, giroscopio, acelerómetro, eventos de movimiento. Mayor variabilidad en sesiones fraudulentas por el estado de tensión del usuario.

4. **Señales de hesitación (3 variables).** Cantidad y duración de pausas. Uno de los mejores indicadores: el usuario en vishing duda antes de ejecutar acciones porque está esperando instrucciones.

5. **Tiempo muerto / inactividad (3 variables).** Períodos sin interacción. Capturan el tiempo en que el usuario está escuchando al atacante por teléfono.

6. **Navegación en la app (3 variables).** Pantallas visitadas, conteo de navegación hacia atrás, tiempo de transición. En vishing el usuario puede navegar de forma inusual siguiendo instrucciones.

7. **Errores y correcciones (4 variables).** Errores de entrada, correcciones en campos de monto y beneficiario, eventos de copiar/pegar. Alta frecuencia en vishing porque el usuario está transcribiendo datos dictados.

8. **Contexto de sesión (5 variables).** Duración, hora del día, si hay llamada telefónica activa, detección de herramientas de acceso remoto, apps sospechosas detectadas.

9. **Datos de transacción (4 variables).** Monto, si el beneficiario es nuevo, tiempo hasta la transacción. Las sesiones de vishing tienden a tener montos más altos y beneficiarios nuevos.

10. **Features derivadas y de BioCatch (excluidas del modelado).** `biocatch_risk_score`, `biocatch_genuine_score` y similares se excluyen porque generarían data leakage. `session_id`, `customer_id`, `session_timestamp` e identificadores también se eliminan.

**Variables finales para modelado: 44**

---

## Estructura del Pipeline

El proyecto se estructura en tres fases principales, más una rama exploratoria con AutoML:

```
┌────────────────────────────────────────────────────────────────┐
│ FASE 1 — Dataset original (50K sesiones, ejecución local)      │
└────────────────────────────────────────────────────────────────┘
        ↓
  1_EDA.ipynb
  2_Data_Balancing_Pipeline.ipynb
  3_Modeling_Vishing_Pipeline.ipynb

┌────────────────────────────────────────────────────────────────┐
│ FASE 2 — Data augmentation con CTGAN y reentrenamiento         │
│          (AWS SageMaker)                                       │
└────────────────────────────────────────────────────────────────┘
        ↓
  4_Biocatch_data_augmentation_CTGAN.ipynb
  5_EDA_augmented_data.ipynb
  6_Data_Balancing_AD_Pipeline.ipynb
  7_Modeling_Vishing_AD.ipynb

┌────────────────────────────────────────────────────────────────┐
│ FASE 3 — Experimentación dirigida con XGBoost (AWS SageMaker)  │
└────────────────────────────────────────────────────────────────┘
        ↓
  8_XGBoost_training.ipynb

┌────────────────────────────────────────────────────────────────┐
│ RAMA EXPLORATORIA — AutoML con AutoGluon                       │
│                     (AWS SageMaker, no adoptada)               │
└────────────────────────────────────────────────────────────────┘
        ↓
  AutoML_Vishing_AutoGluon_EN.ipynb
```

---

## Descripción de cada Notebook

### 1. `1_EDA.ipynb` — Análisis Exploratorio (local)

**Entrada:** `raw_data/biocatch_sinthetic_data.csv` (50K sesiones)

Análisis exploratorio integral del dataset original. Cubre:

- Validación de integridad: nulos, duplicados, tipos, rangos por variable. Sin nulos, sin duplicados, todos los rangos dentro de lo esperado.
- Distribución del target y variables categóricas (device, claim category, hora del día, mes).
- Análisis univariante por clase con histogramas para los grupos físico (keystroke, touch), cognitivo (hesitación, familiaridad) y de sesión (correcciones, navegación).
- Tests estadísticos de separabilidad: Mann-Whitney U, Cohen's d, correlación punto-biserial y AUC univariante por variable.
- Análisis de variables binarias con chi-cuadrado y odds ratio.
- Boxplots comparativos por clase para las Top 12 features por AUC.
- Análisis de correlación (heatmap y detección de pares con |r| > 0.7).
- Perfil comportamental comparativo (radar chart y tabla mediana por clase).
- Análisis de transacciones (distribución de montos, beneficiario nuevo, tiempo hasta la transacción).
- PCA a 10 componentes: scree plot, proyección 2D y análisis de loadings en PC1/PC2.
- Detección de outliers por IQR con enriquecimiento vs. tasa de vishing.
- Random Forest rápido con validación cruzada como estimador preliminar de importancia (CV AUC ≈ 0.88).

**Hallazgos clave.** Las features más discriminativas por AUC univariante son `phone_call_active`, `segmented_typing_ratio`, `hesitation_count`, `data_familiarity_score` e `input_correction_count`. Las sesiones de vishing exhiben tipeo más lento y segmentado, más hesitaciones y correcciones, y montos de transacción 2–3× más altos (mediana 384K COP vs 136K COP en legítimas). Chi-cuadrado y odds ratio confirman que `phone_call_active` (OR≈2.01), `remote_access_tool_detected` (OR≈2.57), `suspicious_app_detected` (OR≈2.05) e `is_new_beneficiary` (OR≈1.76) son significativas al 99.9%.

---

### 2. `2_Data_Balancing_Pipeline.ipynb` — Balanceo del dataset original (local)

**Entrada:** `raw_data/biocatch_sinthetic_data.csv` (desbalance 95%:5%)
**Salida:** 12 datasets balanceados en `data/balanced/original/{técnica}/{ratio}.csv`

Aplica cuatro técnicas de re-muestreo con tres ratios de vishing objetivo (10%, 20%, 25%):

| Técnica | Descripción |
|---|---|
| **Random Oversampling** | Duplica observaciones de la clase minoritaria. |
| **SMOTE** | Genera muestras sintéticas por interpolación k-NN. |
| **Borderline SMOTE** | SMOTE enfocado en ejemplos de frontera de decisión. |
| **SMOTE + Undersampling** | Híbrido: reduce mayoritaria ~10% y aplica SMOTE en la minoritaria. |

Se generan las 12 variantes (4 técnicas × 3 ratios) que serán insumo del modelado.

---

### 3. `3_Modeling_Vishing_Pipeline.ipynb` — Modelado sobre datos originales (local)

**Entrada:** 12 datasets balanceados + holdout del 20% (10K sesiones sin balancear).
**Salida:** Tabla comparativa de métricas y matriz de confusión del mejor modelo.

Entrena cuatro algoritmos sobre cada uno de los 12 datasets balanceados:

| Modelo | Hiperparámetros |
|---|---|
| Regresión Logística | `max_iter=1000` |
| Random Forest | `n_estimators=150`, `max_depth=10` |
| XGBoost | `max_depth=6`, `learning_rate=0.1`, `eval_metric='logloss'` |
| MLP (red neuronal) | Capas ocultas 64→32, 300 iteraciones |

Se evalúa sobre el holdout imbalanceado (9,500 legítimas + 500 vishing) con las métricas Recall, Precisión, F1, ROC-AUC y PR-AUC.

**Mejor resultado.** XGBoost con SMOTE + Undersampling al 10% en holdout:

| Métrica | Valor |
|---|---|
| Recall | 0.9400 |
| Precisión | 0.9419 |
| F1 | 0.9409 |
| ROC-AUC | 0.9988 |
| PR-AUC | 0.9848 |

TN = 9,471 · FP = 29 · FN = 30 · TP = 470. La calidad tan alta se explica en parte por la homogeneidad estadística del dataset sintético; las Fases 2 y 3 introducen mayor exigencia con más datos y desbalance real.

---

### 4. `4_Biocatch_data_augmentation_CTGAN.ipynb` — Augmentación con CTGAN (AWS SageMaker)

**Entrada:** `raw_data/biocatch_sinthetic_data.csv` (50K sesiones).
**Salida:** `data/augmented_data/dataset_1M_vishing_ctgan.parquet` (1M sesiones).

Es el paso más técnico del pipeline. Genera 1 millón de sesiones sintéticas preservando la estructura estadística del dataset original mediante **CTGAN** (Conditional Tabular GAN), el estado del arte para generación de datos tabulares mixtos con features numéricas y categóricas.

**Motivación.** Una implementación previa basada en copula gaussiano con quantile matching y jitter aditivo era trivialmente distinguible: un clasificador simple sobre originales vs. sintéticos alcanzaba AUC = 1.00 porque el copula no capturaba las dependencias no lineales y el jitter sobre features positivas sesgadas dejaba una firma detectable en las colas. CTGAN aprende directamente las dependencias por adversarial training con condicionamiento por modo, y en la práctica reduce el AUC de distinguibilidad al rango 0.55–0.70.

**Estrategia.** Un CTGAN por clase (legit y vishing) usando el filtrado a dispositivos `mobile` (42,579 sesiones: 40,452 legítimas + 2,127 vishing) debido a que existen atributos no aplicables a dispositivos desktop y para el contexto del problema sólo interesa analizar comportamiento en dispotivos móviles
. La clase minoritaria tiene solo 2,127 muestras y necesita hiperparámetros específicos.

**Hiperparámetros de CTGAN (SDV 1.5, entrenado en GPU Tesla T4):**

| Clase | epochs | batch_size | pac | generator_dim | discriminator_dim | embedding_dim | lr |
|---|---|---|---|---|---|---|---|
| Legit   | 300 | 500 | 10 | (256, 256) | (256, 256) | 128 | 2e-4 |
| Vishing | 800 | 250 |  5 | (128, 128) | (128, 128) |  64 | 1e-4 |

La configuración de vishing es más conservadora: red más pequeña (menos overfitting con muestras escasas), `pac` menor (packing de menos filas por evaluación del crítico), batch más pequeño y más épocas para convergencia estable con menos pasos por época.

**Metadata SDV.** Las binarias (`phone_call_active`, `remote_access_tool_detected`, `suspicious_app_detected`, `transaction_attempted`, `is_new_beneficiary`) se declaran como `categorical` para que CTGAN use el condicional discreto (más estable que tratarlas como continuas).


**Post-procesamiento tras la generación.** CTGAN produce marginales razonables pero no respeta consistencias lógicas ni constraints de dominio, por lo que se aplica un pipeline post-generación:

- **Constraints de dominio:** clip de ratios a [0,1], enteros no negativos redondeados, binarias en {0,1}, `hour_of_day` en [0,23], `device_tilt_angle_mean` en [0,90].
- **Consistencias lógicas:** `is_atypical_hour` derivada por regla desde `hour_of_day` ∈ {22,23,0,1,2,3,4,5}; `unique_screens_visited ≤ screens_visited`; `call_overlap_duration_s = 0` si `phone_call_active = 0`; `transaction_amount_cop`, `time_to_transaction_s` e `is_new_beneficiary` a 0 si `transaction_attempted = 0`; `avg_hesitation_duration_s` y `max_hesitation_duration_s` a 0 si `hesitation_count = 0`; `total_dead_time_s` y `dead_time_ratio` a 0 si `dead_time_periods = 0`.
- **Indicadores BioCatch por condicional empírica** (`biocatch_ato_indicator`, `biocatch_social_eng_indicator`, `biocatch_bot_indicator`): tablas de probabilidad por decil de `biocatch_risk_score`, estimadas sobre el dataset original.
- **Features derivadas recalculadas** desde las variables generadas: `errors_per_minute`, `interactions_per_s`, `hesitation_composite`.
- **Metadatos de sesión** (`session_id`, `customer_id`, `session_timestamp`, `device_type='mobile'`, `os_type`, `app_version`, `days_to_claim` y `claim_category`): añadidos post con distribuciones muestrales del dataset original para la clase correspondiente.
- **Flag `is_synthetic`:** todas las filas generadas por CTGAN quedan marcadas con 1 y las originales retenidas con 0 (permite auditar y hacer splits controlados).

**Composición del dataset aumentado (1M):**

- 40,452 sesiones legítimas originales (retenidas intactas).
- 944,548 sesiones legítimas generadas por CTGAN.
- 2,127 sesiones vishing originales (retenidas intactas).
- 12,873 sesiones vishing generadas por CTGAN.
- **Desbalance resultante:** 1.5% vishing (más cercano a la realidad productiva que el 5% original), 62 columnas (61 originales + `is_synthetic`).

Los sintetizadores CTGAN entrenados se serializan y suben a S3 (`s3://poc-fraude-vishing/models/ctgan_legit.pkl` y `ctgan_vishing.pkl`) para poder regenerar datos sin re-entrenar.

---

### 5. `5_EDA_augmented_data.ipynb` — EDA sobre datos aumentados (local)

**Entrada:** `data/augmented_data/dataset_1M_vishing_ctgan.parquet` + dataset original 50K para comparación.

Valida la calidad de la augmentación por CTGAN y caracteriza el nuevo dataset:

- **Integridad:** sin nulos, sin `session_id` duplicados, 89,999 clientes únicos, rango temporal 2024-06-01 → 2025-05-31.
- **Análisis de `is_synthetic`:** proporción global 95.74% sintéticas vs. 4.26% originales. Contingencia con `is_vishing`: chi² = 3,675, OR = 0.259.
- **Rangos:** todas las variables dentro de sus rangos válidos tras el post-procesamiento.
- **Distribuciones por clase** (subsampled a 50K legítimas + todas las vishing): comportamiento físico, cognitivo, sesión.
- **Separabilidad estadística sobre subsample de 115K filas:** 3 features con efecto grande (|d| ≥ 0.8), 10 medio (≥ 0.5), 23 pequeño (≥ 0.2), 17 negligible. Significancia: 52 de 54 con p < 0.001.
- **Variables binarias.** `is_new_beneficiary` OR = 2.24, `phone_call_active` OR = 1.63, `suspicious_app_detected` OR = 1.53, `transaction_attempted` OR = 1.36, `remote_access_tool_detected` OR = 1.28. `is_atypical_hour` cambia dirección a OR = 0.82 (contraintuitivo pero se explica por el ruido introducido por CTGAN en la variable derivada por regla).
- **Correlación.** 4 pares con |r| > 0.7 (multicolinealidad con derivadas): `input_error_count` ↔ `errors_per_minute` (1.00), `hesitation_count` ↔ `hesitation_composite` (0.99), y dos con `interactions_per_s`.
- **Perfil comportamental comparativo** por mediana: mismo patrón que en el original, con `transaction_amount_cop` en vishing ≈ 379K vs 167K en legítimas.
- **PCA:** primeras 5 componentes explican 36.8% de varianza; 10 componentes explican 48.3%. PC1 está dominado por señales cognitivas (`interactions_per_s`, `hesitation_count`, `hesitation_composite`, `dead_time_periods`, `segmented_typing_ratio`); PC2 por transacción (`time_to_transaction_s`, `transaction_attempted`, `is_new_beneficiary`).
- **Outliers por IQR:** `errors_per_minute` enriquece vishing a 12.9% (vs 1.5% global); `interactions_per_s` a 4.8%.
- **Feature importance preliminar.** Random Forest sobre subsample estratificado (155K filas: 15K vishing + 140K legítimas) con CV-AUC = 1.0000 ± 0.0000, confirmando separabilidad extrema en el dataset aumentado.

**Validación vs. original (test Kolmogorov-Smirnov sobre subsample de 50K):**

| Feature | KS | Interpretación |
|---|---|---|
| `session_duration_s` | 0.0000 | Idéntica |
| `avg_keyhold_ms` | 0.047 | Excelente preservación |
| `hesitation_count` | 0.048 | Excelente |
| `unusual_screen_visits` | 0.051 | Excelente |
| `input_correction_count` | 0.070 | Muy buena |
| `transaction_amount_cop` | 0.071 | Muy buena |
| `segmented_typing_ratio` | 0.078 | Buena |
| `typing_speed_cps` | 0.079 | Buena |
| `total_dead_time_s` | 0.086 | Buena |
| `data_familiarity_score` | 0.127 | Drift leve |

CTGAN preserva las distribuciones marginales dentro del rango de fidelidad esperado; solo `data_familiarity_score` presenta drift leve (KS > 0.10). Los deltas de Cohen's d y AUC univariante entre original y aumentado son moderados y no cambian el signo del efecto en ninguna variable relevante.

---

### 6. `6_Data_Balancing_AD_Pipeline.ipynb` — Balanceo sobre datos aumentados (local)

**Entrada:** `data/augmented_data/dataset_1M_vishing_ctgan.parquet` (1M, desbalance 98.5%:1.5%).
**Salida:** 12 datasets balanceados en `data/balanced/augmented/{técnica}/{ratio}.parquet`.

Aplica las mismas cuatro técnicas de re-muestreo en los mismos tres ratios objetivo (10%, 20%, 25%) que en el Notebook 2, pero ahora sobre el dataset de 1M sesiones. Se usa el formato parquet para mayor eficiencia a esta escala.

| Técnica | Tamaño resultante aprox. |
|---|---|
| Random Oversampling | 1.09M – 1.31M filas |
| SMOTE | 1.09M – 1.31M filas |
| Borderline SMOTE | 1.09M – 1.31M filas |
| SMOTE + Undersampling | 985K – 1.18M filas |

---

### 7. `7_Modeling_Vishing_AD.ipynb` — Modelado multi-algoritmo sobre datos aumentados (AWS SageMaker)

**Entrada:** 12 datasets balanceados del Notebook 6 (S3) + dataset raw 1M como 13.° dataset + holdout de 200K sesiones extraído del 1M con `stratify` y desbalance real (~1.5% vishing).
**Salida:** 52 modelos serializados en S3 como `VishingModelWrapper`.

Entrena cuatro algoritmos sobre cada uno de los 13 datasets (12 balanceados + 1 raw), con MLP reescrito en PyTorch para aprovechar GPU CUDA.

| Modelo | Hiperparámetros |
|---|---|
| Regresión Logística | `max_iter=1000` |
| Random Forest | `n_estimators=150`, `max_depth=10`, `n_jobs=-1` |
| XGBoost | `tree_method='hist'`, `device='cuda'`, `max_depth=6`, `lr=0.1` |
| MLP (PyTorch) | 64→32, `max_iter=30`, `batch_size=4096`, GPU |

**Umbral óptimo.** Para cada modelo se calcula el umbral que maximiza F1 sobre la curva Precision-Recall del holdout, en lugar de fijarlo en 0.5.

**Innovación de ingeniería — `VishingModelWrapper`.** Clase de empaquetado que resuelve el problema de reproducibilidad de inferencia. Encapsula en un único artefacto serializado con `joblib`:

- El modelo entrenado.
- El scaler `StandardScaler` (solo para Logística y MLP; los modelos basados en árboles se guardan sin scaler).
- La lista exacta de features en el orden correcto.
- El umbral óptimo de clasificación calculado por maximización de F1.
- Metadatos: nombre del modelo, técnica y ratio.

Expone tres métodos:

- `predict(json)` → etiqueta binaria 0/1.
- `predict_proba_raw(json)` → `{legitimate: float, vishing: float}`.
- `predict_full(json)` → dict completo con etiqueta, probabilidades y umbral usado.

Acepta como entrada un dict Python, string JSON o lista de dicts (batch). Valida features faltantes y lanza `ValueError` explícito, sin fallos silenciosos. Los modelos se almacenan en `s3://poc-fraude-vishing/proyecto/modelos/{técnica}/{ratio}/{modelo}.pkl`.

**Mejor resultado — XGBoost + Random Oversampling 10%:**

| Métrica | Valor |
|---|---|
| PR-AUC | 0.7511 |
| Recall | 0.6530 |
| Precisión | 0.7572 |
| F1 | 0.7013 |
| ROC-AUC | 0.9784 |
| Umbral óptimo | 0.5921 |

TN = 196,372 · FP = 628 · FN = 1,041 · TP = 1,959 sobre 200K de holdout.

**Feature importance (Top 15 XGBoost por Gain).** El orden cambia respecto al dataset original: `gyro_rotation_rate_mean` (0.118), `dead_time_ratio` (0.085), `keystroke_variability` (0.066), `hour_of_day` (0.065), `dead_time_periods` (0.039), `device_tilt_variability` (0.037), `beneficiary_field_corrections` (0.032), `segmented_typing_ratio` (0.032), `transaction_amount_cop` (0.028), `avg_interkey_latency_ms` (0.027), `avg_touch_pressure` (0.027), `navigation_back_count` (0.027), `doodling_events` (0.026), `hesitation_count` (0.026), `call_overlap_duration_s` (0.025).

XGBoost domina consistentemente sobre las demás familias, motivando la exploración dirigida de la Fase 3.

---

### 8. `8_XGBoost_training.ipynb` — Experimentación dirigida con XGBoost (AWS SageMaker)

**Entrada:** 13 datasets de data aumentada (12 balanceados + raw 1M) + 13 datasets de data original (12 balanceados + raw 50K).
**Salida:** 182 modelos serializados en S3 como `VishingModelWrapper`.

Confirmado XGBoost como el algoritmo dominante, este notebook explora **7 variantes hiperparamétricas** entrenadas sobre ambos tipos de dataset con holdouts separados:

- Holdout de datos aumentados: 200K sesiones (desbalance 1.5% vishing).
- Holdout de datos originales: 10K sesiones (desbalance 5% vishing).

**Variantes exploradas:**

| Variante | Descripción |
|---|---|
| `xgb_base` | Configuración de la Fase 2 (línea base). |
| `xgb_deep` | Árboles profundos (`max_depth=9`), 300 estimadores, `lr=0.05`, `min_child_weight=3`. |
| `xgb_shallow` | Árboles poco profundos (`max_depth=3`), 500 estimadores (boosting clásico). |
| `xgb_regularized` | Regularización fuerte (L1=1.0, L2=5.0, `min_child_weight=10`, `gamma=0.3`). |
| `xgb_balanced` | `scale_pos_weight = n_neg/n_pos` calculado por dataset en tiempo de entrenamiento. |
| `xgb_conservative` | Subsampling agresivo (`subsample=0.7`, `colsample_bytree=0.7`, `gamma=0.5`). |
| `xgb_slow_learner` | Aprendizaje lento (`lr=0.01`, 500 estimadores, `subsample=0.8`). |

**Total:** 7 variantes × 13 datasets × 2 tipos = **182 modelos**, todos empaquetados en `VishingModelWrapper` y subidos a `s3://poc-fraude-vishing/proyecto/modelos_xgb/{tipo_data}/{variante}/{técnica}/{ratio}.pkl`.

Todos los modelos se entrenaron con `tree_method='hist'` y `device='cuda'`.

**Resultados consolidados por tipo de dato:**

| Tipo dato | Mejor variante | Técnica | Ratio | PR-AUC | Recall | F1 |
|---|---|---|---|---|---|---|
| Original (50K)  | `xgb_deep` | Random Oversampling | 25% | **0.9484** | 0.878 | 0.902 |
| Aumentado (1M)  | `xgb_deep` | Random Oversampling | 20% | 0.8964     | 0.810 | 0.822 |

**Mejor modelo global.** `xgb_deep` sobre datos originales, Random Oversampling 25%, umbral 0.7264:

- TN = 9,466 · FP = 34 · FN = 61 · TP = 439 (holdout de 10K, 500 vishing).
- Recall = 0.878, Precisión = 0.928, F1 = 0.902, PR-AUC = 0.9484.

Análisis incluidos: tabla de las 182 combinaciones ordenada por PR-AUC, mejor configuración por variante y tipo de data, comparación visual por métrica (PR-AUC, Recall, F1, ROC-AUC), heatmap `variante × técnica de balanceo` por tipo de data, matriz de confusión y feature importance del mejor modelo, curva Precision-Recall con óptimo F1, y una tabla CSV con todos los resultados subida a `s3://poc-fraude-vishing/proyecto/modelos_xgb/resultados_xgb_experimento.csv`.

**Observación relevante.** El modelo de datos originales obtiene métricas más altas que el de datos aumentados, en parte porque su holdout tiene un desbalance del 5% (más fácil) frente al 1.5% del holdout aumentado. Ambos holdouts representan situaciones útiles: el original marca el techo teórico bajo condiciones favorables, y el aumentado se acerca más a la prevalencia realista en producción.

---

### AutoML — `AutoML_Vishing_AutoGluon_EN.ipynb` (rama exploratoria, no adoptada)

**Objetivo.** Verificar si un flujo AutoML podía superar los resultados obtenidos con la experimentación manual multi-algoritmo y el fine-tuning dirigido de XGBoost.

**Estrategia de split (crítica en este caso).**

- Se separan sesiones originales (`is_synthetic=0`, 42,579) de sintéticas (`is_synthetic=1`, 957,421).
- Los originales se dividen 40/30/30: 17,031 train / 12,774 val / 12,774 test.
- El train mixto suma **974,452 filas** (train de originales + todas las sintéticas).
- Val y test son **100% originales**, con tasa de vishing ≈ 5%.
- Esto asegura que la evaluación se hace exclusivamente sobre las 2,127 sesiones vishing originales (no sobre las 12,873 sintéticas), midiendo lo que realmente importa: generalización a data real.

**Configuración de AutoGluon.**

- `TabularPredictor` con `problem_type='binary'` y `eval_metric='average_precision'` (optimiza PR-AUC).
- `presets='best_quality'` (stacking multi-nivel, bagging y búsqueda de hiperparámetros).
- `time_limit=5400` segundos (90 min) sobre GPU Tesla T4.
- `use_bag_holdout=True`, `num_bag_folds=8`, `num_stack_levels=1`.

**Resultados obtenidos (leaderboard de 14 modelos).**

| Modelo | PR-AUC test | ROC-AUC test | Recall @ P=0.90 | Brier |
|---|---|---|---|---|
| `WeightedEnsemble_L3` | 0.1076 | 0.6667 | 0.0000 | 0.0567 |
| `CatBoost_BAG_L2`     | 0.1075 | 0.6704 | 0.0000 | 0.0613 |
| `LightGBM_BAG_L2`     | 0.1063 | 0.6694 | 0.0000 | 0.0618 |
| `WeightedEnsemble_L2` | 0.1049 | 0.6632 | 0.0000 | 0.0542 |
| `LightGBM_BAG_L1`     | 0.1043 | 0.6691 | 0.0000 | 0.0594 |
| ... | ... | ... | ... | ... |
| `XGBoost_BAG_L1`      | 0.0642 | 0.5743 | 0.0000 | 0.0513 |

**Conclusión de la rama AutoML: no viable.**

Todos los modelos del leaderboard se ubican entre PR-AUC 0.06 y 0.11 con ROC-AUC ≈ 0.66, muy por debajo de los 0.75–0.95 obtenidos en los Notebooks 7 y 8. La métrica más operacional, `recall_at_precision=0.90`, es **cero** para toda la tabla: incluso el mejor ensemble no logra ninguna combinación umbral–modelo que produzca alertas con precisión ≥ 90%. El notebook no se ejecutó hasta el final (persistencia, permutation importance, SHAP, análisis de errores) porque las métricas del leaderboard descartaron por sí solas la estrategia.

**Diagnóstico probable.** El split usado por el flujo AutoML (train con 95% de filas sintéticas y evaluación 100% sobre originales) impone un salto de distribución que los modelos base (LightGBM, CatBoost, RandomForest) no consiguen cruzar sin ajuste específico, mientras que la iteración manual de los Notebooks 7 y 8 —con holdouts extraídos con `stratify` de la misma distribución de entrenamiento— produce PR-AUC 4–9× más alto. El experimento confirma el valor de la experimentación dirigida sobre la exploración automatizada en este dataset.

---

## Resumen de Ejecución por Notebook

| Notebook | Ejecución | Entrada principal | Salida principal |
|---|---|---|---|
| `1_EDA.ipynb`                          | Local | CSV 50K | Estadísticas, visualizaciones |
| `2_Data_Balancing_Pipeline.ipynb`      | Local | CSV 50K | 12 CSVs balanceados |
| `3_Modeling_Vishing_Pipeline.ipynb`    | Local | 12 CSVs + holdout 10K | Métricas + matriz de confusión |
| `4_Biocatch_data_augmentation_CTGAN.ipynb` | **AWS (GPU)** | CSV 50K | Parquet 1M + 2 CTGAN synthesizers en S3 |
| `5_EDA_augmented_data.ipynb`           | Local | Parquet 1M + CSV 50K | Análisis comparativo y validación KS |
| `6_Data_Balancing_AD_Pipeline.ipynb`   | Local | Parquet 1M | 12 parquets balanceados |
| `7_Modeling_Vishing_AD.ipynb`          | **AWS (GPU)** | 13 parquets + holdout 200K | 52 wrappers en S3 |
| `8_XGBoost_training.ipynb`             | **AWS (GPU)** | 26 datasets (orig + augm) | 182 wrappers XGBoost en S3 + CSV resultados |
| `AutoML_Vishing_AutoGluon_EN.ipynb`    | **AWS (GPU)** | Parquet 1M | Leaderboard (rama exploratoria) |

---

## Métrica Prioritaria: PR-AUC

Con desbalance de clases del orden 1.5%–5% en los holdouts, la ROC-AUC es engañosamente optimista porque penaliza poco los falsos positivos en presencia de una clase mayoritaria abrumadora. La **PR-AUC** (área bajo la curva Precisión–Recall) es la métrica de referencia del proyecto porque cuantifica directamente el trade-off entre detectar fraude (Recall) y la calidad de las alertas emitidas (Precisión). El umbral de clasificación se optimiza maximizando F1 sobre la curva PR y no se fija en 0.5, lo que explica que el umbral óptimo del mejor modelo global sea 0.7264.

---

## Estructura de Directorios

```
Vishing_synth_data_GenAI/
├── raw_data/
│   ├── biocatch_sinthetic_data.csv                    ← Dataset original (50K)
│   └── diccionario_datos_biocatch_sintetico.md        ← Diccionario de datos
├── data/
│   ├── augmented_data/
│   │   └── dataset_1M_vishing_ctgan.parquet           ← Dataset aumentado por CTGAN (1M)
│   └── balanced/
│       ├── original/                                  ← 12 variantes balanceadas del 50K
│       │   ├── random_oversampling/{10,20,25}.csv
│       │   ├── smote/{10,20,25}.csv
│       │   ├── borderline_smote/{10,20,25}.csv
│       │   └── smote_undersampling/{10,20,25}.csv
│       └── augmented/                                 ← 12 variantes balanceadas del 1M
│           ├── random_oversampling/{10,20,25}.parquet
│           ├── smote/{10,20,25}.parquet
│           ├── borderline_smote/{10,20,25}.parquet
│           └── smote_undersampling/{10,20,25}.parquet
├── ctgan_models/                                      ← CTGAN synthesizers serializados
│   ├── ctgan_legit.pkl
│   └── ctgan_vishing.pkl
├── modelos/                                           ← Modelos locales (espejo de S3)
├── automl_runs/                                       ← Corridas de AutoGluon (predictors + reports)
├── 1_EDA.ipynb
├── 2_Data_Balancing_Pipeline.ipynb
├── 3_Modeling_Vishing_Pipeline.ipynb
├── 4_Biocatch_data_augmentation_CTGAN.ipynb
├── 5_EDA_augmented_data.ipynb
├── 6_Data_Balancing_AD_Pipeline.ipynb
├── 7_Modeling_Vishing_AD.ipynb
├── 8_XGBoost_training.ipynb
├── AutoML_Vishing_AutoGluon_EN.ipynb
└── requirements.txt
```

Bucket S3 de referencia: `s3://poc-fraude-vishing/proyecto/`.
