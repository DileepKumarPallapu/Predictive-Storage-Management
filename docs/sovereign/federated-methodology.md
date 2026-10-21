# AEGISSTOR SOVEREIGN — Federated Forecasting Methodology
**Module:** Collaborative Multi-Site Modeling (Prompt 19.0 Parts 2, 3, 5, 6)  
**Parametric Dimension:** $d = 8$ features  

---

## 1. Local Parametric Feature Pipeline

To ensure strictly causal predictions without future temporal leakage, local site data is transformed into an 8-dimensional feature vector $\mathbf{x}_t \in \mathbb{R}^8$:

1. $x_1 = \sin(2\pi \cdot \text{hour} / 24)$ (Diurnal sine harmonic)
2. $x_2 = \cos(2\pi \cdot \text{hour} / 24)$ (Diurnal cosine harmonic)
3. $x_3 = \sin(2\pi \cdot \text{dow} / 7)$ (Weekly cyclical sine)
4. $x_4 = \cos(2\pi \cdot \text{dow} / 7)$ (Weekly cyclical cosine)
5. $x_5 = (y_{t-1} - y_{t-2}) / \sigma_y$ (Normalized 1-hour change velocity)
6. $x_6 = (y_{t-1} / \text{MA}_6) - 1.0$ (Short-term 6h moving-average surge ratio)
7. $x_7 = (y_{t-1} / \text{MA}_{24}) - 1.0$ (Daily 24h baseline drift ratio)
8. $x_8 = (y_{t-1} - \bar{y}) / \sigma_y$ (Z-score normalized current capacity state)

### Local Ridge Regressor
The site solves the local regularized optimization problem:
$$W_k = \arg\min_{W} \left( \sum_{t=1}^{n_k} (y_{k,t} - \bar{y}_k - W^T \mathbf{x}_{k,t})^2 + \alpha ||W||_2^2 \right) = (X_k^T X_k + \alpha I)^{-1} X_k^T (y_k - \bar{y}_k)$$
$$b_k = \bar{y}_k$$

---

## 2. Aggregation Strategies

### 2.1 Conventional Federated Averaging (FedAvg)
Sample-weighted linear combination across valid participating sites $\mathcal{K}_{\text{valid}}$:
$$W_{\text{global}} = \sum_{k \in \mathcal{K}_{\text{valid}}} \left( \frac{n_k}{\sum_{j \in \mathcal{K}_{\text{valid}}} n_j} \right) W_k, \quad b_{\text{global}} = \sum_{k \in \mathcal{K}_{\text{valid}}} \left( \frac{n_k}{\sum_{j \in \mathcal{K}_{\text{valid}}} n_j} \right) b_k$$

### 2.2 Reliability-Aware Aggregation
Downweights noisy, drifted, or low-reliability nodes:
$$R_k = \frac{\text{ReliabilityScore}_k}{1.0 + \frac{\text{ValRMSE}_k}{50.0}}, \quad w_k = \frac{n_k \cdot R_k}{\sum_{j \in \mathcal{K}_{\text{valid}}} n_j \cdot R_j}$$
$$W_{\text{global}} = \sum_{k \in \mathcal{K}_{\text{valid}}} w_k W_k$$

### 2.3 Personalized Local Adaptation
Combines global representation with local domain specialization:
$$W_{\text{pers}}^{(k)} = \lambda W_k + (1 - \lambda) W_{\text{global}} \quad (\text{Nominal } \lambda = 0.50)$$
$$b_{\text{pers}}^{(k)} = \lambda b_k + (1 - \lambda) b_{\text{global}}$$

---

## 3. Mathematical Defense of Personalization

When site $k$ operates an atypical workload (e.g., intensive write burst OLTP vs calm batch analytics), $W_k$ diverges from $W_{\text{global}}$. Pure FedAvg penalizes specialized sites by diluting local domain coefficients. By applying convex interpolation $W_{\text{pers}}^{(k)}$, site $k$ inherits global seasonal representations while retaining local steepness slopes.
