#!/usr/bin/env bash
# Preparazione della MI300X (AMD Developer Cloud) per l'agente TimeRLM su MetroPT-3.  Gira sulla macchina, in /root/hack.
#  1. TimeRLM ufficiale al commit 31fcd847 e venv_agente (rlm-harness, mcp<1.24, pandas<3, datasets, huggingface-hub);
#  2. pesi di nz00shuuuu/TimeRLM-RL-Qwen-3.5-4B alla revisione pinnata, controllati contro il manifest del cluster;
#  3. ordine delle righe ricalcolato col loro caricatore e confrontato con ORDINE.json.
set -Eeuo pipefail
B=/root/hack
cd "$B"
echo "[$(date -u +%FT%TZ)] avvio"
[ -d timerlm ] || git clone -q https://github.com/OpenTSLM/TimeRLM timerlm
git -C timerlm checkout -q 31fcd847b7cb37a1f1e6859b1dca7973ed0eae74
[ -z "$(git -C timerlm status --porcelain --untracked-files=no)" ]
if [ ! -x venv_agente/bin/python ]; then
  python3 -m venv venv_agente
  venv_agente/bin/pip install -q --upgrade pip
  venv_agente/bin/pip install -q -e timerlm/rlm-harness "mcp<1.24" "pandas>=2,<3" "datasets>=2.19" "huggingface-hub>=0.23" pyarrow matplotlib
fi
venv_agente/bin/python -c "import rlm, openai, pandas, scipy; print('venv_agente ok', pandas.__version__)"
REV=$(python3 -c "import json; print(json.load(open('dati/TimeRLM-RL-Qwen-3.5-4B.revisione.json'))['revisione'])")
venv_agente/bin/python -c "
from huggingface_hub import snapshot_download
print(snapshot_download('nz00shuuuu/TimeRLM-RL-Qwen-3.5-4B', revision='$REV', local_dir='$B/hf/TimeRLM-RL-Qwen-3.5-4B'))"
( cd hf/TimeRLM-RL-Qwen-3.5-4B && sha256sum --quiet -c "$B/dati/TimeRLM-RL-Qwen-3.5-4B.SHA256SUMS" ) && echo "pesi: sha256 identici al manifest del cluster"
for X in p15 a7 fumo; do mkdir -p "dati/agente/$X"; ln -sf "../../metropt3_$X.parquet" "dati/agente/$X/data.parquet"; done
cd timerlm && "$B/venv_agente/bin/python" - <<EOF
import sys, json
sys.path.insert(0, "environments/timeseries_qa")
from ts_datasets import DATASETS
atteso = json.load(open("$B/dati/ORDINE.json"))
for X, n in (("p15", 23), ("a7", 23), ("fumo", 2)):
    fr = DATASETS["anomalyxl"](repo_or_path="$B/dati/agente/" + X, eval_size=n, mode="rlm").load_split("eval")
    assert list(fr["id"]) == atteso[X]["ordine_example_id"], X
print("ordine delle righe identico a ORDINE.json")
EOF
echo "[$(date -u +%FT%TZ)] fine"
