# Design Language: Unknown Site

> Extracted from `https://genome.ucsc.edu/cgi-bin/hgGateway` on June 10, 2026
> 11 elements analyzed

This document describes the complete design language of the website. It is structured for AI/LLM consumption — use it to faithfully recreate the visual design in any framework.

## Color Palette

### Neutral Colors

| Hex | HSL | Usage Count |
|-----|-----|-------------|
| `#000000` | hsl(0, 0%, 0%) | 22 |

### Text Colors

Text color palette: `#000000`

### Full Color Inventory

| Hex | Contexts | Count |
|-----|----------|-------|
| `#000000` | text, border | 22 |

## Typography

### Font Families

- **Helvetica** — used for all (7 elements)
- **Times** — used for body (3 elements)
- **Arial** — used for all (1 elements)

### Type Scale

| Size (px) | Size (rem) | Weight | Line Height | Letter Spacing | Used On |
|-----------|------------|--------|-------------|----------------|---------|
| 16px | 1rem | 400 | normal | normal | html, head, script, body |
| 13.3333px | 0.8333rem | 400 | normal | normal | small, input |

### Heading Scale

```css
h4 { font-size: 16px; font-weight: 400; line-height: normal; }
```

### Font Weights in Use

`400` (10x), `700` (1x)

## Spacing

| Token | Value | Rem |
|-------|-------|-----|
| spacing-8 | 8px | 0.5rem |
| spacing-21 | 21px | 1.3125rem |

## CSS Custom Properties

### Semantic

```css
success: [object Object];
warning: [object Object];
error: [object Object];
info: [object Object];
```

## Transitions & Animations

### Common Transitions

```css
transition: all;
```

## Component Patterns

Detected UI component patterns and their most common styles:

### Inputs (1 instances)

```css
.input {
  color: rgb(0, 0, 0);
  border-color: rgb(0, 0, 0);
  border-radius: 0px;
  font-size: 13.3333px;
  padding-top: 0px;
  padding-right: 0px;
}
```

## Layout System

**0 grid containers** and **0 flex containers** detected.

## Accessibility (WCAG 2.1)

**Overall Score: 100%** — 0 passing, 0 failing color pairs

## Design System Score

**Overall: 82/100 (Grade: B)**

| Category | Score |
|----------|-------|
| Color Discipline | 85/100 |
| Typography Consistency | 80/100 |
| Spacing System | 55/100 |
| Shadow Consistency | 85/100 |
| Border Radius Consistency | 100/100 |
| Accessibility | 100/100 |
| CSS Tokenization | 50/100 |

**Strengths:** Tight, disciplined color palette, Clean elevation system, Consistent border radii, Strong accessibility compliance

**Issues:**
- No clear primary brand color detected
- No consistent spacing base unit detected — values appear arbitrary

## Page Intent

**Type:** `unknown` (confidence 0)

## Material Language

**Label:** `flat` (confidence 0.55)

| Metric | Value |
|--------|-------|
| Avg saturation | 0 |
| Shadow profile | none |
| Avg shadow blur | 0px |
| Max radius | 0px |
| backdrop-filter in use | no |
| Gradients | 0 |

## Quick Start

To recreate this design in a new project:

1. **Install fonts:** Add `Helvetica` from Google Fonts or your font provider
2. **Import CSS variables:** Copy `variables.css` into your project
3. **Tailwind users:** Use the generated `tailwind.config.js` to extend your theme
4. **Design tokens:** Import `design-tokens.json` for tooling integration
