#!/usr/bin/env bash
# C1 DIRECT su HAI 21.03 sulla MI300X (DISEGNO-ZEROSHOT-HAI2103.congelato-*.md).  Porta estesa con gli sha del documento,
# poi fumo (2 righe, controllo meccanico), il multicanale (38 righe) e la scansione a un canale (608 righe).
# La LETTURA non si fa qui.
set -Euo pipefail
B=/root/hack
C=$B/c1
eco() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
DOC=$(ls $B/tools/DISEGNO-ZEROSHOT-HAI2103.congelato-*.md | head -1)
SHA_DOC=$(sha256sum "$DOC" | cut -c1-16)
DOCB=$(basename "$DOC")
mkdir -p $C/docs $C/out $C/datasets/hai
cp -n "$DOC" $C/docs/
cp -n $B/dati/hai/* $C/datasets/hai/ 2>/dev/null || true
cp -n $B/tools/porta_hai.py $C/ 2>/dev/null || true
grep -q '^\*\*Stato:\*\* CONGELATO' "$DOC" || { eco "RIFIUTO: documento non congelato"; exit 72; }
v=$(sha256sum $C/runs/r2e/checkpoints/step_000000004488/model.safetensors | cut -c1-16)
[ "$v" = c38547ae07e75072 ] || { eco "RIFIUTO: checkpoint $v"; exit 72; }
[ "$(sha256sum $C/code_metropt3/configs/metropt3_c1_mi300x.toml | cut -c1-8)" = 9b4a621a ] || { eco "RIFIUTO: config"; exit 75; }
declare -A ATTESO=([src/wavelet_rope/model.py]=e550d6df [src/wavelet_rope/testa_loc.py]=59115a71 [training/validate.py]=03c16485)
for f in "${!ATTESO[@]}"; do
  a=$(sha256sum $C/code_metropt3/$f | cut -c1-8); [ "$a" = "${ATTESO[$f]}" ] || { eco "RIFIUTO: $f $a"; exit 75; }
done
declare -A RIGHE=([fumo]=2 [mc]=38 [loc]=608)
ARGS=()
for X in fumo mc loc; do
  s=$(sha256sum $C/datasets/hai/hai_$X.parquet | cut -d' ' -f1)
  grep -q "$s" "$DOC" || { eco "RIFIUTO: sha di hai_$X non e' quello del documento"; exit 72; }
  ARGS+=("hai_$X:${RIGHE[$X]}:$s")
done
grep -q '"hai_mc"' $C/code_metropt3/src/wavelet_rope/conferma.py || docker exec -w /c1 wrope python porta_hai.py /c1/code_metropt3 "${ARGS[@]}"
for X in fumo mc loc; do
  D=/c1/out/lotto_hai_$X
  if [ -e "$C/out/lotto_hai_$X/COMPLETO" ]; then eco "$X: gia' completo, salto"; continue; fi
  [ -e "$C/out/lotto_hai_$X/c1_direct.json" ] && { eco "RIFIUTO: $D/c1_direct.json esiste gia'"; exit 70; }
  mkdir -p "$C/out/lotto_hai_$X"
  XX=$(echo "$X" | tr a-z A-Z)
  RUN="hai-$X-c1-direct"
  eco "$X: avvio validate.py ($RUN)"
  docker exec -w /c1/code_metropt3 \
    -e PYTHONPATH=/c1/code_metropt3/src -e WR_VA1_CHECKPOINT=/c1/va1/epoch_5_end.pt \
    -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e FLA_TILELANG=0 \
    -e WR_SPLIT_CONFERMA="hai_$X" -e "WR_HAI_${XX}_PARQUET=/c1/datasets/hai/hai_$X.parquet" \
    -e WR_DOCUMENTO_CONGELATO=/c1/docs/$DOCB -e WR_SHA_DOCUMENTO=$SHA_DOC \
    -e WR_REGISTRO_LETTURE="$D/REGISTRO_LETTURE.jsonl" \
    wrope python training/validate.py --config configs/metropt3_c1_mi300x.toml --run-id "$RUN" \
      --checkpoint /c1/runs/r2e/checkpoints/step_000000004488 --tag lotto > "$C/logs/validate_hai_$X.log" 2>&1 \
    || { eco "$X: FALLITO (vedi c1/logs/validate_hai_$X.log)"; tail -20 "$C/logs/validate_hai_$X.log"; exit 1; }
  DUMP=$(ls -t $C/runs/$RUN/logs/val_lotto_*.json 2>/dev/null | head -1)
  [ -n "$DUMP" ] || { eco "$X: FALLITO (nessun dump)"; exit 1; }
  cp -n "$DUMP" "$C/out/lotto_hai_$X/c1_direct.json"
  if [ "$X" = fumo ]; then
    python3 -c "
import json
r = json.load(open('$C/out/lotto_hai_fumo/c1_direct.json'))['records']
assert len(r) == 2 and sorted(x['category'] for x in r) == ['localize', 'localize_all_channels'] and all('pred' in x for x in r), 'forma'
print('fumo: forma del dump OK;', [x['pred'][:90] for x in r])
" || { eco "FUMO NON SUPERATO"; exit 1; }
  fi
  ( cd "$C/out/lotto_hai_$X" && sha256sum c1_direct.json REGISTRO_LETTURE.jsonl > SHA256SUMS.txt && touch COMPLETO )
  eco "$X: OK"
done
eco "HAI COMPLETO"
