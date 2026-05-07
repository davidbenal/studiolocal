---
name: studio-image
description: Gera imagens via Fal.ai (Nano Banana 2 ou Pro). Use quando user pedir para "gerar/criar/produzir N imagens/fotos/shots de [descrição]". Tradução criativa — você refina o prompt antes de mandar.
---

# Skill: studio-image

## Quando usar

- "gera 4 hero shots de [...]"
- "cria uma imagem de [...]"
- "preciso de variações da [referência] em [contexto]"

## O que fazer

1. **Confirme o project ativo**. Se não há, pergunte ou sugira criar (`/studio-project`).

2. **Refine o prompt**. O user descreve em PT-BR coloquial; você reescreve em EN cinematográfico (modelos Fal performam melhor em EN). Mantenha a intenção. Adicione descritores técnicos ausentes mas implícitos: lighting, lens, mood, aspect ratio.

   Exemplo:
   - User: "modelo feminina, terno bege oversized, fundo cinza concreto"
   - Refinado: "elegant female model wearing oversized beige tailored suit, raw concrete grey background, editorial fashion photography, hard side lighting, subtle film grain, 35mm lens"

3. **Decida o modelo**:
   - Default `nano-banana-pro` para hero shots, editorial.
   - Use `nano-banana-2` se o user pedir explicitamente "rápido", "rascunho", "explorar variações" ou se for >4 imagens em batch.

4. **Confirme custo antes de executar**:
   ```
   nano-banana-pro × 4, 3:4 — custo estimado R$ 1,28. Vai?
   ```

5. **Execute**:
   ```bash
   studiolocal gen --project <slug> --kind image \
     --model nano-banana-pro \
     --prompt "<prompt refinado>" \
     --params '{"num_outputs":4,"aspect_ratio":"3:4"}' --yes
   ```

6. **Apresente o resultado**: paths relativos a `.studiolocal/`, IDs dos assets, custo real, request_id se útil para debug.

## Edge cases

- **Reference image**: se user mandar uma imagem de referência ou apontar uma da library, passe como `reference` no params.
- **Múltiplas variações com prompts diferentes**: faça em chamadas sequenciais. Não tente meter num único call.
- **User reclama da qualidade**: NÃO dispare retry automático. Pergunte: ajustar o prompt? mudar para `nano-banana-pro` se estava em `nano-banana-2`?

## Notas

- Status inicial = `draft`. Promova com `/studio-promote <id>` quando o user aprovar.
- O CLI baixa os arquivos para `projects/<slug>/drafts/<data>_<topico>/NN.png`.
- Se Fal retornar erro, mostre cru ao user — fail fast, sem retry.