# StudioLocal — Plano de Arquitetura V1

> Setup de geração de imagem/vídeo via Fal.ai, operado conversacionalmente via Claude Code, voltado a usuários não-técnicos. Componente do David-OS, embeddable em qualquer workspace.

---

## Context

David precisa de um sistema unificado de geração criativa que:

1. **Use Fal.ai como gateway** para acessar múltiplos modelos por uma única API. Core models: Nano Banana 2 + Pro (imagem), Kling 3 + Seedance 2 (vídeo), Clarity (upscale).
2. **Funcione standalone OU embedded** em workspaces refinados (metaKosmos, Ktirio, Montuvia, 214, David-OS). Quando embedded, herda credenciais do workspace pai (`.envmk`/`.env`); quando standalone, mantém próprio `.env`.
3. **Tracking nativo de gerações** para histórico, debug, controle financeiro, categorização de custos por projeto.
4. **Operável por não-técnicos via Claude Code** — modelo mental simples, comandos conversacionais PT-BR, cleanup assistido entre sessões.
5. **Workflows reutilizáveis descobertos a posteriori** — user trabalha, identifica processo bom, pede para salvar; Claude transcreve em pipeline YAML.

O sistema reduz fricção entre "ideia criativa" e "execução com tracking financeiro", elimina dependência em N ferramentas paralelas (sem gateway, sem tracking, sem categorização), e cria substrato para automação futura.

---

## Decisões travadas (interativas com o usuário)

| # | Decisão | Escolha |
|---|---|---|
| 1 | Posicionamento | Componente David-OS — vive em `~/Desktop/David-OS/modules/studiolocal/` |
| 2 | Modelo conceitual | Estendido (7 conceitos): Project, Brief, Workflow, Run, Session, Generation, Asset |
| 3 | Storage de tracking | SQLite local apenas (`$workspace/.studiolocal/tracker.db`); skill `/studio-report` gera markdown a partir de SQL |
| 4 | Instalação | Skill bootstrap global (1× via `curl\|bash`) + `/studiolocal-install` em cada workspace |
| 5 | Nome | **StudioLocal** (canônico). Skills com prefixo curto `studio-*` |
| 6 | Workflow V1 | Pipeline linear multi-step. Discovery-driven (criado a partir do trace). Composição complexa = Claude orquestrando múltiplos workflows |
| 7 | Cleanup | Híbrido — manual com revisão (`/studio-cleanup`) + auto safe ao `/end-session` (apenas `_tmp/` e failed) |

---

## Conceitos Centrais (modelo mental do usuário)

| Conceito | Definição | Quem cria | Persistência |
|---|---|---|---|
| **Project** | Container de trabalho criativo. Tem nome, slug, tags livres, budget opcional, status (active\|archived). Ex: "Petrobras Tanque", "Hero Fashion Q2". | User explicitamente | `projects` (DB) + pasta `projects/{slug}/` |
| **Brief** | Documento markdown de intenção criativa. **Opcional**. Recomendado em projetos grandes. | User (manual) ou Claude (rascunho) | `projects/{slug}/BRIEF.md` |
| **Session** | Período de trabalho contínuo dentro de um project. Auto-aberta na 1ª Generation, auto-fechada após 60min de inatividade. **User não gerencia.** | Sistema | `sessions` (DB) |
| **Generation** | 1 chamada de API Fal → 1+ outputs. Tem prompt, modelo, params, custo, status (pending\|done\|failed), `fal_request_id`. | User (via skill) ou Workflow Run | `generations` (DB) |
| **Asset** | Output individual (imagem/vídeo). Status: `draft` (recém-gerado) \| `library` (promovido) \| `discarded`. Tem `file_path`, parent (p/ derivados como upscale). | Sistema (descende de Generation) | `assets` (DB) + arquivos em `drafts/` ou `library/` |
| **Workflow** | Receita reutilizável (pipeline linear de steps). Salva como YAML. **Criada após o fato** — user identifica processo bom, pede save. | User + Claude (transcreve trace) | `workflows` (DB) + `workflows/{slug}.yaml` |
| **Run** | Execução nomeada de um Workflow. Agrupa N Generations. Permite "qual o custo médio de uma run desse fluxo". | Sistema (ao invocar workflow) | `runs` (DB) |

**Regras de relacionamento:**
- Project tem N Sessions, N Generations, N Workflows associados (workflows ficam globais ao workspace mas têm `source_session_id`).
- Session tem N Generations.
- Run tem N Generations (cada step = 1 Generation).
- Generation tem 1+ Assets (modelos como Nano Banana podem retornar `n=4`).
- Asset pode ter `parent_asset_id` (upscale de uma imagem, vídeo a partir de imagem).

---

## Arquitetura Física

### Estrutura do repositório (`davidbenal/studiolocal`)

Clonado em `~/Desktop/David-OS/modules/studiolocal/`. Skills symlinkadas para `~/.claude/skills/studio-*`.

```
studiolocal/
├── README.md
├── pyproject.toml                  # deps: fal-client, click, pyyaml, sqlite-utils, rich
├── models.yaml                     # catálogo extensível
│
├── .claude/skills/                 # operacionais (symlinkadas em ~/.claude/skills/)
│   ├── studiolocal-install/SKILL.md
│   ├── studio-project/SKILL.md
│   ├── studio-image/SKILL.md
│   ├── studio-video/SKILL.md
│   ├── studio-upscale/SKILL.md
│   ├── studio-promote/SKILL.md
│   ├── studio-discard/SKILL.md
│   ├── studio-workflow/SKILL.md
│   ├── studio-run/SKILL.md
│   ├── studio-cleanup/SKILL.md
│   ├── studio-report/SKILL.md
│   └── studio-status/SKILL.md
│
├── lib/                            # Python core
│   ├── cli.py                      # `studiolocal <subcommand>`
│   ├── env_loader.py               # cascata de credenciais
│   ├── workspace_detector.py       # embedded vs standalone
│   ├── fal_client.py               # wrapper Fal.ai
│   ├── tracker.py                  # SQLite CRUD + queries report
│   ├── workflow_runner.py          # parser + executor YAML
│   ├── models_registry.py          # carrega models.yaml, valida params
│   ├── report_generator.py         # SQL → markdown
│   ├── cleanup_engine.py           # determinístico (safe vs review)
│   ├── session_manager.py          # auto-open/close 60min
│   ├── asset_store.py              # filesystem (drafts/library/_tmp)
│   └── prompts/
│       └── workflow_extraction.md  # template p/ Claude transcrever trace
│
├── templates/
│   ├── BRIEF.md.tmpl
│   ├── workflow.yaml.tmpl
│   ├── project_README.md.tmpl
│   └── env.tmpl
│
├── migrations/
│   ├── 001_initial.sql
│   └── 002_indexes.sql
│
├── scripts/
│   ├── install.sh                  # via curl|bash → instala bootstrap skill global
│   ├── bootstrap-skill.md          # conteúdo de ~/.claude/skills/studiolocal-bootstrap/SKILL.md
│   ├── symlink-skills.sh           # cria links em ~/.claude/skills/studio-*
│   └── doctor.sh                   # diag (FAL_KEY, db, perms, fal connectivity)
│
└── tests/
    ├── test_workspace_detector.py
    ├── test_workflow_runner.py
    └── fixtures/
```

### Estrutura local em cada workspace (`$workspace/.studiolocal/`)

```
$workspace/.studiolocal/
├── tracker.db                      # SQLite — fonte de verdade
├── .env                            # APENAS modo standalone
├── config.yaml                     # mode, default_models, idle_timeout_min, budget_alerts
│
├── projects/
│   ├── petrobras-tanque/
│   │   ├── BRIEF.md                # opcional
│   │   ├── README.md               # auto-gerado: tags, budget, status
│   │   ├── drafts/                 # status=draft
│   │   │   └── 2026-05-06_hero/
│   │   │       ├── 01.png
│   │   │       └── _meta.json
│   │   ├── library/                # status=library
│   │   └── _tmp/                   # discarded/, downloads parciais
│   └── ...
│
├── workflows/                      # YAMLs salvos
│   ├── hero-fashion-light.yaml
│   └── product-shot-orbit.yaml
│
├── _tmp/                           # workspace-level scratch
├── archive/                        # projects archived
└── logs/
    ├── fal-calls.jsonl
    └── cleanup-history.jsonl
```

---

## Catálogo de Skills

| Skill | Propósito | Trigger conversacional |
|---|---|---|
| `/studiolocal-bootstrap` | Instalador global. Vive em `~/.claude/skills/`. Não invocada pelo user — instalada via `curl\|bash`. | — |
| `/studiolocal-install` | Setup do workspace atual. Detecta embedded/standalone, cria `.studiolocal/`, edita `CLAUDE.md` (idempotente, fenced). | "instala o StudioLocal aqui" |
| `/studio-project` | CRUD de projects (create/list/archive/open). | "novo project Petrobras Tanque, tag client:petrobras, budget 5000" |
| `/studio-image` | Gera imagem (Nano Banana 2/Pro). | "gera 4 hero shots de garrafa de gin sobre mármore" |
| `/studio-video` | Gera vídeo (Kling 3 / Seedance 2). | "anima essa imagem com câmera orbitando, 5s" |
| `/studio-upscale` | Upscale via Clarity. | "upscale na imagem 03 em 4x" |
| `/studio-promote` | `draft` → `library`. | "promove a 03" |
| `/studio-discard` | `draft` → `discarded`. | "descarta as 1, 2 e 4" |
| `/studio-workflow` | Salva trace recente como YAML / lista / edita. | "salva esse processo como Hero Fashion Light" |
| `/studio-run` | Invoca workflow salvo. | "roda hero fashion light com prompt X no project atual" |
| `/studio-cleanup` | Limpeza com revisão. Flag `--safe` para auto-end-session. | "/studio-cleanup" |
| `/studio-report` | Custos, histórico, library. Filtros por tag, projeto, modelo, mês. | "quanto gastei em maio com Petrobras?" |
| `/studio-status` | Estado atual: project ativo, session, custos do mês, budget. | "como estamos?" |

---

## Schema SQLite (resumo)

```sql
projects     (id, slug, name, status, tags JSON, budget_brl, created_at, archived_at)
briefs       (id, project_id FK, path, updated_at)
sessions     (id, project_id FK, opened_at, closed_at, last_activity_at, notes)
workflows    (id, slug, name, yaml_path, source_session_id FK, created_at, description)
runs         (id, workflow_id FK, project_id FK, session_id FK, inputs JSON, status, started_at, finished_at, cost_brl)
generations  (id, project_id FK, session_id FK, run_id FK?, step_index?, model, kind, prompt, params JSON, status, cost_brl, fal_request_id, error, created_at, finished_at)
assets       (id, generation_id FK, project_id FK, parent_asset_id FK?, kind, file_path, status, width, height, duration_s, bytes, promoted_at, discarded_at, created_at)
```

Indexes em: `(project_id, created_at)`, `model`, `session_id`, `(status, project_id)`, `parent_asset_id`, `(workflow_id, started_at)`, `closed_at WHERE NULL`, `status`.

**Queries críticas suportadas (todas em `lib/report_generator.py`):**
- Custo por projeto/mês/modelo/tag/período
- Library de assets aprovados de um project
- Histórico de runs por workflow
- Sessions abandonadas (auto-close)
- Budget consumption por project

---

## Schema YAML de Workflow

```yaml
schema: studiolocal/workflow/v1
slug: hero-fashion-light
name: Hero Fashion Light
description: 4 candidatos → pick humano → upscale 4x → vídeo orbit 5s
created_from_session: 142

inputs:
  prompt: { type: string, required: true }
  reference_image: { type: file, required: false }

steps:
  - id: candidates
    kind: image
    model: nano-banana-pro
    params:
      prompt: "{{ inputs.prompt }}, cinematic lighting, editorial fashion, 4k"
      num_outputs: 4
      aspect_ratio: "3:4"
      reference: "{{ inputs.reference_image }}"
    outputs: { assets: candidates.assets }

  - id: pick
    kind: human_pick                       # pausa Run, retorna controle ao Claude
    prompt_to_user: "Escolha 1 dos 4 (1-4)"
    from: "{{ steps.candidates.assets }}"
    outputs: { selected: pick.selected }

  - id: upscale
    kind: upscale
    model: clarity
    params:
      input_asset: "{{ steps.pick.selected }}"
      scale: 4
    outputs: { asset: upscale.asset }

  - id: animate
    kind: video
    model: seedance-2
    params:
      input_image: "{{ steps.upscale.asset }}"
      prompt: "slow orbit camera, subtle parallax"
      duration_s: 5
    outputs: { asset: animate.asset }

finalize:
  promote_to_library:
    - "{{ steps.upscale.asset }}"
    - "{{ steps.animate.asset }}"
```

**Convenções:**
- Únicas interpolações: `{{ inputs.X }}` e `{{ steps.<id>.<output> }}`. Sem branching/condicionais — composição complexa = Claude orquestrando vários workflows em sequência conversacionalmente.
- `kind: human_pick` é o ÚNICO step pausável. Runner persiste estado e retorna controle. User responde → `studio-run --resume <run_id> --selected N`.
- `finalize.promote_to_library` move automaticamente outputs finais para `library/`.

---

## Catálogo de Modelos (`models.yaml`)

| Modelo | Tipo | Fal Endpoint | Notas |
|---|---|---|---|
| `nano-banana-2` | image | `fal-ai/gemini-flash-image` | Rápido, barato. Exploração e mood. |
| `nano-banana-pro` | image | `fal-ai/gemini-flash-image-pro` | Hero shots, editorial, fidelidade alta. |
| `kling-3` | video | `fal-ai/kling-video/v3/pro/text-to-video` | Vídeo prêmio. Caro. |
| `seedance-2` | video | `fal-ai/seedance/v2` | Equilíbrio custo/qualidade. Default p/ image-to-video. |
| `clarity` | upscale | `fal-ai/clarity-upscaler` | Upscale photoreal. Não inventa detalhes. |

**Defaults:** `image: nano-banana-pro`, `video: seedance-2`, `upscale: clarity`.

**Custos em BRL** definidos em `models.yaml` como **placeholders calibráveis** — V1 lê preços hardcoded (estimativa baseada em Fal.ai pricing × cotação USD-BRL). Atualização manual periódica via PR no repo. V2 considera puxar pricing API se Fal expor.

**Budget alerts:** `warn_at_pct: 80`, `block_at_pct: 100` (no 100% pede confirmação extra antes de aceitar nova Generation pesada, não bloqueia).

---

## Detecção embedded vs standalone

```python
def detect(pwd: Path) -> WorkspaceContext:
    signals = {
        "envmk":     (pwd / ".envmk").exists(),
        "claude_md": (pwd / "CLAUDE.md").exists(),
        "env":       (pwd / ".env").exists(),
    }
    if any(signals.values()):
        return WorkspaceContext(
            mode="embedded",
            workspace_root=pwd,
            studiolocal_root=pwd / ".studiolocal",
            credential_strategy="inherit",
            env_files_priority=[
                pwd / ".envmk",                              # 1º
                pwd / ".env",                                # 2º
                Path.home() / ".studiolocal" / ".env",       # fallback global
            ],
        )
    return WorkspaceContext(
        mode="standalone",
        workspace_root=pwd,
        studiolocal_root=pwd / ".studiolocal",
        credential_strategy="own",
        env_files_priority=[pwd / ".studiolocal" / ".env"],
    )
```

**Regras:**
- Embedded: NÃO cria `.studiolocal/.env`. Confia no parent.
- Standalone: cria `.studiolocal/.env` a partir de `templates/env.tmpl` com `FAL_KEY=` placeholder.
- `tracker.db` SEMPRE em `$workspace/.studiolocal/tracker.db`, independente do modo.

**Edição idempotente do CLAUDE.md** (respeita "manual edits are sacred"):

```markdown
<!-- studiolocal:start -->
## StudioLocal

Geração de imagem/vídeo via Fal.ai. Skills: /studio-{project,image,video,upscale,promote,workflow,run,cleanup,report,status}.
Tracker em `.studiolocal/tracker.db`. Modo: embedded (FAL_KEY herdado de .envmk).
<!-- studiolocal:end -->
```

Re-instalação detecta os marcadores e SUBSTITUI apenas o bloco entre eles.

---

## Cleanup — regras determinísticas

| Categoria | Critério | Idade mín. | `--safe` (auto end-session) | Review (manual) |
|---|---|---|---|---|
| `_tmp/` files | qualquer arquivo em `_tmp/` ou `projects/*/\_tmp/` | 0 | **remove** | remove |
| Failed generations | `generations.status='failed'` + arquivos órfãos | 0 | **remove arquivos**, mantém row (debug) | remove tudo |
| Drafts não promovidos | `assets.status='draft'` | >30 dias | preserva | candidato |
| Discarded | `assets.status='discarded'` | >7 dias | preserva | candidato |
| Sessions abandonadas | `closed_at IS NULL AND last_activity_at < now()-60min` | — | **fecha** (não deleta) | fecha |
| Workflows não usados | sem `runs` em 90d | >90d | preserva | flag p/ review (nunca auto-delete) |
| Library assets | `status='library'` | nunca | **NUNCA toca** | **NUNCA toca** |

**Hook ao `/end-session` do workspace pai (mK):** o auto-load no `CLAUDE.md` registra que o `/end-session` deve, antes do commit, executar `studiolocal cleanup --safe --quiet`. Se houver drafts >30d, exibe aviso não-bloqueante: "47 drafts antigos. Rode `/studio-cleanup` quando puder." Cleanup history → `logs/cleanup-history.jsonl`.

---

## UX conversacional — fluxos críticos (PT-BR)

### Instalação em mK
```
User: /studiolocal-install

Claude: Detectei .envmk com FAL_KEY → modo embedded.
        Vou criar .studiolocal/ aqui em ~/Desktop/Ops/metakomos/
        e adicionar bloco <!-- studiolocal --> no CLAUDE.md. Pode?

User: pode

Claude: ✓ tracker.db criado, schema v1 aplicado
        ✓ pastas projects/, workflows/, _tmp/, archive/ criadas
        ✓ CLAUDE.md atualizado (idempotente)
        ✓ 12 skills /studio-* disponíveis
        Pronto. Quer criar o primeiro project?
```

### Multi-step manual → discovery → save workflow
```
User: novo project hero fashion q2, tag campaign:q2
Claude: Project hero-fashion-q2 criado. Ativo.

User: gera 4 hero shots de modelo feminina, terno bege oversized,
      fundo concreto cinza, luz lateral hard, 3:4
Claude: nano-banana-pro × 4, 3:4. Confirma? (~R$ 1,28)
User: vai
Claude: ✓ 4 imgs em drafts/2026-05-06_hero/ — R$ 1,28

User: a 03 ficou. upscale 4x
Claude: Clarity 4x na asset 03. R$ 0,15. Vai.
        ✓ drafts/.../03_4x.png

User: agora anima essa, câmera orbitando devagar, 5s
Claude: Seedance 2, image-to-video, 5s. R$ 1,80.
User: vai
Claude: ✓ drafts/.../03_4x_orbit.mp4 — total session R$ 3,23

User: esse processo eu vou repetir muito. dá pra salvar?
Claude: Sim. Vou ler as últimas 4 generations e transcrever em YAML. Nome?
User: hero fashion light
Claude: ✓ workflows/hero-fashion-light.yaml com 4 steps:
        candidates (nano-banana-pro × 4) → pick → upscale → animate.
        Inputs: prompt (req), reference_image (opt). Quer revisar?
User: tá bom, salva
Claude: ✓ Workflow registrado. Use /studio-run hero-fashion-light.
```

### Re-rodar workflow novo project
```
User: novo project petrobras tanque, client:petrobras, budget 5000.
      roda hero fashion light, prompt "garrafa de gin sobre mármore preto, luz lateral"
Claude: ✓ project criado. Run iniciada.
        Step 1/4 (candidates): R$ 1,28 ✓
        Step 2/4 (pick): escolha 1-4
User: 2
Claude: Step 3/4 (upscale): R$ 0,15 ✓
        Step 4/4 (animate): R$ 1,80 ✓
        Run done. R$ 3,23. 2 assets na library.
```

### Relatório
```
User: quanto gastei em maio com Petrobras?
Claude: [tabela]
        Maio 2026 — client:petrobras
        Total: R$ 142,40 | 38 generations (32 done, 6 failed)
        Por modelo: nano-banana-pro R$ 7,68 | seedance-2 R$ 10,80 | clarity R$ 1,80 | kling-3 R$ 4,80
        Por project: petrobras-tanque R$ 142,40
        Budget: R$ 142 / R$ 5000 (2,8%)
        Library: 14 assets
```

### Cleanup
```
User: /studio-cleanup
Claude: [tabela: 47 drafts >30d (2.1GB), 8 failed, 23 _tmp stale (480MB), 3 sessions abandonadas, 12 discarded >7d (380MB)]
        Total: 2.96 GB. Apagar tudo? [s/n/seleciona]
User: s
Claude: ✓ removido. Log em logs/cleanup-history.jsonl.
```

---

## Roadmap

### V1 — MVP funcional
- Repo + bootstrap skill global + `/studiolocal-install`
- 4 modelos core + Clarity, registry extensível via `models.yaml`
- 12 skills `/studio-*`
- SQLite schema + migrations versionadas
- Workflow YAML linear + `human_pick`
- Detecção embedded/standalone
- Cleanup híbrido (manual + auto safe)
- Budget alerts (80% warn, 100% confirma)
- Tracking completo (custo por gen/run/project/tag/modelo/período)

### V2 — Produtividade
- Batch generation (`/studio-image --batch prompts.txt`)
- Retry policies configuráveis
- Prompt enhancement via LLM (PT-BR → EN otimizado)
- Parallel execution dentro de Run
- Reference library cross-project
- Workflow versionamento (`hero-fashion-light@v2`)
- `/studio-compare` (side-by-side de N assets)
- Webhooks Fal.ai (long-running sem block)

### V3 — Escala / multi-user
- Sync opcional → Airtable (mirror read-only)
- Multi-user no mesmo workspace (owner em assets)
- Eventual SaaS `studiolocal.cloud`
- Marketplace de workflows (publish/install)
- Integração Figma MCP (asset → frame direto)
- Cost forecasting (ML em cima do histórico)

---

## Critical Files (paths absolutos)

- `~/Desktop/David-OS/modules/studiolocal/lib/workflow_runner.py` — coração do executor; parsing YAML, interpolação, gestão de `human_pick` pausável, persistência de Run state.
- `~/Desktop/David-OS/modules/studiolocal/lib/tracker.py` — SQLite wrapper; toda escrita passa por aqui (idempotência, transações, queries de report).
- `~/Desktop/David-OS/modules/studiolocal/lib/fal_client.py` — wrapper Fal.ai; retries, mapeamento `models.yaml` → endpoint, captura de custo + request_id.
- `~/Desktop/David-OS/modules/studiolocal/lib/workspace_detector.py` — embedded vs standalone; ponto crítico pra UX de instalação.
- `~/Desktop/David-OS/modules/studiolocal/.claude/skills/studiolocal-install/SKILL.md` — orquestra clone + symlinks + detect + migrations + edição CLAUDE.md (fenced markers).
- `~/Desktop/David-OS/modules/studiolocal/migrations/001_initial.sql` — schema fundamental; mudanças = migration nova.
- `~/Desktop/David-OS/modules/studiolocal/models.yaml` — catálogo extensível.
- `~/Desktop/David-OS/modules/studiolocal/scripts/install.sh` — bootstrap via `curl|bash`; instala skill global `studiolocal-bootstrap`.

---

## Verificação end-to-end

Após implementar, validar:

1. **Bootstrap inicial** (máquina nova):
   ```
   curl -fsSL https://raw.githubusercontent.com/davidbenal/studiolocal/main/scripts/install.sh | bash
   # confirma: ~/.claude/skills/studiolocal-bootstrap/SKILL.md existe
   ```

2. **Install em workspace mK** (embedded):
   ```
   cd ~/Desktop/Ops/metakomos && claude
   > /studiolocal-install
   # confirma: .studiolocal/{tracker.db,projects/,workflows/} existe
   # confirma: CLAUDE.md tem bloco <!-- studiolocal:start --> ... <!-- studiolocal:end -->
   # confirma: detecta modo embedded, FAL_KEY herdado
   ```

3. **Install standalone** (em pasta nova):
   ```
   mkdir /tmp/teste-standalone && cd /tmp/teste-standalone && claude
   > /studiolocal-install
   # confirma: cria .studiolocal/.env com FAL_KEY= (placeholder)
   ```

4. **Geração + tracking**:
   ```
   > /studio-project novo "Teste V1", tag test
   > /studio-image "logo simples sobre fundo branco"
   # confirma: 1 row em generations, 1 em assets, arquivo em projects/teste-v1/drafts/
   > /studio-status
   # confirma: project ativo, custo session correto
   ```

5. **Workflow discovery + replay**:
   ```
   # após sequência de 3-4 generations
   > /studio-workflow salva como "Teste"
   # confirma: workflows/teste.yaml criado, validar contra schema
   > /studio-run teste com prompt "X"
   # confirma: nova Run, N Generations, status=done
   ```

6. **Report**:
   ```
   > /studio-report --month $(date +%Y-%m)
   # confirma: tabela markdown com totais corretos cruzando models, projects, tags
   ```

7. **Cleanup**:
   ```
   > /studio-cleanup
   # confirma: lista candidatos, idade mínima respeitada
   > /studio-cleanup --safe
   # confirma: só remove _tmp/ e failed
   ```

8. **Migração de schema** (V1.1):
   ```
   # adicionar migrations/003_X.sql, rodar
   studiolocal db migrate
   # confirma: aplicado idempotente, sem perder dados
   ```

9. **Doctor**:
   ```
   bash ~/Desktop/David-OS/modules/studiolocal/scripts/doctor.sh
   # confirma: FAL_KEY presente, fal connectivity ok, db schema atual, perms ok
   ```

---

## Riscos e questões em aberto

1. **Preços calibrados manualmente**: `models.yaml` tem custos hardcoded em BRL. Se Fal mudar pricing ou cotação variar muito, reports ficam imprecisos. Mitigação V1: doctor checa idade do `models.yaml` e avisa se >30d. Refinar em V2.

2. **`human_pick` em Runs longas**: usuário pode "abandonar" no meio do pick. Runner precisa fazer expire de Runs paradas (>24h?). Decisão pendente.

3. **Migração de Workflow schema**: se YAML schema evoluir (V1 → V2), workflows antigos quebram. V2 deve embutir `schema:` (já presente) e ter migrador.

4. **Conflito de slug** entre projects/workflows de workspaces diferentes: cada `tracker.db` é local, então não há colisão. Mas se V3 sincronizar pra cloud, precisa namespacing.

5. **Tamanho do `.studiolocal/`**: assets de vídeo ocupam muito espaço. Cleanup ajuda, mas não há quota nem alerta de disco. Adicionar em V2 (`/studio-status` mostra GB usado, alerta acima de threshold).

6. **Hook ao `/end-session` do mK**: o `/end-session` atual do workspace mK é uma skill própria do David. A integração deve adicionar 1 linha no `CLAUDE.md` (no bloco fenced) instruindo "antes de commit, rodar `studiolocal cleanup --safe`". Não modifica a skill `/end-session` em si.

7. **Idioma das skills**: instructions em PT-BR (alinhado a David). Mas params/keys YAML em EN (padrão internacional). Definido. Validar com user antes de implementar.
