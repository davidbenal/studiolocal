---
name: studiolocal-bootstrap
description: Instala o StudioLocal globalmente (clona repo, faz pip install, symlinka skills). Use quando user pedir "/studiolocal-bootstrap" ou "instala o studiolocal global". Skill instalada via `curl|bash` — fica em ~/.claude/skills/.
---

# Skill: studiolocal-bootstrap

> Esta skill é instalada automaticamente em `~/.claude/skills/studiolocal-bootstrap/SKILL.md`
> pelo `scripts/install.sh` (executado uma vez via `curl|bash`).

## Quando usar

- Usuário digita `/studiolocal-bootstrap`.
- Você detecta que o user quer usar StudioLocal mas o CLI `studiolocal` não está disponível no PATH.

## O que fazer

1. **Verifique se já está instalado**:
   ```bash
   which studiolocal && studiolocal --version
   ```
   Se OK, oriente: "StudioLocal já está instalado. Em qualquer workspace digite `/studiolocal-install`."

2. **Clone ou atualize o repo**:
   ```bash
   REPO=~/Desktop/David-OS/modules/studiolocal
   if [ ! -d "$REPO" ]; then
     mkdir -p ~/Desktop/David-OS/modules
     git clone https://github.com/davidbenal/studiolocal.git "$REPO"
   else
     cd "$REPO" && git pull --ff-only
   fi
   ```

3. **Instale dependências** (uv preferido, pip fallback):
   ```bash
   cd "$REPO"
   if command -v uv >/dev/null 2>&1; then
     uv pip install -e .
   else
     pip install -e .
   fi
   ```

4. **Symlink das skills operacionais**:
   ```bash
   bash "$REPO/scripts/symlink-skills.sh"
   ```

5. **Verifique**:
   ```bash
   studiolocal --version
   ls ~/.claude/skills/ | grep '^studio'
   ```

6. **Reporte ao user**:
   ```
   ✓ StudioLocal v0.1.0 instalado
   ✓ 12 skills /studio-* disponíveis em ~/.claude/skills/
   
   Próximo passo: vá para qualquer workspace e digite /studiolocal-install
   ```

## Notas

- Nunca rode `pip install` em system Python. Se pip falhar, oriente o user a criar venv ou usar pipx.
- O symlink mantém as skills sempre sincronizadas com o repo (git pull → reflete imediatamente).
