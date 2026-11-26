---
description: Translate text or a file between English and Arabic with the portable, key-free seven-stage workflow.
argument-hint: <text-or-file-path> [--target en|ar] [--book]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# /translate

You are running the **portable, key-free EN↔AR translation workflow**. You (the host coding agent) are the translator: do not call an external provider and do not request a credential — none is needed.

## Arguments

`$ARGUMENTS` — a literal string or a file path, optionally `--target en|ar` and `--book`. Default target: Arabic (MSA).

## Procedure

1. Resolve the input: if `$ARGUMENTS` names an existing file, read it; otherwise treat the arguments as literal text. Determine `target_language` (`ar` unless `--target en` is given).
2. Load `config/translator.yaml`, `docs/style-guide.md`, `data/glossary.tbx`, and for `--book` also `data/characters.json` and `data/places.json`.
3. Build the translation brief (the `analysis`, `glossary_terms`, `placeholder_map`, `agent_prompts`, `style_profile` contract in `docs/translation-brief-template.md`). Use `src/pipeline.py::TranslationPipeline.build_brief(...)` if Python is available; otherwise assemble the same five fields yourself.
4. Run the seven stage prompts in order, passing each stage's JSON to the next: `agents/analysis_agent.md` → `agents/translator_agent.md` → `agents/posteditor_agent.md` → `agents/reviewer_agent.md` → `agents/editor_agent.md` → `agents/judge_agent.md` → (only for `--book`) `agents/consistency_agent.md`.
5. Apply the gate: weighted MQM score must be **≥ 85** (dimensions 30/25/20/15/10), with **at most 3 iterations**. If it cannot pass, report the score and unresolved issues honestly — never emit a fake translation.
6. Validate with `src/pipeline.py::TranslationPipeline.validate(host_translation, brief)`. A missing or altered placeholder fails validation.
7. Write the approved Markdown master (RTL-aware, glossary-consistent, diacritics per style profile). For books, optionally export via `scripts/translate_book.py`.

## Output

Report the final target-language text (or the output file path), the Judge score, the iteration count, and any glossary/style notes. Keep placeholders, code and tags byte-for-byte.
