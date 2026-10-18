"""One-shot Qwen3 forced aligner. Separate process from recognition."""

from __future__ import annotations

import argparse
import json
import os
import time

REVISION = "c7cbf2048c462b0d63a45797104fc9db3ad62b7"
REPO = "Qwen/Qwen3-ForcedAligner-0.6B"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    os.environ.setdefault("HF_HOME", "/mnt/volume_nyc1_1791446889637/qwen3-asr/hf")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    snapshot = os.path.join(
        os.environ["HF_HOME"],
        "hub",
        "models--Qwen--Qwen3-ForcedAligner-0.6B",
        "snapshots",
        REVISION,
    )
    if not os.path.isdir(snapshot):
        raise SystemExit(f"missing pinned snapshot {snapshot}")
    import torch
    from qwen_asr import Qwen3ForcedAligner

    started = time.time()
    model = Qwen3ForcedAligner.from_pretrained(
        snapshot,
        dtype=torch.bfloat16,
        device_map="cpu",
    )
    loaded = time.time()
    aligned = model.align(args.audio, args.text, language=args.language)
    tokens = []
    for item in aligned[0].items:
        tokens.append({
            "text": str(item.text),
            "start": round(float(item.start_time), 3),
            "end": round(float(item.end_time), 3),
        })
    payload = {
        "model": REPO,
        "revision": REVISION,
        "loadSeconds": round(loaded - started, 3),
        "inferSeconds": round(time.time() - loaded, 3),
        "tokens": tokens,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


if __name__ == "__main__":
    main()
