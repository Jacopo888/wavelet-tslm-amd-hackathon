#!/usr/bin/env bash
# C1 DIRECT su MetroPT-3 pre-processato (A indicatori, B analogici alla AnomalyXL, C indicatori adattati), sulla MI300X
# (DISEGNO-INDICATORI-METROPT3.congelato-*.md).  Porta estesa con gli sha del documento, poi fumo (2 righe, controllo
# meccanico) e i tre insiemi.  La LETTURA non si fa qui.
set -Euo pipefail
B=/root/hack
C=$B/c1
eco() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
DOC=$(ls $B/tools/DISEGNO-INDICATORI-METROPT3.congelato-*.md | head -1)
SHA_DOC=$(sha256sum "$DOC" | cut -c1-16)
DOCB=$(basename "$DOC")
mkdir -p $C/docs $C/out $C/datasets/metropt3/hi
cp -n "$DOC" $C/docs/
cp -n $B/dati/hi/* $C/datasets/metropt3/hi/ 2>/dev/null || true
cp -n $B/tools/porta_insiemi.py $C/ 2>/dev/null || true
grep -q '^\*\*Stato:\*\* CONGELATO' "$DOC" || { eco "RIFIUTO: documento non congelato"; exit 72; }
v=$(sha256sum $C/runs/r2e/checkpoints/step_000000004488/model.safetensors | cut -c1-16)
[ "$v" = c38547ae07e75072 ] || { eco "RIFIUTO: checkpoint $v"; exit 72; }
[ "$(sha256sum $C/code_metropt3/configs/metropt3_c1_mi300x.toml | cut -c1-8)" = 9b4a621a ] || { eco "RIFIUTO: config"; exit 75; }
declare -A ATTESO=([src/wavelet_rope/model.py]=e550d6df [src/wavelet_rope/testa_loc.py]=59115a71 [training/validate.py]=03c16485)
for f in "${!ATTESO[@]}"; do
  a=$(sha256sum $C/code_metropt3/$f | cut -c1-8); [ "$a" = "${ATTESO[$f]}" ] || { eco "RIFIUTO: $f $a"; exit 75; }
done
declare -A RIGHE=([hifumo]=2 [hia]=90 [hib]=105 [hic]=90)
ARGS=()
for X in hifumo hia hib hic; do
  s=$(sha256sum $C/datasets/metropt3/hi/metropt3_$X.parquet | cut -d' ' -f1)
  grep -q "$s" "$DOC" || { eco "RIFIUTO: sha di metropt3_$X non e' quello del documento"; exit 72; }
  ARGS+=("metropt3_$X:${RIGHE[$X]}:$s")
done
grep -q '"metropt3_hia"' $C/code_metropt3/src/wavelet_rope/conferma.py || docker exec -w /c1 wrope python porta_insiemi.py /c1/code_metropt3 "${ARGS[@]}"
for X in hifumo hia hib hic; do
  D=/c1/out/lotto_$X
  if [ -e "$C/out/lotto_$X/COMPLETO" ]; then eco "$X: gia' completo, salto"; continue; fi
  [ -e "$C/out/lotto_$X/c1_direct.json" ] && { eco "RIFIUTO: $D/c1_direct.json esiste gia'"; exit 70; }
  mkdir -p "$C/out/lotto_$X"
  XX=$(echo "$X" | tr a-z A-Z)
  RUN="mp3-$X-c1-direct"
  eco "$X: avvio validate.py ($RUN)"
  docker exec -w /c1/code_metropt3 \
    -e PYTHONPATH=/c1/code_metropt3/src -e WR_VA1_CHECKPOINT=/c1/va1/epoch_5_end.pt \
    -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e FLA_TILELANG=0 \
    -e WR_SPLIT_CONFERMA="metropt3_$X" -e "WR_METROPT3_${XX}_PARQUET=/c1/datasets/metropt3/hi/metropt3_$X.parquet" \
    -e WR_DOCUMENTO_CONGELATO=/c1/docs/$DOCB -e WR_SHA_DOCUMENTO=$SHA_DOC \
    -e WR_REGISTRO_LETTURE="$D/REGISTRO_LETTURE.jsonl" \
    wrope python training/validate.py --config configs/metropt3_c1_mi300x.toml --run-id "$RUN" \
      --checkpoint /c1/runs/r2e/checkpoints/step_000000004488 --tag lotto > "$C/logs/validate_$X.log" 2>&1 \
    || { eco "$X: FALLITO (vedi c1/logs/validate_$X.log)"; tail -20 "$C/logs/validate_$X.log"; exit 1; }
  DUMP=$(ls -t $C/runs/$RUN/logs/val_lotto_*.json 2>/dev/null | head -1)
  [ -n "$DUMP" ] || { eco "$X: FALLITO (nessun dump)"; exit 1; }
  cp -n "$DUMP" "$C/out/lotto_$X/c1_direct.json"
  if [ "$X" = hifumo ]; then
    python3 -c "
import json
r = json.load(open('$C/out/lotto_hifumo/c1_direct.json'))['records']
assert len(r) == 2 and all(x['category'] == 'localize' and 'pred' in x for x in r), 'forma'
print('fumo: forma del dump OK;', [x['pred'][:90] for x in r])
" || { eco "FUMO NON SUPERATO"; exit 1; }
  fi
  ( cd "$C/out/lotto_$X" && sha256sum c1_direct.json REGISTRO_LETTURE.jsonl > SHA256SUMS.txt && touch COMPLETO )
  eco "$X: OK"
done
eco "INDICATORI COMPLETO"
