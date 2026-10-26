---
paths:
  - "frontend/**"
---

# Frontend (Next.js)

Owned by house-template-nextjs. Sources: the Next.js docs bundled with the installed version (`frontend/node_modules/next/dist/docs/`; see `frontend/AGENTS.md`), React (https://react.dev), Tailwind CSS (https://tailwindcss.com/docs) and pnpm (https://pnpm.io).

- Read the version-matched docs in `frontend/node_modules/next/dist/docs/` before using a Next.js API: this is Next.js 16, and training data is often older (no `next lint`, `proxy.ts` instead of `middleware.ts`, Cache Components). `next dev` keeps a managed block in `frontend/AGENTS.md`; commit it when it changes.
- App Router under `frontend/src/app/`; Server Components by default, `"use client"` only where a component needs state, effects or browser APIs. Cache Components is on: wrap request-time data in `<Suspense>` and mark cached work with `"use cache"`.
- Styling is Tailwind v4 over the semantic tokens in `src/styles/tokens.css` (`bg-bg-secondary`, `text-text-primary`, `border-border-primary`...). Never hard-code colours, radii or fonts in components; re-skin by changing token values, and keep every text colour at 4.5:1 or more on every background (the template's tests check the starter set).
- Accessible by default: one `h1` per page, real buttons and links, labels on every input, visible focus (`:focus-visible` uses the focus-ring token), and nothing that only works on hover.
- Dependencies: pnpm 12 on Node 26 (`.node-version`). Add with `pnpm --dir frontend add <pkg>` (exact versions are saved), run `make lock-frontend`, commit both files. Install scripts run only for packages allowed in `frontend/pnpm-workspace.yaml`.
- Checks: `make check` runs ESLint (no warnings allowed), Prettier, `tsc` with strict settings, Vitest and a production build. Unit-test components with Testing Library by role and text, as a user would find them.
- Never put secrets in `NEXT_PUBLIC_*` variables: they are written into the browser bundle at build time. Server-only code reads plain environment variables.
