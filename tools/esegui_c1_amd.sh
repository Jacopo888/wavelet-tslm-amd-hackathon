#!/usr/bin/env bash
# Zero-shot di C1 DIRECT su MetroPT-3 sulla MI300X (DISEGNO-ZEROSHOT-METROPT3.congelato-6c61e315.md, §9).
# Config per MI300X derivato da metropt3_c1.toml (solo percorsi e sezione runtime), poi per ogni insieme di INSIEMI
# (fumo, p15, a7): validate.py dalla porta guardata, controllo meccanico del fumo, dump e sha.  La LETTURA non si fa qui.
set -Euo pipefail
B=/root/hack
C=$B/c1
DOC=DISEGNO-ZEROSHOT-METROPT3.congelato-6c61e315.md
eco() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
mkdir -p $C/docs $C/datasets/metropt3 $C/out
cp -n $B/tools/$DOC $C/docs/ && chmod 444 $C/docs/$DOC
for X in p15 a7 fumo; do cp -n $B/dati/metropt3_$X.parquet $C/datasets/metropt3/; done
v=$(sha256sum $C/runs/r2e/checkpoints/step_000000004488/model.safetensors | cut -c1-16)
[ "$v" = c38547ae07e75072 ] || { eco "RIFIUTO: checkpoint $v"; exit 72; }
declare -A ATTESO=([src/wavelet_rope/model.py]=e550d6df [src/wavelet_rope/testa_loc.py]=59115a71 [training/validate.py]=03c16485)
for f in "${!ATTESO[@]}"; do
  a=$(sha256sum $C/code_metropt3/$f | cut -c1-8); [ "$a" = "${ATTESO[$f]}" ] || { eco "RIFIUTO: $f $a"; exit 75; }
done
docker exec -i -w /c1/code_metropt3 wrope python - <<'EOF' || { eco "RIFIUTO: config MI300X non scritto"; exit 75; }
from pathlib import Path
import torch
src = Path("configs/metropt3_c1.toml").read_text(encoding="utf-8")
dst = Path("configs/metropt3_c1_mi300x.toml")
sost = {
    'run_root = "/work/u10970284/hackathon-amd-act3/runs"': 'run_root = "/c1/runs"',
    'root = "/work/u10970284/wavelet-tslm-rope-ablation/datasets/va1_layout"': 'root = "/c1/datasets/va1_layout"',
    'authoritative_manifest = "/work/u10970284/wavelet-tslm-rope-ablation/integrity/artifacts/va1/RUN_MANIFEST.json"':
        'authoritative_manifest = "/c1/integrity/artifacts/va1/RUN_MANIFEST.json"',
    'root = "/work/u10970284/wavelet-tslm-rope-ablation/hf/hub/models--Qwen--Qwen3.5-4B/snapshots/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"':
        'root = "/scratch/hf/hub/models--Qwen--Qwen3.5-4B/snapshots/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"',
    'verification_manifest = "/work/u10970284/wavelet-tslm-rope-ablation/hf/qwen35_4b_851bf6e806ef_VERIFIED.json"':
        'verification_manifest = "/scratch/hf/qwen35_4b_851bf6e806ef_VERIFIED.json"',
    'gpu_family = "L4"': 'gpu_family = "MI300X"',
    'platform = "cuda"': 'platform = "rocm"',
    'attention_backend = "EFFICIENT_ATTENTION"': 'attention_backend = "FLEX_PAD512"',
    'attention_qk_pad_to = 0': 'attention_qk_pad_to = 512',
}
for a, b in sost.items():
    assert src.count(a) == 1, a
    src = src.replace(a, b)
righe = src.splitlines()
for i, r in enumerate(righe):
    if r.startswith("torch_build = "):
        righe[i] = f'torch_build = "{torch.__version__}"'
    if r.startswith("accelerator_runtime = "):
        righe[i] = f'accelerator_runtime = "ROCm / HIP {torch.version.hip} / {torch.cuda.get_device_name(0) or "AMD Instinct MI300X VF"}"'
assert "/work/" not in "\n".join(righe)
if not dst.exists():
    dst.write_text("\n".join(righe) + "\n", encoding="utf-8")
print("config MI300X pronto")
EOF
for X in ${INSIEMI:-fumo p15 a7}; do
  case "$X" in fumo|p15|a7) ;; *) eco "RIFIUTO: $X"; exit 2 ;; esac
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
    -e WR_SPLIT_CONFERMA="metropt3_$X" -e "WR_METROPT3_${XX}_PARQUET=/c1/datasets/metropt3/metropt3_$X.parquet" \
    -e WR_DOCUMENTO_CONGELATO=/c1/docs/$DOC -e WR_SHA_DOCUMENTO=6c61e315ed4fb3f5 \
    -e WR_REGISTRO_LETTURE="$D/REGISTRO_LETTURE.jsonl" \
    wrope python training/validate.py --config configs/metropt3_c1_mi300x.toml --run-id "$RUN" \
      --checkpoint /c1/runs/r2e/checkpoints/step_000000004488 --tag lotto > "$C/logs/validate_$X.log" 2>&1 \
    || { eco "$X: FALLITO (vedi c1/logs/validate_$X.log)"; tail -20 "$C/logs/validate_$X.log"; exit 1; }
  DUMP=$(ls -t $C/runs/$RUN/logs/val_lotto_*.json 2>/dev/null | head -1)
  [ -n "$DUMP" ] || { eco "$X: FALLITO (nessun dump)"; exit 1; }
  cp -n "$DUMP" "$C/out/lotto_$X/c1_direct.json"
  if [ "$X" = fumo ]; then
    python3 -c "
import json
r = json.load(open('$C/out/lotto_fumo/c1_direct.json'))['records']
assert len(r) == 2 and all(x['category'] == 'localize_all_channels' and 'pred' in x for x in r), 'forma'
print('fumo: forma del dump OK;', [x['pred'][:90] for x in r])
" || { eco "FUMO NON SUPERATO"; exit 1; }
  fi
  ( cd "$C/out/lotto_$X" && sha256sum c1_direct.json REGISTRO_LETTURE.jsonl > SHA256SUMS.txt && touch COMPLETO )
  eco "$X: OK"
done
eco "C1 COMPLETO"
