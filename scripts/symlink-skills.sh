#!/usr/bin/env bash
#
# Cria symlinks das skills operacionais do repo para ~/.claude/skills/.
# Idempotente: re-execução é segura.

set -euo pipefail

REPO_DIR="${STUDIOLOCAL_REPO:-$HOME/Desktop/David-OS/modules/studiolocal}"
TARGET="$HOME/.claude/skills"

mkdir -p "$TARGET"

count=0
for src in "$REPO_DIR/.claude/skills/"*/; do
    name=$(basename "$src")
    link="$TARGET/$name"
    # remove link/diretório se existe
    if [ -L "$link" ]; then
        rm "$link"
    elif [ -d "$link" ]; then
        echo "    pulando $name — diretório existe (não é symlink)"
        continue
    fi
    ln -s "$src" "$link"
    count=$((count + 1))
done

echo "✓ $count skills symlinkadas em $TARGET"
