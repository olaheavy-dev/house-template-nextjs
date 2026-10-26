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
| `mk/nextjs.mk` | `install-nextjs`, `check-nextjs`, `check-fast-nextjs`, `lock-frontend`, `dev-frontend`, `test-frontend`, `build-frontend`, joined to the base targets |
| `.claude/rules/nextjs.md` | Frontend rules for coding agents, loaded only when they touch `frontend/` |
| `.node-version` | The frontend's Node (26) |

Still to come, through reviewed pull requests: the backend connection (same-origin rewrites and generated API types), security headers and Playwright with axe checks, the container image and Compose service, and releases.

## Develop the template

`uv run pytest` renders the layer and checks it, including the tokens' contrast. CI also generates a real project from house-template-base plus this layer and runs its `make check` on Node 26. After changing `template/frontend/package.json`, regenerate the lockfile with pnpm 12 on Node 26 (`pnpm --dir template/frontend install --lockfile-only`).
