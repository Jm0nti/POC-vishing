# Documentación del Proyecto: Detección de Vishing con Datos Biométricos Sintéticos

## Contexto General

Este proyecto es un **pipeline de machine learning para detección de sesiones de vishing** (voice phishing) en una aplicación bancaria, usando datos biométricos de comportamiento sintéticos generados con ayuda de Claude.

El dataset original fue construido a partir de supuestos del proveedor **BioCatch**, especializado en datos comportamentales para detección de fraude en banca. BioCatch captura señales como dinámica de teclado, presión táctil, movimiento del dispositivo y patrones de navegación para identificar comportamientos anómalos durante sesiones bancarias.

El objetivo es detectar si un usuario está siendo víctima de vishing: una llamada telefónica en la que un atacante lo guía para realizar una transferencia fraudulenta mientras está activo en la app bancaria.

---

## Dataset Original

| Característica | Valor |
|---|---|
| Fuente | Dataset sintético generado con Claude |
| Sesiones totales | 50,000 |
| Sesiones legítimas | 47,500 (95%) |
| Sesiones vishing (fraude) | 2,500 (5%) |
| Variables totales | 61 columnas |
| Periodo simulado | Junio 2024 – Mayo 2025 |
| Archivo | `raw_data/biocatch_sinthetic_data.csv` |

El diccionario completo de variables se encuentra en `raw_data/diccionario_datos_biocatch_sintetico.md`.

### Grupos de Variables

**1. Dinámica de teclado (5 variables)**
Velocidad de escritura, latencia entre teclas, variabilidad y ratio de escritura segmentada. En sesiones de vishing el usuario escribe más despacio y de forma segmentada porque está dictando lo que le indica el atacante por teléfono.

**2. Dinámica táctil (5 variables)**
Presión, tamaño de toque, velocidad y varianza de swipes. En vishing suelen ser más erráticos.

**3. Movimiento del dispositivo (5 variables)**
Ángulo de inclinación, giroscopio, acelerómetro, eventos de movimiento. Mayor variabilidad en sesiones fraudulentas por el estado de tensión del usuario.

**4. Señales de hesitación (3 variables)**
Cantidad y duración de pausas. Uno de los mejores indicadores: el usuario en vishing duda antes de ejecutar acciones porque está esperando instrucciones.

**5. Tiempo muerto / inactividad (3 variables)**
Periodos sin interacción. Capturan el tiempo en que el usuario está escuchando al atacante por teléfono.

**6. Navegación en la app (3 variables)**
Pantallas visitadas, conteo de navegación hacia atrás, tiempo de transición. En vishing el usuario puede navegar de forma inusual siguiendo instrucciones.

**7. Errores y correcciones (4 variables)**
Errores de entrada, correcciones en campos de monto y beneficiario, eventos de copiar/pegar. Alta frecuencia en vishing porque el usuario está transcribiendo datos dictados.

**8. Contexto de sesión (5 variables)**
Duración, hora del día, si hay llamada telefónica activa, detección de herramientas de acceso remoto, apps sospechosas detectadas.

**9. Datos de transacción (4 variables)**
Monto, si el beneficiario es nuevo, tiempo hasta la transacción. Las sesiones de vishing tienden a tener montos más altos y beneficiarios nuevos.

**10. Features derivadas y de BioCatch (excluidas del modelado)**
`biocatch_risk_score`, `biocatch_genuine_score` y similares se excluyen porque generarían data leakage. `session_id`, `customer_id`, `session_timestamp` e identificadores también se eliminan.

**Variables finales para modelado: 44**

---

## Estructura del Pipeline

El proyecto tiene tres fases principales:

```
┌────────────────────────────────────────────────────────────────┐
│ FASE 1 — Dataset original (50K sesiones, ejecución local)      │
└────────────────────────────────────────────────────────────────┘
        ↓
  1_EDA.ipynb
  2_Data_Balancing_Pipeline.ipynb
  3_Modeling_Vishing_Pipeline.ipynb

┌────────────────────────────────────────────────────────────────┐
│ FASE 2 — Data augmentation y reentrenamiento (AWS SageMaker)   │
└────────────────────────────────────────────────────────────────┘
        ↓
  4_Biocatch_data_augmentation_AWS.ipynb
  5_EDA_augmented_data.ipynb
  6_Data_Balancing_AD_Pipeline.ipynb
  7_Modeling_Vishing_AD_AWS_exec v2.ipynb

┌────────────────────────────────────────────────────────────────┐
│ FASE 3 — Validación e inferencia                               │
└────────────────────────────────────────────────────────────────┘
        ↓
  Get_Features_List.ipynb
  8_Inference_Test v2.ipynb
```

---

## Descripción de cada Notebook

### 1. `1_EDA.ipynb` — Análisis Exploratorio (local)

**Entrada:** `raw_data/biocatch_sinthetic_data.csv` (50K sesiones)

Realiza un análisis exploratorio completo del dataset original:

- Validación de integridad (nulos, duplicados, tipos, rangos)
- Comparación de distribuciones entre sesiones legítimas y de vishing
- Tests de Mann-Whitney U y Cohen's d para identificar features discriminativas
- AUC univariante por variable → top 20 features por poder predictivo
- Análisis de correlaciones para detectar multicolinealidad
- Visualizaciones bivariadas, radar chart de perfiles comportamentales
- PCA para visualizar separabilidad en 2D
- Random Forest rápido con validación cruzada (AUC ≈ 0.88)

**Hallazgos clave:** Las features más discriminativas son `phone_call_active`, `segmented_typing_ratio`, `hesitation_count`, `data_familiarity_score` e `input_correction_count`. Las sesiones de vishing tienen tipeo más lento, más hesitaciones y montos de transacción 1.5-2× más altos.

---

### 2. `2_Data_Balancing_Pipeline.ipynb` — Balanceo de datos originales (local)

**Entrada:** `raw_data/biocatch_sinthetic_data.csv` (desbalance 95%:5%)
**Salida:** 12 datasets balanceados en `data/balanced/original/`

Aplica 4 técnicas de resampling en 3 ratios de vishing objetivo (10%, 20%, 25%):

| Técnica | Descripción |
|---|---|
| **Random Oversampling** | Duplica observaciones de la clase minoritaria |
| **SMOTE** | Genera muestras sintéticas por interpolación k-NN |
| **Borderline SMOTE** | SMOTE enfocado en ejemplos de frontera de decisión |
| **SMOTE + Undersampling** | Híbrido: reduce mayoritaria ~10%, aumenta minoritaria |

Resultado: 12 variantes (4 técnicas × 3 ratios) que serán insumo del modelado.

---

### 3. `3_Modeling_Vishing_Pipeline.ipynb` — Modelado sobre datos originales (local)

**Entrada:** 12 datasets balanceados + conjunto de prueba (holdout 20%, desbalanceado)
**Salida:** Métricas comparativas, identificación del mejor modelo

Entrena 4 algoritmos sobre cada uno de los 12 datasets balanceados:

| Modelo | Hiperparámetros |
|---|---|
| Regresión Logística | max_iter=1000 |
| Random Forest | n_estimators=150, max_depth=10 |
| XGBoost | max_depth=6, learning_rate=0.1 |
| MLP (red neuronal) | Capas 64→32, 300 iteraciones |

Evaluación sobre el holdout imbalanceado (47.5K legítimas + 2.5K vishing) con métricas: Recall, Precision, F1, ROC-AUC y PR-AUC. El mejor resultado lo obtiene **XGBoost + SMOTE Undersampling al 10%** (PR-AUC ≈ 0.40–0.50).

---

### 4. `4_Biocatch_data_augmentation_AWS.ipynb` — Augmentación de datos (AWS SageMaker)

**Entrada:** `raw_data/biocatch_sinthetic_data.csv` (50K sesiones)
**Salida:** `data/augmented_data/dataset_1M_vishing_.parquet` (1M sesiones)

Este es el paso más técnico del pipeline. Implementa la clase `CorrelatedAugmenter` para generar 1 millón de sesiones sintéticas que preserven la estructura estadística del dataset original:

**Proceso de augmentación:**
1. Separar datos por clase (legítimas y vishing)
2. Estimar matriz de correlación por clase
3. Aplicar descomposición de Cholesky para generar ruido gaussiano multivariado correlacionado
4. Transformar mediante CDF inversa (quantile matching) para preservar distribuciones marginales
5. Añadir perturbación controlada (`noise_scale=0.03`)
6. Post-procesar para respetar restricciones de dominio (rangos, tipos, no negatividad)

**Composición del dataset aumentado (1M):**
- 47,500 sesiones legítimas originales (conservadas intactas)
- 937,500 sesiones legítimas sintéticas (multiplicador 20.7×)
- 2,500 sesiones vishing originales (conservadas intactas)
- 12,500 sesiones vishing sintéticas (multiplicador 6×)
- **Desbalance resultante:** ~1.5% vishing (más cercano a la realidad productiva que el 5% original)

**Ventaja frente a SMOTE simple:** el augmentador preserva las dependencias conjuntas entre variables, no solo las distribuciones marginales individuales.

---

### 5. `5_EDA_augmented_data.ipynb` — EDA sobre datos aumentados (local)

**Entrada:** `data/augmented_data/dataset_1M_vishing_.parquet` + dataset original (50K)

Valida la calidad de la augmentación comparando el dataset de 1M con el original:

- Test de Kolmogorov-Smirnov por feature (diferencia media ≈ 0.077, excelente preservación)
- Dos features con drift leve detectado: `transaction_amount_cop` (KS=0.24) y `total_dead_time_s` (KS=0.47)
- Random Forest sobre subsample con CV-AUC ≈ 0.95
- PCA: primeras 5 componentes explican 42% de varianza
- Confirmación de que las features más discriminativas mantienen su poder en el dataset aumentado

---

### 6. `6_Data_Balancing_AD_Pipeline.ipynb` — Balanceo sobre datos aumentados (local)

**Entrada:** `data/augmented_data/dataset_1M_vishing_.parquet` (1M, desbalance 98.5%:1.5%)
**Salida:** 12 datasets balanceados en `data/balanced/augmented/` (formato parquet)

Aplica las mismas 4 técnicas de resampling en los mismos 3 ratios objetivo (10%, 20%, 25%) que en el Notebook 2, pero ahora sobre el dataset de 1 millón de sesiones. Los archivos se guardan en formato parquet para mayor eficiencia a esta escala.

| Técnica | Tamaño resultante aprox. |
|---|---|
| Random Oversampling | 1.09M – 1.31M filas |
| SMOTE | 1.09M – 1.31M filas |
| Borderline SMOTE | 1.09M – 1.31M filas |
| SMOTE + Undersampling | 985K – 1.18M filas |

---

### 7. `7_Modeling_Vishing_AD_AWS_exec v2.ipynb` — Modelado sobre datos aumentados (AWS SageMaker)

**Entrada:** 12 datasets balanceados del Notebook 6 + holdout de 200K sesiones
**Salida:** 48 modelos serializados en S3 como `VishingModelWrapper`

Entrena los mismos 4 algoritmos sobre los 12 datasets balanceados del dataset aumentado. La evaluación se hace sobre un holdout de 200K sesiones con desbalance real (~1.5% vishing).

**Innovación principal — `VishingModelWrapper`:**

Esta clase encapsula en un solo objeto serializable todo lo necesario para inferencia en producción:
- El modelo entrenado
- El scaler (StandardScaler)
- La lista exacta de features en el orden correcto
- El umbral óptimo de clasificación (calculado por maximización de F1 en la curva PR, no fijo en 0.5)

La API del wrapper expone tres métodos:
- `predict(json)` → etiqueta binaria (0/1)
- `predict_proba_raw(json)` → probabilidades `{legitimate, vishing}`
- `predict_full(json)` → diccionario completo con etiqueta, probabilidades y umbral usado

Acepta como entrada un dict Python, string JSON o lista de dicts (batch). Valida features faltantes y lanza `ValueError` explícito en caso de error, sin fallos silenciosos.

Los modelos se serializan con joblib y se almacenan en S3: `s3://poc-fraude-vishing/proyecto/modelos/{tecnica}/{ratio}/{modelo}.pkl`

---

### 8. `Get_Features_List.ipynb` — Lista de features finales (local)

**Entrada:** `data/augmented_data/dataset_1M_vishing_.parquet`

Utilidad simple que extrae y documenta la lista definitiva de las **44 variables** usadas en el modelado, eliminando identificadores, features de BioCatch (que causarían data leakage), variables derivadas redundantes y la variable objetivo.

Variables eliminadas: `session_id`, `customer_id`, `session_timestamp`, `device_type`, `os_type`, `app_version`, todos los scores de BioCatch, `days_to_claim`, `claim_category`, `screens_visited`, `unusual_screen_visits`, `is_synthetic`, `interactions_per_s`, `is_vishing`.

---

### 9. `8_Inference_Test v2.ipynb` — Test de inferencia (local)

**Entrada:** `VishingModelWrapper` cargado desde S3 + sesiones de prueba

Valida el pipeline completo de inferencia de extremo a extremo:

1. Carga el wrapper desde S3 e inspecciona sus metadatos
2. Corre predicciones sobre 5 sesiones legítimas + 5 de vishing reales del dataset aumentado, comparando con ground truth
3. Construye y evalúa tres perfiles sintéticos de prueba:
   - **Legítimo:** sin llamada activa, tipeo normal, pocas correcciones, monto ~150K COP
   - **Vishing:** llamada activa, tipeo lento, muchas correcciones, monto ~9.2M COP
   - **Ambiguo:** señales mixtas (llamada activa pero monto moderado)
4. Demuestra los tres métodos de la API del wrapper
5. Procesamiento batch (lista de JSONs → lista de resultados)
6. Validación de manejo de errores (features faltantes, tipos inválidos)
7. Visualizaciones: barras de probabilidades, radar chart de perfiles de riesgo

---

## Resumen de Ejecución por Notebook

| Notebook | Ejecución | Entrada | Salida |
|---|---|---|---|
| `1_EDA.ipynb` | Local | 50K CSV | Estadísticas, visualizaciones |
| `2_Data_Balancing_Pipeline.ipynb` | Local | 50K CSV | 12 CSVs balanceados |
| `3_Modeling_Vishing_Pipeline.ipynb` | Local | 12 CSVs + holdout | Métricas y matrices de confusión |
| `4_Biocatch_data_augmentation_AWS.ipynb` | **AWS** | 50K CSV | 1M parquet |
| `5_EDA_augmented_data.ipynb` | Local | 1M parquet | Análisis comparativo |
| `6_Data_Balancing_AD_Pipeline.ipynb` | Local | 1M parquet | 12 parquets balanceados |
| `7_Modeling_Vishing_AD_AWS_exec v2.ipynb` | **AWS** | 12 parquets + holdout | 48 wrappers en S3 |
| `Get_Features_List.ipynb` | Local | 1M parquet | Lista de 44 features |
| `8_Inference_Test v2.ipynb` | Local | Wrapper S3 + JSONs | Predicciones y validaciones |

---

## Estructura de Directorios

```
Vishing_synth_data_GenAI/
├── raw_data/
│   ├── biocatch_sinthetic_data.csv                    ← Dataset original (50K)
│   └── diccionario_datos_biocatch_sintetico.md        ← Diccionario de datos
├── data/
│   ├── augmented_data/
│   │   └── dataset_1M_vishing_.parquet                ← Dataset aumentado (1M)
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
├── modelos/                                           ← Modelos locales (espejo de S3)
├── 1_EDA.ipynb
├── 2_Data_Balancing_Pipeline.ipynb
├── 3_Modeling_Vishing_Pipeline.ipynb
├── 4_Biocatch_data_augmentation_AWS.ipynb
├── 5_EDA_augmented_data.ipynb
├── 6_Data_Balancing_AD_Pipeline.ipynb
├── 7_Modeling_Vishing_AD_AWS_exec v2.ipynb
├── 8_Inference_Test v2.ipynb
├── Get_Features_List.ipynb
├── Mejorar.md                                         ← Notas de mejoras pendientes
└── requirements.txt
```

---


