#!/usr/bin/env bash
#
# StudioLocal — bootstrap installer
# Uso: curl -fsSL https://raw.githubusercontent.com/davidbenal/studiolocal/main/scripts/install.sh | bash
#
# Faz:
#   1. Garante diretório do repo (~/Desktop/David-OS/modules/studiolocal/)
#   2. Clona ou faz pull
#   3. pip install -e .
#   4. Cria skill global studiolocal-bootstrap em ~/.claude/skills/
#   5. Symlinka skills operacionais

set -euo pipefail

REPO_DIR="${STUDIOLOCAL_REPO:-$HOME/Desktop/David-OS/modules/studiolocal}"
GIT_URL="${STUDIOLOCAL_GIT:-https://github.com/davidbenal/studiolocal.git}"

echo "==> StudioLocal bootstrap"
echo "    repo: $REPO_DIR"

# 1. clone ou pull
if [ -d "$REPO_DIR/.git" ]; then
    echo "==> Atualizando repo existente"
    git -C "$REPO_DIR" pull --ff-only
else
    echo "==> Clonando repo"
    mkdir -p "$(dirname "$REPO_DIR")"
    if [ -d "$REPO_DIR" ]; then
        # diretório existe sem .git (ex: scaffolding manual) — não sobrescreve
        echo "    diretório existe sem .git, pulando clone"
    else
        git clone "$GIT_URL" "$REPO_DIR"
    fi
fi

# 2. pip install
echo "==> Instalando dependências Python"
cd "$REPO_DIR"
if command -v uv >/dev/null 2>&1; then
    uv pip install -e . --system 2>/dev/null || pip install -e .
else
    pip install -e .
fi

# 3. skill global studiolocal-bootstrap
mkdir -p "$HOME/.claude/skills/studiolocal-bootstrap"
cp -f "$REPO_DIR/scripts/bootstrap-skill.md" "$HOME/.claude/skills/studiolocal-bootstrap/SKILL.md"

# 4. symlink skills operacionais
bash "$REPO_DIR/scripts/symlink-skills.sh"

echo ""
echo "✓ StudioLocal instalado"
echo "  CLI:    $(which studiolocal 2>/dev/null || echo 'NÃO ENCONTRADO — adicione $(python -m site --user-base)/bin ao PATH')"
echo "  Skills: $(ls "$HOME/.claude/skills" | grep -c '^studio') em ~/.claude/skills/"
echo ""
echo "Próximo passo: em qualquer workspace, digite /studiolocal-install"
