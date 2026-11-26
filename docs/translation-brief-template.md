# Translation Brief Template

The brief is the single context object passed between stages. It is produced by `src/pipeline.py::TranslationPipeline.build_brief(source_text, domain_hint=None, previous_context=None) -> dict` and consumed by all seven `agents/*.md`. Copy this template when constructing a brief by hand; do not invent new top-level keys.

```json
{
  "analysis": {
    "register": "MSA",
    "domain": "general",
    "audience": "general reader",
    "document_structure": "article",
    "entities": [
      {"text": "UN", "type": "org", "action": "translate"},
      {"text": "New York", "type": "place", "action": "transliterate"}
    ],
    "gender_context": {"subject_gender": "neutral", "object_gender": "neutral"},
    "orthography_norm": null,
    "difficult_terms": ["headquarters"],
    "code_blocks": ["{{placeholder}}", "<b>", "`code`"],
    "word_count": 13,
    "sentence_count": 1,
    "has_rtl": false,
    "needs_diacritics": false
  },
  "glossary_terms": [
    {"en": "API", "ar": "واجهة برمجة التطبيقات", "domain": "technical"}
  ],
  "placeholder_map": {
    "{{name}}": "{{name}}",
    "{id}": "{id}",
    "%s": "%s"
  },
  "agent_prompts": [
    "agents/analysis_agent.md",
    "agents/translator_agent.md",
    "agents/posteditor_agent.md",
    "agents/reviewer_agent.md",
    "agents/editor_agent.md",
    "agents/judge_agent.md",
    "agents/consistency_agent.md"
  ],
  "style_profile": {
    "target_language": "ar",
    "register": "MSA",
    "diacritics_policy": "automatic",
    "quotation_marks": "guillemets",
    "digit_style": "ascii",
    "previous_context": null
  }
}
```

## Field contracts

| Field | Meaning | Produced by |
|-------|---------|-------------|
| `analysis` | Context, entities, gender, formatting constraints | `TranslationPipeline.analyze` / stage 1 |
| `glossary_terms` | Approved source→target pairs injected at every stage | `data/glossary.tbx` via `src/glossary.py` |
| `placeholder_map` | Every protected span → its verbatim rendering; must survive translation unchanged | `src/pipeline.py` |
| `agent_prompts` | The seven stage prompt files, in order | This repository |
| `style_profile` | Register, diacritics policy, quotation/digit style, previous chapter context | `config/translator.yaml` + brief |

## Validation contract

`TranslationPipeline.validate(host_translation, brief) -> dict` returns:

```json
{"passed": true, "issues": [], "score": 0}
```

- `passed` is `true` only when every `placeholder_map` entry appears verbatim the same number of times and the MQM gate is met.
- `issues` is a list of named errors (e.g. `missing_placeholder`, `altered_code_block`, `unapproved_term`). A missing placeholder is a failure, never a silent pass.
- `score` is the Judge's weighted 0–100 MQM total (dimensions 30/25/20/15/10, approval threshold 85, max 3 iterations).

## Rules for every stage

- The host coding agent is the translator; no external provider or credential is used.
- MSA default; glossary injected at every stage; RTL logical order; diacritics per `style_profile`.
- Non-translatable spans from `placeholder_map` are copied byte-for-byte.
- See `docs/style-guide.md` for typography and formatting details.
