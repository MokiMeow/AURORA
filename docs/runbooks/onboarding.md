# Onboarding Runbook (Phase 0)

## Purpose
Provide deterministic steps for engineers to configure AURORA-SE development environments.

## Steps
1. Clone repository and create Python virtual environment.
2. Install dependencies with `pip install -e .[dev]`.
3. Install pre-commit hooks: `pre-commit install`.
4. Start Docker services: `docker compose up -d`.
5. Run smoke tests: `pytest`, `ruff check .`.
6. Explore sample monorepo under `examples/sample_repo/` and run `aurora-se index --full`.
7. Configure environment variables (`CRITIC_*`, database credentials) using `.env` template.
8. Review `docs/quickstart.md` and `docs/architecture.md` for system overview.

