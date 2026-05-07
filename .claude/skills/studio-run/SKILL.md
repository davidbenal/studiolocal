---
name: studio-run
description: Invoca um Workflow salvo como Run nomeada. Cada step do pipeline gera 1 Generation. Pausa em human_pick e retoma com user input. Use quando user disser "roda [workflow]", "executa hero-fashion-light no project X", "rerun aquele fluxo de [...]".
---

# Skill: studio-run

## Quando usar

- "roda hero fashion light com prompt X"
- "executa workflow Y no project Z"
- "rerun aquela receita de hero shots"

## O que fazer

1. **Identifique o workflow** (slug). Liste se ambíguo: `studiolocal workflow list`.

2. **Confirme o project ativo** ou peça para passar via `--project`.

3. **Colete inputs** descritos pelo workflow YAML. Veja `inputs:` no arquivo. Pergunte cada um:
   ```
   O workflow `hero-fashion-light` precisa:
     - prompt (obrigatório)
     - reference_image (opcional)
   Qual o prompt?
   ```

4. **Execute**:
   ```bash
   studiolocal run hero-fashion-light \
     --project petrobras-tanque \
     --inputs '{"prompt":"garrafa de gin sobre mármore preto, luz lateral hard"}'
   ```

5. **Streaming de progresso**: o CLI mostra cada step concluído. Você relata em PT-BR:
   - "Step 1/4 (candidates): 4 imagens em drafts/... R$ 1,28 ✓"
   - Quando o CLI sinaliza `⏸ Run pausada` em um `human_pick`:
     ```
     ⏸ Run pausada. Escolha 1 dos 4 (asset IDs: [12, 13, 14, 15])
     ```
     Pergunte ao user qual ID. Não tente adivinhar.

6. **Resumir após pick**:
   ```bash
   studiolocal run hero-fashion-light --project petrobras-tanque \
     --resume <run_id> \
     --selected '{"selected": 13}'
   ```
   Continue narrando os steps restantes.

7. **Final**: total da Run, assets promovidos para library, ID da Run.

## Edge cases

- **Run falha no meio**: o CLI marca `status=failed`. Apresente o erro do step ao user. Pergunte se quer reiniciar (re-rodar) — não há resume de falha no V1.
- **Inputs incompletos**: o CLI pode reclamar — leia a mensagem, peça ao user o que faltou.
- **Custo total estimado antes de rodar**: some os `cost_brl_per_call` dos steps. Se ficar caro, avise.

## Notas

- Run é apenas para Workflows. Para single-shot (1 imagem agora), use `/studio-image` direto.
- Toda Run consome a Session ativa do project — não abra session nova.