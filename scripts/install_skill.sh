#!/usr/bin/env bash
# install_skill.sh — compatibility shim. Delegates to scripts/install.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/install.sh" "$@"
