# StudioLocal

Setup de geração de imagem e vídeo via Fal.ai, operado conversacionalmente via Claude Code.

Funciona **standalone** (próprio `.env`) ou **embedded** em workspaces refinados (metaKosmos, Ktirio, Montuvia, 214, David-OS) herdando credenciais do parent.

## Instalação rápida

### Pré-requisitos

- macOS ou Linux
- Python 3.11+ (`python3 --version`)
- Claude Code instalado e rodando
- Chave Fal.ai ([fal.ai/dashboard/keys](https://fal.ai/dashboard/keys))

### 1. Bootstrap global (uma vez por máquina)

```bash
curl -fsSL https://raw.githubusercontent.com/davidbenal/studiolocal/main/scripts/install.sh | bash
```

Isso clona o repo em `~/Desktop/David-OS/modules/studiolocal/`, cria virtualenv com deps Python, registra o CLI `studiolocal` e instala 12 skills `/studio-*` em `~/.claude/skills/`.

### 2. Instalar em um workspace

Em **qualquer pasta** onde você quer usar o StudioLocal (workspace de cliente, projeto pessoal, etc.), abra o Claude Code e digite:

```
/studiolocal-install
```

A skill detecta automaticamente:
- Se há `.envmk` ou `.env` no workspace → modo **embedded** (usa credencial herdada)
- Senão → modo **standalone** (cria `.studiolocal/.env` para você preencher `FAL_KEY=...`)

### 3. Validar

```bash
bash ~/Desktop/David-OS/modules/studiolocal/scripts/doctor.sh
```

Deve retornar 8 checks verdes (CLI no PATH, repo presente, skills globais, models.yaml, .studiolocal/ local, FAL_KEY, conectividade Fal).

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

## Skills operacionais

`/studio-project`, `/studio-image`, `/studio-video`, `/studio-upscale`, `/studio-promote`, `/studio-discard`, `/studio-workflow`, `/studio-run`, `/studio-cleanup`, `/studio-report`, `/studio-status`.

## Primeiros passos (uso conversacional)

No Claude Code do workspace já instalado:

```
você: novo project Hero Fashion Q2, tag campaign:q2
Claude: ✓ Project hero-fashion-q2 criado.

você: gera 4 imagens de modelo feminina vestindo terno bege oversized,
      fundo concreto cinza, luz lateral hard, 3:4
Claude: nano-banana-pro × 4 — custo R$ 1,28. Confirma?
você: vai
Claude: ✓ 4 imagens em projects/hero-fashion-q2/drafts/...

você: a 03 ficou. upscale 4x e depois anima orbit 5s
Claude: [executa em sequência]
       ✓ Custo total da session: R$ 3,23

você: salva esse processo como workflow Hero Fashion Light
Claude: ✓ workflows/hero-fashion-light.yaml. Use `/studio-run` pra reusar.

você: quanto gastei esse mês com campaign:q2?
Claude: [tabela markdown com total, por modelo, por project]
```

## Comandos úteis no terminal

```bash
studiolocal status                          # estado geral
studiolocal project list                    # projects ativos
studiolocal report --month 2026-05          # custos do mês
studiolocal cleanup                         # revisão manual
studiolocal cleanup --safe                  # auto end-session
bash scripts/doctor.sh                      # diagnóstico
```

## Documentação

- [docs/DESIGN.md](docs/DESIGN.md) — plano de arquitetura V1 completo
- `models.yaml` — catálogo de modelos
- `migrations/` — schema SQLite versionado
- `templates/` — templates de Brief, Workflow, Project README

## Licença

Privada (David Benalcázar Chang). A definir antes de eventual open-source.
