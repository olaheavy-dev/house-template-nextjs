# house-template-nextjs

The Next.js layer of my Copier project templates. It adds a Next.js frontend under `frontend/` to a project generated from [house-template-base](https://github.com/olaheavy-dev/house-template-base), plugs the frontend's checks into the base `make check` and CI, and talks to any backend with an OpenAPI schema: the [FastAPI layer](https://github.com/olaheavy-dev/house-template-fastapi), an ASP.NET Core API or an external one.

## Use it

```sh
copier copy --trust gh:olaheavy-dev/house-template-base my-app      # choose the nextjs stack
cd my-app && git init -b main && git add -A && git commit -m "chore: start from house-template-base"
copier copy --trust -a .copier-answers.nextjs.yml gh:olaheavy-dev/house-template-nextjs .
make install && make check      # needs Node 26 and pnpm 12
make dev-frontend
```

The layer reads the project's stacks from `.copier-answers.base.yml` and refuses to apply without the `nextjs` stack. Its one question is the backend: FastAPI (the default when the project has that stack), another API with an OpenAPI schema, or none. The project owns `frontend/pnpm-lock.yaml`, so after an update that changes dependencies, run `make lock-frontend` and commit the lockfile.

## What it adds

| Path | What |
|---|---|
| `frontend/` | Next.js 16 App Router under `src/`, React 19, standalone output, Cache Components on; strict TypeScript 5.9; ESLint (`core-web-vitals`, `typescript`) and Prettier; Vitest with Testing Library |
| `frontend/src/styles/tokens.css` | Neutral design tokens (light and dark) with semantic names, mapped into Tailwind v4; every text colour is tested for WCAG AA contrast on every background |
| `frontend/AGENTS.md` | Next.js's managed block pointing coding agents at the version-matched docs in `node_modules/next/dist/docs/`, committed so `next dev` never dirties the tree |
| `frontend/package.json`, `.npmrc`, `pnpm-workspace.yaml` | pnpm 12 on Node 26, exact versions, install scripts allowed one by one |
| `frontend/src/proxy.ts`, `src/lib/csp.ts`, `next.config.ts` | Security headers on every response (nosniff, frame-deny, no-referrer, COOP, Permissions-Policy, HSTS in production) and a Content Security Policy per request: prerendered pages allow only this origin's scripts (inline ones included, since they're built before any request), and paths listed in `NONCE_PATHS` get a per-request nonce with `'strict-dynamic'` |
| `frontend/src/app/{not-found,error,global-error}.tsx` | Error pages that never show an error's message, only the digest the server logged it under |
| `frontend/e2e/`, `playwright.config.ts` | Playwright 1.64 against the standalone production build, in light, dark and a phone's width: every page passes axe (WCAG 2.2 AA) with no CSP violations or page errors, and the headers arrive. Part of `make check` |
| `frontend/src/app/api/[...path]/route.ts`, `src/lib/api/` | The backend connection: a same-origin `/api/*` proxy to `API_BASE_URL` (read per request, so one build runs anywhere; streams bodies, passes only a short list of headers, never the browser's cookies or Authorization), and typed `openapi-fetch` clients for the browser (`api`, through the proxy) and the server (`serverApi()`, direct). Types come from the backend's OpenAPI schema with `make api-types`; with FastAPI, `make check` fails while they are behind |
| `frontend/src/lib/auth.ts` | `backendCredentials`, the sign-in hook a project replaces with its provider: it turns the frontend's session into the headers the backend checks. It fails closed; `DEV_USER` stands in for a user in development through the FastAPI layer's `X-Dev-User` |
| `mk/nextjs.mk` | `install-nextjs`, `check-nextjs`, `check-fast-nextjs`, `lock-frontend`, `dev-frontend`, `test-frontend`, `build-frontend`, `e2e-frontend` and `api-types`, joined to the base targets |
| `.claude/rules/nextjs.md` | Frontend rules for coding agents, loaded only when they touch `frontend/` |
| `.node-version` | The frontend's Node (26) |

With no backend, the proxy, clients and sign-in hook are left out.

Still to come, through reviewed pull requests: screenshot baselines made in a pinned Linux image, the container image and Compose service, and releases.

## Develop the template

`uv run pytest` renders the layer and checks it, including the tokens' contrast. CI also generates real projects and runs their `make check` on Node 26: base plus this layer with no backend and with an OpenAPI one, and base plus the FastAPI layer plus this layer, where it also calls the backend through the frontend's proxy in production and development. After a new FastAPI layer release, regenerate the starter API types from it (`make api-types` in a generated project, then copy `frontend/src/lib/api/schema.d.ts` to the fastapi-named file in `template/frontend/src/lib/api/`). After changing `template/frontend/package.json`, regenerate the lockfile with pnpm 12 on Node 26 (`pnpm --dir template/frontend install --lockfile-only`).
