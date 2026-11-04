# Multi-Agent Translation System — Implementation Plan

**Project:** `/data/workspace/projects/translator`  
**Scope:** English ↔ Arabic (EN-AR / AR-EN) multi-agent translation system  
**Target users:** Coding agents (Claude Code, Codex, OpenCode, OpenHands, Aider, etc.)  
**Use cases:** Code/UI localization, books (fiction & non-fiction), technical docs  
**Prepared:** 2026-11-04  
**Status:** Ready for implementation

---

## 1. Executive Summary

This plan defines a professional, multi-agent translation system built from agents and precise, high-quality skills. The system:

- Operates as a role-specialized pipeline (Analysis → Translate → Post-edit → Review → Judge)
- Integrates dictionary, glossary, terminology, and style-guide skills
- Handles Arabic-specific challenges (root morphology, MSA vs dialect, gender agreement, RTL, 6 plural forms)
- Translates books with chapter-level consistency (character registry, dynamic glossary, cross-chapter coherence)
- Is portable to any coding agent via the SKILL.md standard
- Is evaluated with COMET-MQM (primary), chrF, AL-BLEU, and MQM human evaluation

Research inputs: `research/translation_agents_skills.md`, `research/dictionaries_references.md`, `research/papers_articles.md`.

---

## 2. System Architecture

### 2.1 High-Level Pipeline (Sequential, Quality-Gated)

```
Source Text
    │
    ▼
┌─────────────────┐
│ 1. Analysis     │ ← Detect register (MSA/dialect), domain, entities,
│    Agent        │    gender context, Arabic orthography normalization
└─────────────────┘
    │ glossary + style context
    ▼
┌─────────────────┐
│ 2. Translator   │ ← Draft translation (LLM, glossary injected,
│    Agent        │    RTL-aware, code-blocks preserved)
└─────────────────┘
    │ draft
    ▼
┌─────────────────┐
│ 3. Post-editor  │ ← Gender/plural agreement, morphology,
│    Agent        │    diacritics policy, named-entity handling
└─────────────────┘
    │ revised draft
    ▼
┌─────────────────┐
│ 4. Reviewer     │ ← MQM-style error critique (accuracy, fluency,
│    Agent        │    style, terminology, coherence)
└─────────────────┘
    │ critique + severity
    ▼
┌─────────────────┐
│ 5. LLM Judge    │ ← Quality gate (0–100 rubric); approves or
│    Agent        │    routes back to Editor (max 3 iterations)
└─────────────────┘
    │ approved translation
    ▼
Consistent, evaluated EN ↔ Arabic output
```

### 2.2 Design Principles (from research)

- **Sequential pipelines outperform parallel-generation+selection** for terminology consistency (WMT25, AIDAterm).
- **Glossary injected at every stage** improves term success rate (AIDAterm production finding).
- **2–3 iterations** yield optimal results before diminishing returns (Wu et al. 2024; Feng et al. 2024).
- **Role specialization** significantly outperforms generic "revise" instructions.
- **Higher initial translation quality leads to better final outcomes** — invest in the Translator Agent prompt.

---

## 3. Agent Specifications

Each agent is a portable prompt/skill block usable in Claude Code, Codex, OpenCode, etc.

### 3.1 Analysis Agent

**Purpose:** Pre-process source text, extract context for downstream agents.

**Inputs:** Source text (EN or AR), target language, domain hint (optional), existing glossary/TBX.

**Outputs:** Structured analysis JSON:
- `register`: MSA | dialect | mixed
- `domain`: technical | literary | legal | medical | UI | general
- `entities`: [{text, type: person|place|org|other, transliterate|translate}]
- `gender_context`: detected gender of subjects (for AR agreement)
- `orthography_norm`: normalized Arabic (alef/ya/ta-marbuta variants)
- `difficult_terms`: terms requiring dictionary lookup
- `code_blocks`: spans to preserve unchanged

**Skills used:** `en_lexicon`, `en_ar_bilingual`, `ner`, `style_reference`.

### 3.2 Translator Agent

**Purpose:** Produce initial draft translation.

**Inputs:** Source text, analysis output, glossary injection, style guide, previous chapter context (for books).

**Outputs:** Draft translation + confidence flags for ambiguous terms.

**Key constraints (from research):**
- Never translate code blocks, placeholders, XML/HTML tags, IDs.
- Preserve formatting (RTL markers, paragraph structure).
- Inject glossary at every stage.
- Use MSA by default for written Arabic unless dialect is explicitly requested.
- Handle 6 Arabic plural forms (zero/one/two/few/many/other).

### 3.3 Post-Editor Agent

**Purpose:** Arabic-specific grammatical and morphological correction.

**Outputs:** Revised draft + list of corrections made.

**Focus areas (from research):**
- Gender agreement (verb-subject, noun-adjective, definiteness)
- Broken plural agreement (gender + definiteness only)
- Diacritics policy (retain/remove per project config)
- Named entity consistency (transliteration vs translation)
- Orthography normalization

### 3.4 Reviewer Agent

**Purpose:** MQM-style structured critique.

**Outputs:** Critique with error spans, categories, severity (critical/major/minor), and suggested fixes.

**Evaluation dimensions:** Accuracy, fluency, style/register, terminology, coherence.

### 3.5 Editor Agent

**Purpose:** Apply reviewer feedback to produce revised draft.

**Inputs:** Draft + reviewer critique.

**Outputs:** Revised translation.

### 3.6 LLM Judge Agent

**Purpose:** Quality gate; approve or request revision.

**Outputs:** Score (0–100), pass/fail decision, rationale.

**Rubric (MQM-inspired):** Accuracy (30%), Fluency (25%), Style/Register (20%), Terminology (15%), Coherence (10%).

**Threshold:** ≥ 85 = approve; 70–84 = one revision; < 70 = full re-translation (max 3 total iterations).

### 3.7 Consistency Agent (books only)

**Purpose:** Cross-chapter coherence for book translation.

**Maintains:** Character registry (names, aliases, pronouns, titles), place/world-building glossary, dynamic term base updated per chapter.

---

## 4. Skills / Dictionary Integration Layer

Skills follow the SKILL.md standard (adopted across Claude Code, Codex, OpenCode, Gemini CLI). Each skill is a lazy-loadable tool module.

### 4.1 Phase 1 — Offline, Zero-Cost (immediate)

| Skill | Resource | Role | Access |
|-------|----------|------|--------|
| `en_lexicon` | Open English Wordnet 2025 (JSON/LMF) | Synonyms, hypernyms, glosses, WSD | Local, no network |
| `en_ar_bilingual` | Wiktionary EN + AR dumps | EN-AR headword pairs, etymology | Local dump |
| `synonym_expansion` | Roget's Thesaurus 1911 (Gutenberg 10681) | Concept-based synonym expansion | Local parse |
| `style_reference` | UNESCO Style Manual 2004 + AUSIT Arabic + Mozilla Arabic | Style rules, Arabic transliteration | Ingested into knowledge base |
| `datamuse_synonyms` | Datamuse API (`api.datamuse.com`) | Lightweight synonyms, no key | Network, free |

### 4.2 Phase 2 — Metered APIs (with caching + quota guards)

| Skill | Resource | Role | Limit |
|-------|----------|------|-------|
| `merriam_webster` | Merriam-Webster Collegiate API | Authoritative EN definitions/audio | 1,000 q/day/key (free) |
| `collins` | Collins Dictionary API | Bilingual coverage | 5,000 calls/mo (free) |
| `oxford` | Oxford Dictionaries API | Current-usage EN definitions | Paid; verify AI-use ToS |

### 4.3 Phase 3 — Parallel Corpora (MT fine-tuning / context examples)

| Skill | Resource | Role |
|-------|----------|------|
| `un_pc` | Helsinki-NLP/un_pc (ar-en, 20M units) | Formal register examples |
| `opensubtitles` | OpenSubtitles ar-en | Colloquial/dialogue register |
| `ted2020` / `mtedx` | TED/TEDx ar-en | Spoken register |

### 4.4 Skill Integration Pattern

```python
# Each skill exposes structured tool calls:
lookup_definition(word, dictionary="merriam_webster")
lookup_synonyms(word, source="wordnet|datamuse|roget")
lookup_en_ar(term, direction="en-ar|ar-en")
lookup_style_guide(lang="ar", topic="transliteration|gender|plural")
query_glossary(term, domain, tmx_path)
```

**Caching:** Cache dictionary lookups, termbase queries, TM matches to respect quotas (MW 1000/day; Collins/Oxford metered).

---

## 5. Arabic-Specific Handling

### 5.1 Register Detection & Routing
- Default target: Modern Standard Arabic (MSA) for written text.
- Dialect target only when explicitly requested (Egyptian, Gulf, Levantine, etc.).
- MSA has dual/case/mood; dialects have cliticization/circumfix negation — agent prompts must be register-aware.

### 5.2 Morphology & Agreement
- Root-and-pattern morphology (triliteral roots + patterns).
- 6 plural forms (zero/one/two/few/many/other) per CLDR.
- Gender agreement: verb-subject, noun-adjective, definiteness.
- Broken plurals agree in gender + definiteness only.

### 5.3 Orthography & Diacritics
- Normalize alef/ya/ta-marbuta variants.
- Diacritics (tashkīl) optional; project config sets retain/remove policy.
- Tokenizers (Stanza, AraNizer) must handle Arabic ligatures.

### 5.4 Named Entities
- Transliterate vs translate decision per entity type and project glossary.
- Diacritic ambiguity (omitted short vowels) — resolve via context.

### 5.5 RTL & Formatting
- Use `python-bidi` / `arabic_reshaper` for display/RTL rendering.
- Preserve code blocks, placeholders, XML/HTML tags unchanged.
- Preserve paragraph structure and RTL markers.

---

## 6. Book Translation Workflow

Books require cross-chapter consistency beyond single-text translation.

### 6.1 Per-Chapter Pipeline
1. Load previous chapter context (summary, character registry, dynamic glossary).
2. Translate chapter through the 5-agent pipeline + Consistency Agent.
3. Update character registry and dynamic glossary from new chapter.
4. Save manifest with integrity checks (resumable).

### 6.2 Consistency Artifacts
- `glossary.tbx` / `glossary.utx` — term base (ISO 30042 / AAMT).
- `characters.json` — character names, aliases, pronouns, titles, Arabic renderings.
- `places.json` — place/world-building terms.
- `manifest.json` — chapter checksums, translation status, resume points.

### 6.3 Supported Formats
PDF, DOCX, EPUB, Markdown, plain text (per `translate-book` research).

---

## 7. Coding Agent Compatibility

### 7.1 SKILL.md Standard
Package the system as a skill installable via `npx skills add <name>` or manual drop into:
- `.claude/skills/` (Claude Code)
- `.agents/skills/` (Codex, OpenCode, etc.)

Each skill directory contains:
```
skill-name/
├── SKILL.md          # skill definition, tools, triggers
├── prompt.md         # agent system prompt
├── tools/            # skill tool implementations
└── data/             # embedded glossaries, style guides
```

### 7.2 Invocation Pattern
- Lazy-load: skill loads only when translation is requested.
- Agent queries glossary before drafting.
- Runs locally (`--changed-only`) or delegates bulk work to CI.
- Project-wide rules in `CLAUDE.md` / `AGENTS.md`; translation procedures in the skill.

---

## 8. Evaluation Framework

### 8.1 Automatic Metrics (primary → secondary)

| Metric | Role | Why |
|--------|------|-----|
| COMET-MQM | Primary | Highest correlation with human judgments; MQM-trained |
| chrF | Secondary | Robust for Arabic morphology (character n-gram F-score) |
| AL-BLEU | Arabic-specific | Morphologically-aware BLEU; highest correlation on Arabic corpus |
| TSR (Term Success Rate) | Terminology | Glossary adherence measurement |

BLEU alone is rejected — it underestimates Arabic quality.

### 8.2 Human Evaluation
- MQM (Multidimensional Quality Metrics) expert error annotation.
- Direct Assessment (DA): 0–100 scalar.
- Monolingual Human Preference (MHP).

### 8.3 Quality Gate
- LLM Judge (0–100 MQM-inspired rubric) with threshold ≥ 85.
- Max 3 iterations per segment.

---

## 9. Project File Structure

```
/data/workspace/projects/translator/
├── README.md
├── AGENTS.md                  # Project-wide rules for coding agents
├── CLAUDE.md                  # Claude Code specific rules
├── plan.md                    # This implementation plan
├── research/
│   ├── translation_agents_skills.md
│   ├── dictionaries_references.md
│   └── papers_articles.md
├── skills/                    # SKILL.md skills for coding agents
│   ├── translator-skill/
│   │   ├── SKILL.md
│   │   ├── prompt.md
│   │   ├── tools/
│   │   │   ├── analysis.py
│   │   │   ├── translate.py
│   │   │   ├── postedit.py
│   │   │   ├── review.py
│   │   │   ├── judge.py
│   │   │   └── consistency.py
│   │   └── data/
│   │       ├── glossary.tbx
│   │       ├── style_guides/
│   │       └── wordnet/
│   └── reference-skills/
│       ├── en_lexicon/
│       ├── en_ar_bilingual/
│       ├── synonym_expansion/
│       └── style_reference/
├── agents/                    # Agent prompt definitions
│   ├── analysis_agent.md
│   ├── translator_agent.md
│   ├── posteditor_agent.md
│   ├── reviewer_agent.md
│   ├── editor_agent.md
│   ├── judge_agent.md
│   └── consistency_agent.md
├── src/                       # Core implementation (Python/Node)
│   ├── pipeline.py            # Orchestrates the agent graph
│   ├── evaluation.py          # COMET-MQM, chrF, AL-BLEU
│   ├── arabic.py              # Arabic-specific NLP (morphology, RTL, plurals)
│   ├── glossary.py            # TBX/UTX term base
│   └── book.py                # Book workflow (chapters, manifest, registry)
├── data/
│   ├── glossary.tbx
│   ├── characters.json
│   ├── places.json
│   └── parallel_corpus/       # UNPC, OpenSubtitles, TED (downloaded)
├── tests/                     # Unit + integration tests
│   ├── test_arabic_morphology.py
│   ├── test_pipeline.py
│   └── test_evaluation.py
├── config/
│   └── translator.yaml        # diacritics policy, register default, thresholds
├── scripts/
│   ├── install_skill.sh       # Install skill into coding agents
│   └── translate_book.py      # CLI for book translation
└── outputs/                   # Translated output (gitignored)
```

---

## 10. Implementation Roadmap (Phased)

### Phase 1 — Foundation (Weeks 1–2)
- [ ] Scaffold project structure (`skills/`, `agents/`, `src/`, `config/`, `tests/`)
- [ ] Implement core pipeline orchestrator (LangGraph/CrewAI or custom graph)
- [ ] Implement 5 base agents (Analysis, Translator, Post-editor, Reviewer, Judge)
- [ ] Integrate Phase 1 skills (Wordnet, Wiktionary, Roget's, Datamuse, style guides)
- [ ] Implement Arabic handling (orthography normalization, MSA default, plural forms)
- [ ] Unit tests for Arabic morphology and pipeline

### Phase 2 — Arabic Refinement & Evaluation (Weeks 3–4)
- [ ] Gender agreement and broken plural correction (Post-editor)
- [ ] Named entity handling (transliterate vs translate)
- [ ] RTL preservation and code-block protection
- [ ] Evaluation framework: COMET-MQM, chrF, AL-BLEU integration
- [ ] LLM Judge quality gate with 0–100 rubric
- [ ] Benchmark on EN-AR test sets

### Phase 3 — Coding Agent Skills (Weeks 5–6)
- [ ] Package as SKILL.md skills (`.claude/skills/`, `.agents/skills/`)
- [ ] Lazy-load pattern; glossary pre-fetch; CI delegation
- [ ] `npx skills add` install script
- [ ] Test in Claude Code, Codex, OpenCode
- [ ] AGENTS.md / CLAUDE.md templates for consumer projects

### Phase 4 — Book Translation (Weeks 7–8)
- [ ] Consistency Agent (character registry, dynamic glossary, cross-chapter)
- [ ] Chapter-by-chapter pipeline with manifest integrity checks
- [ ] Resumable translation (checkpoint per chapter)
- [ ] Format support: PDF, DOCX, EPUB, Markdown
- [ ] End-to-end book translation test

### Phase 5 — Metered APIs & Optimization (Weeks 9–10)
- [ ] Merriam-Webster, Collins, Oxford API skills (with caching + quota guards)
- [ ] Parallel corpus integration (UNPC, OpenSubtitles, TED) for fine-tuning examples
- [ ] Model selection per agent (cheaper for draft/QA, stronger for review/judge)
- [ ] Cost/latency optimization, early termination, caching
- [ ] Final benchmark and human MQM evaluation

---

## 11. Quality Assurance & Risks

### 11.1 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Arabic morphology errors | Post-editor Agent + AL-BLEU + chrF; human MQM spot checks |
| Terminology inconsistency | Glossary injected at every stage; TSR metric; consistency checker |
| Dialect vs MSA confusion | Analysis Agent register detection; explicit config |
| Code block corruption | Preserve placeholders/tags; QA checker validates |
| API quota exhaustion | Caching, quota guards, offline-first skills |
| Over-editing (diminishing returns) | Max 3 iterations; quality-gated early termination |

### 11.2 Definition of Done
- Pipeline produces EN↔AR translations scoring ≥ 85 on LLM Judge rubric
- COMET-MQM + chrF + AL-BLEU all meet project thresholds
- Glossary adherence (TSR) ≥ 95%
- Skill installs and runs in Claude Code, Codex, OpenCode
- Book translation maintains character/place consistency across 5+ chapters
- All unit + integration tests pass

---

## 12. Next Steps (Immediate)

1. Confirm this plan is approved for implementation.
2. (Optional) Choose primary LLM provider/models for each agent.
3. Begin Phase 1 scaffolding in `/data/workspace/projects/translator`.

All research is complete and saved under `research/`. The system is ready to be implemented per this plan.
