#!/usr/bin/env bash
# install_skill.sh — Install translator-skill into coding agents

set -euo pipefail

SKILL_SOURCE="/data/workspace/projects/translator/skills/translator-skill"
REFERENCE_SOURCE="/data/workspace/projects/translator/skills/reference-skills"

echo "=== Installing Multi-Agent Translation Skill ==="

# Detect coding agent
if [ -d "$HOME/.claude" ]; then
    echo "Detected Claude Code"
    AGENT_DIR="$HOME/.claude/skills"
    mkdir -p "$AGENT_DIR"
    cp -r "$SKILL_SOURCE" "$AGENT_DIR/translator"
    cp -r "$REFERENCE_SOURCE" "$AGENT_DIR/reference-skills"
    echo "Installed translator-skill to $AGENT_DIR/translator"
elif [ -d "$HOME/.agents" ]; then
    echo "Detected Codex/OpenCode"
    AGENT_DIR="$HOME/.agents/skills"
    mkdir -p "$AGENT_DIR"
    cp -r "$SKILL_SOURCE" "$AGENT_DIR/translator"
    cp -r "$REFERENCE_SOURCE" "$AGENT_DIR/reference-skills"
    echo "Installed translator-skill to $AGENT_DIR/translator"
else
    echo "No coding agent directory found (.claude or .agents)"
    echo "Manually copy $SKILL_SOURCE to your agent's skills directory"
fi

echo ""
echo "=== Installation Complete ==="
echo "Usage:"
echo "  skills translator-skill translate --source \"text\" --target ar"
echo "  skills translator-skill pipeline --source input.txt --target ar --output output_ar.txt"
