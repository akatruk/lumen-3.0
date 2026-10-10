"""Generate stills with the lumen-owned SDXL checkpoint.

Uses the container PyTorch. Weights live under the lumen directory on the
volume. This script does not read another project's model tree.
"""
import argparse
import json
import time
from pathlib import Path

import torch
from diffusers import StableDiffusionXLPipeline


def load_pipeline(checkpoint):
    pipe = StableDiffusionXLPipeline.from_single_file(
        checkpoint,
        torch_dtype=torch.float16,
        use_safetensors=True,
    )
    pipe.to("cuda")
    return pipe


def render(pipe, plan, output):
    generator = torch.Generator(device="cuda").manual_seed(int(plan["seed"]))
    started = time.time()
    image = pipe(
        prompt=plan["prompt"],
        negative_prompt=plan["negative_prompt"],
        width=int(plan["width"]),
        height=int(plan["height"]),
        num_inference_steps=int(plan["num_inference_steps"]),
        guidance_scale=float(plan["guidance_scale"]),
        generator=generator,
    ).images[0]
    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest)
    meta = dict(plan)
    meta["seconds"] = round(time.time() - started, 2)
    meta["output"] = str(dest)
    meta["provider"] = "runpod"
    dest.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    return meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--plan")
    parser.add_argument("--output")
    parser.add_argument("--batch")
    parser.add_argument("--outdir")
    args = parser.parse_args()
    pipe = load_pipeline(args.checkpoint)
    if args.batch:
        outdir = Path(args.outdir or "/workspace/lumen-media-v1/out")
        for line in Path(args.batch).read_text().splitlines():
            if not line.strip():
                continue
            plan = json.loads(line)
            dest = outdir / (plan["id"] + ".png")
            if dest.is_file() and dest.stat().st_size > 0:
                print("SKIP", plan["id"], flush=True)
                continue
            meta = render(pipe, plan, dest)
            print("DONE", plan["id"], meta["seconds"], flush=True)
        print("BATCH_DONE", flush=True)
        return
    if not args.plan or not args.output:
        raise SystemExit("plan and output are required")
    plan = json.loads(Path(args.plan).read_text())
    meta = render(pipe, plan, args.output)
    print("DONE", meta["seconds"], args.output, flush=True)


if __name__ == "__main__":
    main()
