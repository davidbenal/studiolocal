---
name: studio-cleanup
description: Remove resíduos do .studiolocal/ — drafts antigos, failed generations, _tmp/ stale, sessions abandonadas. Modo padrão pede revisão; flag --safe (auto end-session) só remove _tmp/ e failed. Use quando user disser "/studio-cleanup", "limpa", "faz uma limpeza", ou ao /end-session do workspace pai.
---

# Skill: studio-cleanup

## Quando usar

- "/studio-cleanup"
- "faz uma limpeza"
- "limpa drafts antigos"
- Hook ao `/end-session` do workspace pai (mK, etc): rodar `--safe`.

## Modos

### Manual (review)

Default. Lista candidatos com motivo + tamanho, pede confirmação batch.

```bash
studiolocal cleanup
```

Apresente a tabela ao user (já vem formatada). Pergunte: "Apagar tudo? [s/n]". NÃO assuma — espere resposta.

### Safe (auto end-session)

Acionado pelo `/end-session` do workspace pai. Só remove:
- `_tmp/` files
- Failed generations (arquivos órfãos, mantém row no DB para debug)
- Fecha sessions inativas há >60min (não deleta dados)

```bash
studiolocal cleanup --safe --quiet
```

Não pergunta nada. Não toca em drafts. Loga em `logs/cleanup-history.jsonl`.

## O que fazer

1. **Pergunte qual modo** se ambíguo. "Cleanup completo (review) ou apenas o seguro (--safe)?"
2. **Execute** com flag apropriada.
3. **Reporte** ao final: total removido + categorias.
4. **Avise sobre drafts** se houver muitos (>20 com idade >30d):
   "Tem 47 drafts antigos não promovidos. Quer revisar com `/studio-cleanup` (modo review) quando puder?"

## Notas

- Library NUNCA é tocada. Se você for tentado a oferecer "limpa library", recuse — isso é trabalho manual deliberado.
- Cleanup history em `logs/cleanup-history.jsonl` permite auditoria reversa.