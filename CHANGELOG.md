# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Finding IDs (F1–F20, N1–N14, S1–S15) refer to the ECC audit of 2026-11-19;
see [docs/audit-2026-11-19.md](docs/audit-2026-11-19.md) for the full report.

## [Unreleased]

### Added

- `LICENSE` file (MIT), matching the license the README already declared (F18, blocker B6).
- `requirements-dev.txt` with lower bounds for pytest, pytest-cov, ruff, mypy, bandit (F1, F19).
- `tests/test_regressions.py`: 58 regression tests encoding the confirmed defects; RED on the audited commit, GREEN after the fix sweep (F1–F18, F20, N1, N3, N6, N7, N11).
- `tests/test_hardening.py`: 49 hardening tests covering the LLM client layer via mocked OpenAI/Anthropic SDKs, glossary round-trips, evaluation edges, book consistency, and cache behavior (F11–F15, F17, N4, N5, N9, S7).
- `tests/conftest.py`: autouse fixture that closes every `TranslationPipeline` (including failed constructors), eliminating 16 leaked sqlite connections per run and test writes into tracked `data/` (F19, N9).
- Loud placeholder mode: `run()` results carry `mode` and `warnings`; the CLI prints warnings to stderr and exits 1 on pipeline error (F9, blocker B3).
- Real editor revision pass (`TranslationPipeline._revise`) applied between judge iterations in LLM mode (F8).
- Structured book translation: EPUB/DOCX/PDF inputs are parsed, translated segment-by-segment, and reconstructed via the format handlers (`BookTranslator._translate_structured`); previously dead integration code (N2, F15).
- Context-manager support and `close()` on `BookTranslator` and `TranslationPipeline`; atomic tmp+replace writes for registries, manifest, and glossary files (N9).
- `--project-root` option on both book CLIs; defaults are now repository-relative (F4, S12, blocker B2).
- `arabic.normalize_output` config flag: lossy alef/ya normalization of final output is opt-in, default false (F20).
- `ReviewResult.score_source` provenance field (`"llm"` vs `"fallback"`) so fabricated fallback scores are distinguishable from measured LLM scores (F7).
- Truncation detection: `finish_reason == "length"` is logged and surfaced as a `__truncated__` confidence flag (N5).
- Glossary hardening: 50 MB file-size cap and defusedxml-preferred XML parsing (S5).
- README: dependency-install section, placeholder-mode warning, and an honest "Current Limitations" section (F1, F9, F17).
- `.gitignore` entries for runtime state (`data/manifest.json`) and coverage artifacts (`.coverage`) (F19).

### Changed

- `requirements.txt`: removed `comet_ml` (wrong package — an experiment-tracking SDK); COMET-MQM is the optional `unbabel-comet` extra, documented inline; declared `requests` and `defusedxml`; documented optional extras (openai, anthropic, ebooklib, beautifulsoup4, python-docx, pypdf); moved pytest to dev requirements (F1, S13, blocker B4).
- Judge/review quality gate: the deterministic threshold is authoritative; validated LLM scores and rationale are preserved, but an LLM "approve" can never bypass the gate; LLM JSON is type-validated and scores clamped to 0–100 (F6, N3, S4).
- LLM failures now raise and surface as `approved=False` with an `error` and empty translation — never as glossary-substituted pseudo-text with fabricated scores (F7, F9).
- Config loading: an explicit `--config` path must exist and parse (raises otherwise); missing default config logs and falls back; config can no longer override an explicit `use_llm=False`; a non-null `llm.api_key` in the tracked YAML emits an insecurity warning (F7, N6, S3).
- Glossary: `save()` preserves the format implied by the extension (TBX/UTX/JSON) with atomic writes; TBX loading is namespace-agnostic (ISO 30042 ed-2 files load); `load()` resets terms (no reload duplicates); `check_adherence()` accepts `source_text` and scores only source-relevant terms; term matching is whole-word and case-insensitive (F12, N7).
- Placeholder-mode glossary substitution uses whole-word, case-insensitive regex replacement instead of case-sensitive `str.replace` (F12).
- Code-block protection: fenced ``` and ~~~ blocks are protected; indexed markers with collision-safe base and order-independent restoration; protection now applies on the LLM path, not only the placeholder path (F11, N4).
- Arabic plural forms follow CLDR modulo rules (`n % 100`), correct for n > 100 and negative counts (F10).
- Evaluation: chrF honors `word_order` (chrF+ word n-grams); BLEU weights renormalized over available orders on both the NLTK and fallback paths (identical short text now scores ~100); COMET model loaded once and cached, operational failures logged (F13, N10).
- Dictionary: resource dicts renamed private so they no longer shadow the public lookup methods; TTL honored in the memory cache layer; corrupt cache entries dropped with a warning; Datamuse failures are no longer negatively cached; Merriam-Webster URL path segment quoted (F2, F7, S6, S9).
- LLM clients: explicit timeouts and retries on all providers (OpenAI/Anthropic 60 s / 2 retries, local 120 s / 1); `urlsplit`-based host/port parsing with scheme-default ports; socket probe uses a context manager (F14, S7, S8, N9).
- Book formats: EPUB parsing extracts block-level elements so inline tags no longer fragment sentences; EPUB language follows `structure.language`; DOCX `para.style is None` guarded; `pypdf` preferred over deprecated `PyPDF2`; PDF reconstruction writes a `.txt` sibling instead of a fake `.pdf`, with a warning (F15, N8, S11).
- `TextHandler`: fenced/indented code detected before stripping; chapter counter off-by-one fixed (N8).
- Book registries: capitalized-word heuristic skips sentence-initial words and stopwords; `check_consistency()` implements alias-vs-canonical name checks instead of always returning `consistent=True` (F17).
- `post_edit`: final output is no longer lossy-normalized by default; diacritics correction position/slices computed from the draft, not the stripped text (F20, F5).
- CLIs: `--use-llm` is tri-state (absent = follow config); `--llm-api-key` help documents process-list exposure and prefers env vars (F9, N6, S2).
- `config/translator.yaml`: duplicate `book:` key removed (the surviving block keeps `output_dir`); `arabic.normalize_output` added (F16, F20).
- README and `scripts/install_skill.sh`: all hardcoded `/data/workspace/projects/translator` paths replaced with portable relative paths (F4, S12).
- Tooling cleanup across `src/` and `scripts/`: PEP 585/604 typing, `ClassVar` constants, unused-import removal, logged exception handlers, executable bits on shebang modules, `status`→`overall` rename in the book CLI — ruff 254 → 16 errors, mypy 22 → 0 errors across `src/` + `scripts/` (F19, N14).

### Deprecated

- `PyPDF2` as the PDF parsing dependency: `pypdf` is preferred; the `PyPDF2` import remains only as a fallback (F15, S13).
- `Glossary.check_adherence()` without `source_text` (legacy whole-glossary scoring); prefer source-scoped scoring (F12).

### Fixed

- Book CLI crashed 100% of the time: `result["judge"]["score"]` subscripted a `JudgeResult` dataclass; now `.score` at both sites (F3, blocker B1).
- Every multi-chapter book crashed at chapter 2: two-argument `list.append` in the translator prompt builder; now `list.extend` (N1).
- Resumed books raised `KeyError: 'judge_score'`: the resume path now returns `judge_score`, `approved`, and `iterations` (N11).
- `lookup_en_ar()` and `lookup_synonyms(source="roget"/"all")` raised `TypeError: 'dict' object is not callable` (instance attrs shadowed methods); attrs renamed `_wiktionary_data` / `_roget_data` (F2, blocker B5).
- Diacritics correction audit records had wrong position and empty `corrected` slices (scanned stripped text, which never contains diacritics); regression introduced by local commit `04d1b9c` (F5).
- Deterministic fallback unconditionally overwrote parsed LLM judge decisions and review recommendations (F6).
- `Glossary.save()` wrote JSON over `.tbx` paths, irreversibly corrupting term bases (F12).
- Namespaced TBX files (ISO 30042 ed-2) loaded 0 terms silently (F12).
- Glossary adherence scored against ALL terms: a perfect 1-term translation of a 10-term glossary scored 10% (F12).
- Glossary substitution corrupted words ("malfunction" → "malدالة") and missed case-insensitive detections ("The api works") (F12).
- Datamuse network failures were negatively cached for 7 days in persistent SQLite (F7).
- `LocalClient.is_available()` returned False for every portless URL (`int('')`), silently forcing placeholder mode (F14, S8).
- EPUB reconstruction interpolated translations unescaped — stored markup/script injection into output EPUBs, confirmed end-to-end without any LLM (F15, S1).
- `PDFHandler.reconstruct` wrote plain text to `.pdf` paths (corrupt "PDF" artifacts) (F15, S11).
- Hardcoded author-machine paths caused stray writes outside the repo (F4, S12, blocker B2).
- Placeholder mode silently emitted pseudo-translations with fabricated review scores; the README quickstart led straight there (F9, blocker B3).
- `requirements.txt` named `comet_ml` while the code imports `unbabel-comet`'s `comet` (F1, blocker B4).
- MIT license declared in README but no LICENSE file existed (F18, blocker B6).
- 16 leaked sqlite connections per test run (`ResourceWarning`); tests also wrote into tracked `data/` (F19, N9).
- Iteration loop re-reviewed identical text three times with no revision step (F8).
- Parseable-but-mistyped LLM JSON (string scores, string errors) crashed review/judge arithmetic (N3).
- Long completions truncated at `max_tokens` were reviewed and could be approved without any warning (N5).
- Config `llm.enabled: true` silently overrode an explicit `use_llm=False` (N6).
- `Glossary.load()` called twice doubled the term list (N7).
- `TextHandler` code-block branch was unreachable (strip before indent test) and chapter numbering was shifted by one (N8).
- DOCX parsing crashed on paragraphs with `style is None` (F15).
- EPUB parsing fragmented sentences at every inline tag via `get_text()` (F15).
- Dead code removed: nonsense `get_handler` expression in `reconstruct_book`, pass-loop in `list_supported_formats`, unused imports/variables (F17, N11).
- `bleu()`/`_simple_bleu` under-scored identical short text (50.0 instead of ~100) by dividing over absent n-gram orders (F13, N10).
- `chrf()` accepted `word_order` but ignored it (F13).
- `comet_mqm()` re-downloaded/reloaded the model on every call and returned None silently on any failure (F13).

### Security

- EPUB output is HTML-escaped (`html.escape`), eliminating the confirmed stored XSS/markup-injection sink (S1, HIGH; F15). Guarded by `test_epub_escapes_translation_markup`.
- Glossary XML parsing prefers `defusedxml` with a stdlib fallback, plus a 50 MB size cap; the three residual bandit XML findings (B314/B405/B406) are suppressed with documented `#nosec` justifications. Classic billion-laughs is blocked by expat ≥ 2.4; XXE file-read/SSRF verified not exploitable on Python 3.13/expat 2.9 (S5).
- API keys in the git-tracked config trigger an insecurity warning; the `--llm-api-key` CLI flag is documented as exposing keys in process listings — env vars preferred (S2, S3).
- The quality gate cannot be persuaded past the configured threshold by LLM output (prompt-injection hardening); reviewer scores are schema-validated and clamped (S4, F6, N3).
- Merriam-Webster lookup words are URL-quoted, closing path/query-parameter injection against the metered API (S6).
- Corrupt sqlite cache entries are dropped instead of crashing lookups (S9, partial — see audit report residuals).
- Explicit request timeouts and retries on all LLM providers (S7).
- Secret scan CLEAN: 60 text files, full git history, git config/remote, and the sqlite cache dump — zero hardcoded secrets (security review §2).
- Verified-safe controls retained: `yaml.safe_load`, fully parameterized SQL, no eval/exec/pickle/shell, no zip-slip in EPUB/DOCX handling, DOCX output escaped, HTTPS-only dictionary hosts (S15).