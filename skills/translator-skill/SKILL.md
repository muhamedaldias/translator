---
name: translator-skill
description: Portable, key-free EN↔AR translation workflow for any coding agent. Use when the user asks to translate English↔Arabic text, documents, books or UI strings, or invokes the /translate slash command.
---

# Translator Skill

A host-agnostic English ↔ Arabic translation workflow carried out entirely by the **host coding agent's own model**. It is portable across Claude Code, Codex, OpenCode, Hermes and generic agents, requires no API key, no provider account and no network call, and keeps Markdown as the master format.

## Triggers

- The user requests translation between English and Arabic.
- The user asks to translate a book, document, article, subtitle or code/UI strings.
- The user invokes `/translate` or asks to "use the translation workflow".
- A chapter, segment or term base needs quality-gating or consistency checking.

## Key-free operating rule

The host coding agent is the translator. Every stage below is a **prompt procedure** executed by that agent, assisted by a deterministic Python support layer (`src/pipeline.py`, `scripts/translate_book.py`) that only prepares briefs, protects placeholders and validates output. No external model, API, token or credential is used or requested; if a translation cannot be produced, the tool says so explicitly rather than emitting a fake translation.

## Workflow

1. **Load context** — read `config/translator.yaml`, `docs/style-guide.md` and `data/glossary.tbx`; if this is a book, read `data/characters.json` and `data/places.json`.
2. **Build the translation brief** — `src/pipeline.py::TranslationPipeline.build_brief(...)` produces the `analysis`, `glossary_terms`, `placeholder_map`, `agent_prompts` and `style_profile` recorded in `docs/translation-brief-template.md`.
3. **Run the seven stages in order**, passing each stage's JSON output to the next:
   1. `agents/analysis_agent.md` — context, entities, formatting scan.
   2. `agents/translator_agent.md` — glossary-injected draft.
   3. `agents/posteditor_agent.md` — Arabic grammar, morphology, orthography, diacritics.
   4. `agents/reviewer_agent.md` — MQM critique (0–100 dimensions; weights 30/25/20/15/10).
   5. `agents/editor_agent.md` — apply the critique.
   6. `agents/judge_agent.md` — quality gate: weighted score ≥ 85, at most 3 iterations.
   7. `agents/consistency_agent.md` — cross-chapter coherence (books only).
4. **Validate** — `src/pipeline.py::TranslationPipeline.validate(host_translation, brief)` must return `passed: true`; a missing or altered placeholder is a named failure, never a silent pass.
5. **Export** — write the approved Markdown master; use `scripts/translate_book.py` for EPUB/DOCX (and optional PDF) output for books.

MSA is the default register; a dialect is used only on explicit request. The glossary is injected at every stage, and RTL order, diacritics policy and placeholder/code protection follow `docs/style-guide.md`.

## MQM scoring contract (shared by Review and Judge)

- **Dimensions and weights:** Accuracy 30%, Fluency 25%, Style/Register 20%, Terminology 15%, Coherence 10% (equivalently weighted points out of 30/25/20/15/10).
- **Single scoring rule:** score **each dimension from 0 to 100**. The **total** is the weighted sum `0.30 × accuracy + 0.25 × fluency + 0.20 × style_register + 0.15 × terminology + 0.10 × coherence`, a single number in **0–100**. No dimension uses a reduced scale; the weights are applied exactly once.
- **`glossary_adherence` is a 0–100 percentage**, separate from the weighted total.
- **Diacritics policy values:** `retain` / `remove` / `optional` (no other value).
- **Judge decisions:** exactly `approve` / `revise` / `retranslate`. At the 3-iteration cap, a further revision is mapped to `retranslate`; there is no fourth decision value.
- **Gate and cap:** approve at **≥ 85**, with a hard cap of **3 iterations**.

## Tools (prompt procedures, not binaries)

| Procedure | What the host agent does |
|-----------|--------------------------|
| `analysis` | Follow `agents/analysis_agent.md` to emit structured `analysis` JSON. |
| `translate` | Follow `agents/translator_agent.md` to emit `draft_translation`. |
| `postedit` | Follow `agents/posteditor_agent.md` to emit `revised_translation`. |
| `review` | Follow `agents/reviewer_agent.md` to emit `reviewer_critique`. |
| `edit` | Follow `agents/editor_agent.md` to apply fixes. |
| `judge` | Follow `agents/judge_agent.md` to gate at 85 with ≤ 3 iterations. |
| `consistency` | Follow `agents/consistency_agent.md` for book coherence. |
| `lookup` | Use `skills/reference-skills/SKILL.md` for offline dictionary/style lookups. |
| `validate` | Call `TranslationPipeline.validate(...)` in `src/pipeline.py`. |

## Real files in this pack

- `agents/*.md` — the seven role prompts (frontmatter: `name`, `description`).
- `skills/reference-skills/SKILL.md` — offline reference procedures.
- `docs/style-guide.md` — EN↔AR typography and formatting rules.
- `docs/translation-brief-template.md` — the brief contract consumed by the agents.
- `data/glossary.tbx`, `data/characters.json`, `data/places.json` — term and entity registries.
- `config/translator.yaml` — register, threshold, diacritics and iteration settings.
- `commands/translate.md` — the `/translate` slash command.
- `.claude-plugin/plugin.json` — Claude Code plugin manifest.
- `scripts/install.sh`, `scripts/install_skill.sh` — host installers.

## Usage

Invoke `/translate <text-or-file> [--target en|ar] [--book]`, or follow the workflow directly. Do not call `python` with an LLM flag: there is no LLM client in the default path.

## Installation

Run `bash scripts/install.sh --help` for options. `scripts/install_skill.sh` is a compatibility shim that delegates to `scripts/install.sh`.
