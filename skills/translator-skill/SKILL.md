# translator-skill — SKILL.md

**Name:** translator-skill
**Version:** 1.0.0
**Description:** Multi-agent English ↔ Arabic translation skill for coding agents (Claude Code, Codex, OpenCode, etc.)
**Author:** Kilo
**License:** MIT

## Triggers

- User requests translation between English and Arabic
- User asks to translate a book, document, or code strings
- User invokes `/translate` or similar translation command

## Tools

| Tool | Description |
|------|-------------|
| `analysis` | Pre-process source text, extract context (register, domain, entities, gender) |
| `translate` | Produce draft translation with glossary injection |
| `postedit` | Arabic grammar, morphology, gender/plural correction |
| `review` | MQM-style structured critique |
| `judge` | Quality gate (0–100 rubric), approve or request revision |
| `consistency` | Cross-chapter coherence for books |

## Usage

```
# Translate text
skills translator-skill translate --source "Hello world" --target ar

# Translate a file
skills translator-skill translate --file input.txt --target ar --output output_ar.txt

# Translate a book
skills translator-skill translate-book --input book.epub --target ar --output book_ar.epub

# Run full pipeline
skills translator-skill pipeline --source input.txt --target ar --output output_ar.txt
```

## Configuration

- Default target Arabic register: MSA
- Quality threshold: 85 (LLM Judge)
- Max iterations: 3
- Glossary: data/glossary.tbx
- Diacritics policy: remove (configurable in config/translator.yaml)

## Installation

```bash
# Into Claude Code:
cp -r skills/translator-skill ~/.claude/skills/translator

# Into Codex/OpenCode:
cp -r skills/translator-skill ~/.agents/skills/translator

# Via npx:
npx skills add /path/to/skills/translator-skill
```

## Project Files

- `prompt.md` — Agent system prompts (7 agents)
- `tools/analysis.py` — Analysis Agent implementation
- `tools/translate.py` — Translator Agent implementation
- `tools/postedit.py` — Post-Editor Agent implementation
- `tools/review.py` — Reviewer Agent implementation
- `tools/judge.py` — LLM Judge Agent implementation
- `tools/consistency.py` — Consistency Agent implementation
- `data/glossary.tbx` — Term base (ISO 30042)
- `data/style_guides/` — Style guide references
- `data/wordnet/` — Open English Wordnet 2025
