---
name: studio-video
description: Gera vídeos via Fal.ai (Kling 3 ou Seedance 2). Use quando user pedir para "animar [imagem]", "gerar clip de [...]", "vídeo de N segundos com [...]". Suporta image-to-video (a partir de asset existente) ou text-to-video (do zero).
---

# Skill: studio-video

## Quando usar

- "anima essa imagem com câmera orbitando"
- "gera um vídeo de 5s de [descrição]"
- "transforma a 03 em vídeo"

## O que fazer

1. **Project ativo**: confirme.

2. **Image-to-video vs text-to-video**:
   - Se user diz "anima essa", "transforma a [N]", "a partir desta imagem" → **image-to-video**. Pegue o asset_id e passe via `--input-asset`.
   - Se descrição é puramente textual → **text-to-video**.

3. **Modelo default**: `seedance-2` (custo/qualidade). Use `kling-3` se user pedir "máxima qualidade", "premium", ou em produção final.

4. **Refine o prompt em EN cinematográfico**. Foque em movimento da câmera, ritmo, parallax, transições. Adicione duração se ausente (default 5s).

5. **Confirme custo**:
   ```
   seedance-2, 5s, image-to-video — R$ 1,80. Vai?
   ```
   Para `kling-3`, sempre destaque que é caro: "Kling 3 — R$ 2,40 por clip. Confirma?"

6. **Execute**:
   ```bash
   studiolocal gen --project <slug> --kind video \
     --model seedance-2 \
     --input-asset <asset_id> \
     --prompt "slow orbit camera, subtle parallax" \
     --params '{"duration_s":5}' --yes
   ```

7. **Apresente**: path do `.mp4`, custo, ID. Sugira promover se ficou bom.

## Edge cases

- **Sem prompt textual em image-to-video**: alguns modelos exigem. Forneça um genérico se user não disse: "subtle natural motion" ou "static shot with light parallax".
- **Duração maior**: Seedance 3-10s, Kling 5 ou 10s. Valide antes de chamar.
- **Asset de input não é imagem**: aborte e explique.

## Notas

- Vídeo é caro. Confirme sempre, mesmo se user disse "só faz".
- Status inicial `draft`. Library só após promote.