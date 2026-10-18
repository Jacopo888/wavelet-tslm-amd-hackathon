#!/usr/bin/env bash
# Agente TimeRLM su MetroPT-3 sulla MI300X (DISEGNO-AGENTE-TIMERLM-METROPT3.congelato-41abe9af.md, §7).
# vLLM nel container ROCm, poi per ogni insieme (fumo, p15, a7): rollout col protocollo v1 non modificato, controllo
# meccanico del fumo, conversione nel formato del lettore, sha.  La LETTURA non si fa qui.
set -Euo pipefail
B=/root/hack
T=$B/timerlm
PY=$B/venv_agente/bin/python
NOME=timerlm-rl-qwen35-4b
PORTA=18000   # la 8000 dell'host e' gia' pubblicata dal container rocm dell'immagine
eco() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
[ "$(git -C "$T" rev-parse HEAD)" = 31fcd847b7cb37a1f1e6859b1dca7973ed0eae74 ] || { eco "RIFIUTO: TimeRLM non al commit"; exit 75; }
[ -z "$(git -C "$T" status --porcelain --untracked-files=no)" ] || { eco "RIFIUTO: TimeRLM modificato"; exit 75; }
( cd "$B/hf/TimeRLM-RL-Qwen-3.5-4B" && sha256sum --quiet -c "$B/dati/TimeRLM-RL-Qwen-3.5-4B.SHA256SUMS" ) || { eco "RIFIUTO: pesi"; exit 72; }
if ! docker ps --format '{{.Names}}' | grep -qx vllm-nico; then
  docker rm -f vllm-nico >/dev/null 2>&1 || true
  docker run -d --name vllm-nico --device=/dev/kfd --device=/dev/dri --group-add video --ipc=host \
    --security-opt seccomp=unconfined -p 127.0.0.1:$PORTA:8000 -v "$B/hf:/models:ro" \
    vllm/vllm-openai-rocm:v0.27.1 /models/TimeRLM-RL-Qwen-3.5-4B --served-model-name "$NOME" --host 0.0.0.0 --port 8000 \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder --max-model-len 65536 --gpu-memory-utilization 0.5 >/dev/null     || { eco "RIFIUTO: docker run di vLLM fallito"; exit 73; }
  eco "vLLM avviato"
fi
for t in $(seq 1 120); do curl -sf "http://127.0.0.1:$PORTA/health" >/dev/null && break; sleep 10; done
curl -sf "http://127.0.0.1:$PORTA/health" >/dev/null || { eco "RIFIUTO: vLLM non pronto dopo 20 minuti"; docker logs --tail 40 vllm-nico; exit 73; }
eco "vLLM pronto: $(curl -s http://127.0.0.1:$PORTA/v1/models | head -c 200)"
export RLM_PYTHON=$PY
cd "$T"
for X in ${INSIEMI:-fumo p15 a7}; do
  case "$X" in fumo) N=2; LIM="--limit 1" ;; p15|a7) N=23; LIM="" ;; *) eco "RIFIUTO: $X"; exit 2 ;; esac
  D="$B/out/agente_$X"
  if [ -e "$D/COMPLETO" ]; then eco "$X: gia' completo, salto"; continue; fi
  mkdir -p "$D"
  eco "$X: avvio dei rollout"
  "$PY" scripts/eval_v1_rlm.py --dataset anomalyxl --repo-or-path "$B/dati/agente/$X" --eval-size "$N" \
    --base-url "http://127.0.0.1:$PORTA/v1" --api-key EMPTY --model "$NOME" --max-turns 15 --concurrency 4 \
    --out "$D/agente.jsonl" $LIM || { eco "$X: FALLITO (rollout)"; exit 1; }
  if [ "$X" = fumo ]; then
    "$PY" -I -c "
import json
r = [json.loads(x) for x in open('$D/agente.jsonl') if x.strip()]
assert len(r) == 1 and r[0]['num_turns'] and not r[0]['error'], r
print('fumo: rollout chiuso in', r[0]['num_turns'], 'turni,', r[0]['seconds'], 's')
" || { eco "FUMO NON SUPERATO: gli insiemi veri non partono"; exit 1; }
    touch "$D/COMPLETO"; eco "fumo superato"
  else
    "$PY" "$B/tools/converti_agente.py" --jsonl "$D/agente.jsonl" --ordine "$B/dati/ORDINE.json" --insieme "$X" \
      --timerlm "$T" --out "$D/agente_direct.json" || { eco "$X: FALLITO (conversione)"; exit 1; }
    ( cd "$D" && sha256sum agente.jsonl agente_direct.json > SHA256SUMS.txt && touch COMPLETO )
    eco "$X: OK"
  fi
done
eco "AGENTE COMPLETO"
