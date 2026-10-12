#!/usr/bin/env python3
"""Control the local Ollama LLM on lumen-hypit-4090 (load / unload / health / chat).

Uses the same RunPod account + SSH channel as Hypit. Does not create pods.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["health", "load", "unload", "chat"])
    parser.add_argument("--model", default=os.environ.get("RUNPOD_LLM_MODEL", "qwen2.5:7b-instruct"))
    parser.add_argument("--prompt", default="Reply with OK")
    args = parser.parse_args()
    os.environ.setdefault("RUNPOD_LLM_MODEL", args.model)

    from backend import runpod_llm

    if args.cmd == "health":
        print(json.dumps(runpod_llm.health_check(ensure_model=True), indent=2))
        return
    if args.cmd == "load":
        runpod_llm.load_model(args.model)
        print(json.dumps({"ok": True, "loaded": args.model}))
        return
    if args.cmd == "unload":
        runpod_llm.unload_model(args.model)
        print(json.dumps({"ok": True, "unloaded": args.model}))
        return
    data = runpod_llm.chat_completions(
        messages=[{"role": "user", "content": args.prompt}],
        model=args.model,
        max_tokens=64,
    )
    print(runpod_llm.extract_message_content(data))


if __name__ == "__main__":
    main()
