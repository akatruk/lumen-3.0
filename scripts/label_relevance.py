#!/usr/bin/env python3
"""Record one catalog judgment. Does not write user ratings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'media' / 'library' / 'relevance' / 'intents_v2.json'
GRADES = ('highly_relevant', 'relevant', 'weakly_relevant', 'irrelevant')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--intent', required=True)
    parser.add_argument('--asset', required=True)
    parser.add_argument('--grade', required=True, choices=GRADES)
    args = parser.parse_args()
    payload = json.loads(DATASET.read_text(encoding='utf-8'))
    match = next((item for item in payload['intents'] if item['id'] == args.intent), None)
    if match is None:
        raise SystemExit(f'unknown intent {args.intent}')
    match.setdefault('judgments', {})[args.asset] = args.grade
    DATASET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{args.intent} {args.asset} {args.grade}')


if __name__ == '__main__':
    main()
