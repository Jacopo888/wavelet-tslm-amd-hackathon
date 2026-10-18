#!/usr/bin/env bash
# Preparazione di C1 sulla MI300X (stesso schema del bootstrap di settembre, droplet/bootstrap.sh della linea Rope):
# container `wrope` dall'immagine rocm:latest della macchina, stack del modello vincolato a torch/numpy dell'immagine,
# AnomalyXL e Qwen3.5-4B ai pin verificati per sha, layout del dataset come sul cluster, config per MI300X.
set -Eeuo pipefail
B=/root/hack
C=$B/c1
eco() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
mkdir -p $C/scratch/{hf,cache,tmp,pip,torch,triton,datasets} $C/runs $C/logs
if ! docker inspect wrope >/dev/null 2>&1; then
  docker run -d --name wrope --restart no --device=/dev/kfd --device=/dev/dri --group-add video \
    --ipc=host --shm-size=32g --network host --security-opt seccomp=unconfined \
    -v $C:/c1 -v $C/scratch:/scratch \
    -e HF_HOME=/scratch/hf -e HF_HUB_CACHE=/scratch/hf/hub -e XDG_CACHE_HOME=/scratch/cache -e TMPDIR=/scratch/tmp \
    -e PIP_CACHE_DIR=/scratch/pip -e TORCH_HOME=/scratch/torch -e TRITON_CACHE_DIR=/scratch/triton \
    -e TOKENIZERS_PARALLELISM=false -w /c1 rocm:latest sleep infinity >/dev/null
fi
docker start wrope >/dev/null 2>&1 || true
eco "container wrope pronto"
docker exec wrope bash -lc '
set -e
python - > /c1/logs/pip_constraints.txt <<EOF
import torch, numpy
print(f"torch=={torch.__version__}"); print(f"numpy=={numpy.__version__}")
EOF
pip install -q -c /c1/logs/pip_constraints.txt \
  "transformers @ git+https://github.com/huggingface/transformers@5c1c72b" peft==0.18.1 \
  einops einops-exts datasets pyyaml huggingface-hub safetensors pandas pyarrow scipy psutil pytest
pip install -q --no-deps flash-linear-attention==0.5.2 fla-core==0.5.2
python -c "import transformers, peft, torch; assert torch.cuda.is_available(); print(\"stack\", transformers.__version__, peft.__version__, torch.__version__, torch.version.hip)"
python -c "from fla.ops.gated_delta_rule import chunk_gated_delta_rule; print(\"fla-core 0.5.2 importabile\")"
'
eco "stack installato"
docker exec -w /c1/code_metropt3 wrope python tools/fetch_anomalyxl.py | tail -2
docker exec -w /c1/code_metropt3 wrope python tools/fetch_qwen_snapshot.py | tail -2
# layout del dataset come sul cluster (datasets/va1_layout/LAYOUT.json), con lo sha di ogni file
S=$C/scratch/datasets/anomalyxl_df363a467f855e55aaad414b0bdd58590829df9a/Localize
L=$C/datasets/va1_layout/anomalyXL/datasets
mkdir -p $L/anomalyxl-train/anomalyxl-precise $L/anomalyxl-precise
ln -sf /scratch/datasets/anomalyxl_df363a467f855e55aaad414b0bdd58590829df9a/Localize/train.parquet $L/anomalyxl-train/anomalyxl-precise/train.parquet
ln -sf /scratch/datasets/anomalyxl_df363a467f855e55aaad414b0bdd58590829df9a/Localize/val.parquet $L/anomalyxl-train/anomalyxl-precise/val.parquet
ln -sf /scratch/datasets/anomalyxl_df363a467f855e55aaad414b0bdd58590829df9a/Localize/test.parquet $L/anomalyxl-precise/data.parquet
docker exec wrope bash -lc 'cd /c1/datasets/va1_layout/anomalyXL/datasets && sha256sum anomalyxl-train/anomalyxl-precise/train.parquet anomalyxl-train/anomalyxl-precise/val.parquet anomalyxl-precise/data.parquet' | cut -c1-16,66-
eco "fine"
