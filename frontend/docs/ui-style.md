Dr Chaffee AI — UI Style Notes (Frontend)
1. Overall vibe

Dark-first, premium UI

Strong contrast, but not neon

Layout is clean + focused, not “dashboard noisy”

Color used sparingly for:

Brand (Dr Chaffee avatar, icons)

Status (warnings, exclusives)

Links/icons (YouTube red, Zoom blue)

2. Layout

App content lives in a centered column with a max width (around 960–1100px).

Hero section:

Avatar + “Ask Dr Chaffee” + subtitle are centered.

Content cards below are left-aligned within the same column.

Use CSS grid or flex for sections, but avoid clever nesting that makes simple cards hard to reason about.

3. Typography

Font: Inter / system stack.

Hierarchy:

H1 (Ask Dr Chaffee): large, bold, centered.

H2/H3 inside cards: left-aligned, medium weight.

Body: comfortable line-height, no ultra-light greys for critical copy.

Avoid changing font sizes per component—prefer a small set of tokens:

--text-xl (hero)

--text-lg (card headings)

--text-base (body)

--text-sm (labels, pills)

4. Colors & themes

Do not invent new colors; always use theme variables.

Dark mode:

Background: deep neutral (--color-background)

Cards: slightly lighter neutral (--color-card)

Text: --color-text / --color-text-muted / --color-text-strong

Light mode:

Same structure: --color-background-light, --color-card-light, etc.

When wiring light/dark mode:

Toggle happens on <html> (e.g. .dark-mode / .light-mode).

Components should read only from CSS variables, never hard-coded hex.

5. Header & navigation

Header uses display: flex; align-items: center; justify-content: space-between;.

Nav links (.nav-link):

.nav-link,
.nav-link:visited {
  color: var(--color-text-strong); /* effectively white on dark */
  text-decoration: none;
}

.nav-link:hover,
.nav-link:focus-visible {
  text-decoration: underline;
}


“Tuning Dashboard” and “Logout” share the same styling; no purple / red UA colors.

6. Cards

Cards are the main building block.

Visual rules:

border-radius: large, consistent (same as dashboard).

border: subtle, var(--color-border-subtle).

background: var(--color-card).

Internal padding: use spacing tokens (--space-3, --space-4), not random numbers.

“How it works” card:

Horizontal layout:

.how-it-works {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}
.how-it-works-icon { flex-shrink: 0; }
.how-it-works-text { text-align: left; }

7. Search area

Search bar lives under the main cards, centered in the column.

Pattern:

max-width (e.g. 640px) + margin: 0 auto;

Input + icons wrapped in a flex container for alignment.

“Search” button shares width with input and sits directly below.

Use box-sizing: border-box; globally so width + padding don’t cause overflow.

8. Source filter pills

Overall look: monochrome premium; brand color only in icons.

Container:

.filter-pills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}


Pills:

.filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;

  background: transparent;
  border: 1px solid var(--color-border-subtle);
  color: var(--color-text-muted);

  font-size: 0.85rem;
  cursor: pointer;
}

.filter-pill.active {
  background: var(--color-card);
  border-color: var(--color-primary);
  color: var(--color-text);
}


Ensure “All” pill text is always legible in both themes.

9. Avatar

Avatar must always remain circular, even on narrow screens:

.profile-avatar {
  width: 72px;        /* or token */
  height: 72px;
  border-radius: 999px;
  object-fit: cover;
  flex-shrink: 0;
}

10. Global sanity rules

body { margin: 0; } — no browser margin.

Global box model:

*,
*::before,
*::after {
  box-sizing: border-box;
}


Prefer composable flex/grid over deeply nested margins.

If something looks “off by a few pixels”, fix alignment rather than adding micro-offset hacks.