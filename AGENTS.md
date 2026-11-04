# Project-Wide Rules for Coding Agents

This file provides project-wide rules for all coding agents (Claude Code, Codex, OpenCode, OpenHands, Aider, etc.)
working on the Multi-Agent Translation System (EN ↔ Arabic).

## Project Overview

- **Project:** Multi-Agent Translation System (EN ↔ Arabic)
- **Location:** `/data/workspace/projects/translator/`
- **Goal:** A role-specialized, quality-gated translation pipeline for English ↔ Arabic
- **Target users:** Coding agents and book translation workflows

## Core Principles

1. **Sequential pipeline over parallel generation** — terminology consistency is paramount
2. **Glossary injected at every stage** — improves term success rate
3. **Role specialization** — each agent has one clear responsibility
4. **Arabic-first quality** — COMET-MQM, chrF, AL-BLEU; BLEU alone is insufficient
5. **Never translate code blocks** — placeholders, XML/HTML tags, IDs remain unchanged
6. **MSA default** — Modern Standard Arabic for written text unless dialect is explicitly requested

## Agent Roles

| Agent | Responsibility |
|-------|---------------|
| Analysis | Register detection, domain, entities, gender context, orthography normalization |
| Translator | Initial draft translation with glossary injection |
| Post-editor | Arabic grammar, morphology, gender/plural agreement, diacritics |
| Reviewer | MQM-style structured critique (accuracy, fluency, style, terminology, coherence) |
| Editor | Apply reviewer feedback to produce revised draft |
| Judge | Quality gate (0–100 rubric), approve or route back (max 3 iterations) |
| Consistency | Cross-chapter coherence for books (character registry, dynamic glossary) |

## Code Conventions

- Language: Python 3.10+
- Type hints required on all public functions
- Docstrings in Google style
- Black formatting, isort import ordering
- Tests in `tests/` using pytest
- Configuration in `config/translator.yaml`

## File Handling

- Preserve RTL markers, paragraph structure, code blocks, placeholders
- Arabic orthography normalization before processing
- 6 Arabic plural forms (zero/one/two/few/many/other)
- Glossary format: TBX (ISO 30042) / UTX (AAMT)

## Testing

Run all tests:
```bash
pytest tests/
```

Run specific test:
```bash
pytest tests/test_arabic_morphology.py -v
```

## Quality Thresholds

- LLM Judge score ≥ 85 for approval
- Glossary adherence (TSR) ≥ 95%
- Max 3 iterations per segment
