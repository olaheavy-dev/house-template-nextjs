# Owned by house-template-nextjs. Included by the base Makefile; adds the frontend's install and
# checks to `make install`, `make check` and `make check-fast`. Its own targets end in -frontend,
# so they never clash with another layer's (the FastAPI layer has `dev`, `test` and `lock`).

FRONTEND := pnpm --dir frontend

INSTALLS += install-nextjs
CHECKS += check-nextjs
FAST_CHECKS += check-fast-nextjs

.PHONY: install-nextjs check-nextjs check-fast-nextjs lock-frontend dev-frontend test-frontend build-frontend

install-nextjs: ## Install the frontend's dependencies (from frontend/pnpm-lock.yaml; needs Node 26 and pnpm 12)
	$(FRONTEND) install --frozen-lockfile

check-nextjs: ## Frontend: lint, format, types, unit tests and a production build
	$(FRONTEND) lint
	$(FRONTEND) format:check
	$(FRONTEND) typecheck
	$(FRONTEND) test
	$(FRONTEND) build

check-fast-nextjs: ## Frontend: lint and types (the pre-push and stop-hook checks)
	$(FRONTEND) lint
	$(FRONTEND) typecheck

lock-frontend: ## Update frontend/pnpm-lock.yaml after changing frontend/package.json
	$(FRONTEND) install --lockfile-only

dev-frontend: ## Run the frontend with reload on http://localhost:3000
	$(FRONTEND) dev

test-frontend: ## Run the frontend's unit tests
	$(FRONTEND) test

build-frontend: ## Build the frontend for production (the standalone server)
	$(FRONTEND) build
