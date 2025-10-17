# Repository Guidelines

## Project Structure & Module Organization
- `main.py` hosts the Slack standup sender; keep helper modules in `src/` if the logic grows, and mirror business domains in subpackages.
- Place integration assets (sample payloads, webhook docs) in `docs/`; reference them from the README for onboarding.
- Store automated tests under `tests/` with names that match the module under test, e.g., `tests/test_main.py`.

## Build, Test, and Development Commands
- `python3 main.py` sends the standup message using the configured webhook; use a sandbox webhook when experimenting.
- `python3 -m venv .venv && source .venv/bin/activate` sets up a local environment; pin dependencies in `requirements.txt`.
- `pytest` runs the test suite; add `-k` to target individual tests during development.

## Coding Style & Naming Conventions
- Follow PEP 8: 4-space indentation, descriptive snake_case for functions and variables, PascalCase for classes.
- Prefer pure functions for message formatting and keep network calls isolated for easier mocking.
- Run `ruff check .` before committing; configure ignores in `pyproject.toml` if needed.

## Testing Guidelines
- Use `pytest` fixtures for timestamps and webhook stubs; store fixtures in `tests/conftest.py` for reuse.
- Name tests after the behavior under verification, e.g., `test_send_message_includes_date`.
- Maintain coverage for message formatting and Slack integration adapters; add regression tests whenever webhook behavior changes.

## Commit & Pull Request Guidelines
- Write commits in the imperative mood (`Add slack payload formatter`) and keep them scoped to one logical change.
- Reference issues in the footer (`Refs #123`) and describe validation steps in the body (`Test: pytest`).
- Pull requests should summarize the problem, the solution, and include screenshots or transcripts of Slack test posts when relevant.

## Security & Configuration Tips
- Never hardcode production webhooks; read `WEBHOOK_URL` from environment variables or a secrets manager in deployment code.
- Rotate shared secrets after demos and scrub logs before attaching them to issues or PRs.
