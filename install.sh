#!/usr/bin/env bash
# closeloop installer - copies skills into ~/.claude/skills/
# Prompts before overwriting anything that already exists.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

[ -d "$SRC" ] || { echo "ERROR: skills/ not found next to this script." >&2; exit 1; }
mkdir -p "$DEST"

installed=0
skipped=0

for dir in "$SRC"/*/; do
  name="$(basename "$dir")"
  target="$DEST/$name"
  if [ -e "$target" ]; then
    printf 'Skill "%s" already exists at %s. Overwrite? [y/N] ' "$name" "$target"
    read -r reply </dev/tty || reply="n"
    case "$reply" in
      [yY]*) rm -rf "$target" ;;
      *) echo "  skipped $name"; skipped=$((skipped + 1)); continue ;;
    esac
  fi
  cp -R "$dir" "$target"
  echo "  installed $name"
  installed=$((installed + 1))
done

echo
echo "closeloop: $installed installed, $skipped skipped -> $DEST"
echo
echo "Optional next steps:"
echo "  * Copy docs/CLAUDE.md.template into your finance working folder as CLAUDE.md"
echo "  * Read ENTERPRISE.md before relying on any skill on a managed seat"
echo "  * Hooks are OFF by default - see hooks/README.md to enable them deliberately"
