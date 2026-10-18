"""Qwen3-TTS on lumen-web-gpu. The host uploads this file and a job list."""
import json
import sys
from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


def main():
    jobs = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    model_dir = sys.argv[2]
    model = Qwen3TTSModel.from_pretrained(
        model_dir,
        device_map='cuda:0',
        dtype=torch.bfloat16,
    )
    for job in jobs:
        wavs, sample_rate = model.generate_custom_voice(
            text=job['text'],
            language=job['language'],
            speaker=job['speaker'],
        )
        destination = Path(job['out'])
        sf.write(destination, wavs[0], sample_rate)
        if not destination.is_file() or destination.stat().st_size < 1000:
            raise SystemExit('empty speech')
    print('SPEECH_DONE', flush=True)


if __name__ == '__main__':
    main()
