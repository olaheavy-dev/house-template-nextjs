"""The rendered layer: files, answers, the checks it plugs into the base Makefile, and tokens."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess

import pytest
import yaml

from conftest import BASE_ANSWERS, TEMPLATE


def test_layer_renders_the_frontend_and_its_answers(render):
    project = render()
    for path in ("frontend/package.json", "frontend/src/app/page.tsx", "frontend/AGENTS.md",
                 "mk/nextjs.mk", ".node-version", ".claude/rules/nextjs.md",
                 ".github/template-owned/nextjs.txt"):
        assert (project / path).is_file(), path
    answers = yaml.safe_load((project / ".copier-answers.nextjs.yml").read_text())
    assert answers["backend"] == "fastapi"  # the base answers list the fastapi stack


@pytest.mark.parametrize(("stacks", "expected"), [(["fastapi", "nextjs"], "fastapi"),
                                                  (["nextjs"], "none"),
                                                  (["nextjs", "dotnet"], "none")])
def test_the_backend_defaults_from_the_stacks(render, project, stacks, expected):
    dst = render(project(stacks=stacks))
    assert yaml.safe_load((dst / ".copier-answers.nextjs.yml").read_text())["backend"] == expected


def test_any_openapi_backend_can_be_chosen(render, project):
    dst = render(project(stacks=["nextjs", "dotnet"]), backend="openapi")
    assert yaml.safe_load((dst / ".copier-answers.nextjs.yml").read_text())["backend"] == "openapi"


@pytest.mark.filterwarnings("ignore:File not found:UserWarning")
def test_layer_refuses_a_project_without_base_answers(render, project):
    with pytest.raises(Exception, match="Apply house-template-base first"):
        render(project(base=None))


def test_layer_refuses_base_answers_without_the_nextjs_stack(render, project):
    with pytest.raises(Exception, match="nextjs stack"):
        render(project(stacks=["fastapi"]))


def test_the_fastapi_backend_needs_the_fastapi_stack(render, project):
    with pytest.raises(Exception, match="needs the fastapi stack"):
        render(project(stacks=["nextjs"]), backend="fastapi")


def test_node_and_pnpm_are_pinned_together():
    package = json.loads((TEMPLATE / "frontend/package.json").read_text())
    node = (TEMPLATE / ".node-version").read_text().strip()
    assert package["engines"]["node"] == f">={node} <{int(node) + 1}"
    assert re.fullmatch(r"pnpm@\d+\.\d+\.\d+", package["packageManager"])
    # Exact versions only: save-exact, and nothing with a range in the template.
    for name, version in {**package["dependencies"], **package["devDependencies"]}.items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), (name, version)


def test_lockfile_is_project_owned_after_the_first_copy():

    config = yaml.safe_load((TEMPLATE.parent / "copier.yml").read_text())
    assert "frontend/pnpm-lock.yaml" in config["_skip_if_exists"]
    assert (TEMPLATE / "frontend/pnpm-lock.yaml").is_file()


def test_mk_file_adds_its_targets_to_the_base_aggregates(render):
    mk = (render() / "mk" / "nextjs.mk").read_text()
    assert "INSTALLS += install-nextjs" in mk
    assert "CHECKS += check-nextjs" in mk
    assert "FAST_CHECKS += check-fast-nextjs" in mk
    targets = re.findall(r"^([a-z][a-z0-9-]*):", mk, flags=re.MULTILINE)
    described = re.findall(r"^([a-z][a-z0-9-]*):.*## ", mk, flags=re.MULTILINE)
    assert targets and targets == described
    # No target another layer already defines (the FastAPI layer has dev, test and lock).
    assert not {"dev", "test", "lock", "build"} & set(targets)


@pytest.mark.parametrize("backend", ["fastapi", "openapi", "none"])
def test_every_template_owned_entry_matches_a_file(render, project, backend):
    # The base's check reads each line as an fnmatch glob.
    dst = render(project(stacks=["fastapi", "nextjs"]), backend=backend)
    lines = (dst / ".github/template-owned/nextjs.txt").read_text().splitlines()
    entries = [line for line in lines if line and not line.startswith("#")]
    files = [p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file()]
    assert entries
    for entry in entries:
        assert any(fnmatch.fnmatch(f, entry) for f in files), entry


def make_dry_run(project, target, **variables):
    """The commands `make` would run for one of the layer's targets, with CI unset unless given."""
    env = {k: v for k, v in os.environ.items() if k not in {"CI", "E2E_DOCKER"}}
    args = [f"{name}={value}" for name, value in variables.items()]
    return subprocess.run(
        ["make", "-n", "-f", "mk/nextjs.mk", target, *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()


def test_locally_the_end_to_end_tests_use_an_installed_chromium_after_the_build(render):
    project = render()
    assert "pnpm --dir frontend exec playwright install --only-shell chromium" in make_dry_run(
        project, "install-nextjs"
    )
    check = make_dry_run(project, "check-nextjs")
    assert check.index("pnpm --dir frontend build") < check.index("pnpm --dir frontend e2e")


@pytest.mark.parametrize("variables", [{"CI": "true"}, {"E2E_DOCKER": "1"}])
def test_ci_runs_the_end_to_end_tests_in_playwrights_image_with_no_chromium_here(
    render, variables
):
    project = render()
    install = make_dry_run(project, "install-nextjs", **variables)
    assert not any("playwright install" in line for line in install)
    check = make_dry_run(project, "check-nextjs", **variables)
    assert check.index("pnpm --dir frontend build") < check.index("pnpm --dir frontend e2e:docker")


def test_screenshots_are_remade_only_in_playwrights_image(render):
    lines = make_dry_run(render(), "screenshots-frontend")
    assert lines[-1] == "pnpm --dir frontend e2e:docker --update-snapshots=changed"


def test_the_docker_script_is_executable_and_runs_the_installed_playwright_version(render):
    script = render() / "frontend" / "scripts" / "e2e-docker.sh"
    assert os.access(script, os.X_OK)
    text = script.read_text()
    assert 'mcr.microsoft.com/playwright:v${version}-noble' in text
    assert '"playwright@${version}" run-server' in text


def test_every_page_has_a_screenshot_in_every_project(render):
    frontend = render() / "frontend"
    spec = (frontend / "e2e" / "pages.spec.ts").read_text()
    pages = json.loads(re.search(r"const PAGES = (\[.*?\]);", spec).group(1))
    projects = re.findall(r'name: "(\w+)"', (frontend / "playwright.config.ts").read_text())
    assert projects == ["light", "dark", "mobile"]
    expected = {
        f"{'home' if page == '/' else page[1:].replace('/', '-')}-{name}.png"
        for page in pages
        for name in projects
    }
    shots = frontend / "e2e" / "screenshots" / "pages.spec.ts"
    assert {path.name for path in shots.iterdir()} == expected


def test_rules_file_loads_only_for_frontend_paths(render):
    rules = (render() / ".claude/rules/nextjs.md").read_text()
    front = yaml.safe_load(rules.split("---")[1])
    assert front == {"paths": ["frontend/**"]}


def test_agents_file_holds_nextjs_managed_block():
    # Committed as next dev writes it, so an agent running the dev server leaves the tree clean.
    agents = (TEMPLATE / "frontend/AGENTS.md").read_text()
    assert agents.startswith("<!-- BEGIN:nextjs-agent-rules -->")
    assert "node_modules/next/dist/docs/" in agents
    assert agents.rstrip().endswith("<!-- END:nextjs-agent-rules -->")


def test_claude_code_reads_the_frontends_agents_file():
    # Claude Code loads CLAUDE.md, not AGENTS.md, from a directory it works in; base's root
    # CLAUDE.md does the same for the root AGENTS.md.
    assert (TEMPLATE / "frontend/CLAUDE.md").read_text() == "@AGENTS.md\n"


def test_no_local_build_output_or_secrets_are_ever_copied(render):
    secret = TEMPLATE / "frontend" / ".env"
    created = not secret.exists()
    if created:
        secret.write_text("SECRET=never-copied\n")
    try:
        project = render()
    finally:
        if created:
            secret.unlink()
    for leftover in ("node_modules", ".next", ".env", "next-env.d.ts"):
        assert not (project / "frontend" / leftover).exists(), leftover


def test_base_answers_fixture_matches_the_pinned_base_version():
    workflow = (TEMPLATE.parent / ".github/workflows/test.yml").read_text()
    assert f"BASE_VERSION: {BASE_ANSWERS['_commit']}" in workflow



# --- The backend connection, per backend choice ----------------------------------------------

API_FILES = ("frontend/src/app/api/[...path]/route.ts", "frontend/src/lib/api/proxy.ts",
             "frontend/src/lib/api/server.ts", "frontend/src/lib/api/browser.ts",
             "frontend/src/lib/api/schema.d.ts", "frontend/src/lib/auth.ts",
             "frontend/.env.example")


def test_fastapi_gets_the_proxy_types_from_its_api_and_a_staleness_check(render):
    project = render()
    for path in API_FILES:
        assert (project / path).is_file(), path
    assert '"/v1/me"' in (project / "frontend/src/lib/api/schema.d.ts").read_text()
    mk = (project / "mk/nextjs.mk").read_text()
    assert "CHECKS += check-nextjs check-api-types" in mk
    assert "app.main import create_app" in mk
    assert "make api-types" in (project / ".claude/rules/nextjs.md").read_text()


def test_another_openapi_backend_starts_with_empty_types_and_a_schema_argument(render, project):
    dst = render(project(stacks=["nextjs", "dotnet"]), backend="openapi")
    for path in API_FILES:
        assert (dst / path).is_file(), path
    schema = (dst / "frontend/src/lib/api/schema.d.ts").read_text()
    assert "export type paths = Record<string, never>;" in schema
    mk = (dst / "mk/nextjs.mk").read_text()
    assert "API_SCHEMA ?=" in mk
    assert "check-api-types" not in mk
    assert "app.main" not in mk
    assert "API_SCHEMA=" in (dst / ".claude/rules/nextjs.md").read_text()


def test_no_backend_means_no_proxy_types_or_sign_in_hook(render, project):
    dst = render(project(stacks=["nextjs"]), backend="none")
    for path in API_FILES:
        assert not (dst / path).exists(), path
    assert not (dst / "frontend/src/lib/api").exists()
    mk = (dst / "mk/nextjs.mk").read_text()
    assert "api-types" not in mk
    assert mk.endswith("$(FRONTEND) e2e:docker --update-snapshots=changed\n")
    rules = (dst / ".claude/rules/nextjs.md").read_text()
    assert "backendCredentials" not in rules
    assert rules.endswith("never a tag.\n")


def test_the_api_types_belong_to_the_project_after_the_first_copy():
    config = yaml.safe_load((TEMPLATE.parent / "copier.yml").read_text())
    assert "frontend/src/lib/api/schema.d.ts" in config["_skip_if_exists"]


def test_the_env_example_is_committed_and_holds_no_public_variables(render):
    project = render()
    ignore = (project / "frontend/.gitignore").read_text().splitlines()
    assert ignore.index("!.env.example") > ignore.index(".env*")
    example = (project / "frontend/.env.example").read_text()
    assert "API_BASE_URL=" in example
    assert not [line for line in example.splitlines() if line.startswith("NEXT_PUBLIC_")]

# --- Tokens: WCAG contrast for the starter palette, light and dark ---------------------------

TOKENS = (TEMPLATE / "frontend/src/styles/tokens.css").read_text()


def palette(block: str) -> dict[str, str]:
    return dict(re.findall(r"--color-([a-z-]+):\s*(#[0-9a-f]{6})", block))


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


LIGHT = palette(TOKENS.split("@media")[0])
DARK = palette(TOKENS.split(':root[data-theme="dark"]')[1])
BACKGROUNDS = ("bg-primary", "bg-secondary", "bg-tertiary")
TEXT = ("text-primary", "text-secondary", "text-tertiary", "text-link",
        "status-success", "status-warning", "status-danger", "accent-primary")


def test_dark_mode_is_defined_once_for_the_system_and_once_for_the_switch():
    media = palette(TOKENS.split("@media")[1].split(':root[data-theme="dark"]')[0])
    assert media == DARK
    assert set(DARK) == set(LIGHT)


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("text", TEXT)
@pytest.mark.parametrize("background", BACKGROUNDS)
def test_text_meets_aa_on_every_background(mode, text, background):
    colours = LIGHT if mode == "light" else DARK
    assert contrast(colours[text], colours[background]) >= 4.5


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_interactive_edges_and_buttons_are_readable(mode):
    colours = LIGHT if mode == "light" else DARK
    for edge in ("border-secondary", "focus-ring"):
        for background in BACKGROUNDS:
            assert contrast(colours[edge], colours[background]) >= 3, (edge, background)
    # Text on the accent button, and inverse text on the inverse background.
    assert contrast(colours["text-inverse"], colours["accent-primary"]) >= 4.5
    assert contrast(colours["text-inverse"], colours["accent-primary-hover"]) >= 4.5
    assert contrast(colours["text-inverse"], colours["bg-inverse"]) >= 4.5


def web_service(dst):
    return yaml.safe_load((dst / "frontend" / "compose.yaml").read_text())["services"]["web"]


def test_the_image_runs_the_node_major_the_project_pins(render):
    dst = render()
    major = (dst / ".node-version").read_text().strip()
    dockerfile = (dst / "frontend" / "Dockerfile").read_text()
    images = re.findall(r"^FROM (node:\S+)", dockerfile, re.MULTILINE)
    assert images and all(
        re.fullmatch(rf"node:{major}\.\d+\.\d+-trixie-slim@sha256:[0-9a-f]{{64}}", image)
        for image in images
    ), images


def test_the_image_runs_the_standalone_server_as_a_non_root_user(render):
    dockerfile = (render() / "frontend" / "Dockerfile").read_text()
    assert "USER 10001:10001" in dockerfile
    assert 'CMD ["node", "server.js"]' in dockerfile
    # pnpm comes from package.json's packageManager, so the two never drift.
    assert "require(\"./package.json\").packageManager" in dockerfile


def test_the_build_gets_the_commit_before_next_build_prerenders_the_health_route(render):
    # Base's publish-image.yml passes GIT_COMMIT; /health/live is prerendered, so `next build` must see it.
    dockerfile = (render() / "frontend" / "Dockerfile").read_text()
    build_stage = dockerfile.split("FROM base AS build")[1].split("\nFROM ")[0]
    assert build_stage.index('ARG GIT_COMMIT=""') < build_stage.index("RUN pnpm build")


def test_secrets_and_local_builds_stay_out_of_the_image(render):
    ignored = (render() / "frontend" / ".dockerignore").read_text().splitlines()
    for entry in [".env", ".env.*", "node_modules/", ".next/"]:
        assert entry in ignored


def test_the_web_service_calls_the_fastapi_layer_inside_compose(render):
    web = web_service(render())
    assert web["environment"]["API_BASE_URL"] == "http://api:8000"
    assert web["depends_on"] == {"api": {"condition": "service_healthy"}}
    assert web["ports"] == ["127.0.0.1:${WEB_PORT:-3000}:3000"]
    assert "http://127.0.0.1:3000/health/live" in web["healthcheck"]["test"][-1]


def test_the_web_service_reaches_another_api_on_this_machine(render, project):
    web = web_service(render(project(stacks=["nextjs"]), backend="openapi"))
    assert web["environment"]["API_BASE_URL"] == "${API_BASE_URL:-}"
    assert web["extra_hosts"] == ["host.docker.internal:host-gateway"]
    assert "depends_on" not in web


def test_the_web_service_needs_nothing_without_a_backend(render, project):
    web = web_service(render(project(stacks=["nextjs"]), backend="none"))
    assert "API_BASE_URL" not in web["environment"]
    assert "depends_on" not in web


def test_the_healthcheck_path_is_a_route(render):
    assert (render() / "frontend/src/app/health/live/route.ts").exists()


@pytest.mark.parametrize("container_images", [True, False])
def test_the_web_image_is_published_only_with_container_images(render, project, container_images):
    dst = render(project(container_images=container_images))
    workflow = dst / ".github/workflows/publish-web.yml"
    owned = (dst / ".github/template-owned/nextjs.txt").read_text().splitlines()
    assert workflow.exists() == container_images
    assert (".github/workflows/publish-web.yml" in owned) == container_images
    if container_images:
        job = yaml.safe_load(workflow.read_text())["jobs"]["web"]
        assert job["uses"] == "./.github/workflows/publish-image.yml"
        assert job["with"] == {"image": "web", "context": "frontend"}
