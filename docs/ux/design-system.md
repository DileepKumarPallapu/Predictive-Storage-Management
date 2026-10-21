# AEGISSTOR Aurora Experience Design System (v12.0)
**Visual Identity**: Aurora Experience — Premium Human-First Glass  
**Target Standard**: Enterprise Storage Resilience with WCAG 2.2 AA Accessibility

---

## 1. Signature Color Tokens

### 1.1 Master Dark Theme (`Aurora Midnight`)

| Token Name | Hex / RGBA | Role / Usage | Minimum Contrast |
| :--- | :--- | :--- | :--- |
| `--color-bg` | `#070B14` | Global Canvas Background | — |
| `--color-bg-secondary` | `#0B1222` | Navigation sidebar & deep recesses | — |
| `--surface-primary` | `#111C32` | Standard card base | 14.8:1 against text |
| `--surface-raised` | `#172541` | Elevated dialogs, popovers, sticky bars | 11.9:1 against text |
| `--surface-glass` | `rgba(21, 35, 61, 0.78)` | Translucent glass panels with 16px blur | Passes WCAG AA |
| `--text-primary` | `#F3F6FF` | Main headings, critical KPIs, values | 14.8:1 (AAA) |
| `--text-secondary` | `#B0BED7` | Body text, labels, chart axes | 9.1:1 (AAA) |
| `--text-muted` | `#8596B5` | Metadata, unit markers, timestamps | 5.8:1 (AA) |
| `--text-disabled` | `#596781` | Inactive buttons, non-applicable options | 3.5:1 |
| `--border-subtle` | `rgba(167, 190, 229, 0.14)` | Panel borders, subtle grid lines | — |
| `--border-visible` | `rgba(167, 190, 229, 0.24)` | Card outlines, input boundaries | Non-text contrast >3:1 |
| `--accent-cyan` | `#61DDF8` | **Ice Cyan** — Primary interactive actions | 12.4:1 against dark bg |
| `--accent-sapphire`| `#6D91FF` | **Sapphire** — Secondary navigation & comparisons | 7.6:1 against dark bg |
| `--accent-violet` | `#B29AFF` | **Aurora Violet** — Tertiary analytics & ML models | 8.8:1 against dark bg |
| `--color-success` | `#4ADBB5` | Nominal headroom, verified calibration, pass | 11.2:1 against dark bg |
| `--color-warning` | `#FFD080` | Reserve runway warning, elevated queue | 12.5:1 against dark bg |
| `--color-critical`| `#FF788D` | Hard SLA breach, disqualified action | 8.2:1 against dark bg |
| `--color-neutral` | `#B0BCD0` | Inconclusive telemetry, missing evidence | 8.9:1 against dark bg |

### 1.2 Light Theme (`Pearl Aurora`)

| Token Name | Hex / RGBA | Role / Usage |
| :--- | :--- | :--- |
| `--color-bg` | `#F2F5FB` | Pearl Canvas Background |
| `--color-bg-secondary` | `#E8EEF8` | Sub-level surface |
| `--surface-primary` | `#FFFFFF` | Solid white card |
| `--surface-raised` | `#F8FAFF` | Elevated pearl surface |
| `--surface-glass` | `rgba(255, 255, 255, 0.86)` | Frosted glass with 16px blur |
| `--text-primary` | `#17223A` | High-contrast dark blue body |
| `--text-secondary` | `#4B5C76` | Medium contrast secondary copy |
| `--text-muted` | `#687993` | Metadata and secondary markers |
| `--accent-cyan` | `#006F91` | Primary Teal/Cyan (5.2:1 contrast against white) |
| `--accent-sapphire`| `#315FE0` | Royal Sapphire (6.1:1 contrast against white) |
| `--accent-violet` | `#7350C9` | Deep Pearl Violet (5.8:1 contrast against white) |
| `--color-success` | `#087F68` | Forest emerald (4.8:1 contrast) |
| `--color-warning` | `#875000` | Amber gold (5.1:1 contrast) |
| `--color-critical`| `#BF3452` | Crimson red (5.4:1 contrast) |

---

## 2. The Three Surface Levels (Glassmorphism)

1. **Level 1 — Standard Glass (`.glass-panel` / `.glass-level-1`)**:
   - Background: `var(--surface-glass)`
   - Backdrop filter: `blur(16px)`
   - Border: `1px solid var(--border-subtle)`
   - Layered shadow: `0 8px 30px 0 rgba(0, 0, 0, 0.32)`
   - Intended for dashboard metric cards, charts, and content panels.

2. **Level 2 — Elevated Glass (`.glass-panel-elevated` / `.glass-level-2`)**:
   - Background: `var(--surface-raised)`
   - Backdrop filter: `blur(20px)`
   - Border: `1px solid var(--border-visible)`
   - Inset light rim: `inset 0 1px 0 0 rgba(255, 255, 255, 0.08)`
   - Shadow: `0 14px 40px 0 rgba(0, 0, 0, 0.45)`
   - Intended for sticky command bars, floating metric popovers, and dropdown menus.

3. **Level 3 — Focus Surface (`.glass-modal` / `.glass-level-3`)**:
   - Background: `var(--surface-primary)` (opacity 0.96)
   - Backdrop filter: `blur(8px)`
   - Shadow: `0 24px 60px 0 rgba(0, 0, 0, 0.60)`
   - Intended for identity modals, complex forms, and safety-critical decisions.

---

## 3. The Three-Color Discipline

- **Primary Accent (Ice Cyan `#61DDF8`)**: Reserved exclusively for key interactive triggers (primary CTA buttons, active route indicator, observed telemetry line, and primary confirmation).
- **Secondary Accent (Sapphire `#6D91FF`)**: Used for supporting navigation, secondary button outlines, comparison baselines, and cross-pool links.
- **Tertiary Accent (Aurora Violet `#B29AFF`)**: Reserved for machine-learning forecast distributions, statistical quantiles, and digital twin simulation curves.
- **Status Accents**: Never used purely for decoration. Every status icon is accompanied by human-readable text (*"Healthy"*, *"Warning"*, *"Critical"*, *"Inconclusive"*).

---

## 4. Guided vs. Expert Mode System

| Capability | Guided Mode (Default) | Expert Mode |
| :--- | :--- | :--- |
| **Capacity Breach Probability** | "Chance of running short of storage" with plain tooltip | Capacity Breach Probability $P(\text{Used} \ge \text{Cap})$ |
| **Prediction Interval** | "Expected range (80% confidence)" | Conformal Quantile Interval $[q_{10}, q_{90}]$ |
| **Workload Drift** | "Workload pattern has changed" | Page-Hinkley Drift Score & Statistical Deviation |
| **Interventions** | "Compare possible actions" | Counterfactual Multi-Pool Relocation Matrix |
| **Model Degradation** | "Forecast reliability has decreased" | Calibration Error $\Delta\text{ECE}$ & Pinball Loss |
| **Latency Metric** | "Time required to generate a prediction" | Inference Latency ($t_{\text{inf}}$ in ms) |
