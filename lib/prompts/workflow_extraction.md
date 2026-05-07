# Prompt: extrair Workflow YAML a partir do trace de uma Session

Você está convertendo a sequência de Generations executadas pelo usuário em um Workflow YAML reutilizável do schema `studiolocal/workflow/v1`.

## Entrada

Você receberá:

1. **Trace** — lista ordenada de Generations da Session ativa (id, model, kind, prompt, params, asset_ids gerados, custo, timestamps).
2. **Decisões manuais do usuário** — quando o user escolheu 1 asset entre vários gerados (ex: "a 03 ficou"), isso vira step `human_pick`.
3. **Nome sugerido pelo user** (opcional) — se ausente, proponha 2-3 e pergunte qual prefere.

## Sua tarefa

Gerar um YAML que, ao ser executado via `/studio-run`, replique o processo. Generalize prompts: substitua valores específicos por `{{ inputs.X }}`.

### Identificar inputs parametrizáveis

- O **prompt principal** quase sempre vira `inputs.prompt`. Qualquer texto descritivo único.
- **Reference images** locais viram `inputs.reference_image` (opcional).
- Outros params (`aspect_ratio`, `num_outputs`) **devem permanecer hardcoded** se foram a escolha que deu certo.

### Reconhecer human_pick

Quando o trace mostra:
- 1 Generation com `num_outputs > 1` ou múltiplos assets gerados em paralelo.
- Em seguida, 1 Generation que usou `parent_asset_id` apontando para apenas 1 dos N anteriores.

→ Insira step `kind: human_pick` entre eles, com `from: {{ steps.<id_anterior>.assets }}` e `outputs: { selected: pick.selected }`.

### Inferir finalize.promote_to_library

Olhe quais assets o user **promoveu para library** durante a Session. Esses são os outputs finais. Liste-os em `finalize.promote_to_library` referenciando os steps que os geraram.

## Saída

Apenas o YAML, sem cercas markdown, válido contra o schema:

```yaml
schema: studiolocal/workflow/v1
slug: <kebab-case do nome>
name: <nome legível>
description: <1 linha — o que o workflow faz>
created_from_session: <session_id da entrada>

inputs:
  prompt:
    type: string
    required: true
    description: <breve descrição do que vai aqui>
  # ... outros inputs inferidos

steps:
  - id: <id curto kebab-case>
    kind: <image|video|upscale|human_pick>
    model: <nome do modelo, exatamente como em models.yaml>
    params:
      <params específicos do modelo>
    outputs:
      <chaves usadas pelos próximos steps>

finalize:
  promote_to_library:
    - "{{ steps.<id>.<output> }}"
```

## Boas práticas

- **Step ids**: descritivos e curtos. `candidates`, `pick`, `upscale`, `animate`. Evite `step1`, `step2`.
- **Generalize com cuidado**: se o user usou `aspect_ratio: 3:4` e funcionou bem, mantenha hardcoded. Não tente parametrizar tudo.
- **Recomende quebra**: se o trace tem >6 steps ou mistura conceitos diferentes (ex: gerar hero shot + também variantes de campanha), proponha quebrar em 2 workflows e diga para o user encadeá-los conversacionalmente. Composição complexa = orquestração pelo Claude, não branching no YAML.
- **Custo médio**: ao final, comente o custo médio estimado de uma Run (soma dos custos dos steps).
- **Preserve as refs**: se uma `reference_image` foi usada e veio de `library/`, marque como `inputs.reference_image` opcional. Se veio do disco do user (path absoluto), **avise** que precisa ser passada toda vez como input.
