---
name: studio-report
description: Gera relatórios de custo a partir do tracker.db — por mês, tag, project, modelo. Use quando user perguntar "quanto gastei", "custo do project X", "relatório de maio", "como estão os custos por modelo".
---

# Skill: studio-report

## Quando usar

- "quanto gastei em maio com Petrobras?"
- "relatório do mês"
- "custo por modelo"
- "como tá o budget do project X?"

## O que fazer

1. **Mapeie a pergunta a filtros**:
   - "maio" / "este mês" → `--month YYYY-MM`
   - "petrobras" / "client X" → `--tag client:petrobras` ou `--project <slug>`
   - "modelo" / "kling" → vai mostrar tabela "por modelo" automática
   - sem filtro → mês atual

2. **Execute**:
   ```bash
   studiolocal report --month 2026-05 --tag client:petrobras
   ```

3. **Apresente o markdown** retornado. Não reformate.

4. **Comente** se houver sinal:
   - Budget consumido: "Você está em 87% do budget do project — atenção."
   - Modelo desproporcional: "70% do gasto foi em `kling-3` esse mês — é a intenção?"
   - Failed generations: "6 generations falharam — quer ver os erros?" (sugira abrir o tracker.db ou logs/fal-calls.jsonl)

## Filtros disponíveis

- `--month YYYY-MM` — período mensal
- `--tag <tag>` — filtra projects que contenham aquela tag
- `--project <slug>` — só aquele project

Combinar é OK: `--month 2026-05 --tag client:petrobras`.

## Notas

- Não há filtros por modelo direto — o report já agrega por modelo. Se user pediu "só Kling", filtre o output mentalmente ao apresentar.
- Para auditoria detalhada (lista de cada Generation), abra o tracker.db diretamente:
  ```bash
  sqlite3 .studiolocal/tracker.db 'SELECT * FROM generations ORDER BY created_at DESC LIMIT 20;'
  ```