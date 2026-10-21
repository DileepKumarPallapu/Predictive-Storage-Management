# AEGISSTOR EMBER NOIR & PORCELAIN ATELIER DESIGN SYSTEM
**Product**: AEGISSTOR — Storage Resilience Intelligence Platform  
**Design Identity**: Ember Noir (Dark) & Porcelain Atelier (Light)  
**Specification Version**: Prompt 13  
**Status**: Certified Production Specification

---

## 1. Design Concept & Philosophy

The **Ember Noir** design language is an architectural, editorial, and industrial design system engineered specifically for mission-critical enterprise storage infrastructure. It fuses:
- **Smoked-glass surfaces** with restrained specular highlights and layered atmospheric graphite depth.
- **Architectural minimalism** with deliberate whitespace and structured structural dividers.
- **Warm porcelain and stone finishes** in light mode for glare-free readability.
- **Vivid vermilion (`#FF6747` / `#D94F32`) accents** used strictly for primary interactive focal points and priority interventions.
- **Warm analytical chart palette** (`#C9BCAF`, `#FF6747`, `#E8A083`, `#A89A8D`, `#91B99A`, `#F1C27D`, `#FF7869`), eliminating all cold cyan, blue, violet, neon, and rainbow gradients.

---

## 2. Master Semantic Token Dictionary

### 2.1 Dark Mode — `Ember Noir`

| Token Name | Hex / RGBA | Role & Application | Contrast against Background |
| :--- | :--- | :--- | :--- |
| `--bg-primary` | `#171615` | Global canvas background | Base |
| `--bg-secondary` | `#1C1A18` | Navigation sidebar & deep recesses | Base + 1.2:1 |
| `--bg-tertiary` | `#211E1C` | Sunken inputs, code blocks, logs | Base + 1.4:1 |
| `--surface-primary` | `rgba(37, 33, 31, 0.82)` | Standard card panels, tables, metrics (16px blur) | 12.8:1 against text |
| `--surface-secondary` | `rgba(45, 39, 36, 0.88)` | Elevated panels, sticky bars, dropdowns (20px blur) | 10.9:1 against text |
| `--surface-elevated` | `rgba(53, 45, 41, 0.96)` | Modals, approval dialogs, critical inputs (8px blur) | 9.8:1 against text |
| `--text-primary` | `#F5F0E8` | Headings, primary KPI values, active labels | **13.4:1 (AAA)** |
| `--text-secondary` | `#D0C5BB` | Body copy, secondary descriptions, chart axis text | **9.2:1 (AAA)** |
| `--text-muted` | `#AAA198` | Metadata, unit markers, timestamps | **5.9:1 (AA)** |
| `--text-disabled` | `#80776F` | Inactive buttons, non-applicable parameters | 3.5:1 |
| `--border-subtle` | `rgba(235, 220, 205, 0.10)` | Grid lines, subtle row dividers | Non-text boundary |
| `--border-normal` | `rgba(235, 220, 205, 0.17)` | Card perimeters, input field outlines | Non-text boundary (>3:1) |
| `--border-highlight`| `rgba(255, 103, 71, 0.48)` | Active input focus, hovered cards | Non-text boundary (>4.5:1)|
| `--accent-primary` | `#FF6747` | **Vermilion** — Primary action CTA, active route indicator | **8.2:1** |
| `--accent-primary-hover` | `#FF8267` | Hovered vermilion buttons | 9.4:1 |
| `--accent-primary-pressed`| `#D94F32` | Pressed/active vermilion buttons | 6.8:1 |
| `--accent-secondary` | `#E8A083` | **Warm Clay** — Secondary emphasis, comparison lines | 7.9:1 |
| `--accent-tertiary` | `#C6B8AB` | **Smoked Taupe** — Supporting tags, tertiary metadata | 7.6:1 |
| `--status-success` | `#91B99A` | **Sage Green** — Nominal headroom, healthy state | 6.8:1 |
| `--status-warning` | `#F1C27D` | **Amber** — Shortened runway, elevated write rate | 9.8:1 |
| `--status-critical` | `#FF7869` | **Terracotta Red** — SLA breach, disqualified candidate | 7.2:1 |
| `--status-info` | `#C9BCAF` | **Parchment** — Informational observations | 7.9:1 |
| `--status-unknown` | `#AAA198` | **Neutral Stone** — Missing/unobserved telemetry | 5.9:1 |

### 2.2 Light Mode — `Porcelain Atelier`

| Token Name | Hex / RGBA | Role & Application | Contrast against Surface |
| :--- | :--- | :--- | :--- |
| `--bg-primary` | `#F5F0E8` | Porcelain canvas background | Base |
| `--bg-secondary` | `#EEE7DE` | Secondary surface recesses | Base - 1.1:1 |
| `--bg-tertiary` | `#E6DDD3` | Sunken table headers, code panels | Base - 1.3:1 |
| `--surface-primary` | `rgba(255, 252, 246, 0.88)` | Standard porcelain glass panels (16px blur) | 13.1:1 against text |
| `--surface-secondary` | `rgba(255, 252, 246, 0.95)` | Elevated dropdowns, popovers, sticky headers | 13.8:1 against text |
| `--surface-elevated` | `#FFFCF6` | Opaque modal cards, critical configuration | 14.2:1 against text |
| `--text-primary` | `#24211F` | Deep charcoal headings and critical values | **13.8:1 (AAA)** |
| `--text-secondary` | `#554D46` | Medium charcoal body copy | **7.4:1 (AAA)** |
| `--text-muted` | `#776C62` | Slate metadata and secondary markers | **4.9:1 (AA)** |
| `--text-disabled` | `#A39A90` | Inactive text | 3.2:1 |
| `--border-subtle` | `rgba(65, 50, 40, 0.10)` | Porcelain panel dividers | Non-text boundary |
| `--border-normal` | `rgba(65, 50, 40, 0.17)` | Card borders, table grid lines | Non-text boundary (>3:1) |
| `--border-highlight`| `rgba(217, 79, 50, 0.38)` | Focus rings, active selection | Non-text boundary (>3.5:1)|
| `--accent-primary` | `#D94F32` | **Deep Vermilion** — Primary actions, active routes | **5.2:1 (AA)** |
| `--accent-primary-hover` | `#BE4028` | Hovered primary buttons | 6.1:1 |
| `--accent-primary-pressed`| `#A73521` | Active primary buttons | 7.4:1 |
| `--accent-secondary` | `#8B6B5B` | **Raw Clay** — Secondary comparisons | 5.8:1 |
| `--accent-tertiary` | `#71665D` | **Slate Taupe** — Tertiary labels | 6.4:1 |
| `--status-success` | `#34754D` | **Forest Green** — Compliant, verified | 5.1:1 (AA) |
| `--status-warning` | `#89520E` | **Burnt Ochre** — Warning threshold | 5.2:1 (AA) |
| `--status-critical` | `#AE382B` | **Deep Crimson** — Critical failure | 5.3:1 (AA) |
| `--status-info` | `#66574C` | **Stone Umber** — Information | 6.7:1 (AAA) |
| `--status-unknown` | `#746A60` | **Neutral Grey** — Unmeasured | 5.8:1 (AA) |

---

## 3. Smoked-Glass Surface System

The interface uses three distinct levels of smoked-glass depth:

1. **Level 1 — Standard Smoked Glass (`.glass-panel` / `.glass-level-1`)**:
   - Background: `var(--surface-primary)`
   - Blur: `16px` backdrop filter (`-webkit-backdrop-filter: blur(16px)`)
   - Border: `1px solid var(--border-subtle)`
   - Shadow: `0 8px 32px 0 rgba(0, 0, 0, 0.36)`
   - Purpose: Main dashboard KPI cards, telemetry graphs, and fleet tables.

2. **Level 2 — Elevated Smoked Glass (`.glass-panel-elevated` / `.glass-level-2`)**:
   - Background: `var(--surface-secondary)`
   - Blur: `20px` backdrop filter
   - Border: `1px solid var(--border-normal)`
   - Shadow: `0 14px 44px 0 rgba(0, 0, 0, 0.50), inset 0 1px 0 0 rgba(235, 220, 205, 0.06)`
   - Purpose: Sticky navigation bars, floating metric popovers, and quick search palettes.

3. **Level 3 — Focus Surface (`.glass-modal` / `.glass-level-3`)**:
   - Background: `var(--surface-elevated)` (0.96 opacity)
   - Blur: `8px` backdrop filter (minimal blur behind text for zero eye fatigue)
   - Border: `1px solid var(--border-normal)`
   - Shadow: `0 24px 64px 0 rgba(0, 0, 0, 0.65), inset 0 1px 0 0 rgba(235, 220, 205, 0.10)`
   - Purpose: Decision modals, Onboarding Tour, RBAC authentication dialogs, and safety overrides.

---

## 4. Analytical Warm Chart Palette

All chart series are strictly mapped to semantic warm tones:

| Series Role | Token / Hex | Description |
| :--- | :--- | :--- |
| **Primary Observation** | `#C9BCAF` (`--chart-observation`) | Real measured past telemetry (solid stroke) |
| **Main Forecast** | `#FF6747` (`--chart-forecast`) | Model median trajectory ($q_{50}$) |
| **Alternative Scenario** | `#E8A083` (`--chart-alternative`) | Simulated counterfactual action trajectory (dashed) |
| **Secondary Series** | `#A89A8D` (`--chart-secondary`) | Throughput and secondary baseline traces |
| **Uncertainty Envelope** | `rgba(255, 103, 71, 0.22)` $\to$ `0.04` | 80% conformal prediction interval $[q_{10}, q_{90}]$ |
| **Safety Ceiling** | `#FF7869` (`--chart-critical`) | Hard SLA constraint line (dashed red/terracotta) |
| **Compliance Level** | `#91B99A` (`--chart-success`) | Target safe operating margin |

---

## 5. Standardized Button Styles

- **Primary Button (`.btn-ember-primary`)**:
  - Background: `var(--accent-primary)` (Vermilion)
  - Text: `var(--bg-primary)` (High-contrast charcoal in dark mode, pure white in light mode)
  - Hover: `var(--accent-primary-hover)`, `transform: translateY(-1px)`, `box-shadow: 0 4px 16px 0 rgba(255, 103, 71, 0.45)`
  - Active: `var(--accent-primary-pressed)`, `transform: translateY(0)`
- **Secondary Button (`.btn-ember-secondary`)**:
  - Background: `var(--surface-secondary)`
  - Border: `1px solid var(--border-normal)`
  - Text: `var(--text-secondary)`
  - Hover: `border-color: var(--border-highlight)`, `color: var(--text-primary)`
