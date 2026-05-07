---
name: studio-project
description: CRUD de projects do StudioLocal — criar, listar, arquivar. Use quando user mencionar "novo project", "criar projeto", "lista projects", "arquiva project X", ou ao iniciar trabalho criativo num contexto novo (campanha, cliente, peça).
---

# Skill: studio-project

## Quando usar

- "novo project [nome]" / "cria projeto [nome]"
- "lista projects" / "quais projects ativos"
- "arquiva o project X" / "fecha campanha Y"
- Quando o user inicia trabalho criativo e ainda não há project ativo (você sente que falta contexto).

## O que fazer

### Criar project

1. Extraia do pedido: nome, tags, budget. Se faltar nome, pergunte. Tags e budget são opcionais.
2. Tags são livres mas use convenção `chave:valor` (ex: `client:petrobras`, `type:production`, `campaign:q2`). Se user disser "petrobras", sugira `client:petrobras`.
3. Confirme com ele antes de criar:
   ```
   Vou criar:
     nome:   Hero Fashion Q2
     slug:   hero-fashion-q2
     tags:   campaign:q2, type:production
     budget: R$ 5000
   Confirma?
   ```
4. Execute:
   ```bash
   studiolocal project new "Hero Fashion Q2" --tag campaign:q2 --tag type:production --budget 5000
   ```
5. Após criar, ofereça abrir um BRIEF.md ou já partir para gerar.

### Listar

```bash
studiolocal project list             # ativos
studiolocal project list --archived  # arquivados
```

Apresente como tabela (já vem formatada).

### Arquivar

Pergunte antes — arquivar é semi-permanente. "Arquivar `petrobras-tanque`? Os assets na library são preservados; drafts antigos vão pra cleanup quando você rodar `/studio-cleanup`."

Execute: `studiolocal project archive petrobras-tanque`.

## Notas

- O project ativo é o que tem session aberta. Se o user pediu para gerar em outro project, abra session lá implicitamente (não precisa "switch" explícito).
- Slug é gerado automaticamente do nome. Se houver colisão, o CLI falha — pergunte se quer usar variação (`hero-fashion-q2-v2`).
- Budget é apenas guia (warn em 80%, confirma extra em 100%). Não bloqueia.