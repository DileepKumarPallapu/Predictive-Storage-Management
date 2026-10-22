# Hitit Design System Analysis & AEGISSTOR Adaptation Strategy

## 1. Executive Summary & Reference Analysis
This document records the empirical design observations from inspecting **Hitit's live enterprise platform** (`https://hitit.com/`) and outlines how those architectural design patterns are adapted to **AEGISSTOR: Storage Resilience Intelligence Platform**.

---

## 2. Hitit Live Reference Findings

### 2.1 Color Architecture
- **Canvas & Surfaces**: Clean architectural light-first foundation. Not sterile clinical white, but a warm, confident porcelain (`#F5F5F2` / `#F8F8F6`) paired with pure white cards (`#FFFFFF`).
- **Brand Crimson**: Hitit employs a distinctive, confident enterprise crimson (`#B82432` / `#A01D26`) for primary focus, logo accents, and high-priority action states.
- **Neutrals & Typography**: Rich dark graphite (`#1C1E1C` / `#242724`) providing WCAG AAA text contrast, balanced with slate-green neutral secondary text (`#555C56` / `#727971`).
- **Dividers & Hairlines**: Crisp, understated borders (`#DFE2DD` / `#E8ECE6`) that structure complex enterprise grids without visual clutter.

### 2.2 Typography Hierarchy
- **Primary Typefaces**: Hitit uses `Manrope` and `Outfit` for geometric headlines, paired with clean sans-serif for body.
- **Scale & Weight**:
  - H1 Page Titles: Bold / Extra Bold (700-800), tight letter spacing (`-0.02em`).
  - Section Headings: Semi-bold (600), clean line height (`1.3`).
  - Monospace Data: Clean alignment for numbers, metrics, timestamps, and capacity values.

### 2.3 Layout & Structural Discipline
- **Header**: Fixed, horizontal command bar with prominent brand mark, grouped contextual controls, search utility, notifications, and profile pill.
- **Navigation**: Structured vertical sidebar with grouped operational categories, clear active-state indicator with brand crimson bar, and collapsed icon tooltips.
- **Card System**: Purposeful grouping with 8px-10px border radius, 1px hairline border, subtle micro-elevation on hover, and generous whitespace.

### 2.4 Restrained Motion & Enterprise Interactions
- **Transition Times**: Fast, purposeful 120ms–200ms easing (`cubic-bezier(0.16, 1, 0.3, 1)`).
- **Feedback**: Subtle border-color shifts and micro-elevation on hover without distracting bouncing or gratuitous glowing.

---

## 3. AEGISSTOR Adaptation Tokens

### Light Theme (Default)
```css
--app-background: #F5F5F2;
--surface-primary: #FFFFFF;
--surface-secondary: #F8F8F6;
--surface-subtle: #EEEEEC;
--text-primary: #1C1E1C;
--text-secondary: #555C56;
--text-muted: #727971;
--border-subtle: #E8ECE6;
--border-normal: #DFE2DD;
--border-visible: #CED2CC;
--brand-primary: #B82432;
--brand-hover: #981E2A;
--brand-soft: #F9E9EB;
--status-success: #22784D;
--status-warning: #94651A;
--status-critical: #C33F36;
--focus-ring: #B82432;
```

### Dark Theme (Independent, High Contrast)
```css
--app-background: #121412;
--surface-primary: #181B18;
--surface-secondary: #202420;
--surface-subtle: #272C27;
--text-primary: #F0F2EF;
--text-secondary: #B0B8AF;
--text-muted: #7A8479;
--border-subtle: #252A26;
--border-normal: #323833;
--border-visible: #424A43;
--brand-primary: #D13847;
--brand-hover: #E64C5B;
--brand-soft: rgba(209, 56, 71, 0.15);
--status-success: #2EB369;
--status-warning: #CCA038;
--status-critical: #E24C43;
--focus-ring: #D13847;
```

---

## 4. Protected Workflows & Regression Plan
- Zero modification to backend services, API client, or telemetry collectors.
- Preserve Demo Mode, Replay Mode, and Live Host passive mode.
- Preserve Guided vs. Expert narrative switching.
- Complete visual alignment across all 19 application routes and modals.
