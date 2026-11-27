#!/usr/bin/env bash
# install.sh — install the portable, key-free EN<->AR translation skill pack.
# All source paths are resolved relative to THIS script's repository root.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

HOST="auto"
DRY_RUN=0
PROJECT_DIR=""

usage() {
  printf '%s\n' \
    "Usage: bash scripts/install.sh [options]" \
    "" \
    "Install the portable, key-free EN<->AR translation skill pack into a coding agent." \
    "" \
    "Options:" \
    "  --help                 Show this help and exit." \
    "  --host HOST            Target host: claude|claude-code|codex|opencode|hermes|generic|auto" \
    "                         (default: auto)." \
    "  --dry-run              Print the planned actions without writing any files." \
    "  --project DIR          Install project-locally into DIR/.agents instead of" \
    "                         the host's global directory." \
    "  --dest DIR             Alias for --project." \
    "" \
    "Sources are always read from the repository containing this script:" \
    "  $REPO_ROOT" \
    "No other absolute path is used. The installer is idempotent: unchanged files" \
    "are left untouched. Nothing is installed under --host auto unless a host is detected."
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --host)
      if [ "$#" -lt 2 ]; then printf 'error: --host needs a value\n' >&2; exit 2; fi
      HOST="$2"
      shift 2
      ;;
    --host=*)
      HOST="${1#--host=}"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --project)
      if [ "$#" -lt 2 ]; then printf 'error: --project needs a value\n' >&2; exit 2; fi
      PROJECT_DIR="$2"
      shift 2
      ;;
    --project=*)
      PROJECT_DIR="${1#--project=}"
      shift
      ;;
    --dest)
      if [ "$#" -lt 2 ]; then printf 'error: --dest needs a value\n' >&2; exit 2; fi
      PROJECT_DIR="$2"
      shift 2
      ;;
    --dest=*)
      PROJECT_DIR="${1#--dest=}"
      shift
      ;;
    *)
      printf 'error: unknown option: %s (try --help)\n' "$1" >&2
      exit 2
      ;;
  esac
done

case "$HOST" in
  claude|claude-code|codex|opencode|hermes|generic|auto) ;;
  *) printf 'error: invalid --host %s (expected claude|claude-code|codex|opencode|hermes|generic|auto)\n' "$HOST" >&2; exit 2 ;;
esac

if [ "$HOST" = "claude-code" ]; then
  HOST="claude"
fi

detect_host() {
  if [ -d "$HOME/.claude" ]; then
    printf 'claude'
  elif [ -d "$HOME/.codex" ]; then
    printf 'codex'
  elif [ -d "$HOME/.opencode" ]; then
    printf 'opencode'
  elif [ -d "$HOME/.hermes" ]; then
    printf 'hermes'
  elif [ -d "$HOME/.agents" ]; then
    printf 'codex'
  else
    printf 'none'
  fi
}

if [ "$HOST" = "auto" ]; then
  DETECTED="$(detect_host)"
  if [ "$DETECTED" = "none" ]; then
    printf 'No supported host detected; nothing installed (no global side effects).\n'
    printf 'Re-run with --host claude|codex|opencode|hermes|generic to install explicitly.\n'
    exit 0
  fi
  HOST="$DETECTED"
fi

if [ -n "$PROJECT_DIR" ]; then
  TARGET="$PROJECT_DIR/.agents"
else
  case "$HOST" in
    claude)            TARGET="$HOME/.claude" ;;
    codex|opencode)    TARGET="$HOME/.agents" ;;
    hermes)            TARGET="$HOME/.hermes" ;;
    generic)           TARGET="$PWD/.agents" ;;
  esac
fi

printf 'Translation pack installer\n'
printf '  host:     %s\n' "$HOST"
printf '  source:   %s\n' "$REPO_ROOT"
printf '  target:   %s\n' "$TARGET"
if [ "$DRY_RUN" -eq 1 ]; then
  printf '  mode:     dry-run (no files will be written)\n'
else
  printf '  mode:     install\n'
fi
printf '\n'

install_file() {
  SRC="$1"
  DST="$2"
  if [ ! -f "$SRC" ]; then
    printf '  skip (missing source): %s\n' "$SRC"
    return 0
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '  would install: %s -> %s\n' "$SRC" "$DST"
    return 0
  fi
  mkdir -p "$(dirname "$DST")"
  if [ -f "$DST" ] && cmp -s "$SRC" "$DST"; then
    printf '  unchanged: %s\n' "$DST"
  else
    cp -f "$SRC" "$DST"
    printf '  installed: %s\n' "$DST"
  fi
}

printf 'Skills:\n'
for SKILL_SRC in "$REPO_ROOT"/skills/*/SKILL.md; do
  [ -f "$SKILL_SRC" ] || continue
  SKILL_NAME="$(basename "$(dirname "$SKILL_SRC")")"
  install_file "$SKILL_SRC" "$TARGET/skills/$SKILL_NAME/SKILL.md"
done

printf 'Agents:\n'
for AGENT_SRC in "$REPO_ROOT"/agents/*.md; do
  [ -f "$AGENT_SRC" ] || continue
  install_file "$AGENT_SRC" "$TARGET/agents/$(basename "$AGENT_SRC")"
done

printf 'Docs:\n'
for DOC_SRC in "$REPO_ROOT"/docs/style-guide.md "$REPO_ROOT"/docs/translation-brief-template.md; do
  install_file "$DOC_SRC" "$TARGET/docs/$(basename "$DOC_SRC")"
done

printf 'Runtime support files:\n'
install_file "$REPO_ROOT/config/translator.yaml" "$TARGET/config/translator.yaml"
mkdir -p "$TARGET/data/dictionaries" "$TARGET/data/cache"
for DATA_SRC in "$REPO_ROOT"/data/*.json "$REPO_ROOT"/data/*.tbx; do
  [ -f "$DATA_SRC" ] || continue
  install_file "$DATA_SRC" "$TARGET/data/$(basename "$DATA_SRC")"
done
for SRC_PY in "$REPO_ROOT"/src/*.py; do
  [ -f "$SRC_PY" ] || continue
  install_file "$SRC_PY" "$TARGET/src/$(basename "$SRC_PY")"
done
install_file "$REPO_ROOT/scripts/translate_book.py" "$TARGET/scripts/translate_book.py"
install_file "$REPO_ROOT/requirements.txt" "$TARGET/requirements.txt"
install_file "$REPO_ROOT/requirements-optional.txt" "$TARGET/requirements-optional.txt"

install_file "$REPO_ROOT/scripts/install.sh" "$TARGET/scripts/install.sh"
install_file "$REPO_ROOT/scripts/install_skill.sh" "$TARGET/scripts/install_skill.sh"
install_file "$REPO_ROOT/commands/translate.md" "$TARGET/commands/translate.md"
install_file "$REPO_ROOT/.claude-plugin/plugin.json" "$TARGET/.claude-plugin/plugin.json"

printf '\n'
if [ "$DRY_RUN" -eq 1 ]; then
  printf 'Dry run complete; no files were written.\n'
else
  printf 'Done. The pack is key-free: the host agent performs all translation stages.\n'
fi
