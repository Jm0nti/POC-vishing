# Data Dictionary — Synthetic BioCatch Dataset for Vishing Detection

## General Information

| Concept | Detail |
|---|---|
| Total sessions | 50,000 |
| Vishing sessions | 2,500 (5.0%) |
| Legitimate sessions | 47,500 (95.0%) |
| Simulated period | June 2024 – May 2025 |
| Columns | 61 |

---

## 1. Identifiers and Session Context

| Column | Type | Description |
|---|---|---|
| `session_id` | string | Unique session ID (SES-XXXXXX) |
| `customer_id` | string | Customer ID (CUS-XXXXX). A customer can have multiple sessions |
| `session_timestamp` | datetime | Session start date and time |
| `device_type` | string | Device type: `mobile` (85%) or `web` (15%) |
| `os_type` | string | Operating system: Android, iOS, Windows, macOS |
| `app_version` | string | Simulated MiBancolombia app version |

---

## 2. Keystroke Dynamics (Physical Behavior - Typing)

Simulate the signals that BioCatch collects about how the user types. In vishing sessions, typing is slower, more variable, and shows dictation patterns.

| Column | Type | Unit | Description |
|---|---|---|---|
| `avg_keyhold_ms` | float | milliseconds | Average duration a key is held down |
| `avg_interkey_latency_ms` | float | milliseconds | Average time between pressing one key and the next |
| `typing_speed_cps` | float | characters/sec | Typing speed in characters per second |
| `keystroke_variability` | float | ratio (0-1) | Variability in typing rhythm. High values = irregular typing |
| `segmented_typing_ratio` | float | ratio (0-1) | Proportion of segmented typing (dictation pattern). **Key vishing signal**: the scammer dictates data to the customer |

---

## 3. Touch Dynamics (Physical Behavior - Touchscreen)

Signals captured by the BioCatch SDK about how the user taps and swipes on the screen.

| Column | Type | Unit | Description |
|---|---|---|---|
| `avg_touch_pressure` | float | ratio (0-1) | Average finger pressure on the screen |
| `avg_touch_size_px` | float | pixels | Average size of the finger's contact area |
| `swipe_speed_px_s` | float | pixels/sec | Average speed of swipe gestures |
| `swipe_directional_variance` | float | ratio (0-1) | Variability in swipe direction. High = erratic swipes |
| `scroll_speed_avg` | float | pixels/sec | Average scroll speed |

---

## 4. Accelerometer and Gyroscope (Device Sensors)

BioCatch captures data from the phone's sensors to profile how the user holds and moves the device.

| Column | Type | Unit | Description |
|---|---|---|---|
| `device_tilt_angle_mean` | float | degrees (0-90) | Average device tilt angle |
| `device_tilt_variability` | float | degrees | Variability in tilt angle. High = nervous movement |
| `gyro_rotation_rate_mean` | float | rad/s | Average device rotation rate |
| `accelerometer_jerk_mean` | float | m/s³ | Average change in acceleration (phone shaking) |
| `phone_motion_events` | int | count | Number of significant phone motion events |

---

## 5. Cognitive Signals — Hesitation

Indicators of doubt, confusion, or waiting for instructions. **Central to vishing detection.**

| Column | Type | Unit | Description |
|---|---|---|---|
| `hesitation_count` | int | count | Number of significant pauses (>1s) during the session |
| `avg_hesitation_duration_s` | float | seconds | Average duration of each hesitation |
| `max_hesitation_duration_s` | float | seconds | Longest hesitation in the session |

---

## 6. Cognitive Signals — Dead Time (Inactivity)

Periods without activity in the session. In vishing, the customer has long periods of inactivity while listening to instructions over the phone.

| Column | Type | Unit | Description |
|---|---|---|---|
| `dead_time_periods` | int | count | Number of periods without activity (>3 seconds) |
| `total_dead_time_s` | float | seconds | Total inactivity time in the session |
| `dead_time_ratio` | float | ratio (0-1) | Proportion of the session spent inactive |

---

## 7. Cognitive Signals — In-App Navigation

How the user navigates within MiBancolombia. In vishing, the customer navigates erratically following instructions.

| Column | Type | Unit | Description |
|---|---|---|---|
| `screens_visited` | int | count | Total screens visited (includes repetitions) |
| `unique_screens_visited` | int | count | Unique screens visited |
| `unusual_screen_visits` | int | count | Visits to sections the user does not normally access |
| `navigation_back_count` | int | count | Number of times the user navigates back |
| `screen_transition_time_avg_s` | float | seconds | Average time between screen changes |

---

## 8. Cognitive Signals — Errors and Corrections

Indicators that the user is unsure of what they are entering. **Key for vishing**: the customer makes errors when entering dictated data.

| Column | Type | Unit | Description |
|---|---|---|---|
| `input_error_count` | int | count | Total input errors during the session |
| `input_correction_count` | int | count | Total corrections made |
| `amount_field_corrections` | int | count | Corrections specifically in amount fields |
| `beneficiary_field_corrections` | int | count | Corrections in beneficiary fields |
| `copy_paste_events` | int | count | Copy/paste events during the session |

---

## 9. Cognitive Signals — Familiarity and Doodling

| Column | Type | Unit | Description |
|---|---|---|---|
| `data_familiarity_score` | float | ratio (0-1) | Familiarity score with the entered data. Low = data unknown to the user (dictated) |
| `doodling_events` | int | count | Purposeless touch movements (touch/mouse doodling), indicates anxiety or waiting |

---

## 10. Session Context

| Column | Type | Unit | Description |
|---|---|---|---|
| `session_duration_s` | float | seconds | Total session duration |
| `hour_of_day` | int | hour (0-23) | Hour of the day the session started |
| `is_atypical_hour` | int | binary | 1 if the session was during atypical hours (22:00–05:00) |
| `phone_call_active` | int | binary | **1 if there was an active phone call during the session.** Strongest vishing signal (85% of vishing sessions) |
| `call_overlap_duration_s` | float | seconds | Duration of the call overlapping with the banking session |
| `remote_access_tool_detected` | int | binary | 1 if a remote-access tool (RAT) was detected |
| `suspicious_app_detected` | int | binary | 1 if an active suspicious app was detected |

---

## 11. Transaction Data

| Column | Type | Unit | Description |
|---|---|---|---|
| `transaction_attempted` | int | binary | 1 if a transaction was attempted in the session |
| `transaction_amount_cop` | int | COP | Transaction amount in Colombian pesos |
| `is_new_beneficiary` | int | binary | 1 if the transaction beneficiary was new |
| `time_to_transaction_s` | float | seconds | Time from session start to the transaction |

---

## 12. Simulated BioCatch Scores

Simulate the outputs that BioCatch returns to the bank via API.

| Column | Type | Range | Description |
|---|---|---|---|
| `biocatch_risk_score` | int | 0–1000 | Overall session risk score |
| `biocatch_genuine_score` | int | 0–1000 | Confidence score that the user is genuine |
| `biocatch_ato_indicator` | int | binary | Account Takeover indicator |
| `biocatch_social_eng_indicator` | int | binary | Detected social-engineering indicator |
| `biocatch_bot_indicator` | int | binary | Bot activity indicator |

---

## 13. Derived Features

| Column | Type | Description |
|---|---|---|
| `errors_per_minute` | float | Error rate per minute of session |
| `interactions_per_s` | float | Interactions per second (overall flow) |
| `hesitation_composite` | float | Composite score: (hesitation_count × avg_duration) / session_duration |

---

## 14. Labels (Target Variable + Claim Metadata)

| Column | Type | Description |
|---|---|---|
| `is_vishing` | int | **Target variable**: 1 = confirmed vishing session, 0 = legitimate session |
| `days_to_claim` | int | Days between the session and the customer's claim (-1 if not applicable) |
| `claim_category` | string | Claim category: `vishing`, `ingenieria_social_telefonica`, `fraude_telefono`, `none` |

---

## Notes on the Dataset Design

1. **Differentiated distributions**: Each feature was generated with different distributions for legitimate vs. vishing sessions, based on what the BioCatch literature documents as indicators of social-engineering manipulation.

2. **Simulated realistic correlations**: For example, vishing sessions tend to simultaneously have an active call + segmented typing + high hesitation + long session + new beneficiary.

3. **Intentional noise**: Not all vishing sessions have all indicators active (there is overlap with legitimate sessions), to simulate the real complexity of the problem.

4. **Suggested use**: The `is_vishing` field is the target variable for supervised training. The `biocatch_*_score` and `*_indicator` fields simulate BioCatch's current outputs and can be excluded from the model's own feature set to avoid data leakage, or included as complementary features if the goal is to build a model that combines its own signals with those of BioCatch.
