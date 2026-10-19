# Development Environment and Coding Standards

**Document ID:** DEV-001  
**Status:** DRAFT  
**Linked:** [`PLAN.md`](../PLAN.md), [`TEST-STRATEGY`](test-strategy.md), [`SECURITY`](security.md)

## 1. Environment setup

| Item | Value | Notes |
|---|---|---|
| Python | 3.13.15 | `.venv` active |
| Virtual environment | `.venv` (project-local) | stdlib `venv`; excluded from git via `.gitignore` |
| Activation (PowerShell) | `.venv\Scripts\Activate.ps1` | |
| Dev dependencies | `requirements-dev.txt` | ruff, pytest, bandit, pip-audit + FastAPI runtime stack |
| Installation | `python -m pip install -r requirements-dev.txt` | |

## 2. Verification commands

| Purpose | Command |
|---|---|
| Python version | `python --version` |
| Lint | `python -m ruff check .` |
| Format check | `python -m ruff format --check .` |
| Unit tests | `python -m pytest` |
| Security SAST | `python -m bandit -r gateway users catalog inventory orders payments shared` |
| Dependency scan | `python -m pip_audit` |
| Compose validate | `docker compose config --quiet` |
| Trivy version | `trivy --version` |

## 3. Coding standards (Ponytail-aligned)

| Rule | Description |
|---|---|
| YAGNI | Does this need to exist at all? Speculative need = skip it. |
| Stdlib first | Use standard library before adding dependencies (e.g., `hashlib.pbkdf2_hmac` instead of passlib/bcrypt). |
| No unrequested abstractions | No interface with one implementation, no factory for one product. |
| Fewest files | Shortest working diff wins. Deletion over addition. |
| Mark simplifications | Use `# ponytail:` comment for deliberate simplifications with ceiling + upgrade path. |
| Security non-negotiable | Never simplify away input validation, error handling preventing data loss, or security measures. |
| One runnable check | Non-trivial logic leaves one small test or `assert`-based self-check. |

## 4. File conventions
- Python files: `snake_case.py`
- Test files: `test_*.py` alongside code or in `tests/` directory
- Ruff configuration: `.ruff.toml` (ignores B008 for FastAPI `Depends()`, E501 line length)
- `.gitignore`: excludes `.venv/`, `.env`, `*.db`, `__pycache__/`, `.ruff_cache/`, `.pytest_cache/`

## 5. Dependency rules
- Pin major versions in `requirements-dev.txt` with `<next-major>` upper bound
- Add runtime deps to per-service `requirements.txt` as services are implemented
- Never commit secrets; `.env.example` is the template only

## 6. Open questions
- Ruff line length: default 88 or custom? (`DECIDED`: E501 ignored)
- Pre-commit hooks? (`OPEN`)
