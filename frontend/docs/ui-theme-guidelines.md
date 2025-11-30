# Dr Chaffee UI Theme – Guardrails

> **STATUS: FINAL** — This theme is locked unless explicitly updated by Hugo.

## 1. Theme Lock Policy

The Dr Chaffee UI theme is **FINAL** and considered an **immutable design contract**.
Do NOT modify any visual styling unless Hugo explicitly instructs the change.

## 2. Protected Elements — DO NOT MODIFY

The following elements are locked and must not be changed:

- **Global color tokens** (CSS custom properties in `:root`, `.dark-mode`, `.light-mode`)
- **Background gradients** (search button, cards, overlays)
- **Card styling** (border-radius, shadows, border thickness)
- **Dashboard layout** under `/tuning/*` (except `/tuning/auth` for auth-specific fixes)
- **Typography scale** (font sizes, weights, line heights)
- **Spacing scale** (`--space-*` variables)
- **Shadow definitions** (`--shadow-*` variables)
- **Border radius tokens** (`--radius-*` variables)

## 3. Allowed Changes

Only apply **targeted changes** when Hugo explicitly requests them:

- Bug fixes that don't alter visual appearance
- Accessibility improvements (focus states, ARIA attributes)
- New components that reuse existing design tokens
- Content updates (text, labels, copy)

## 4. Component Reuse Policy

Always reuse existing UI primitives:

- `<SearchBar>` — Main search input with answer style toggle
- `<FilterPills>` — Source and year filter chips
- `<AnswerCard>` — AI response display
- `<VideoCard>` — Video result cards
- `<LoadingSkeleton>` — Loading states
- `<Footer>` — Page footer with disclaimer
- `<DarkModeToggle>` — Theme switcher
- `<DisclaimerBanner>` — Medical disclaimer

## 5. Forbidden Actions

- ❌ Never introduce new color palettes
- ❌ Never redesign components without explicit instruction
- ❌ Never change global CSS variables
- ❌ Never modify card radii, shadows, or borders
- ❌ Never alter the tuning dashboard layout
- ❌ Never change button gradients or hover states
- ❌ Never modify typography scale

## 6. Confirmation Required

For any change that would alter the look/feel:

1. **STOP** before implementing
2. **ASK** Hugo for explicit confirmation
3. **DOCUMENT** the requested change
4. **IMPLEMENT** only after approval

## 7. Protected Files

The following files define the locked-in visual system:

| File | Purpose |
|------|---------|
| `src/styles/globals.css` | Global CSS variables and base styles |
| `src/styles/tuning.css` | Tuning dashboard styles |
| `src/styles/custom-instructions.css` | Custom instructions editor styles |
| `src/components/SearchBar.tsx` | Search input styling |
| `src/components/FilterPills.tsx` | Filter chip styling |
| `src/components/AnswerCard.tsx` | Answer card styling |
| `src/components/VideoCard.tsx` | Video card styling |
| `src/components/Footer.tsx` | Footer styling |
| `src/components/DarkModeToggle.tsx` | Theme toggle styling |

## 8. Design Contract

Treat this theme as an **immutable design contract** unless told otherwise by Hugo.

The current dark/light theme, card styles, and tuning dashboard appearance are the **final baseline**.
Any deviation requires explicit written approval.