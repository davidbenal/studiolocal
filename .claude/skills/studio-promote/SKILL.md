---
name: studio-promote
description: Promove um asset draft para library — move arquivo de drafts/ para library/, atualiza status no DB. Use quando user disser "promove a [N]", "salva essa pra library", "essa ficou", "aprova [asset]".
---

# Skill: studio-promote

## Quando usar
- "promove a 03"
- "salva essa pra library"
- "essa eu quero guardar"
- "aprova o clip"

## O que fazer

1. Mapeie o número/descrição → asset_id. Se ambíguo, pergunte ("qual ID? você gerou 03 e 04 hoje").
2. Execute: `studiolocal promote <asset_id>`
3. Mostre o novo path em library/.

## Notas

- Library é a fonte de verdade do que foi aprovado. Cleanup nunca toca em library.
- Promover múltiplos: rode N vezes. Não tem batch no V1.