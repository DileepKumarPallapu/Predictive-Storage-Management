# AEGISSTOR SOVEREIGN — Privacy Threat Model & Security Analysis
**Standard:** Prompt 19.0 Part 7 (Privacy Model) & Part 8 (Model-Update Integrity)  
**Security Classification:** Public Technical Specification  

---

## 1. Threat Actors & Adversary Model

SOVEREIGN evaluates three distinct adversary classes:

1. **Curious Coordinator:**  
   * *Capabilities:* Observes incoming weight updates $W_k$, scalar sample counts $n_k$, and validation RMSE. Has full access to database logs.
   * *Objective:* Reconstruct exact raw storage telemetry (e.g. precise timestamped capacity or IOPS traces) from parameter vectors.
   * *Defense:* Raw time series is never transmitted. Linear weights $W_k \in \mathbb{R}^8$ represent aggregated dataset-level covariance $(X^T X)^{-1} X^T y$. For $n_k \gg d$ (e.g. $480 \text{ samples} \gg 8 \text{ weights}$), exact row inversion is an under-determined system with infinite solutions.

2. **Network Eavesdropper:**  
   * *Capabilities:* Intercepts packets transmitted between sites and coordinator.
   * *Defense:* All update exchange occurs over TLS with mutual authentication.

3. **Malicious / Rogue Participant:**  
   * *Capabilities:* Submits poisoned or corrupted model updates to degrade global forecasting accuracy (model replacement attack).
   * *Defense:* Coordinator Update Integrity Shield (validates parameter dimension $d=8$, enforces finite checks, and bounds update norm $||W_k||_2 \le 1000.0$).

---

## 2. Differential Privacy (DP-FedAvg)

When differential privacy is enabled (`aggregation_strategy: "DIFFERENTIAL_PRIVACY"`), each participating site applies bounded sensitivity clipping and calibrated Gaussian noise:

$$\bar{W}_k = W_k \cdot \min\left(1, \frac{C}{||W_k||_2}\right)$$
$$\tilde{W}_k = \bar{W}_k + \mathcal{N}(0, \sigma^2 I)$$

* **Clip Threshold ($C$):** Typically $10.0\,\text{GB}$.
* **Noise Scale ($\sigma$):** Tunable between $0.01$ and $1.0$.
* **Privacy-Utility Trade-Off:** Introducing $\sigma = 0.05$ adds $\sim 1.8\%$ relative MAE degradation while providing formal $(\epsilon, \delta)$ differential privacy against parameter reconstruction.

---

## 3. Explicit Caveats & What Federated Learning Does NOT Guarantee

1. **Not Zero-Knowledge:** Transmitting model weights minimizes data leakage compared to raw streaming, but standard FedAvg does not constitute cryptographic zero-knowledge.
2. **Membership Inference:** Without DP noise ($\sigma = 0$), sophisticated white-box adversaries with access to intermediate global models can theoretically test whether an extreme outlier day was present in training data.
3. **Data Quality Dependency:** If a site’s local sensor is faulty or miscalibrated, federated aggregation cannot magically clean local telemetry without Reliability-Aware weighting.
