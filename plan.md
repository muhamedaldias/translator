# Portable Translation Skill Pack — Implementation Plan

**Status:** current architecture, implementation in progress
**Spec:** `docs/superpowers/specs/2026-11-26-portable-translation-skill-pack-design.md`
**Goal:** rebuild the repository as a key-free, portable EN ↔ AR skill pack with a deterministic Python support layer, professional outputs, CI and a protected `main`.

---

## 1. Architecture

The canonical pack (`skills/`, `agents/`, `docs/`) is host-agnostic. Thin adapters and an installer map it into Claude Code, Codex, OpenCode, Hermes or a generic coding agent. **The host agent's own model performs every translation stage.** Python never calls an LLM: it prepares a context-rich translation brief and validates host-produced output. Translation quality comes from seven role-specialized prompts and an explicit MQM gate.

```
Source → deterministic brief → seven host-executed agents → MQM gate → validation → Markdown master → EPUB / DOCX / PDF
```

### Design principles

- Sequential stages outperform parallel generation for terminology consistency.
- The approved term base is injected at every stage; protected spans are never translated.
- Two or three revision rounds capture most of the quality gain.
- Role specialization beats a generic "revise" instruction.
- Absence of a host translation is declared explicitly; it is never faked.

## 2. Global constraints

- No API key, provider SDK call or network request in the default translation path.
- All paths are relative to the repository root; the retired absolute workspace path must not reappear.
- Every `SKILL.md` and `agents/*.md` begins with YAML frontmatter containing `name` and `description`.
- Tests pass offline; no test requires a model download or a credential.
- User-facing docs describe only the current key-free architecture.

## 3. Seven agents

| Agent | Responsibility |
|-------|----------------|
| Analysis | Genre, audience, register, domain, entities, gender context and document structure. |
| Translator | First target-language draft from the source and the brief. |
| Post-editor | Arabic grammar, morphology, agreement and orthography. |
| Reviewer | MQM error spans, categories, severity and suggested fixes. |
| Editor | Applies review findings to produce a revised target text. |
| Judge | MQM gate decision; approve or return for another round. |
| Consistency | Character, place and terminology coherence across chapters. |

Quality bar: MQM score ≥ 85 approves; 70–84 allows one revision; below 70 requires retranslation; at most 3 rounds. MSA is the default register; dialect only on explicit request.

## 4. Workstreams

| Task | Focus | Deliverables |
|------|-------|--------------|
| A | Deterministic core | `build_brief()` and `validate()`; real analysis; no LLM calls in the default path; legacy flags deprecated. |
| B | Book workflow and formats | Chapter preparation and assembly with context, real consistency findings, guarded optional imports, format handlers. |
| C | Portable skill pack | Loadable skills and seven agents with frontmatter; Claude Code plugin and command; installer for all hosts; style guide and brief template. |
| D | Docs and domain model | `GLOSSARY.md`, the no-API-key ADR, rewritten README/AGENTS/CLAUDE/plan, and docs consistency tests. |
| E | CI and validation | Pack validation script, GitHub Actions workflow, de-duplicated config, pinned requirements with optional extras. |
| F | Publish and protect | Push to `main`, verify CI, enable branch protection (required PR, required checks, no force push or deletion, no admin bypass). |

## 5. Interfaces

- **Brief:** analysis, glossary terms, placeholder map, seven agent prompts and style profile.
- **Validation:** `passed`, `issues` and `score`; a missing placeholder fails with a named error.
- **Book:** per-chapter preparation and assembly with character, place and dynamic term state; resumable manifests.
- **Installer:** `--help`, `--host`, `--dry-run`, `--dest`; no global side effects.

## 6. Outputs and quality

Well-formatted Markdown is the master: headings, quotes, paragraphs, RTL and preserved placeholders/code. Professional EPUB and DOCX exports and optional PDF are derived from it under a bundled style guide. COMET-MQM and other automatic metrics are optional and degrade honestly when their model is unavailable.

## 7. Operations

CI runs pytest, pack validation and a key-free smoke test on pushes and pull requests. Changes reach `main` only through pull requests with required status checks. Force pushes, branch deletion and admin bypass are disabled. Documentation, tests and CI must stay aligned with this contract.

## 8. Definition of done

- Seven agents produce an approved translation through the brief/validation contract with no credential involved.
- Pack validation, the docs consistency test and the offline pytest suite pass in a clean environment.
- The installer works for Claude Code, Codex, OpenCode, Hermes and generic hosts.
- Book translation keeps character, place and terminology coherent across chapters.
- `main` is protected and its required CI checks are green.
