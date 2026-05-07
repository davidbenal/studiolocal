---
name: studio-workflow
description: Salva o trace recente de generations como Workflow YAML reutilizável. Discovery-driven — só ativada quando user identifica que o processo executado é repetível. Use quando user disser "salva esse processo", "transforma isso num workflow", "vou repetir muito".
---

# Skill: studio-workflow

## Quando usar

- "salva esse processo como workflow"
- "isso eu vou repetir muito, dá pra salvar?"
- "transforma isso num workflow chamado X"
- "lista os workflows que tenho"

## O que fazer ao SALVAR

1. **Confirme com o user** o que vai virar workflow. Mostre o trace recente (últimas 4-8 generations da session ativa) em forma resumida:
   ```
   Identifiquei estes 4 passos na sua session:
     1. nano-banana-pro × 4 (hero shots)
     2. clarity 4x na asset 12
     3. seedance-2 5s a partir da 12 upscalada
   Vou transformar em workflow `hero-fashion-light`. Confirma?
   ```

2. **Refine usando o prompt em `lib/prompts/workflow_extraction.md`**. Sua tarefa:
   - Generalize o prompt: substitua valores específicos por `{{ inputs.X }}`
   - Identifique `human_pick` quando user escolheu manualmente entre N
   - Liste outputs finais em `finalize.promote_to_library`
   - Escolha step ids descritivos (`candidates`, `pick`, `upscale`, `animate`)

3. **Salve o YAML** em `/tmp/<slug>.yaml` primeiro, mostre ao user, deixe ele revisar:
   ```
   workflows/hero-fashion-light.yaml:
   [yaml]
   Quer ajustar antes de salvar?
   ```

4. **Persista** após aprovação:
   ```bash
   studiolocal workflow save \
     --name "Hero Fashion Light" \
     --from-yaml /tmp/hero-fashion-light.yaml \
     --description "4 candidatos → pick → upscale 4x → vídeo orbit 5s"
   ```

5. **Recomende quebra se complexo**. Se o trace tem >6 steps ou mistura conceitos, sugira 2 workflows separados que podem ser encadeados conversacionalmente.

## O que fazer ao LISTAR

```bash
studiolocal workflow list
```

Apresente a tabela como veio.

## Notas

- Workflow ≠ macro. É uma receita de produção repetível com inputs claros.
- Não invente steps que não estão no trace. Se algo crítico ficou implícito (ex: user usou outra ferramenta entre os steps), avise antes de salvar.
- Para invocar workflow salvo: `/studio-run <slug>`.