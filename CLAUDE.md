# Claude Code Rules — Portable Translation Skill Pack

This file configures Claude Code for the key-free EN ↔ Arabic translation skill pack. Claude Code is the host agent: its own model performs every translation stage. No provider key is used or requested.

## Project context

- **Architecture:** portable core (`skills/`, `agents/`, `docs/`) plus thin host adapters installed by `scripts/install.sh`.
- **Who translates:** the host agent — here, Claude Code itself. Python prepares a brief and validates the result; it never produces target text.
- **Seven agents:** Analysis → Translator → Post-editor → Reviewer → Editor → Judge → Consistency.
- **Quality:** MQM gate, score ≥ 85, at most 3 revision rounds, approved terminology injected at every stage.

## Translation procedure

When asked to translate English ↔ Arabic:

1. **Load the skill** from `.claude/skills/translator` (or the `/translate` command installed with the plugin). Load it only for translation work.
2. **Use the deterministic brief** — let the Python layer supply context, approved terms, protected spans and the style profile before drafting.
3. **Run the seven agents in sequence.** Each is a role-specialized prompt in `agents/` and `skills/`; do not collapse or parallelize their responsibilities.
4. **Never translate protected spans** — code, `{{placeholders}}`, tags and IDs remain verbatim. Preserve RTL markers and paragraph structure.
5. **Apply the MQM gate** — Reviewer then Judge; a score below 85 returns the text for revision, capped at three rounds.
6. **Validate and deliver** — check the host output against the brief, then write the master Markdown and export EPUB/DOCX or optional PDF if requested.
7. **If no translation is produced, say so explicitly.** Never invent target text.
8. **Do not ask for, set or generate an API key or provider credential.** There is nothing to configure for translation. `src/llm_client.py` is deprecated and must not be called from the default path.

## Arabic rules

- MSA for written text; Egyptian, Gulf or Levantine only on explicit request.
- Root-and-pattern morphology, six plural forms, gender and definiteness agreement, broken-plural agreement.
- Normalize alef/ya/ta-marbuta variants; follow the configured diacritics policy.
- Resolve named entities against the term base and style profile; transliterate or translate accordingly.

## Installation for this host

```bash
bash scripts/install.sh --host claude-code          # plugin manifest, .claude/skills, .claude/agents, /translate command
bash scripts/install.sh --host claude-code --dry-run
bash scripts/install.sh --help
```

The Claude Code adapter adds `.claude-plugin/plugin.json`, `.claude/skills/`, `.claude/agents/` and `commands/translate.md`. Other supported hosts are `codex`, `opencode`, `hermes` and `generic`. `scripts/install_skill.sh` is a compatibility shim only.

## Commands for contributors

```bash
python -m pytest tests/ -v
python scripts/validate_pack.py
python -m pytest tests/test_docs_consistency.py -v
```

All paths are repository-relative. Work through pull requests on protected `main`; CI must pass before merge.
