---
name: studiolocal-install
description: Instala o StudioLocal no workspace atual — detecta modo embedded vs standalone, cria .studiolocal/ com tracker.db, edita CLAUDE.md (idempotente). Use quando o usuário pedir "instala o studiolocal aqui", "/studiolocal-install" ou ao detectar um workspace sem .studiolocal/.
---

# Skill: studiolocal-install

## Quando usar
- Usuário digita `/studiolocal-install` ou pede "instala o StudioLocal".
- Você detectou que o usuário tentou usar `/studio-image` ou similar mas o `.studiolocal/` não existe.

## O que fazer

1. **Detectar modo**: rode `studiolocal install --help` para confirmar que o CLI está acessível. Se não estiver, oriente: o repo precisa estar em `~/Desktop/David-OS/modules/studiolocal/` com `pip install -e .` aplicado.

2. **Anunciar o que vai fazer**, em PT-BR direto:
   - Se há `.envmk` ou `.env` no PWD: "Detectei modo **embedded** (FAL_KEY herdado de `.envmk`/`.env`)."
   - Senão: "Modo **standalone** — vou criar `.studiolocal/.env` que você precisa preencher com FAL_KEY."

3. **Pedir confirmação**: "Vou criar `.studiolocal/` aqui em `<PWD>` e adicionar bloco `<!-- studiolocal -->` no `CLAUDE.md`. Pode?"

4. **Executar**: `studiolocal install`

5. **Mostrar resultado**:
   ```
   ✓ tracker.db criado, schema v2
   ✓ pastas projects/, workflows/, _tmp/, archive/ criadas
   ✓ CLAUDE.md atualizado (idempotente)
   ✓ skills /studio-* disponíveis
   ```

6. **Próximo passo**: pergunte "Quer criar o primeiro project?"
   - Sim → invoque `/studio-project`.
   - Não → fim.

## Notas

- **NUNCA** sobrescreva `.studiolocal/` existente sem flag `--force` explícita.
- O bloco no CLAUDE.md é fenced (`<!-- studiolocal:start -->` ... `<!-- studiolocal:end -->`) — se já existe, é substituído por completo, preservando edições manuais fora do bloco.
- Em modo standalone, lembre o user que precisa preencher `.studiolocal/.env` com `FAL_KEY` antes de gerar.