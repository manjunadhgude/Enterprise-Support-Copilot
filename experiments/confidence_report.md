# Confidence calibration experiment

Dataset: authored synthetic end-to-end support scenarios with executable expected-outcome assertions.
Train/test: 12/6 cases.
Abstention threshold selected on training data: 0.8000.

| Metric | Raw signal | Calibrated |
|---|---:|---:|
| Brier score (lower is better) | 0.2303 | 0.0359 |
| Expected calibration error (lower is better) | 0.3720 | 0.1889 |

## Selective answer trade-off

| Confidence threshold | Coverage | Accuracy among retained | Count |
|---:|---:|---:|---:|
| 0.5 | 1.000 | 1.000 | 6 |
| 0.6 | 1.000 | 1.000 | 6 |
| 0.7 | 1.000 | 1.000 | 6 |
| 0.8 | 1.000 | 1.000 | 6 |

Small, authored synthetic set from a deterministic demo application. The expected-outcome checks are narrow, examples are not independent production observations, and the holdout is too small for a production confidence or abstention claim. Rebuild calibration with representative reviewed outcomes before deployment.
