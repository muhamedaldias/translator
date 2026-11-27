# Portable Translation Skill Pack (EN ↔ Arabic)

[![CI](https://github.com/muhamedaldias/translator/actions/workflows/ci.yml/badge.svg)](https://github.com/muhamedaldias/translator/actions/workflows/ci.yml)
[![Release](https://github.com/muhamedaldias/translator/actions/workflows/release.yml/badge.svg)](https://github.com/muhamedaldias/translator/actions/workflows/release.yml)

A professional, portable skill pack that adds a high-quality English ↔ Arabic translation workflow to any coding agent. The host agent's own model performs every translation stage; there is **no API key, no provider account and no network dependency** in the translation path.

## Why it is different

- **Host agent translates.** Claude Code, Codex, OpenCode, Hermes or a generic agent supplies the model; the pack supplies the method.
- **No API key anywhere.** Nothing to provision, nothing to export, no secret to rotate and no per-call provider bill from this repository.
- **Python is deterministic support only.** It builds a context-rich brief, protects placeholders, checks the term base, validates host output, converts formats and scores results. It never invents a translation.
- **Seven role-specialized agents** run in sequence, with approved terminology injected at every stage.
- **An explicit MQM gate** accepts or returns a translation (score ≥ 85, at most 3 revision rounds).
- **Professional deliverables:** a formatted Markdown master with EPUB and DOCX export and optional PDF.

## Install

The installer maps the portable core into the host's native layout. It has no global side effects and supports a preview:

```bash
bash scripts/install.sh --host claude-code          # plugin manifest, .claude/skills, .claude/agents, /translate command
bash scripts/install.sh --host codex                # .agents/skills + .agents/agents
bash scripts/install.sh --host opencode             # .agents/...
bash scripts/install.sh --host hermes               # ~/.hermes/skills
bash scripts/install.sh --host generic --dest .     # AGENTS.md + skills in a chosen directory
bash scripts/install.sh --dry-run --host claude-code
bash scripts/install.sh --help
```

For Claude Code the pack also ships a plugin manifest (`.claude-plugin/plugin.json`) and a `/translate` command (`commands/translate.md`). For Hermes it installs under `~/.hermes/skills/`. The generic path places a portable `AGENTS.md` and the skills in a directory you choose. `scripts/install_skill.sh` is kept as a compatibility shim; prefer `scripts/install.sh`.

## The seven agents

| Agent | Responsibility |
|-------|----------------|
| Analysis | Establish genre, audience, register, domain, entities, gender context and document structure. |
| Translator | Produce the first target-language draft from the source and the brief. |
| Post-editor | Repair Arabic grammar, morphology, agreement and orthography. |
| Reviewer | Record MQM errors with category and severity, plus suggested fixes. |
| Editor | Apply review findings and produce a revised target text. |
| Judge | Apply the MQM gate: approve or send back for another round. |
| Consistency | Keep names, places and terminology coherent across book chapters. |

Every stage receives the same brief and the same approved term base. The workflow never translates code, placeholders, tags or identifiers, and never fabricates target text when a host translation is missing.

## How a translation runs

1. **Brief** — the deterministic layer extracts context, approved terms and verbatim spans into a translation brief.
2. **Draft and refine** — the host agent executes the seven agents in sequence using the brief and the bundled prompts.
3. **Gate** — the Reviewer and Judge apply the MQM rubric. A score below 85 returns the text for revision, up to three rounds.
4. **Validate** — the deterministic layer checks placeholders, terminology and structure; a missing placeholder is a named failure, never a silent pass.
5. **Deliver** — the approved text becomes the master Markdown, then an EPUB/DOCX edition and optional PDF.

## Quality and Arabic handling

- MSA is the default for written Arabic; a dialect is used only when explicitly requested.
- Root-and-pattern morphology, six plural forms, gender and definiteness agreement, and alef/ya/ta-marbuta normalization are handled in the prompts and checks.
- RTL layout, paragraph structure and the diacritics policy follow a bundled style profile.
- Automatic metrics are optional and degrade honestly: no model download is required to run the pack or its tests.

## Repository layout

```
README.md, AGENTS.md, CLAUDE.md, plan.md   # user- and agent-facing docs
GLOSSARY.md                                # canonical domain terms
docs/adr/                                  # architecture decision records
docs/style-guide.md, docs/translation-brief-template.md
skills/                                    # portable core: skills and seven agent prompts
agents/                                    # role definitions
scripts/install.sh                         # host installer
config/translator.yaml                     # deterministic settings
src/                                       # brief, validation, term base, formats, scoring
tests/                                     # offline pytest suite
```

All paths are relative to the repository root.

## Develop and verify

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=75
python scripts/validate_pack.py
ruff check src tests scripts
black --check src tests scripts
mypy -p src
bandit -q -r src -ll
bash scripts/install.sh --host generic --dest /tmp/pack-host --dry-run
```

### CI/CD gates

Every push to `main` and every pull request runs four independent jobs:

- **test** — pytest with a 75% coverage floor, pack validation and a key-free brief smoke test on Python 3.10, 3.11 and 3.12.
- **quality** — Ruff lint, Black format check and Mypy type check.
- **security** — Bandit scan at medium severity and above; no known medium/high findings are tolerated.
- **install-smoke** — installs the pack into an isolated directory and runs the installed support layer, so prompts can never point at files that were not shipped.

`main` is protected: changes require a pull request, all status checks must pass, force pushes and deletions are blocked, and there is no admin bypass. Direct pushes to `main` are not part of the workflow.

### Continuous delivery

Pushing a `v*` tag runs `.github/workflows/release.yml`, which packages the portable core (skills, agents, docs, config, data, support layer, adapters) into `translator-skill-pack.zip`, uploads it as a build artifact and publishes a GitHub Release with generated notes. Example:

```bash
git tag v1.1.0 && git push origin v1.1.0
```

Dependabot checks pip and GitHub Actions dependencies weekly.

## License

MIT
