# Portable Translation Skill Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** rebuild the repository as a key-free, portable EN↔AR agent/skill pack with a deterministic Python support layer, professional outputs, CI, and a protected `main`.

**Architecture:** the canonical pack (`skills/`, `agents/`, `docs/`) is host-agnostic; thin adapters and an installer map it into Claude Code, Codex/OpenCode, Hermes or a generic agent. Python never calls an LLM: it prepares a context-rich translation brief and validates host-produced output. Translation quality comes from the seven role-specialized prompts and an explicit MQM gate.

**Tech Stack:** Python 3.10+ (stdlib, PyYAML, pytest; optional ebooklib/python-docx/bs4/pypdf), Markdown SKILL.md standard, GitHub Actions, `gh` CLI.

**Spec:** `docs/superpowers/specs/2026-11-26-portable-translation-skill-pack-design.md`

## Global Constraints

- No API key, provider SDK call or network request in the default translation path.
- No absolute stale path `/data/workspace/projects/translator` anywhere.
- Every `SKILL.md` and `agents/*.md` begins with YAML frontmatter containing `name` and `description`.
- No silent fake translation: absence of a host translation must be explicit.
- Tests must pass offline with `pytest tests/ -v`; no test may require a model download.

## Review Focus

- Empty/whitespace source → `analyze()` returns zero counts, no exception, brief still generated.
- Source containing `{{term}}`, backticks, XML tags and `{"id": 7}` → placeholder map preserves all verbatim through brief and validation.
- Host translation with a missing placeholder → validation fails with a named error, never silently passes.
- TBX with XML namespace and multiple `<term>` per language section → all terms load; adherence computed only over relevant terms.
- `previous_context` supplied (chapter 2+) → no TypeError; book CLI completes without `JudgeResult` subscripting.
- Missing optional dependency (ebooklib/docx/bs4/pypdf) → import succeeds, CLI prints a clear actionable error, no crash at module load.
- Duplicate YAML key or malformed config → clear error or safe default, never silent swallow of all exceptions.

---

### Task A — Deterministic core + brief/validation pipeline

**Files:** Modify `src/arabic.py`, `src/evaluation.py`, `src/glossary.py`, `src/dictionary.py`, `src/pipeline.py`; Modify `tests/test_arabic_morphology.py`, `tests/test_evaluation.py`, `tests/test_pipeline.py`; Create `tests/test_glossary.py`, `tests/test_dictionary.py`.

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `TranslationPipeline.build_brief(source_text, domain_hint=None, previous_context=None) -> dict` with keys `analysis`, `glossary_terms`, `placeholder_map`, `agent_prompts`, `style_profile`; `TranslationPipeline.validate(host_translation, brief) -> dict` with `passed`, `issues`, `score`; `TranslationPipeline.analyze(...) -> AnalysisResult` with real entities/gender/code_blocks.

- [ ] **Step 1: Write failing tests** for: `build_brief` returns 7 prompts and preserves placeholders; `validate` rejects a missing placeholder; namespace TBX loads all terms; identical strings score BLEU 100; `post_edit` keeps orthography normalization after diacritic removal; `previous_context` does not raise.
- [ ] **Step 2: Run `pytest tests/test_pipeline.py tests/test_arabic_morphology.py tests/test_evaluation.py tests/test_glossary.py tests/test_dictionary.py -v` and confirm the new tests fail.**
- [ ] **Step 3: Implement the fixes** in the owned files; remove `_llm_complete` and every LLM import/call from `pipeline.py`; keep legacy CLI flags as no-op with a deprecation warning; make `run()` return `"translation": ""` and `"host_agent_required": True` when no translation is supplied.
- [ ] **Step 4: Run the owned test files and confirm all pass.**
- [ ] **Step 5: Commit** `fix: deterministic key-free core with brief and validation`.

### Task B — Book workflow, formats and CLI

**Files:** Modify `src/book.py`, `src/book_formats.py`, `scripts/translate_book.py`; Create `tests/test_book.py`, `tests/test_book_formats.py`.

**Interfaces:**
- Consumes: `TranslationPipeline.build_brief` and `validate` from Task A.
- Produces: `BookTranslator.prepare_chapter(...)`, `BookTranslator.assemble_chapter(chapter_id, host_translation)`, `BookTranslator.check_consistency()` returning real findings; CLI flags `--prepare`, `--assemble`, `--list-formats`.

- [ ] **Step 1: Write failing tests** for: two-chapter book with `previous_context` completes; `result["judge_score"]` exists on resume; consistency detects a renamed character; code blocks are detected in indented paragraphs; `--list-formats` works without `--input`.
- [ ] **Step 2: Run the owned tests and confirm failure.**
- [ ] **Step 3: Implement fixes**: no `JudgeResult` subscripting; relative `project_root`; real registry updates; optional imports guarded; EPUB spine preserved; PDF handler refuses to fake PDF output; `list_supported_formats()` implemented.
- [ ] **Step 4: Run owned tests and confirm pass.**
- [ ] **Step 5: Commit** `fix: book workflow and format handlers`.

### Task C — Portable skill pack, agent prompts and installer

**Files:** Rewrite `skills/translator-skill/SKILL.md`, `skills/reference-skills/SKILL.md`, all `agents/*.md`; Create `.claude-plugin/plugin.json`, `commands/translate.md`, `scripts/install.sh`, replace `scripts/install_skill.sh` with a compatibility shim, `docs/style-guide.md`, `docs/translation-brief-template.md`.

**Interfaces:**
- Consumes: the brief schema from Task A.
- Produces: loadable `name`/`description` frontmatter on every skill and agent; installer detects Claude Code / Codex / OpenCode / Hermes / generic.

- [ ] **Step 1: Write a validation test** (in `tests/test_pack_validation.py`, owned by Task D) asserting frontmatter and no stale paths.
- [ ] **Step 2: Confirm it fails.**
- [ ] **Step 3: Rewrite the pack**: seven agents with concrete inputs/outputs, MQM rubric, glossary injection, register/format rules; skills with triggers, workflow, and host-agent delegation; installer with `--help`, `--host`, `--dry-run`, no global side effects.
- [ ] **Step 4: Run the validation test and confirm pass.**
- [ ] **Step 5: Commit** `feat: portable key-free skill pack and installer`.

### Task D — Docs, domain model and ADRs

**Files:** Create `GLOSSARY.md`, `docs/adr/0001-portable-skill-pack-no-api-key.md`; Rewrite `README.md`, `AGENTS.md`, `CLAUDE.md`, `plan.md`.

**Interfaces:** Consumes the approved decisions in the spec. Produces user-facing documentation with no stale paths and no API-key instructions.

- [ ] **Step 1: Add `tests/test_docs_consistency.py`** asserting no `/data/workspace/projects/translator`, no `api_key` setup instruction in README, and presence of GLOSSARY + ADR.
- [ ] **Step 2: Confirm failure.**
- [ ] **Step 3: Write docs** with domain-modeling discipline: canonical terms in GLOSSARY.md, one ADR for the hard-to-reverse no-API-key decision.
- [ ] **Step 4: Confirm the test passes.**
- [ ] **Step 5: Commit** `docs: professional docs, glossary and ADR`.

### Task E — CI, config and pack validation script

**Files:** Create `.github/workflows/ci.yml`, `scripts/validate_pack.py`, `tests/test_pack_validation.py` (if not created in C); Modify `config/translator.yaml`, `requirements.txt`, `.gitignore`.

**Interfaces:** Consumes all tasks. Produces `python scripts/validate_pack.py` exit 0 on a valid pack; CI job `test` running pytest and validation.

- [ ] **Step 1: Write tests** for validator detecting missing frontmatter and stale paths.
- [ ] **Step 2: Confirm failure.**
- [ ] **Step 3: Implement** validator, CI workflow, de-duplicated config, pinned requirements with optional extras.
- [ ] **Step 4: Run `pytest tests/ -v` and `python scripts/validate_pack.py`; confirm both pass.**
- [ ] **Step 5: Commit** `ci: add tests, pack validation and clean config`.

### Task F — Push, verify CI, protect main

- [ ] **Step 1: Push all commits to `main`** under `muhamedaldias`.
- [ ] **Step 2: Wait for the CI run** and confirm it succeeds via `gh run list`/`gh run view`.
- [ ] **Step 3: Enable classic protection or ruleset on `main`**: required PR, required status checks, block force push, block deletion, no admin bypass.
- [ ] **Step 4: Verify** with `gh api repos/muhamedaldias/translator/branches/main/protection` and `gh api repos/muhamedaldias/translator/rulesets`.
- [ ] **Step 5: Report** the final state with real command output.
