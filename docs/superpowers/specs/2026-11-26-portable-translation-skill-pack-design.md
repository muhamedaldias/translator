# Portable Translation Skill Pack — Design (approved 2026-11-26)

> Decisions approved by the repository owner in the grill-with-docs interview.

**Goal:** turn `muhamedaldias/translator` into a professional, portable skill pack that
adds a high-quality EN↔AR translation workflow to *any* coding agent, with **no API key,
no provider account and no network dependency** for translation itself.

## Approved decisions

1. **Package model:** one portable core (`skills/`, `agents/`, `docs/`) plus thin adapters
   for Claude Code (plugin manifest + `.claude/skills` + `.claude/agents` + command),
   Codex/OpenCode (`.agents/`), Hermes (`~/.hermes/skills/`), and a generic `AGENTS.md`
   path. An installer detects the host and installs the right layout.
2. **Intelligence source:** the host coding agent's own model performs every translation
   stage. `src/llm_client.py` is deprecated and never called from the default path.
   Python is a deterministic support layer only: TBX/glossary handling, term-base
   checks, placeholder protection, format conversion, scoring, validation.
3. **Quality:** adaptive context analysis (genre, audience, register, domain, document
   structure) → seven sequential agents (Analysis, Translator, Post-editor, Reviewer,
   Editor, Judge, Consistency) → MQM gate ≥85, ≤3 iterations. MSA default; dialect only
   on explicit request. Glossary injected at every stage.
4. **Output:** well-formatted Markdown is the master (headings, quotes, paragraphs, RTL,
   preserved `{{placeholders}}`/code), with professional EPUB and DOCX export and
   optional PDF. A bundled style guide governs typography and formatting.
5. **Operations:** CI runs pytest + pack validation + a key-free smoke test; all changes
   are pushed to `main` under `muhamedaldias`; only then is `main` protected with
   required PR, required status checks, blocked force pushes/deletions, and no admin
   bypass. Later changes go through PRs.

## Non-goals / anti-goals

- No hosted service, no API-key prompt, no automatic network calls in the translation path.
- No claim that COMET-MQM works without the optional model; it must degrade honestly.
- No silent placeholder translation: if no host agent supplies a translation, the tool
  must say so explicitly rather than emit a fake translation.

## Constraints

- Python 3.10+, stdlib-first; optional extras never imported at module import time.
- All paths relative to repository root; no `/data/workspace/projects/translator`.
- Every SKILL.md and agent definition must be loadable: YAML frontmatter with `name`
  and `description`.
- All tests must pass in a clean environment; no test may need a network model download.
