# Project-Wide Rules for Coding Agents

Rules for every coding agent working in this repository. This project is a portable, key-free English ↔ Arabic translation skill pack — not a hosted translation service.

## Project overview

- **What:** a portable core of skills, seven agent prompts and documentation, mapped into any host agent by an installer.
- **Who translates:** the host agent's own model performs all seven stages. Python never generates target text.
- **No credentials:** there is no API key, provider account or network request in the translation path. Do not add one.
- **Quality:** an explicit MQM gate (score ≥ 85, at most 3 revision rounds) with approved terminology injected at every stage.

## Core principles

1. **Host-agent intelligence, deterministic support.** Python builds the brief, protects placeholders, checks the term base, validates output, converts formats and scores. It does not translate.
2. **Seven sequential agents.** Analysis → Translator → Post-editor → Reviewer → Editor → Judge → Consistency. Do not parallelize stages for the same segment.
3. **Brief in, validation out.** Consumption of a translation brief and validation of host-produced text are the only contract with the model layer.
4. **Never translate protected spans.** Code blocks, placeholders, XML/HTML tags and identifiers stay verbatim; a missing placeholder is a named failure.
5. **Explicit absence.** If no host translation is available, say so. Never emit a stub or fabricated translation.
6. **MSA default.** Modern Standard Arabic for written text; a dialect only on explicit request.
7. **Markdown master.** Well-formatted Markdown is the authoritative deliverable; EPUB/DOCX/PDF are exports.

## The seven agents

| Agent | Responsibility |
|-------|----------------|
| Analysis | Genre, audience, register, domain, entities, gender context, document structure. |
| Translator | First target-language draft from the source and the brief. |
| Post-editor | Arabic grammar, morphology, gender/plural agreement, orthography. |
| Reviewer | MQM-style error spans, categories, severity and suggested fixes. |
| Editor | Applies review findings to produce the revised target text. |
| Judge | MQM gate decision: approve or return for another round. |
| Consistency | Character, place and terminology coherence across chapters. |

## Arabic rules

- Default register MSA; Egyptian, Gulf or Levantine only when explicitly requested.
- Handle root-and-pattern morphology and the six plural forms (zero, one, two, few, many, other).
- Gender and definiteness agreement, including broken plurals; normalize alef/ya/ta-marbuta variants.
- Preserve RTL markers, paragraph structure and code blocks; follow the configured diacritics policy.
- Transliterate or translate named entities according to the term base and style profile.

## Contributor rules

- Use paths relative to the repository root. The former absolute workspace path is retired; do not reintroduce it.
- Never add a credential, credential placeholder or setup instruction for a translation provider to docs, config or code.
- Every `SKILL.md` and `agents/*.md` starts with YAML frontmatter containing `name` and `description`.
- `GLOSSARY.md` holds canonical domain terms only — no implementation detail. Decisions belong in `docs/adr/` using context, decision, consequences and alternatives.
- Keep the portable core host-agnostic; host-specific behavior lives in thin adapters in the installer.
- Prefer offline resources. Optional extras are imported lazily and must never break a clean install.
- All documentation must describe the current key-free architecture. Run the docs consistency test after editing docs.

## Testing and quality gates

```bash
python -m pytest tests/ -v
python scripts/validate_pack.py
python -m pytest tests/test_docs_consistency.py -v
```

CI runs pytest, pack validation and a key-free smoke test. `main` is protected: work happens on branches through pull requests with required status checks; force pushes, deletions and admin bypass are blocked.
