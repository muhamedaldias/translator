# Research Report: Translation Agents & Skills (English ↔ Arabic)

## 1. AI/LLM Multi-Agent Translation Systems

### Architecture patterns

- **Prompt chaining (Translate → Postedit → Proofread)**: IR_Multi-agentMT (WMT25) uses sequential agents each refining output; RUBRIC-MQM for error annotation. (arXiv 2504.12891, WMT25)
- **Role-specialized pipelines**: AIDAterm (ACL Industry 2026) — Analysis → Translation → Post-editing → Review, with glossary injection at every stage and a reasoning-enabled Review agent. Achieved highest ChrF2++×Accuracy on WMT25 Terminology (en→de/es/ru). (aclanthology.org/2026.acl-industry.63.pdf)
- **AIDA Agents** (EAMT 2026): translation/rating/post-editing/re-rating with optional RAG (translation memories, terminology, style guides). Outperforms all on 10/11 WMT24++ pairs. (aclanthology.org/2026.eamt-2.4)
- **TransAgents** (TACL 2025): multi-agent "virtual company" for ultra-long literary texts — preparation/translation/localization/proofreading; glossary Addition/Subtraction agents. Uses GPT-4-turbo. (direct.mit.edu/tacl/.../132121)
- **MeGuMa** (WMT25): parallel generators (Gemma 3, Qwen 3, EuroLLM) + metric-guided selection. (aclanthology)
- **Four-agent legal MT** (Briva-Iglesias, MTSummit 2025): Translator, Adequacy Reviewer, Fluency Reviewer, Editor. (arXiv 2504.12891)
- **MAS-LitEval** (arXiv 2506.14199): evaluation agents for terminology/narrative/style.

### Coordination findings

- Sequential pipelines outperform parallel-generation+selection for terminology consistency.
- Computational capacity (model size) is critical.
- Higher initial translation quality leads to better final outcomes.

## 2. Translation Skills in Coding Agents

- **SKILL.md open standard** adopted across Claude Code, Cursor, Codex, Gemini CLI, OpenCode. Skills live in `.claude/skills/`, `.agents/skills/`. (localhero.ai blog 2026-05-18)
- **translate-book** (github.com/deusyu/translate-book, 2.1k★): parallel subagents, manifest-driven integrity checks, resumable, PDF/DOCX/EPUB/MD. Installs via `npx skills add`.
- **translating-products-skill** (BrunoMiguens): orchestrator + language/writing-system/surface/platform/review specialists.
- **i18nstack** (i18nagent.ai): 46 native-quality translation skills for Claude Code; locale-chain fallback libs.
- **Localhero agent-skill**: fetches glossary + tone/style from project at write time; CI integration to avoid duplicate translations.
- **i18next-localization skill**: `npx skills add i18next/i18next-cli`; Locize MCP server for glossary/style/TM.
- **translate-content** (pjt222/agent-almanac): preserves code blocks, IDs, file structure.

### Prompt patterns

- Put project-wide rules in CLAUDE.md/AGENTS.md; translation procedures in skill (lazy-loaded).
- Inject glossary before drafting; enforce "do not translate code blocks".

## 3. Arabic-Specific Challenges

### Morphology

- **Root-and-pattern morphology**: triliteral roots (KTB = writing) + patterns (fa'il, maf'ul) derive forms; broken plurals; rich inflection. (MDPI 2025 review; Habash AMTA 2012)
- Arabic has 6 plural forms (zero/one/two/few/many/other) per CLDR.

### Register & dialect

- **MSA vs dialects**: 25+ dialects; MSA has dual/case/mood; dialects have cliticization/circumfix negation; no standard orthography; Gulf closest, Egyptian farthest. MT trained on MSA fails on dialects. (ACL dialect papers; MADAR corpus)
- Agent must detect/register-route: MSA target vs dialect target.

### Agreement & grammar

- **Gender agreement**: verb-subject and noun-adjective agreement in number/gender/definiteness; broken plurals agree in gender+definiteness only.
- **Diacritics**: optional in writing; omission increases ambiguity; tokenizers (AraNizer, SentencePiece) must handle ligatures.

### Named entities & orthography

- **Named entities**: transliteration vs translation; diacritic ambiguity (omitted short vowels) causes ambiguity.
- **Orthography normalization**: alef/ya/ta-marbuta variants.
- **RTL text**: bidirectional rendering issues in UI/code; Arabic reshaper/bidi libraries needed (python-bidi, arabic_reshaper).

## 4. Open-Source Frameworks/Tools

- **Argos Translate** (argosopentech, PyPI `argostranslate` 1.11.0, MIT, Feb 2026): offline NMT via OpenNMT/CTranslate2; supports Arabic; pivot translation; LibreTranslate API on top.
- **TURJUMAN** (ACL OSACT 2022): Python toolkit, AraT5 fine-tuned, 20 langs→Arabic.
- **Helsinki-NLP/opus-mt-en-ar, opus-mt-ar-en** (MarianMT): widely used baselines.
- **CAMeL Tools** (Habash): Arabic NLP toolkit.
- **MarianMT fine-tuning repos**: MarEzzat, SultanArfeen (ATHAR dataset), muhammed1k, mohamed22311 (ARABISH, OPUS ccmatrix 59M pairs).
- **Strifee/arabic2english**: from-scratch Transformer.
- **AdamHuub/arabic-english-translation-LLM**: Gemini API + prompt engineering + BLEU eval.
- **ai-l10n** (npm): 165 langs incl. Arabic, plural forms, glossary, MCP server for agents.
- **transmart** (npm): ChatGPT-based i18n.
- **i18n-agent / i18nstack**: Claude Code toolkit.

## 5. Evaluation Metrics for Arabic

- **BLEU** (Papineni 2002): too strict for morphologically rich Arabic; AL-BLEU (Bouamor et al., EMNLP 2014) adapts via morphological/syntactic/lexical matching; highest correlation with human judgments on Arabic corpus. (aclanthology.org/D14-1026.pdf)
- **chrF**: character n-gram F-score; best string-based metric; robust for Arabic morphology.
- **COMET / COMET-MQM / COMET-DA**: neural, highest correlation with human judgments generally; COMET-MQM trained on MQM. (WMT metrics tasks)
- **MQM** (Multidimensional Quality Metrics): expert error annotation ontology; WMT standard.
- **Direct Assessment (DA)**: 0–100 scalar.
- **TER**: edit distance; weak.
- **chrF2++ × Accuracy** (Proper mode): WMT Terminology official ranking.
- **TSR** (Term Success Rate) for terminology.
- **Human eval**: Monolingual Human Preference (MHP), Bilingual LLM-based (TransAgents).
- **Recommendation**: use COMET-MQM + chrF + AL-BLEU together; BLEU alone underestimates Arabic quality.

## 6. Tool-Use Patterns / File-Based Workflows

- Skill loads lazily; agent queries glossary before drafting; runs `npx ... translate --changed-only` locally or delegates to CI.
- File-based: source locale JSON/YAML/PO/XLIFF/ARB; preserve placeholders, plural suffixes, RTL markers.
- Chunking for long docs: split into segments, translate via parallel subagents, manifest integrity checks, merge.
- Pre-processing: normalize Arabic text, remove/keep diacritics, handle bidi; chunk by sentence (Stanza).
- Post-processing: validate placeholders, RTL embedding, glossary compliance check.

## 7. Glossary/Terminology Management

- **TBX** (ISO 30042) and **UTX** (AAMT tab-delimited) exchange formats.
- **Translation Memory (TM)**: segment reuse; **TMS** centralizes files/terminology/TM/automation.
- Enforcement: inject glossary into prompt at every stage (AIDAterm); post-hoc consistency check; term success rate metric.
- Governance: SME curation, versioning, corpus-wide consistency checks to discover unlisted terms.
- Morphological variations must be accounted for (inflected forms).
- For Arabic: include MSA vs dialect target, gender forms, plural forms of terms.

## Concrete Recommendations for Building Multi-Agent EN↔AR System

1. **Pipeline**: Analysis Agent (detect dialect/MSA, domain, entities, gender context) → Translator Agent (LLM with glossary injection, RTL-aware) → Post-editor Agent (gender/plural agreement, morphology) → Review Agent (reasoning-enabled, MQM error listing) → Selection by COMET-MQM + chrF + AL-BLEU.
2. **Arabic handling**: normalize input; decide MSA vs dialect target; preserve diacritics policy; use python-bidi/arabic_reshaper for display; handle 6 plural forms; gender-aware prompts.
3. **Glossary**: TBX/UTX store; inject at every stage; consistency checker; morphological variant list.
4. **Evaluation**: COMET-MQM (primary), chrF (secondary), AL-BLEU, terminology accuracy/TSR, MQM human eval.
5. **Agent skills**: implement as SKILL.md for Claude Code/Codex/OpenCode; lazy-load; fetch glossary from TMS at write time; delegate bulk translation to CI; never translate code blocks/placeholders.
6. **Models**: prefer large LLMs (GPT-4/Claude) for Arabic; fine-tune MarianMT/AraT5 for domain; use NLLB for low-resource dialects.
7. **RAG**: inject translation memories + style guides at Analysis and Translation stages (AIDAterm production finding).

## Key Citations

- Briva-Iglesias 2025, arXiv 2504.12891
- AIDAterm, ACL Industry 2026, aclanthology.org/2026.acl-industry.63.pdf
- AIDA Agents, EAMT 2026, aclanthology.org/2026.eamt-2.4
- TransAgents, TACL 2025
- IR_Multi-agentMT, WMT25, aclanthology.org/2025.wmt-1.32.pdf
- IRB-MT WMT25 Terminology, aclanthology.org/2025.wmt-1.110.pdf
- AL-BLEU, EMNLP 2014, aclanthology.org/D14-1026.pdf
- TURJUMAN, OSACT 2022, aclanthology.org/2022.osact-1.1.pdf
- Habash AMTA 2012 tutorial
- MDPI Arabic NLP review 2025, mdpi.com/2073-431X/14/11/497
- Argos Translate, github.com/argosopentech/argos-translate, PyPI 1.11.0
- translate-book, github.com/deusyu/translate-book
- localhero.ai agent-skill blog 2026-05-18
