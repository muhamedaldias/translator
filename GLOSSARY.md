# Translation Skill Pack

The canonical vocabulary of the portable English ↔ Arabic translation skill pack. These terms name the domain — what the work is, what it produces and who performs it — and are shared by host agents, prompts and documentation.

## Pack and participants

**Skill Pack**:
A portable, host-agnostic bundle of translation skills, role prompts and documentation that adds an English ↔ Arabic workflow to any coding agent.
_Avoid_: plugin bundle, tool library, translation service.

**Portable Core**:
The single canonical set of skills, agent prompts and documents to which every host mapping points.
_Avoid_: backend, source tree, runtime.

**Host Agent**:
The coding agent whose own model performs the translation work; it is the sole source of linguistic judgment in the workflow.
_Avoid_: API provider, model client, translation backend.

**Adapter**:
A thin host-specific mapping of the portable core into one coding agent's native layout.
_Avoid_: wrapper, bridge, integration layer.

## Work units

**Translation Brief**:
A context-rich description of one translation task: the source, the register, the approved terminology and the spans that must remain untouched.
_Avoid_: prompt bundle, job spec, request payload.

**Term Base**:
The approved source-to-target terminology made available at every translation stage.
_Avoid_: glossary, dictionary, termbase.

**Placeholder**:
A verbatim span — a code token, markup tag, identifier or `{{variable}}` — that must appear unchanged in the target text.
_Avoid_: token, variable, template slot.

**Style Profile**:
The register and typographic conventions that govern the target text, including the Arabic default, orthography, diacritics and right-to-left layout.
_Avoid_: style guide, formatting rules, tone settings.

**Chapter Context**:
The accumulated character, place and terminology state carried forward from earlier chapters of a book.
_Avoid_: previous context, memory, summary.

## Roles

**Translation Agent**:
A role-specialized prompt that the host agent executes for one stage of the translation workflow.
_Avoid_: stage, worker, model call.

**Analysis Agent**:
The role that establishes genre, audience, register, domain, entities and document structure before any target text is drafted.
_Avoid_: preprocessor, scanner.

**Translator Agent**:
The role that produces the first target-language draft from the source and the brief.
_Avoid_: drafter, generator.

**Post-editor Agent**:
The role that repairs Arabic grammar, morphology, agreement and orthography in a draft.
_Avoid_: corrector, proofreader.

**Reviewer Agent**:
The role that records translation errors with category and severity under the MQM framework.
_Avoid_: critic, checker.

**Editor Agent**:
The role that applies review findings to produce a revised target text.
_Avoid_: reviser, patcher.

**Judge Agent**:
The role that makes the final acceptance decision against the MQM gate.
_Avoid_: scorer, approver.

**Consistency Agent**:
The role that keeps names, places and terminology coherent across the chapters of a book.
_Avoid_: continuity editor, reconciler.

## Quality and deliverables

**MQM Gate**:
The single acceptance decision that approves a translation or sends it back for another round, measured on the MQM rubric.
_Avoid_: score check, approval threshold, quality gate.

**Revision Round**:
One critique-and-revise pass before the MQM gate is reconsidered, capped at three rounds.
_Avoid_: iteration, retry, loop.

**Master Markdown**:
The formatted Markdown document that is the authoritative translated deliverable.
_Avoid_: intermediate draft, source file.

**Exported Edition**:
A publishable rendering — EPUB, DOCX or optional PDF — derived from the master Markdown.
_Avoid_: output file, converted document.

**Explicit Absence**:
The declared outcome when no host-produced translation is available; the workflow reports this rather than emitting an invented target text.
_Avoid_: placeholder translation, stub, fallback output.
