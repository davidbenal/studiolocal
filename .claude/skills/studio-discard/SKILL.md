---
name: studio-discard
description: Descarta asset(s) draft — move para _tmp/discarded/, atualiza status. Use quando user disser "descarta [N]", "joga fora a [N]", "essas não", "deleta a [N]".
---

# Skill: studio-discard

## Quando usar
- "descarta a 02"
- "as 1, 2, 4 não me servem"
- "essa eu não quero"

## O que fazer

1. Mapeie IDs. Múltiplos é comum.
2. Execute: `studiolocal discard <id>` para cada um.
3. Confirme ao user: "✓ N assets descartados".

## Notas

- Discard é soft delete: arquivo vai para `_tmp/discarded/`, registro fica com `status='discarded'`. Cleanup remove definitivamente após 7 dias.
- Para reverter, mova manualmente o arquivo de volta e rode SQL para mudar status. Operação rara.