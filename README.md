# Vishing Detection with Synthetic Behavioral Biometrics

## General Context

This project is a **machine learning pipeline for detecting vishing sessions** (voice phishing) in a banking application, using synthetic behavioral biometrics generated with the help of generative AI.

The original dataset was built based on assumptions from the vendor **BioCatch**, which specializes in behavioral data for banking fraud detection. BioCatch captures signals such as keystroke dynamics, touch pressure, device motion and navigation patterns to identify anomalous behavior during banking sessions.

The goal is to detect whether a user is being victim of vishing: a phone call in which an attacker guides them into performing a fraudulent transfer while they are active in the banking app. The structural difficulty of the problem is that the user is legitimately operating their app, from their own device and with their own credentials; the only thing that differs is **how** they interact: they type slower, pause while listening to instructions, correct more fields, and tend to transfer larger amounts.

---

## Original Dataset

| Attribute | Value |
|---|---|
| Source | Synthetic dataset generated with generative AI (Claude) |
| Total sessions | 50,000 |
| Legitimate sessions | 47,500 (95%) |
| Vishing (fraud) sessions | 2,500 (5%) |
| Unique customers | 19,782 |
| Sessions per customer (average) | 2.53 |
| Total variables | 61 columns |
| Simulated period | June 2024 – May 2025 |
| File | `raw_data/biocatch_sinthetic_data.csv` |

The full data dictionary is available at `raw_data/diccionario_datos_biocatch_sintetico.md`.

### How was the dataset built?

BioCatch publishes general information about the behavioral vectors it uses to detect banking fraud, but **does not disclose the exact variables nor how they are computed**. Based on the public documentation about its risk indicators (particularly for vishing and social engineering), we designed a set of 61 variables covering eight functional groups and generated a synthetic dataset in which sessions simulate both legitimate and fraudulent behavior, using generative AI (Claude) as an assistant in the construction process.

### Variable Groups

1. **Keystroke dynamics (5 variables).** Typing speed, inter-key latency, variability and segmented typing ratio. In vishing sessions the user types slower and in a segmented manner because they are dictating what the attacker is telling them over the phone.

2. **Touch dynamics (5 variables).** Pressure, touch size, swipe speed and directional variance. In vishing they tend to be more erratic.

3. **Device motion (5 variables).** Tilt angle, gyroscope, accelerometer, motion events. Greater variability in fraudulent sessions due to the user's state of tension.

4. **Hesitation signals (3 variables).** Number and duration of pauses. One of the strongest indicators: the user in vishing hesitates before executing actions because they are waiting for instructions.

5. **Dead time / inactivity (3 variables).** Periods with no interaction. Capture the time the user spends listening to the attacker on the phone.

6. **In-app navigation (3 variables).** Screens visited, back-navigation count, transition time. In vishing the user may navigate unusually while following instructions.

7. **Errors and corrections (4 variables).** Input errors, corrections in amount and beneficiary fields, copy/paste events. High frequency in vishing because the user is transcribing dictated data.

8. **Session context (5 variables).** Duration, hour of day, whether a phone call is active, remote access tool detection, suspicious apps detected.

9. **Transaction data (4 variables).** Amount, whether the beneficiary is new, time to transaction. Vishing sessions tend to have higher amounts and new beneficiaries.

10. **Derived and BioCatch features (excluded from modeling).** `biocatch_risk_score`, `biocatch_genuine_score` and similar are excluded because they would cause data leakage. `session_id`, `customer_id`, `session_timestamp` and other identifiers are also dropped.

**Final variables for modeling: 44**

---

## Pipeline Structure

The project is organized in three main phases, plus an exploratory branch with AutoML:

```
┌────────────────────────────────────────────────────────────────┐
│ PHASE 1 — Original dataset (50K sessions, local execution)     │
└────────────────────────────────────────────────────────────────┘
        ↓
  1_EDA.ipynb
  2_Data_Balancing_Pipeline.ipynb
  3_Modeling_Vishing_Pipeline.ipynb

┌────────────────────────────────────────────────────────────────┐
│ PHASE 2 — CTGAN data augmentation and re-training              │
│          (AWS SageMaker)                                       │
└────────────────────────────────────────────────────────────────┘
        ↓
  4_Biocatch_data_augmentation_CTGAN.ipynb
  5_EDA_augmented_data.ipynb
  6_Data_Balancing_AD_Pipeline.ipynb
  7_Modeling_Vishing_AD.ipynb

┌────────────────────────────────────────────────────────────────┐
│ PHASE 3 — Focused XGBoost experimentation (AWS SageMaker)      │
└────────────────────────────────────────────────────────────────┘
        ↓
  8_XGBoost_training.ipynb

┌────────────────────────────────────────────────────────────────┐
│ EXPLORATORY BRANCH — AutoML with AutoGluon                     │
│                     (AWS SageMaker, not adopted)               │
└────────────────────────────────────────────────────────────────┘
        ↓
  AutoML_Vishing_AutoGluon_EN.ipynb
```

---

## Notebook-by-Notebook Description

### 1. `1_EDA.ipynb` — Exploratory Analysis (local)

**Input:** `raw_data/biocatch_sinthetic_data.csv` (50K sessions)

Comprehensive exploratory analysis of the original dataset. Covers:

- Integrity validation: nulls, duplicates, types, per-variable ranges. No nulls, no duplicates, all ranges within expected bounds.
- Target and categorical variable distribution (device, claim category, hour of day, month).
- Per-class univariate analysis with histograms for the physical (keystroke, touch), cognitive (hesitation, familiarity) and session (corrections, navigation) groups.
- Statistical separability tests: Mann-Whitney U, Cohen's d, point-biserial correlation and per-variable univariate AUC.
- Binary variable analysis with chi-square and odds ratio.
- Comparative boxplots by class for the Top 12 features by AUC.
- Correlation analysis (heatmap and detection of pairs with |r| > 0.7).
- Comparative behavioral profile (radar chart and per-class median table).
- Transaction analysis (amount distribution, new beneficiary, time to transaction).
- 10-component PCA: scree plot, 2D projection and analysis of loadings on PC1/PC2.
- IQR-based outlier detection with enrichment vs. vishing rate.
- Quick Random Forest with cross-validation as a preliminary importance estimator (CV AUC ≈ 0.88).

**Key findings.** The most discriminative features by univariate AUC are `phone_call_active`, `segmented_typing_ratio`, `hesitation_count`, `data_familiarity_score` and `input_correction_count`. Vishing sessions exhibit slower and more segmented typing, more hesitations and corrections, and transaction amounts 2–3× higher (median 384K COP vs. 136K COP in legitimate sessions). Chi-square and odds ratio confirm that `phone_call_active` (OR≈2.01), `remote_access_tool_detected` (OR≈2.57), `suspicious_app_detected` (OR≈2.05) and `is_new_beneficiary` (OR≈1.76) are significant at 99.9%.

---

### 2. `2_Data_Balancing_Pipeline.ipynb` — Balancing the original dataset (local)

**Input:** `raw_data/biocatch_sinthetic_data.csv` (95%:5% imbalance)
**Output:** 12 balanced datasets in `data/balanced/original/{technique}/{ratio}.csv`

Applies four resampling techniques with three target vishing ratios (10%, 20%, 25%):

| Technique | Description |
|---|---|
| **Random Oversampling** | Duplicates observations from the minority class. |
| **SMOTE** | Generates synthetic samples via k-NN interpolation. |
| **Borderline SMOTE** | SMOTE focused on decision-boundary examples. |
| **SMOTE + Undersampling** | Hybrid: reduces the majority class by ~10% and applies SMOTE on the minority class. |

This produces 12 variants (4 techniques × 3 ratios) that feed the modeling stage.

---

### 3. `3_Modeling_Vishing_Pipeline.ipynb` — Modeling on the original data (local)

**Input:** 12 balanced datasets + 20% holdout (10K unbalanced sessions).
**Output:** Comparative metrics table and confusion matrix of the best model.

Trains four algorithms on each of the 12 balanced datasets:

| Model | Hyperparameters |
|---|---|
| Logistic Regression | `max_iter=1000` |
| Random Forest | `n_estimators=150`, `max_depth=10` |
| XGBoost | `max_depth=6`, `learning_rate=0.1`, `eval_metric='logloss'` |
| MLP (neural network) | Hidden layers 64→32, 300 iterations |

Evaluated on the imbalanced holdout (9,500 legitimate + 500 vishing) using Recall, Precision, F1, ROC-AUC and PR-AUC.

**Best result.** XGBoost with SMOTE + Undersampling at 10% on the holdout:

| Metric | Value |
|---|---|
| Recall | 0.9400 |
| Precision | 0.9419 |
| F1 | 0.9409 |
| ROC-AUC | 0.9988 |
| PR-AUC | 0.9848 |

TN = 9,471 · FP = 29 · FN = 30 · TP = 470. The very high quality is explained in part by the statistical homogeneity of the synthetic dataset; Phases 2 and 3 raise the bar with more data and realistic imbalance.

---

### 4. `4_Biocatch_data_augmentation_CTGAN.ipynb` — CTGAN augmentation (AWS SageMaker)

**Input:** `raw_data/biocatch_sinthetic_data.csv` (50K sessions).
**Output:** `data/augmented_data/dataset_1M_vishing_ctgan.parquet` (1M sessions).

This is the most technical step of the pipeline. Generates 1 million synthetic sessions preserving the statistical structure of the original dataset using **CTGAN** (Conditional Tabular GAN), the state of the art for generating mixed tabular data with numerical and categorical features.

**Motivation.** A previous implementation based on a Gaussian copula with quantile matching and additive jitter was trivially distinguishable: a simple classifier on originals vs. synthetics reached AUC = 1.00 because the copula failed to capture nonlinear dependencies and the jitter on positively skewed features left a detectable fingerprint in the tails. CTGAN directly learns the dependencies via adversarial training with mode-specific conditioning, and in practice reduces the distinguishability AUC to the 0.55–0.70 range.

**Strategy.** One CTGAN per class (legit and vishing) using data filtered to `mobile` devices (42,579 sessions: 40,452 legitimate + 2,127 vishing) because some attributes do not apply to desktop devices and, in the context of the problem, only behavior on mobile devices is of interest. The minority class has only 2,127 samples and requires class-specific hyperparameters.

**CTGAN hyperparameters (SDV 1.5, trained on Tesla T4 GPU):**

| Class | epochs | batch_size | pac | generator_dim | discriminator_dim | embedding_dim | lr |
|---|---|---|---|---|---|---|---|
| Legit   | 300 | 500 | 10 | (256, 256) | (256, 256) | 128 | 2e-4 |
| Vishing | 800 | 250 |  5 | (128, 128) | (128, 128) |  64 | 1e-4 |

The vishing configuration is more conservative: smaller network (less overfitting with scarce samples), lower `pac` (packing of fewer rows per critic evaluation), smaller batch and more epochs to reach stable convergence with fewer steps per epoch.

**SDV metadata.** Binary variables (`phone_call_active`, `remote_access_tool_detected`, `suspicious_app_detected`, `transaction_attempted`, `is_new_beneficiary`) are declared as `categorical` so CTGAN uses the discrete conditional mechanism (much more stable than treating them as continuous).

**Post-processing after generation.** CTGAN produces reasonable marginals but does not respect logical consistencies nor domain constraints, so a post-generation pipeline is applied:

- **Domain constraints:** clip ratios to [0,1], round non-negative integers, binaries in {0,1}, `hour_of_day` in [0,23], `device_tilt_angle_mean` in [0,90].
- **Logical consistencies:** `is_atypical_hour` derived by rule from `hour_of_day` ∈ {22,23,0,1,2,3,4,5}; `unique_screens_visited ≤ screens_visited`; `call_overlap_duration_s = 0` if `phone_call_active = 0`; `transaction_amount_cop`, `time_to_transaction_s` and `is_new_beneficiary` set to 0 if `transaction_attempted = 0`; `avg_hesitation_duration_s` and `max_hesitation_duration_s` set to 0 if `hesitation_count = 0`; `total_dead_time_s` and `dead_time_ratio` set to 0 if `dead_time_periods = 0`.
- **BioCatch indicators by empirical conditioning** (`biocatch_ato_indicator`, `biocatch_social_eng_indicator`, `biocatch_bot_indicator`): probability tables per decile of `biocatch_risk_score`, estimated on the original dataset.
- **Derived features recomputed** from the generated variables: `errors_per_minute`, `interactions_per_s`, `hesitation_composite`.
- **Session metadata** (`session_id`, `customer_id`, `session_timestamp`, `device_type='mobile'`, `os_type`, `app_version`, `days_to_claim` and `claim_category`): attached after generation using sampled distributions from the original dataset for the corresponding class.
- **`is_synthetic` flag:** all rows generated by CTGAN are marked with 1 and retained originals with 0 (enables auditing and controlled splits).

**Composition of the augmented dataset (1M):**

- 40,452 legitimate original sessions (retained intact).
- 944,548 legitimate sessions generated by CTGAN.
- 2,127 vishing original sessions (retained intact).
- 12,873 vishing sessions generated by CTGAN.
- **Resulting imbalance:** 1.5% vishing (closer to production reality than the original 5%), 62 columns (61 original + `is_synthetic`).

The trained CTGAN synthesizers are serialized and uploaded to S3 (`s3://poc-fraude-vishing/models/ctgan_legit.pkl` and `ctgan_vishing.pkl`) so data can be regenerated without re-training.

---

### 5. `5_EDA_augmented_data.ipynb` — EDA on the augmented data (local)

**Input:** `data/augmented_data/dataset_1M_vishing_ctgan.parquet` + original 50K dataset for comparison.

Validates the quality of the CTGAN augmentation and characterizes the new dataset:

- **Integrity:** no nulls, no duplicated `session_id`, 89,999 unique customers, temporal range 2024-06-01 → 2025-05-31.
- **`is_synthetic` analysis:** global proportion 95.74% synthetic vs. 4.26% original. Contingency with `is_vishing`: chi² = 3,675, OR = 0.259.
- **Ranges:** all variables within their valid ranges after post-processing.
- **Per-class distributions** (subsampled to 50K legitimate + all vishing): physical, cognitive and session behavior.
- **Statistical separability on a 115K subsample:** 3 features with large effect (|d| ≥ 0.8), 10 medium (≥ 0.5), 23 small (≥ 0.2), 17 negligible. Significance: 52 out of 54 with p < 0.001.
- **Binary variables.** `is_new_beneficiary` OR = 2.24, `phone_call_active` OR = 1.63, `suspicious_app_detected` OR = 1.53, `transaction_attempted` OR = 1.36, `remote_access_tool_detected` OR = 1.28. `is_atypical_hour` reverses direction to OR = 0.82 (counterintuitive but explained by the noise CTGAN introduces in the rule-derived variable).
- **Correlation.** 4 pairs with |r| > 0.7 (multicollinearity with derived features): `input_error_count` ↔ `errors_per_minute` (1.00), `hesitation_count` ↔ `hesitation_composite` (0.99), and two with `interactions_per_s`.
- **Comparative behavioral profile** by median: same pattern as in the original, with `transaction_amount_cop` in vishing ≈ 379K vs 167K in legitimate.
- **PCA:** first 5 components explain 36.8% of variance; 10 components explain 48.3%. PC1 is dominated by cognitive signals (`interactions_per_s`, `hesitation_count`, `hesitation_composite`, `dead_time_periods`, `segmented_typing_ratio`); PC2 by transaction signals (`time_to_transaction_s`, `transaction_attempted`, `is_new_beneficiary`).
- **IQR outliers:** `errors_per_minute` enriches vishing to 12.9% (vs. 1.5% global); `interactions_per_s` to 4.8%.
- **Preliminary feature importance.** Random Forest on a stratified subsample (155K rows: 15K vishing + 140K legitimate) with CV-AUC = 1.0000 ± 0.0000, confirming extreme separability in the augmented dataset.

**Validation vs. original (Kolmogorov-Smirnov test on a 50K subsample):**

| Feature | KS | Interpretation |
|---|---|---|
| `session_duration_s` | 0.0000 | Identical |
| `avg_keyhold_ms` | 0.047 | Excellent preservation |
| `hesitation_count` | 0.048 | Excellent |
| `unusual_screen_visits` | 0.051 | Excellent |
| `input_correction_count` | 0.070 | Very good |
| `transaction_amount_cop` | 0.071 | Very good |
| `segmented_typing_ratio` | 0.078 | Good |
| `typing_speed_cps` | 0.079 | Good |
| `total_dead_time_s` | 0.086 | Good |
| `data_familiarity_score` | 0.127 | Mild drift |

CTGAN preserves the marginal distributions within the expected fidelity range; only `data_familiarity_score` exhibits mild drift (KS > 0.10). The deltas in Cohen's d and univariate AUC between original and augmented are moderate and do not change the sign of the effect in any relevant variable.

---

### 6. `6_Data_Balancing_AD_Pipeline.ipynb` — Balancing on the augmented data (local)

**Input:** `data/augmented_data/dataset_1M_vishing_ctgan.parquet` (1M, 98.5%:1.5% imbalance).
**Output:** 12 balanced datasets in `data/balanced/augmented/{technique}/{ratio}.parquet`.

Applies the same four resampling techniques at the same three target ratios (10%, 20%, 25%) as Notebook 2, but now on the 1M-session dataset. Uses parquet format for greater efficiency at this scale.

| Technique | Approx. resulting size |
|---|---|
| Random Oversampling | 1.09M – 1.31M rows |
| SMOTE | 1.09M – 1.31M rows |
| Borderline SMOTE | 1.09M – 1.31M rows |
| SMOTE + Undersampling | 985K – 1.18M rows |

---

### 7. `7_Modeling_Vishing_AD.ipynb` — Multi-algorithm modeling on augmented data (AWS SageMaker)

**Input:** 12 balanced datasets from Notebook 6 (S3) + raw 1M dataset as the 13th dataset + 200K-session holdout extracted from the 1M with `stratify` and realistic imbalance (~1.5% vishing).
**Output:** 52 models serialized to S3 as `VishingModelWrapper`.

Trains four algorithms on each of the 13 datasets (12 balanced + 1 raw), with the MLP re-written in PyTorch to leverage CUDA GPU.

| Model | Hyperparameters |
|---|---|
| Logistic Regression | `max_iter=1000` |
| Random Forest | `n_estimators=150`, `max_depth=10`, `n_jobs=-1` |
| XGBoost | `tree_method='hist'`, `device='cuda'`, `max_depth=6`, `lr=0.1` |
| MLP (PyTorch) | 64→32, `max_iter=30`, `batch_size=4096`, GPU |

**Optimal threshold.** For each model the threshold that maximizes F1 on the holdout's Precision-Recall curve is computed, instead of using the default 0.5.

**Engineering innovation — `VishingModelWrapper`.** Packaging class that solves the inference reproducibility problem. Encapsulates in a single artifact serialized with `joblib`:

- The trained model.
- The `StandardScaler` (only for Logistic Regression and MLP; tree-based models are stored without a scaler).
- The exact feature list in the correct order.
- The optimal classification threshold computed by F1 maximization.
- Metadata: model name, technique and ratio.

Exposes three methods:

- `predict(json)` → binary label 0/1.
- `predict_proba_raw(json)` → `{legitimate: float, vishing: float}`.
- `predict_full(json)` → full dict with label, probabilities and threshold used.

Accepts as input a Python dict, JSON string or a list of dicts (batch). Validates missing features and raises an explicit `ValueError`, with no silent failures. Models are stored in `s3://poc-fraude-vishing/proyecto/modelos/{technique}/{ratio}/{model}.pkl`.

**Best result — XGBoost + Random Oversampling 10%:**

| Metric | Value |
|---|---|
| PR-AUC | 0.7511 |
| Recall | 0.6530 |
| Precision | 0.7572 |
| F1 | 0.7013 |
| ROC-AUC | 0.9784 |
| Optimal threshold | 0.5921 |

TN = 196,372 · FP = 628 · FN = 1,041 · TP = 1,959 on a 200K holdout.

**Feature importance (Top 15 XGBoost by Gain).** The order changes with respect to the original dataset: `gyro_rotation_rate_mean` (0.118), `dead_time_ratio` (0.085), `keystroke_variability` (0.066), `hour_of_day` (0.065), `dead_time_periods` (0.039), `device_tilt_variability` (0.037), `beneficiary_field_corrections` (0.032), `segmented_typing_ratio` (0.032), `transaction_amount_cop` (0.028), `avg_interkey_latency_ms` (0.027), `avg_touch_pressure` (0.027), `navigation_back_count` (0.027), `doodling_events` (0.026), `hesitation_count` (0.026), `call_overlap_duration_s` (0.025).

XGBoost consistently dominates over the other families, motivating the focused exploration of Phase 3.

---

### 8. `8_XGBoost_training.ipynb` — Focused XGBoost experimentation (AWS SageMaker)

**Input:** 13 augmented-data datasets (12 balanced + raw 1M) + 13 original-data datasets (12 balanced + raw 50K).
**Output:** 182 models serialized to S3 as `VishingModelWrapper`.

With XGBoost confirmed as the dominant algorithm, this notebook explores **7 hyperparameter variants** trained on both dataset types with separate holdouts:

- Augmented-data holdout: 200K sessions (1.5% vishing imbalance).
- Original-data holdout: 10K sessions (5% vishing imbalance).

**Variants explored:**

| Variant | Description |
|---|---|
| `xgb_base` | Phase 2 configuration (baseline). |
| `xgb_deep` | Deep trees (`max_depth=9`), 300 estimators, `lr=0.05`, `min_child_weight=3`. |
| `xgb_shallow` | Shallow trees (`max_depth=3`), 500 estimators (classic boosting). |
| `xgb_regularized` | Strong regularization (L1=1.0, L2=5.0, `min_child_weight=10`, `gamma=0.3`). |
| `xgb_balanced` | `scale_pos_weight = n_neg/n_pos` computed per dataset at training time. |
| `xgb_conservative` | Aggressive subsampling (`subsample=0.7`, `colsample_bytree=0.7`, `gamma=0.5`). |
| `xgb_slow_learner` | Slow learning (`lr=0.01`, 500 estimators, `subsample=0.8`). |

**Total:** 7 variants × 13 datasets × 2 types = **182 models**, all packaged in `VishingModelWrapper` and uploaded to `s3://poc-fraude-vishing/proyecto/modelos_xgb/{data_type}/{variant}/{technique}/{ratio}.pkl`.

All models were trained with `tree_method='hist'` and `device='cuda'`.

**Consolidated results by data type:**

| Data type | Best variant | Technique | Ratio | PR-AUC | Recall | F1 |
|---|---|---|---|---|---|---|
| Original (50K)   | `xgb_deep` | Random Oversampling | 25% | **0.9484** | 0.878 | 0.902 |
| Augmented (1M)   | `xgb_deep` | Random Oversampling | 20% | 0.8964     | 0.810 | 0.822 |

**Best global model.** `xgb_deep` on original data, Random Oversampling 25%, threshold 0.7264:

- TN = 9,466 · FP = 34 · FN = 61 · TP = 439 (holdout of 10K, 500 vishing).
- Recall = 0.878, Precision = 0.928, F1 = 0.902, PR-AUC = 0.9484.

Included analyses: table of the 182 combinations sorted by PR-AUC, best configuration per variant and data type, visual comparison per metric (PR-AUC, Recall, F1, ROC-AUC), `variant × balancing technique` heatmap per data type, confusion matrix and feature importance of the best model, Precision-Recall curve with F1 optimum, and a CSV table with all results uploaded to `s3://poc-fraude-vishing/proyecto/modelos_xgb/resultados_xgb_experimento.csv`.

**Relevant observation.** The model on original data achieves higher metrics than the one on augmented data, partly because its holdout has a 5% imbalance (easier) versus the 1.5% of the augmented holdout. Both holdouts represent useful situations: the original marks the theoretical ceiling under favorable conditions, and the augmented one gets closer to the realistic prevalence in production.

---

### AutoML — `AutoML_Vishing_AutoGluon_EN.ipynb` (exploratory branch, not adopted)

**Objective.** Verify whether an AutoML flow could outperform the results obtained with the manual multi-algorithm experimentation and the focused XGBoost fine-tuning.

**Split strategy (critical in this case).**

- Original sessions (`is_synthetic=0`, 42,579) are separated from synthetic sessions (`is_synthetic=1`, 957,421).
- Originals are split 40/30/30: 17,031 train / 12,774 val / 12,774 test.
- The mixed train totals **974,452 rows** (train of originals + all synthetic rows).
- Val and test are **100% originals**, with a vishing rate of ≈ 5%.
- This ensures the evaluation is done exclusively on the 2,127 original vishing sessions (not on the 12,873 synthetic ones), measuring what really matters: generalization to real data.

**AutoGluon configuration.**

- `TabularPredictor` with `problem_type='binary'` and `eval_metric='average_precision'` (directly optimizes PR-AUC).
- `presets='best_quality'` (multi-level stacking, bagging and hyperparameter search).
- `time_limit=5400` seconds (90 min) on Tesla T4 GPU.
- `use_bag_holdout=True`, `num_bag_folds=8`, `num_stack_levels=1`.

**Results obtained (leaderboard of 14 models).**

| Model | PR-AUC test | ROC-AUC test | Recall @ P=0.90 | Brier |
|---|---|---|---|---|
| `WeightedEnsemble_L3` | 0.1076 | 0.6667 | 0.0000 | 0.0567 |
| `CatBoost_BAG_L2`     | 0.1075 | 0.6704 | 0.0000 | 0.0613 |
| `LightGBM_BAG_L2`     | 0.1063 | 0.6694 | 0.0000 | 0.0618 |
| `WeightedEnsemble_L2` | 0.1049 | 0.6632 | 0.0000 | 0.0542 |
| `LightGBM_BAG_L1`     | 0.1043 | 0.6691 | 0.0000 | 0.0594 |
| ... | ... | ... | ... | ... |
| `XGBoost_BAG_L1`      | 0.0642 | 0.5743 | 0.0000 | 0.0513 |

**Conclusion of the AutoML branch: not viable.**

All models in the leaderboard sit between PR-AUC 0.06 and 0.11 with ROC-AUC ≈ 0.66, far below the 0.75–0.95 obtained in Notebooks 7 and 8. The most operational metric, `recall_at_precision=0.90`, is **zero** across the whole table: even the best ensemble fails to produce any threshold–model combination that yields alerts with precision ≥ 90%. The notebook was not executed all the way to the end (persistence, permutation importance, SHAP, error analysis) because the leaderboard metrics alone were enough to discard the strategy.

**Probable diagnosis.** The split used by the AutoML flow (train with 95% synthetic rows and evaluation 100% on originals) imposes a distribution shift that the base models (LightGBM, CatBoost, RandomForest) cannot cross without specific tuning, whereas the manual iteration in Notebooks 7 and 8 —with holdouts extracted via `stratify` from the same training distribution— produces PR-AUC 4–9× higher. The experiment confirms the value of focused experimentation over automated exploration on this dataset.

---

## Execution Summary per Notebook

| Notebook | Execution | Main input | Main output |
|---|---|---|---|
| `1_EDA.ipynb`                          | Local | CSV 50K | Statistics, visualizations |
| `2_Data_Balancing_Pipeline.ipynb`      | Local | CSV 50K | 12 balanced CSVs |
| `3_Modeling_Vishing_Pipeline.ipynb`    | Local | 12 CSVs + 10K holdout | Metrics + confusion matrix |
| `4_Biocatch_data_augmentation_CTGAN.ipynb` | **AWS (GPU)** | CSV 50K | 1M parquet + 2 CTGAN synthesizers on S3 |
| `5_EDA_augmented_data.ipynb`           | Local | 1M parquet + CSV 50K | Comparative analysis and KS validation |
| `6_Data_Balancing_AD_Pipeline.ipynb`   | Local | 1M parquet | 12 balanced parquets |
| `7_Modeling_Vishing_AD.ipynb`          | **AWS (GPU)** | 13 parquets + 200K holdout | 52 wrappers on S3 |
| `8_XGBoost_training.ipynb`             | **AWS (GPU)** | 26 datasets (orig + augm) | 182 XGBoost wrappers on S3 + results CSV |
| `AutoML_Vishing_AutoGluon_EN.ipynb`    | **AWS (GPU)** | 1M parquet | Leaderboard (exploratory branch) |

---

## Priority Metric: PR-AUC

With class imbalances on the order of 1.5%–5% in the holdouts, ROC-AUC is deceptively optimistic because it under-penalizes false positives in the presence of an overwhelming majority class. **PR-AUC** (area under the Precision–Recall curve) is the project's reference metric because it directly quantifies the trade-off between detecting fraud (Recall) and the quality of the alerts issued (Precision). The classification threshold is optimized by maximizing F1 on the PR curve rather than being fixed at 0.5, which explains why the optimal threshold of the best global model is 0.7264.

---

## Directory Structure

```
Vishing_synth_data_GenAI/
├── raw_data/
│   ├── biocatch_sinthetic_data.csv                    ← Original dataset (50K)
│   └── diccionario_datos_biocatch_sintetico.md        ← Data dictionary
├── data/
│   ├── augmented_data/
│   │   └── dataset_1M_vishing_ctgan.parquet           ← CTGAN-augmented dataset (1M)
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
├── ctgan_models/                                      ← Serialized CTGAN synthesizers
│   ├── ctgan_legit.pkl
│   └── ctgan_vishing.pkl
├── modelos/                                           ← Local models (mirror of S3)
├── automl_runs/                                       ← AutoGluon runs (predictors + reports)
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

Reference S3 bucket: `s3://poc-fraude-vishing/proyecto/`.
