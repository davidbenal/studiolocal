#!/usr/bin/env bash
#
# StudioLocal — diagnóstico
# Roda checks em ordem; cada falha imprime um aviso mas continua.

set -uo pipefail

REPO_DIR="${STUDIOLOCAL_REPO:-$HOME/Desktop/David-OS/modules/studiolocal}"
PWD_DIR="$(pwd)"

ok()   { printf "  ✓ %s\n" "$1"; }
warn() { printf "  ⚠ %s\n" "$1"; }
fail() { printf "  ✗ %s\n" "$1"; }

echo "==> StudioLocal doctor"
echo "    repo:      $REPO_DIR"
echo "    workspace: $PWD_DIR"
echo ""

echo "→ CLI"
if command -v studiolocal >/dev/null 2>&1; then
    ok "studiolocal $(studiolocal --version 2>&1 | tr -d 'studiolocal, ')"
else
    fail "CLI 'studiolocal' não no PATH"
fi

echo "→ Repo"
if [ -d "$REPO_DIR" ]; then
    ok "repo presente em $REPO_DIR"
    if [ -d "$REPO_DIR/.git" ]; then
        ok "git: $(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null) on $(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    else
        warn "repo sem .git — clone manual?"
    fi
else
    fail "repo ausente em $REPO_DIR"
fi

echo "→ Skills globais"
shopt -s nullglob
skills=("$HOME/.claude/skills/studio"*)
if [ ${#skills[@]} -gt 0 ]; then
    ok "${#skills[@]} skills /studio-* em ~/.claude/skills/"
else
    warn "nenhuma skill /studio-* encontrada"
fi

echo "→ models.yaml"
if [ -f "$REPO_DIR/models.yaml" ]; then
    cal=$(grep '^calibrated_at:' "$REPO_DIR/models.yaml" | awk '{print $2}')
    if [ -n "$cal" ]; then
        # macOS date vs Linux date — try both
        days_old=$(( ( $(date +%s) - $(date -j -f "%Y-%m-%d" "$cal" +%s 2>/dev/null || date -d "$cal" +%s 2>/dev/null) ) / 86400 ))
        if [ "$days_old" -gt 30 ]; then
            warn "models.yaml calibrado há $days_old dias (>30) — atualize preços"
        else
            ok "models.yaml calibrado há $days_old dias"
        fi
    else
        warn "models.yaml sem calibrated_at"
    fi
else
    fail "models.yaml ausente"
fi

echo "→ Workspace local"
if [ -d "$PWD_DIR/.studiolocal" ]; then
    ok ".studiolocal/ presente"
    if [ -f "$PWD_DIR/.studiolocal/tracker.db" ]; then
        size=$(stat -f %z "$PWD_DIR/.studiolocal/tracker.db" 2>/dev/null || stat -c %s "$PWD_DIR/.studiolocal/tracker.db")
        ok "tracker.db ($size bytes)"
    else
        warn "tracker.db ausente — rode /studiolocal-install"
    fi
else
    warn "este workspace não tem .studiolocal/ — rode /studiolocal-install"
fi

echo "→ FAL_KEY"
if [ -n "${FAL_KEY:-}" ]; then
    ok "FAL_KEY no shell env (override)"
else
    found=""
    for f in "$PWD_DIR/.envmk" "$PWD_DIR/.env" "$PWD_DIR/.studiolocal/.env" "$HOME/.studiolocal/.env"; do
        if [ -f "$f" ] && grep -q "^FAL_KEY=" "$f" 2>/dev/null; then
            val=$(grep "^FAL_KEY=" "$f" | head -1 | cut -d= -f2-)
            if [ -n "$val" ]; then
                ok "FAL_KEY em $f"
                found=1
                break
            fi
        fi
    done
    [ -z "$found" ] && fail "FAL_KEY não encontrada — defina em .envmk ou .studiolocal/.env"
fi

echo "→ Connectivity Fal.ai"
if command -v curl >/dev/null 2>&1; then
    code=$(curl -sS -o /dev/null -w "%{http_code}" "https://fal.run" 2>/dev/null || echo "ERR")
    if [ "$code" != "ERR" ]; then
        ok "fal.run responde ($code)"
    else
        warn "fal.run inalcançável"
    fi
fi

echo ""
echo "✓ doctor finalizado"
