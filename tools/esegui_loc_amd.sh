#!/usr/bin/env bash
# C1 DIRECT su MetroPT-3 a un canale alla volta, sulla MI300X (DISEGNO-LOCALIZE-CANALE-METROPT3.congelato-*.md).
#   FASE=righe : costruisce le 161 righe e il fumo nel container, stampa gli sha (prima del congelamento)
#   FASE=lotto : estende la porta con gli sha, poi fumo (2 righe, controllo meccanico) e le 161 righe
# La LETTURA non si fa qui.
set -Euo pipefail
B=/root/hack
C=$B/c1
eco() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
FASE="${FASE:?righe oppure lotto}"
mkdir -p $C/datasets/metropt3 $C/out $C/docs
cp -n $B/dati/metropt3_a7.parquet $C/datasets/metropt3/ 2>/dev/null || true
cp -n $B/tools/costruisci_loc_canale.py $B/tools/porta_loc.py $C/ 2>/dev/null || true
if [ "$FASE" = righe ]; then
  docker exec -w /c1 wrope python costruisci_loc_canale.py --a7 /c1/datasets/metropt3/metropt3_a7.parquet \
    --sha-a7 13bc066618de948e15fa4387750fb2002888128a82b7b2d3671f6a28a070534e \
    --val /c1/datasets/va1_layout/anomalyXL/datasets/anomalyxl-train/anomalyxl-precise/val.parquet \
    --out-dir /c1/datasets/metropt3/loc
  exit $?
fi
DOC=$(ls $B/tools/DISEGNO-LOCALIZE-CANALE-METROPT3.congelato-*.md | head -1)
SHA_DOC=$(sha256sum "$DOC" | cut -c1-16)
cp -n "$DOC" $C/docs/
DOCB=$(basename "$DOC")
grep -q '^\*\*Stato:\*\* CONGELATO' "$DOC" || { eco "RIFIUTO: documento non congelato"; exit 72; }
v=$(sha256sum $C/runs/r2e/checkpoints/step_000000004488/model.safetensors | cut -c1-16)
[ "$v" = c38547ae07e75072 ] || { eco "RIFIUTO: checkpoint $v"; exit 72; }
declare -A ATTESO=([src/wavelet_rope/model.py]=e550d6df [src/wavelet_rope/testa_loc.py]=59115a71 [training/validate.py]=03c16485)
for f in "${!ATTESO[@]}"; do
  a=$(sha256sum $C/code_metropt3/$f | cut -c1-8); [ "$a" = "${ATTESO[$f]}" ] || { eco "RIFIUTO: $f $a"; exit 75; }
done
S_LOC=$(sha256sum $C/datasets/metropt3/loc/metropt3_loc.parquet | cut -d' ' -f1)
S_FUMO=$(sha256sum $C/datasets/metropt3/loc/metropt3_locfumo.parquet | cut -d' ' -f1)
grep -q "$S_LOC" "$DOC" && grep -q "${S_FUMO:0:16}" "$DOC" || { eco "RIFIUTO: gli sha delle righe non sono quelli del documento"; exit 72; }
grep -q metropt3_loc $C/code_metropt3/src/wavelet_rope/conferma.py || docker exec -w /c1 wrope python porta_loc.py /c1/code_metropt3 "$S_LOC" "$S_FUMO"
for X in locfumo loc; do
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
    -e WR_SPLIT_CONFERMA="metropt3_$X" -e "WR_METROPT3_${XX}_PARQUET=/c1/datasets/metropt3/loc/metropt3_$X.parquet" \
    -e WR_DOCUMENTO_CONGELATO=/c1/docs/$DOCB -e WR_SHA_DOCUMENTO=$SHA_DOC \
    -e WR_REGISTRO_LETTURE="$D/REGISTRO_LETTURE.jsonl" \
    wrope python training/validate.py --config configs/metropt3_c1_mi300x.toml --run-id "$RUN" \
      --checkpoint /c1/runs/r2e/checkpoints/step_000000004488 --tag lotto > "$C/logs/validate_$X.log" 2>&1 \
    || { eco "$X: FALLITO (vedi c1/logs/validate_$X.log)"; tail -20 "$C/logs/validate_$X.log"; exit 1; }
  DUMP=$(ls -t $C/runs/$RUN/logs/val_lotto_*.json 2>/dev/null | head -1)
  [ -n "$DUMP" ] || { eco "$X: FALLITO (nessun dump)"; exit 1; }
  cp -n "$DUMP" "$C/out/lotto_$X/c1_direct.json"
  if [ "$X" = locfumo ]; then
    python3 -c "
import json
r = json.load(open('$C/out/lotto_locfumo/c1_direct.json'))['records']
assert len(r) == 2 and all(x['category'] == 'localize' and 'pred' in x for x in r), 'forma'
print('fumo: forma del dump OK;', [x['pred'][:90] for x in r])
" || { eco "FUMO NON SUPERATO"; exit 1; }
  fi
  ( cd "$C/out/lotto_$X" && sha256sum c1_direct.json REGISTRO_LETTURE.jsonl > SHA256SUMS.txt && touch COMPLETO )
  eco "$X: OK"
done
eco "LOCALIZE A UN CANALE COMPLETO"
