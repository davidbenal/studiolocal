---
name: studio-status
description: Mostra estado atual do StudioLocal — project ativo, session aberta, custos do mês, calibração dos preços. Use quando user perguntar "como estamos", "status", "/studio-status", "onde paramos", "qual project tá ativo".
---

# Skill: studio-status

## Quando usar

- "como estamos?"
- "/studio-status"
- "qual project tá ativo?"
- "quanto gastamos esse mês?"

## O que fazer

```bash
studiolocal status
```

Apresente o output. Adicione 1 linha de contexto se houver sinal:
- Sem project ativo + tem projects → "Quer abrir um project ou criar novo?"
- Session aberta há muito tempo → "Sua session tá aberta há X horas. Cleanup --safe vai fechar automaticamente quando você der /end-session."
- Calibração `models.yaml` velha (>30d) → "Heads up: cotação Fal foi calibrada há 35d. Custos podem estar drift."

## Notas

- Status é leitura-only. Não faz nenhuma alteração.