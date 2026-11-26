---
name: reference-skills
description: Offline EN↔AR reference procedures for the translation workflow — dictionary, synonym, term-base and style-guide lookups. Use when an agent needs lexical evidence or approved terminology without network access.
---

# Reference Skills

Offline-first lookup procedures used by the translation agents for word-sense disambiguation, synonym expansion, approved terminology and style decisions. All lookups are performed by the host coding agent reading bundled local resources; no API, token or metered network service is used or required.

## Triggers

- An agent needs a definition, synonym, EN↔AR headword pair or usage note.
- A term must be checked against the approved term base before being rendered.
- A style or transliteration question arises (see `docs/style-guide.md`).

## Reference procedures (prompt procedures)

| Procedure | Local resource | Role |
|-----------|----------------|------|
| `en_lexicon` | WordNet-style lexical notes in `research/dictionaries_references.md` | Synonyms, hypernyms, glosses, word-sense disambiguation |
| `en_ar_bilingual` | `data/glossary.tbx` + `research/dictionaries_references.md` | EN↔AR headword pairs and approved renderings |
| `synonym_expansion` | `research/dictionaries_references.md` | Concept-based synonym expansion for register choices |
| `style_reference` | `docs/style-guide.md`, `research/papers_articles.md` | Arabic style, transliteration and formatting rules |

Named-entity detection is a reasoning step inside `agents/analysis_agent.md`; no separate entity tool exists. There is no network/metered dictionary service: offline resources are authoritative and the workflow stays air-gapped.

## Tools (prompt procedures)

| Tool | What the host agent does |
|------|--------------------------|
| `lookup_definition` | Reads the local lexical notes to explain a headword and its senses. |
| `lookup_synonyms` | Reads local synonym material to propose register-appropriate alternatives. |
| `lookup_en_ar` | Looks up an EN↔AR pair in `data/glossary.tbx` and the bilingual notes. |
| `lookup_style_guide` | Reads `docs/style-guide.md` for headings, quotes, RTL, diacritics and code rules. |
| `query_glossary` | Returns the approved target term for a source term and domain from `data/glossary.tbx`. |

## Integration

These procedures are consulted by: Analysis (entity and difficult-term decisions), Translator (glossary injection), Post-editor (orthography and named entities), Reviewer and Judge (terminology adherence and MQM scoring), and Consistency (term tracking). The glossary is injected at **every** stage; an approved rendering is never replaced by a lookup synonym without an explicit flag.

## Offline-first policy

Prefer the bundled local resources. If a term is genuinely absent, flag it with `confidence_flags` in `agents/translator_agent.md` for human review rather than contacting an external service. No API key or provider account exists in this pack.
