# StudioLocal

Setup de geração de imagem e vídeo via Fal.ai, operado conversacionalmente via Claude Code.

Funciona **standalone** (próprio `.env`) ou **embedded** em workspaces refinados (metaKosmos, Ktirio, Montuvia, 214, David-OS) herdando credenciais do parent.

## Modelos core (V1)

| Tipo | Modelo | Endpoint Fal.ai |
|---|---|---|
| Imagem | Nano Banana 2 (Gemini 2.5 Flash Image) | `fal-ai/gemini-flash-image` |
| Imagem | Nano Banana Pro | `fal-ai/gemini-flash-image-pro` |
| Vídeo | Kling 3 | `fal-ai/kling-video/v3/pro/text-to-video` |
| Vídeo | Seedance 2 | `fal-ai/seedance/v2` |
| Upscale | Clarity | `fal-ai/clarity-upscaler` |

Catálogo extensível em `models.yaml`.

## Conceitos centrais

7 entidades. Detalhes em [docs/DESIGN.md](docs/DESIGN.md).

- **Project** — container de trabalho criativo
- **Brief** — documento de intenção (opcional)
- **Session** — período contínuo de trabalho (auto-gerenciado)
- **Workflow** — receita YAML reutilizável (criada a posteriori)
- **Run** — execução nomeada de um Workflow
- **Generation** — 1 chamada de API Fal → 1+ outputs
- **Asset** — output individual (status: draft / library / discarded)

## Instalação

### 1. Bootstrap global (uma vez por máquina)

```bash
curl -fsSL https://raw.githubusercontent.com/davidbenal/studiolocal/main/scripts/install.sh | bash
```

Instala a skill `studiolocal-bootstrap` em `~/.claude/skills/`.

### 2. Em cada workspace

```
/studiolocal-install
```

Detecta modo embedded vs standalone, cria `.studiolocal/`, registra skills operacionais, edita `CLAUDE.md` (idempotente, fenced).

## Skills operacionais

`/studio-project`, `/studio-image`, `/studio-video`, `/studio-upscale`, `/studio-promote`, `/studio-discard`, `/studio-workflow`, `/studio-run`, `/studio-cleanup`, `/studio-report`, `/studio-status`.

## Documentação

- [docs/DESIGN.md](docs/DESIGN.md) — plano de arquitetura V1 completo
- `models.yaml` — catálogo de modelos
- `migrations/` — schema SQLite versionado
- `templates/` — templates de Brief, Workflow, Project README

## Licença

Privada (David Benalcázar Chang). A definir antes de eventual open-source.
