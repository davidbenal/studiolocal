---
name: studio-upscale
description: Upscale fotorrealista de imagens via Clarity. Use quando user pedir "upscale [N]", "aumenta a resolução de [asset]", "melhora a [imagem] em 4x". Não inventa detalhes — preserva o original em maior resolução.
---

# Skill: studio-upscale

## Quando usar

- "upscale na 03 em 4x"
- "aumenta a resolução dessa imagem"
- "melhora a qualidade da imagem aprovada"

## O que fazer

1. **Identifique o asset**. Por ID (preferido) ou pela descrição ("a aprovada", "a última que gerei").

2. **Escala**: 2x ou 4x. Default 2x. Se user disse "máximo", use 4x.

3. **Confirme custo**: Clarity é R$ 0,15. Direto:
   ```
   Clarity 4x na asset 03. R$ 0,15. Vai.
   ```
   (Confirmação tácita por ser barato — só pergunta se user pediu várias.)

4. **Execute**:
   ```bash
   studiolocal gen --project <slug> --kind upscale \
     --model clarity \
     --input-asset <asset_id> \
     --params '{"scale":4}' --yes
   ```

5. **Apresente**: path do upscale, ID novo (asset com `parent_asset_id` apontando para o original).

## Notas

- Clarity NÃO inventa detalhes — não use para "melhorar uma imagem ruim". Se a base é ruim, gere de novo, não upscale.
- Para vídeo, não há upscale no V1. Se user pedir, explique e sugira gerar com modelo de mais qualidade (Kling 3) na primeira chamada.