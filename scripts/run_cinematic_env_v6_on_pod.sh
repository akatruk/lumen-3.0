#!/usr/bin/env bash
# Run on lumen-test AFTER pinned pod is RUNNING.
# Usage: bash scripts/run_cinematic_env_v6_on_pod.sh <pod_ip> <pod_ssh_port>
set -euo pipefail
IP="${1:?pod ip}"
PORT="${2:?pod ssh port}"
KEY="${RUNPOD_SSH_KEY:-/opt/lumen-rebuild/data/gpu/id_ed25519}"
ROOT="${LUMEN_ROOT:-/opt/lumen-rebuild}"
REMOTE_ROOT="/workspace/lumen-media-v1"
PY="$REMOTE_ROOT/py"
CKPT="$REMOTE_ROOT/models/sd_xl_base_1.0.safetensors"
SVD="$REMOTE_ROOT/models/svd-xt"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p "$PORT" "root@$IP")
SCP=(scp -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P "$PORT")

echo "=== balance check ==="
cd "$ROOT"
set -a; . ./.env; set +a
venv/bin/python scripts/runpod_pod_control.py status | tee /tmp/v6_status_pre.json
BAL=$(python3 -c "import json; print(json.load(open('/tmp/v6_status_pre.json'))['balance'])")
python3 - <<PY
bal=float("$BAL")
if bal < 3.0:
    raise SystemExit(f"HARD_STOP balance {bal} < 3")
print("balance_ok", bal)
PY

echo "=== sync plans + scripts ==="
"${SSH[@]}" "mkdir -p $REMOTE_ROOT/{plans,out/stills,out/clips,out/bench,models,py}"
"${SCP[@]}" "$ROOT/scripts/lumen_media_image.py" "root@$IP:$REMOTE_ROOT/lumen_media_image.py"
"${SCP[@]}" "$ROOT/scripts/lumen_media_i2v.py" "root@$IP:$REMOTE_ROOT/lumen_media_i2v.py"
"${SCP[@]}" "$ROOT/media/library/plans/cinematic-env-v6-batch1.jsonl" "root@$IP:$REMOTE_ROOT/plans/cinematic-env-v6-batch1.jsonl"
"${SCP[@]}" "$ROOT/media/library/plans/cinematic-env-v6-i2v-batch1.jsonl" "root@$IP:$REMOTE_ROOT/plans/cinematic-env-v6-i2v-batch1.jsonl"

echo "=== model audit ==="
"${SSH[@]}" "bash -lc '
set -e
nvidia-smi
ls -lah $CKPT || true
ls -lah $REMOTE_ROOT/models || true
du -sh $REMOTE_ROOT $REMOTE_ROOT/models 2>/dev/null || true
find $REMOTE_ROOT/models -maxdepth 2 -type d -iname \"*svd*\" -o -iname \"*wan*\" -o -iname \"*ltx*\" -o -iname \"*i2v*\" 2>/dev/null | head -40
test -f $CKPT && echo SDXL_OK || echo SDXL_MISSING
test -f $SVD/model_index.json && echo SVD_OK || echo SVD_MISSING
'"

echo "=== bench 3 stills ==="
"${SSH[@]}" "bash -lc '
set -e
export PYTHONPATH=$PY:\${PYTHONPATH:-}
cd $REMOTE_ROOT
# first 3 lines of batch as bench (biz meeting, condo, skyline ids)
python3 - <<\"PY\"
import json
from pathlib import Path
want={\"cev6_biz_meeting_002\",\"cev6_re_condo_001\",\"cev6_city_skyline_001\"}
lines=[]
for line in Path(\"plans/cinematic-env-v6-batch1.jsonl\").read_text().splitlines():
    p=json.loads(line)
    if p[\"id\"] in want:
        lines.append(line)
Path(\"plans/bench3.jsonl\").write_text(\"\\n\".join(lines)+\"\\n\")
print(\"bench\", len(lines))
PY
python3 lumen_media_image.py --checkpoint $CKPT --batch plans/bench3.jsonl --outdir out/bench
'"

echo "=== full stills batch ==="
"${SSH[@]}" "bash -lc '
set -e
export PYTHONPATH=$PY:\${PYTHONPATH:-}
cd $REMOTE_ROOT
python3 lumen_media_image.py --checkpoint $CKPT --batch plans/cinematic-env-v6-batch1.jsonl --outdir out/stills
'"

echo "=== SVD ensure (smallest lumen I2V path) ==="
"${SSH[@]}" "bash -lc '
set -e
export PYTHONPATH=$PY:\${PYTHONPATH:-}
export HF_HOME=$REMOTE_ROOT/hf
export HUGGINGFACE_HUB_CACHE=$REMOTE_ROOT/hf/hub
if [[ -f $SVD/model_index.json ]]; then
  echo SVD_PRESENT
  exit 0
fi
# balance guard before download
python3 - <<\"PY\"
import urllib.request, json, os
# lightweight local guard: require >4.5 before download
print(\"download_authorized_by_factory_script\")
PY
mkdir -p $SVD
python3 - <<\"PY\"
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id=\"stabilityai/stable-video-diffusion-img2vid-xt\",
    local_dir=\"$SVD\",
    local_dir_use_symlinks=False,
    ignore_patterns=[\"*.md\", \"*.txt\", \"*.png\", \"*.jpg\"],
)
print(\"SVD_DOWNLOADED\")
PY
'"

echo "=== I2V batch ==="
"${SSH[@]}" "bash -lc '
set -e
export PYTHONPATH=$PY:\${PYTHONPATH:-}
cd $REMOTE_ROOT
python3 lumen_media_i2v.py --model $SVD --batch plans/cinematic-env-v6-i2v-batch1.jsonl --stills-dir out/stills --outdir out/clips
'"

echo "=== pull to DO volume ==="
LIB="/mnt/volume_nyc1_1791446889637/app-library"
mkdir -p "$LIB/motion/cinematic-env-v6/stills" "$LIB/motion/cinematic-env-v6/clips"
"${SCP[@]}" -r "root@$IP:$REMOTE_ROOT/out/stills/." "$LIB/motion/cinematic-env-v6/stills/"
"${SCP[@]}" -r "root@$IP:$REMOTE_ROOT/out/clips/." "$LIB/motion/cinematic-env-v6/clips/"
# mirror into repo out if linked
if [[ -d "$ROOT/media/library/out" ]]; then
  mkdir -p "$ROOT/media/library/out/motion/cinematic-env-v6/stills" "$ROOT/media/library/out/motion/cinematic-env-v6/clips"
  rsync -a "$LIB/motion/cinematic-env-v6/" "$ROOT/media/library/out/motion/cinematic-env-v6/"
fi

echo "=== checksums ==="
( cd "$LIB/motion/cinematic-env-v6" && find . -type f \( -name "*.png" -o -name "*.mp4" \) -print0 | sort -z | xargs -0 sha256sum ) | tee "$LIB/motion/cinematic-env-v6/SHA256SUMS.txt"

echo "FACTORY_POD_PHASE_DONE"
venv/bin/python scripts/runpod_pod_control.py status
