# reference-skills — SKILL.md

**Name:** reference-skills
**Version:** 1.0.0
**Description:** Reference skills for the Multi-Agent Translation System — dictionaries, thesauri, style guides
**Author:** Kilo
**License:** MIT

## Sub-Skills

| Skill | Resource | Role | Access |
|-------|----------|------|--------|
| `en_lexicon` | Open English Wordnet 2025 | Synonyms, hypernyms, glosses, WSD | Local, offline |
| `en_ar_bilingual` | Wiktionary EN + AR dumps | EN-AR headword pairs | Local dump |
| `synonym_expansion` | Roget's Thesaurus 1911 | Concept-based synonym expansion | Local parse |
| `style_reference` | UNESCO/AUSIT/Mozilla Arabic guides | Style rules, transliteration | Ingested knowledge base |
| `datamuse_synonyms` | Datamuse API | Lightweight synonyms | Network, free |

## Tools

| Tool | Description |
|------|-------------|
| `lookup_definition` | Look up word definitions (Merriam-Webster, WordNet) |
| `lookup_synonyms` | Look up synonyms (WordNet, Datamuse, Roget's) |
| `lookup_en_ar` | Look up EN-AR translations (Wiktionary) |
| `lookup_style_guide` | Look up style guide rules |
| `query_glossary` | Query term base for approved translations |

## Usage

```
# Look up definition
skills reference-skills lookup_definition --word "hello" --dictionary wordnet

# Look up synonyms
skills reference-skills lookup_synonyms --word "translate" --source wordnet

# Look up EN-AR translation
skills reference-skills lookup_en_ar --term "computer" --direction en-ar

# Query glossary
skills reference-skills query_glossary --term "API" --domain technical
```

## Integration

These skills are used by the translator-skill agents for:
- Word sense disambiguation (Analysis Agent)
- Synonym expansion (Translator Agent)
- Style guide compliance (all agents)
- Glossary lookup (all agents)

## Offline-First Policy

Prefer offline/local resources (WordNet, Wiktionary dumps, Roget's, style guides) to avoid rate limits and work air-gapped. Use metered APIs (Merriam-Webster, Collins, Oxford) only when offline resources are insufficient, with caching and quota guards.
