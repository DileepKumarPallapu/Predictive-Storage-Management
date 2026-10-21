# AEGISSTOR — Research Protocol & IEEE Manuscript Skeleton

## Title
**Predictive Storage Capacity and Performance Management Using Machine Learning: A Resilience Digital Twin Approach**

---

## 1. Abstract Skeleton
Modern enterprise and cloud storage tiers face non-stationary I/O workloads with high variability, where reactive threshold monitoring frequently fails to provide sufficient operational lead time. In this paper, we propose AEGISSTOR, a resilience intelligence framework coupling multi-horizon quantile forecasting with a constraint-aware digital twin simulator. By modeling both capacity depletion and performance degradation (tail latency P95) alongside their prediction intervals ($q_{10}, q_{50}, q_{90}$), AEGISSTOR evaluates candidate interventions—such as cold data tiering, dynamic capacity expansion, and workload rebalancing—against an immutable Hard Safety Envelope. In empirical evaluations across heterogeneous simulated storage workloads, the framework demonstrates calibrated uncertainty bounds and provides preventative lead-time improvements over classical reactive static threshold monitors.

---

## 2. Research Hypotheses
- **$H_1$ (Forecast Lead Time)**: Quantile regression forecasting ($q_{90}$ upper bound for capacity and latency) provides significantly longer actionable warning lead time prior to SLA violation compared to conventional static threshold alerts (e.g., 85% fill limit).
- **$H_2$ (Digital Twin Counterfactual Safety)**: Simulating preventive interventions within a physics-modeled Digital Twin prevents secondary induced SLA violations (e.g. migration I/O thrashing) compared to heuristic unconstrained reactive migrations.
- **$H_3$ (Uncertainty Calibration)**: Conformal prediction calibration on residual intervals bounds empirical violation rates within the targeted nominal significance level ($\alpha = 0.10, 0.20$).

---

## 3. Evaluation Metrics
1. **Forecast Accuracy**:
   - Mean Absolute Error (MAE)
   - Root Mean Squared Error (RMSE)
   - Quantile Pinball Loss ($\mathcal{L}_q(y, \hat{y})$)
2. **Uncertainty Calibration**:
   - Empirical Interval Coverage: $\frac{1}{N} \sum_{i=1}^N \mathbf{1}(y_i \in [\hat{y}_{i, q_{10}}, \hat{y}_{i, q_{90}}])$
   - Interval Sharpness (Mean Width): $\frac{1}{N} \sum_{i=1}^N (\hat{y}_{i, q_{90}} - \hat{y}_{i, q_{10}})$
3. **Operational Storage Resilience**:
   - Warning Lead Time (hours prior to breach)
   - False Discovery Rate (FDR) on threshold breaches
   - Migration I/O Overhead & Duration
   - Hard Safety Constraint Violations Count
