# Project Documentation: Vishing Detection with Synthetic Biometric Data

## General Context

This project is a **machine learning pipeline for detecting vishing (voice phishing) sessions** in a banking application, using synthetic behavioral biometric data generated with the help of Claude.

The original dataset was built from assumptions based on the vendor **BioCatch**, which specializes in behavioral data for fraud detection in banking. BioCatch captures signals such as keystroke dynamics, touch pressure, device motion, and navigation patterns to identify anomalous behaviors during banking sessions.

The goal is to detect whether a user is being victimized by vishing: a phone call in which an attacker guides them to make a fraudulent transfer while they are active in the banking app.

---

## Original Dataset

| Characteristic | Value |
|---|---|
| Source | Synthetic dataset generated with Claude |
| Total sessions | 50,000 |
| Legitimate sessions | 47,500 (95%) |
| Vishing (fraud) sessions | 2,500 (5%) |
| Total variables | 61 columns |
| Simulated period | June 2024 – May 2025 |
| File | `raw_data/biocatch_sinthetic_data.csv` |

The full variable dictionary is available in `raw_data/diccionario_datos_biocatch_sintetico.md`.

### How was the dataset created?

Based on information from BioCatch portals that expose fraud trends and different risk vectors, a set of behavioral variables relevant to vishing was defined. This organization does not explicitly disclose how it collects data or which specific variables it uses, but it does describe at a high level which types of behavior can signal vishing during a session. From these assumptions, a dataset was generated with sessions simulating both legitimate and vishing behaviors with the help of Generative AI (Claude).


### Variable Groups

**1. Keystroke dynamics (5 variables)**
Typing speed, inter-key latency, variability, and segmented typing ratio. In vishing sessions the user types more slowly and in a segmented way because they are dictating what the attacker tells them over the phone.

**2. Touch dynamics (5 variables)**
Pressure, touch size, speed, and swipe variance. In vishing they tend to be more erratic.

**3. Device motion (5 variables)**
Tilt angle, gyroscope, accelerometer, motion events. Higher variability in fraudulent sessions due to the user's state of tension.

**4. Hesitation signals (3 variables)**
Number and duration of pauses. One of the best indicators: the vishing user hesitates before executing actions because they are waiting for instructions.

**5. Dead time / inactivity (3 variables)**
Periods without interaction. They capture the time the user spends listening to the attacker on the phone.

**6. In-app navigation (3 variables)**
Screens visited, back-navigation count, transition time. In vishing the user may navigate unusually following instructions.

**7. Errors and corrections (4 variables)**
Input errors, corrections in amount and beneficiary fields, copy/paste events. High frequency in vishing because the user is transcribing dictated data.

**8. Session context (5 variables)**
Duration, time of day, whether there is an active phone call, detection of remote-access tools, suspicious apps detected.

**9. Transaction data (4 variables)**
Amount, whether the beneficiary is new, time to transaction. Vishing sessions tend to have higher amounts and new beneficiaries.

**10. Derived and BioCatch features (excluded from modeling)**
`biocatch_risk_score`, `biocatch_genuine_score`, and similar are excluded because they would introduce data leakage. `session_id`, `customer_id`, `session_timestamp`, and other identifiers are also removed.

**Final variables for modeling: 44**

---

## Pipeline Structure

The project has four main phases:

```
┌────────────────────────────────────────────────────────────────┐
│ PHASE 1 — Original dataset (50K sessions, local execution)     │
└────────────────────────────────────────────────────────────────┘
        ↓
  1_EDA.ipynb
  2_Data_Balancing_Pipeline.ipynb
  3_Modeling_Vishing_Pipeline.ipynb

┌────────────────────────────────────────────────────────────────┐
│ PHASE 2 — Data augmentation and retraining (AWS SageMaker)     │
└────────────────────────────────────────────────────────────────┘
        ↓
  4_Biocatch_data_augmentation_AWS.ipynb
  5_EDA_augmented_data.ipynb
  6_Data_Balancing_AD_Pipeline.ipynb
  7_Modeling_Vishing_AD_AWS_exec v2.ipynb

┌────────────────────────────────────────────────────────────────┐
│ PHASE 3 — Focused experimentation with XGBoost (AWS SageMaker) │
└────────────────────────────────────────────────────────────────┘
        ↓
  9_XGBoost_training_exec.ipynb

┌────────────────────────────────────────────────────────────────┐
│ PHASE 4 — Data generation for inference simulation             │
│          (AWS SageMaker)                                       │
└────────────────────────────────────────────────────────────────┘
        ↓
  10_Inference_Data_Generation.ipynb
```

---

## Description of each Notebook

### 1. `1_EDA.ipynb` — Exploratory Analysis (local)

**Input:** `raw_data/biocatch_sinthetic_data.csv` (50K sessions)

Performs a complete exploratory analysis of the original dataset:

- Integrity validation (nulls, duplicates, types, ranges)
- Comparison of distributions between legitimate and vishing sessions
- Mann-Whitney U tests and Cohen's d to identify discriminative features
- Univariate AUC per variable → top 20 features by predictive power
- Correlation analysis to detect multicollinearity
- Bivariate visualizations, radar chart of behavioral profiles
- PCA to visualize separability in 2D
- Quick Random Forest with cross-validation (AUC ≈ 0.88)

**Key findings:** The most discriminative features are `phone_call_active`, `segmented_typing_ratio`, `hesitation_count`, `data_familiarity_score`, and `input_correction_count`. Vishing sessions have slower typing, more hesitations, and transaction amounts 1.5-2× higher.

---

### 2. `2_Data_Balancing_Pipeline.ipynb` — Balancing of original data (local)

**Input:** `raw_data/biocatch_sinthetic_data.csv` (95%:5% imbalance)
**Output:** 12 balanced datasets in `data/balanced/original/`

Applies 4 resampling techniques at 3 target vishing ratios (10%, 20%, 25%):

| Technique | Description |
|---|---|
| **Random Oversampling** | Duplicates observations of the minority class |
| **SMOTE** | Generates synthetic samples by k-NN interpolation |
| **Borderline SMOTE** | SMOTE focused on decision-boundary examples |
| **SMOTE + Undersampling** | Hybrid: reduces majority ~10%, increases minority |

Result: 12 variants (4 techniques × 3 ratios) that will feed the modeling step.

---

### 3. `3_Modeling_Vishing_Pipeline.ipynb` — Modeling on original data (local)

**Input:** 12 balanced datasets + test set (20% holdout, imbalanced)
**Output:** Comparative metrics, identification of the best model

Trains 4 algorithms on each of the 12 balanced datasets:

| Model | Hyperparameters |
|---|---|
| Logistic Regression | max_iter=1000 |
| Random Forest | n_estimators=150, max_depth=10 |
| XGBoost | max_depth=6, learning_rate=0.1 |
| MLP (neural network) | Layers 64→32, 300 iterations |

Evaluation on the imbalanced holdout (47.5K legitimate + 2.5K vishing) with metrics: Recall, Precision, F1, ROC-AUC, and PR-AUC. The best result is obtained by **XGBoost + SMOTE Undersampling at 10%** (PR-AUC ≈ 0.40–0.50).

---

### 4. `4_Biocatch_data_augmentation_AWS.ipynb` — Data augmentation (AWS SageMaker)

**Input:** `raw_data/biocatch_sinthetic_data.csv` (50K sessions)
**Output:** `data/augmented_data/dataset_1M_vishing_.parquet` (1M sessions)

This is the most technical step of the pipeline. It implements the `CorrelatedAugmenter` class to generate 1 million synthetic sessions that preserve the statistical structure of the original dataset:

**Augmentation process:**
1. Separate data by class (legitimate and vishing)
2. Estimate the correlation matrix per class
3. Apply Cholesky decomposition to generate correlated multivariate Gaussian noise
4. Transform via inverse CDF (quantile matching) to preserve marginal distributions
5. Add controlled perturbation (`noise_scale=0.03`)
6. Post-process to respect domain constraints (ranges, types, non-negativity)

**Composition of the augmented dataset (1M):**
- 47,500 original legitimate sessions (kept intact)
- 937,500 synthetic legitimate sessions (multiplier 20.7×)
- 2,500 original vishing sessions (kept intact)
- 12,500 synthetic vishing sessions (multiplier 6×)
- **Resulting imbalance:** ~1.5% vishing (closer to production reality than the original 5%)

**Advantage over plain SMOTE:** the augmenter preserves the joint dependencies between variables, not just the individual marginal distributions.

---

### 5. `5_EDA_augmented_data.ipynb` — EDA on augmented data (local)

**Input:** `data/augmented_data/dataset_1M_vishing_.parquet` + original dataset (50K)

Validates the quality of the augmentation by comparing the 1M dataset with the original:

- Kolmogorov-Smirnov test per feature (mean difference ≈ 0.077, excellent preservation)
- Two features with slight drift detected: `transaction_amount_cop` (KS=0.24) and `total_dead_time_s` (KS=0.47)
- Random Forest on a subsample with CV-AUC ≈ 0.95
- PCA: the first 5 components explain 42% of variance
- Confirmation that the most discriminative features keep their power in the augmented dataset

---

### 6. `6_Data_Balancing_AD_Pipeline.ipynb` — Balancing on augmented data (local)

**Input:** `data/augmented_data/dataset_1M_vishing_.parquet` (1M, 98.5%:1.5% imbalance)
**Output:** 12 balanced datasets in `data/balanced/augmented/` (parquet format)

Applies the same 4 resampling techniques at the same 3 target ratios (10%, 20%, 25%) as in Notebook 2, but now on the 1 million session dataset. Files are saved in parquet format for greater efficiency at this scale.

| Technique | Approx. resulting size |
|---|---|
| Random Oversampling | 1.09M – 1.31M rows |
| SMOTE | 1.09M – 1.31M rows |
| Borderline SMOTE | 1.09M – 1.31M rows |
| SMOTE + Undersampling | 985K – 1.18M rows |

---

### 7. `7_Modeling_Vishing_AD_AWS_exec v2.ipynb` — Modeling on augmented data (AWS SageMaker)

**Input:** 12 balanced datasets from Notebook 6 + holdout of 200K sessions
**Output:** 48 serialized models in S3 as `VishingModelWrapper`

Trains the same 4 algorithms on the 12 balanced datasets of the augmented dataset. Evaluation is done on a holdout of 200K sessions with real imbalance (~1.5% vishing).

**Main innovation — `VishingModelWrapper`:**

This class encapsulates everything needed for production inference in a single serializable object:
- The trained model
- The scaler (StandardScaler)
- The exact list of features in the correct order
- The optimal classification threshold (computed by F1 maximization on the PR curve, not fixed at 0.5)

The wrapper's API exposes three methods:
- `predict(json)` → binary label (0/1)
- `predict_proba_raw(json)` → probabilities `{legitimate, vishing}`
- `predict_full(json)` → full dictionary with label, probabilities, and threshold used

It accepts as input a Python dict, JSON string, or list of dicts (batch). It validates missing features and raises an explicit `ValueError` on error, with no silent failures.

Models are serialized with joblib and stored in S3: `s3://poc-fraude-vishing/proyecto/modelos/{technique}/{ratio}/{model}.pkl`

---

### 8. `9_XGBoost_training_exec.ipynb` — Focused experimentation with XGBoost (AWS SageMaker)

**Input:** 13 augmented-data datasets (12 balanced from Notebook 6 + raw 1M) + 13 original-data datasets (12 balanced from Notebook 2 + raw 50K)
**Output:** 182 serialized models in S3 as `VishingModelWrapper`

After confirming in Notebook 7 that XGBoost is the best-performing algorithm, this notebook goes deeper by exploring **7 hyperparameter variants** of the algorithm, trained on both dataset types (original and augmented) with separate holdouts (10K and 200K sessions respectively):

| Variant | Description |
|---|---|
| `xgb_base` | Same configuration as Notebook 7 (baseline) |
| `xgb_deep` | Deeper trees, more estimators, low learning rate |
| `xgb_shallow` | Shallow trees, many estimators (classic boosting) |
| `xgb_regularized` | Strong regularization (L1 + L2 + high min_child_weight) |
| `xgb_balanced` | `scale_pos_weight` computed dynamically according to each dataset's real imbalance |
| `xgb_conservative` | Aggressive subsampling (subsample + colsample_bytree + gamma) |
| `xgb_slow_learner` | Very low learning rate (0.01) with 500 estimators |

**Total combinations:** 7 variants × 13 datasets × 2 data types = **182 models**, each packaged in `VishingModelWrapper` (the same wrapper from Notebook 7) and uploaded to `s3://poc-fraude-vishing/proyecto/modelos_xgb/{data_type}/{variant}/{technique}/{ratio}.pkl`.

Includes a comparative analysis of the 182 combinations: table sorted by PR-AUC, best configuration per variant, variant × balancing-technique heatmaps, confusion matrix, Precision-Recall curve, and feature importance of the best global model.

**Best result obtained:** `xgb_deep` on original data with Random Oversampling at 25% (PR-AUC ≈ 0.95, Recall ≈ 0.88, F1 ≈ 0.90).

---

### 9. `10_Inference_Data_Generation.ipynb` — Data generation for inference simulation (AWS SageMaker)

**Input:** `raw_data/biocatch_sinthetic_data.csv` (50K, used only as statistical reference)
**Output:** `data/inference_simulation/inference_100k.parquet` (100K fully synthetic sessions)

Generates a dataset of **100,000 fully synthetic sessions** (no row comes from the original dataset) to simulate a realistic production inference flow:

- Reuses the `CorrelatedAugmenter` from Notebook 4 without modifications, training an independent augmenter per class (legitimate / vishing) on the original dataset as reference
- Target distribution: **98,500 legitimate + 1,500 vishing (~1.5% vishing)**, consistent with the imbalance of the augmented 1M dataset
- Adds synthetic `session_id` values (`INF-0000001`, ...) and `session_timestamp` distributed between June and November 2025 to simulate real sessions
- Validates generation quality by comparing distributions of key features (`typing_speed_cps`, `hesitation_count`, `segmented_typing_ratio`, `data_familiarity_score`, `input_correction_count`, `transaction_amount_cop`) between the original and synthetic datasets

---

## Execution Summary per Notebook

| Notebook | Execution | Input | Output |
|---|---|---|---|
| `1_EDA.ipynb` | Local | 50K CSV | Statistics, visualizations |
| `2_Data_Balancing_Pipeline.ipynb` | Local | 50K CSV | 12 balanced CSVs |
| `3_Modeling_Vishing_Pipeline.ipynb` | Local | 12 CSVs + holdout | Metrics and confusion matrices |
| `4_Biocatch_data_augmentation_AWS.ipynb` | **AWS** | 50K CSV | 1M parquet |
| `5_EDA_augmented_data.ipynb` | Local | 1M parquet | Comparative analysis |
| `6_Data_Balancing_AD_Pipeline.ipynb` | Local | 1M parquet | 12 balanced parquets |
| `7_Modeling_Vishing_AD_AWS_exec v2.ipynb` | **AWS** | 12 parquets + holdout | 48 wrappers in S3 |
| `9_XGBoost_training_exec.ipynb` | **AWS** | 26 datasets (orig + augmented) + holdouts | 182 XGBoost wrappers in S3 |
| `10_Inference_Data_Generation.ipynb` | **AWS** | 50K CSV (reference) | 100K fully synthetic parquet |

---

## Directory Structure

```
Vishing_synth_data_GenAI/
├── raw_data/
│   ├── biocatch_sinthetic_data.csv                    ← Original dataset (50K)
│   └── diccionario_datos_biocatch_sintetico.md        ← Data dictionary
├── data/
│   ├── augmented_data/
│   │   └── dataset_1M_vishing_.parquet                ← Augmented dataset (1M)
│   └── balanced/
│       ├── original/                                  ← 12 balanced variants of the 50K
│       │   ├── random_oversampling/{10,20,25}.csv
│       │   ├── smote/{10,20,25}.csv
│       │   ├── borderline_smote/{10,20,25}.csv
│       │   └── smote_undersampling/{10,20,25}.csv
│       └── augmented/                                 ← 12 balanced variants of the 1M
│           ├── random_oversampling/{10,20,25}.parquet
│           ├── smote/{10,20,25}.parquet
│           ├── borderline_smote/{10,20,25}.parquet
│           └── smote_undersampling/{10,20,25}.parquet
│   └── inference_simulation/
│       └── inference_100k.parquet                     ← Fully synthetic dataset for inference simulation
├── modelos/                                           ← Local models (mirror of S3)
├── 1_EDA.ipynb
├── 2_Data_Balancing_Pipeline.ipynb
├── 3_Modeling_Vishing_Pipeline.ipynb
├── 4_Biocatch_data_augmentation_AWS.ipynb
├── 5_EDA_augmented_data.ipynb
├── 6_Data_Balancing_AD_Pipeline.ipynb
├── 7_Modeling_Vishing_AD_AWS_exec v2.ipynb
├── 9_XGBoost_training_exec.ipynb
├── 10_Inference_Data_Generation.ipynb
├── Mejorar.md                                         ← Pending improvement notes
└── requirements.txt
```

---

