"""Provision the pinned official catalogue: python -m scripts.provision_soundtracks."""
import hashlib
import json
import urllib.request
from backend.config import settings
from backend.soundtracks import curated
from backend.music import probe_audio


def main():
    folder = settings.data_dir / 'soundtracks'
    folder.mkdir(parents=True, exist_ok=True)
    for track in curated():
        target = folder / (track['id'] + '.mp3')
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == track['sha256']:
            print('Verified', track['id'])
            continue
        temporary = target.with_suffix('.part')
        try:
            with urllib.request.urlopen(track['download_url'], timeout=90) as response:
                data = response.read(40 * 1024 * 1024 + 1)
            if len(data) > 40 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != track['sha256']:
                raise ValueError('Source file changed; review catalogue before updating')
            temporary.write_bytes(data)
            meta = probe_audio(temporary)
            if abs(meta['duration'] - track['duration']) > .1:
                raise ValueError('Duration mismatch')
            temporary.replace(target)
            print('Provisioned', track['id'])
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
