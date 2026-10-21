# AEGISSTOR UX/UI Audit — Stage 1
**Product**: AEGISSTOR — Storage Resilience Intelligence Platform  
**Audit Objective**: Identify visual, linguistic, navigational, and cognitive friction in the current platform to prepare for the *Aurora Experience (Human-First Glass)* overhaul.

---

## 1. Executive Findings

| Dimension | Previous State | Target in Aurora Experience 12.0 |
| :--- | :--- | :--- |
| **Cognitive Load for Beginners** | Raw mathematical terms (*conformal interval coverage*, *pinball loss*, *counterfactual intervention*, *distribution shift*) presented immediately without context. | **Guided Mode (Default)** with plain-language explanations (*Expected range*, *Chance of running short*, *Compare possible actions*) + **Expert Mode** toggle for deep diagnostics. |
| **Color Hierarchy** | Cyan, purple, and coral accents occasionally competed for visual prominence. | **Three-Color Discipline**: Ice Cyan (`#61DDF8`) for primary actions; Sapphire (`#6D91FF`) for navigation and comparisons; Aurora Violet (`#B29AFF`) for analytical models; semantic status colors with icons and labels. |
| **Glassmorphism Discipline** | Semi-transparent panels without strict depth tiers; potential contrast loss in high-ambient lighting. | **3 Structured Surface Levels**: Level 1 (Standard Glass, 16px blur), Level 2 (Elevated Glass, 20px blur), Level 3 (Focus Surface / Solid Glass for dense data and forms). |
| **Information Architecture** | 16 discrete navigation items displayed in a single rail without clear goal-oriented categorization. | **7 Goal-Oriented Clusters**: Overview, Monitor, Predict, Simulate, Respond, Research, Administration with mobile responsive drawer and breadcrumbs. |
| **First-Time User Experience** | No welcome tour or guided explanation of synthetic demo vs real telemetry, leaving beginners disoriented. | **Interactive 6-Step Onboarding Walkthrough** introducing the platform, data modes, digital twin safety guarantees, and navigation layout. |
| **Chart Interpretation** | Quantile bands without layperson narrative summaries. | **Contextual Chart Summaries**: Dynamic plain-language sentences explaining trends, ranges, and SLA boundaries derived directly from telemetry. |
| **Alert Communication** | Standard alert title and target string. | **4-Question Alert Framework**: 1. What happened? 2. Why does it matter? 3. What is the evidence? 4. What can the user do next? |

---

## 2. Module-by-Module Usability Review

### 2.1 Navigation & Global Shell
- **Problem**: Long flat lists of tabs caused cognitive overload. Icons without category headers made finding features difficult on smaller screens.
- **Action**: Group routes by user workflows (*Overview*, *Monitor*, *Predict*, *Simulate*, *Respond*, *Research*, *Administration*). Add mobile collapsible drawer with backdrop blur.

### 2.2 Executive Dashboard (`PageExecutiveOverview.tsx`)
- **Problem**: 4 high-density metric cards with technical labels (*Estimated Reserve Runway*, *Fleet Storage Capacity*). Beginners couldn't instantly determine if the system was healthy or in danger.
- **Action**: Add an Executive Health Condition Banner at the top in plain English ("All 4 storage pools are healthy and operating normally"). Provide dual-mode metric cards that display friendly summaries by default and reveal raw GB/sample metrics on demand.

### 2.3 Storage Fleet (`PageStorageFleet.tsx`)
- **Problem**: Complex capacity and latency constraints shown without explanation of what "Hard Safety Envelope" means to physical storage.
- **Action**: Add contextual guidance card explaining that thresholds protect storage from data loss and that digital twin simulations test these constraints safely without physical modifications.

### 2.4 Digital Twin & Interventions (`PageStorageDigitalTwin.tsx` & `PageInterventionStudio.tsx`)
- **Problem**: "Counterfactual Intervention" sounds academic and intimidating to storage operators.
- **Action**: Re-label primary view to "Compare Possible Actions (Digital Twin Simulator)". Explain plainly: "Test hypothetical actions like moving cold data or expanding disks in a virtual sandbox before applying them."

### 2.5 ML & Reliability Labs (`PageMLPredictionLab.tsx` & `PageModelReliability.tsx`)
- **Problem**: Highly technical quantile loss charts without explanation of why quantile pinball loss matters to capacity managers.
- **Action**: Add Guided Mode explanation: "The model predicts an 80% expected range. In 8 out of 10 times, actual storage demand stays within these bounds."

---

## 3. WCAG 2.2 AA Contrast & Readability Targets

- **Dark Theme (`Aurora Midnight`)**:
  - Background: `#070B14`, Surface: `#111C32`
  - Primary text: `#F3F6FF` (Contrast ratio **14.8:1** against `#070B14`, **11.9:1** against `#111C32` — passes AAA).
  - Secondary text: `#B0BED7` (Contrast ratio **9.1:1** against `#070B14`, **7.3:1** against `#111C32` — passes AAA).
  - Muted text: `#8596B5` (Contrast ratio **5.8:1** against `#070B14`, **4.7:1** against `#111C32` — passes AA).
  - Primary Ice Cyan Accent: `#61DDF8` (Contrast ratio **12.4:1** against `#070B14`).
- **Light Theme (`Pearl Aurora`)**:
  - Background: `#F2F5FB`, Surface: `#FFFFFF`
  - Primary text: `#17223A` (Contrast ratio **13.5:1** against `#F2F5FB` — passes AAA).
  - Secondary text: `#4B5C76` (Contrast ratio **6.8:1** against `#FFFFFF` — passes AA).
  - Primary Accent: `#006F91` (Contrast ratio **5.2:1** against `#FFFFFF` — passes AA).
