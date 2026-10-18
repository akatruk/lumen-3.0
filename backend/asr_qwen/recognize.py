"""One-shot Qwen3-ASR. Runs in the isolated interpreter, never in the web or worker."""

from __future__ import annotations

import argparse
import json
import os
import time

REVISION = "7278e1e70fe206f11671096ffdd38061171dd6e5"
REPO = "Qwen/Qwen3-ASR-1.7B"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--language", default="")
    args = parser.parse_args()
    os.environ.setdefault("HF_HOME", "/mnt/volume_nyc1_1791446889637/qwen3-asr/hf")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    root = os.environ.get("QWEN_ASR_ROOT", "/mnt/volume_nyc1_1791446889637/qwen3-asr")
    snapshot = os.path.join(
        os.environ["HF_HOME"],
        "hub",
        "models--Qwen--Qwen3-ASR-1.7B",
        "snapshots",
        REVISION,
    )
    if not os.path.isdir(snapshot):
        raise SystemExit(f"missing pinned snapshot {snapshot}")
    import torch
    from qwen_asr import Qwen3ASRModel

    started = time.time()
    model = Qwen3ASRModel.from_pretrained(
        snapshot,
        dtype=torch.bfloat16,
        device_map="cpu",
        max_inference_batch_size=1,
        max_new_tokens=1024,
    )
    loaded = time.time()
    language = args.language.strip() or None
    result = model.transcribe(args.audio, language=language, return_time_stamps=False)
    row = result[0]
    payload = {
        "text": str(getattr(row, "text", "") or "").strip(),
        "language": getattr(row, "language", None),
        "model": REPO,
        "revision": REVISION,
        "loadSeconds": round(loaded - started, 3),
        "inferSeconds": round(time.time() - loaded, 3),
        "root": root,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


if __name__ == "__main__":
    main()
