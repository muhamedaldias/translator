## What changed

<!-- Describe the change and why. Link issues with Closes #N. -->

## Verification

- [ ] `python -m pytest tests/ -q --cov=src --cov-fail-under=75`
- [ ] `python scripts/validate_pack.py`
- [ ] `ruff check src tests scripts`
- [ ] `black --check src tests scripts`
- [ ] `mypy -p src`
- [ ] `bandit -q -r src -ll`
- [ ] Installed-pack smoke test (CI job `install-smoke`)

## Pack contract

- [ ] No API key, provider call or fake translation in the default path
- [ ] Every `SKILL.md` / `agents/*.md` has valid frontmatter
- [ ] Prompts and code agree on the MQM scale, decision values and stage names
