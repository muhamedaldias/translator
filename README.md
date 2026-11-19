# Multi-Agent Translation System (EN ↔ Arabic)

A professional, role-specialized multi-agent translation system for English ↔ Arabic translation.
Designed to work with any coding agent (Claude Code, Codex, OpenCode, OpenHands, Aider, etc.)
and suitable for translating books, technical documentation, UI/strings, and code.

## Project Structure

```
translator/
├── README.md
├── AGENTS.md                  # Project-wide rules for coding agents
├── CLAUDE.md                  # Claude Code specific rules
├── plan.md                    # Implementation plan
├── research/                  # Deep research reports
├── skills/                    # SKILL.md skills for coding agents
├── agents/                    # Agent prompt definitions
├── src/                       # Core implementation (Python)
├── data/                      # Glossaries, character/place registries
├── tests/                     # Unit + integration tests
├── config/                    # Configuration (translator.yaml)
├── scripts/                   # Install + CLI scripts
└── outputs/                   # Translated output (gitignored)
```

## Quick Start

### Install as a coding agent skill

```bash
# From within your coding agent project:
npx skills add ./skills/translator-skill
```

Or manually copy the skill directory to:
- `.claude/skills/` (Claude Code)
- `.agents/skills/` (Codex, OpenCode)

### Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Optional: LLM providers and book formats
pip install openai ebooklib beautifulsoup4 python-docx pypdf
```

### Run the pipeline

Real translation requires an LLM provider. Without one, the pipeline runs
in PLACEHOLDER mode (glossary substitution only) and warns loudly — that
output is NOT a translation.

```bash
export OPENAI_API_KEY=sk-...   # or ANTHROPIC_API_KEY
python src/pipeline.py --source input.txt --target ar --output output_ar.txt --use-llm
```

### Translate a book

```bash
python scripts/translate_book.py --input book.epub --target ar --output book_ar.epub
```

## Pipeline Architecture

```
Analysis Agent → Translator Agent → Post-editor Agent → Reviewer Agent → LLM Judge Agent
```

Each agent is role-specialized. The system injects glossary at every stage and uses a quality gate (LLM Judge, threshold ≥ 85) with up to 3 iterations.

## Evaluation

- **COMET-MQM** (primary) — highest correlation with human judgments
- **chrF** (secondary) — robust for Arabic morphology
- **AL-BLEU** — Arabic-specific morphologically-aware BLEU
- **TSR** — Term Success Rate for glossary adherence

## Arabic-Specific Features

- MSA default for written text; dialect support on request
- Root-and-pattern morphology handling
- 6 Arabic plural forms (zero/one/two/few/many/other)
- Gender agreement (verb-subject, noun-adjective, definiteness)
- Orthography normalization (alef/ya/ta-marbuta variants)
- RTL preservation and code-block protection
- Diacritics policy (configurable)

## Current Limitations

- Register detection, diacritization, and transliteration are heuristic
  placeholders (documented in `src/arabic.py`).
- Cross-chapter consistency checks are limited to alias-vs-canonical
  name checks against the registries.
- PDF output is text-only (`.txt`); PDF input is extraction-only.
- EPUB reconstruction produces a simplified EPUB (original images/CSS
  are not preserved).
- COMET-MQM requires `pip install unbabel-comet` and a model download;
  without it, evaluation falls back to chrF/AL-BLEU.

## License

MIT — see [LICENSE](LICENSE).
