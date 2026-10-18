"""CLI: audit (default dry-run), contact sheets, quarantine apply/restore."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import run_audit, write_inventory_md
from .contact_sheets import build_cleanup_sheets
from .quarantine import apply_review, load_manifest, restore_ids, save_manifest


def _default_library() -> Path:
    here = Path(__file__).resolve()
    local = here.parents[2] / "media" / "library" / "out"
    if local.is_dir() and (local / "manifest.json").is_file():
        return local
    return Path("/mnt/volume_nyc1_1791446889637/app-library")


def cmd_audit(args: argparse.Namespace) -> int:
    library = Path(args.library)
    review = run_audit(
        library,
        manifest_path=Path(args.manifest) if args.manifest else None,
        phash_threshold=args.phash_threshold,
        limit=args.limit,
    )
    reports = Path(args.reports)
    reports.mkdir(parents=True, exist_ok=True)
    review_path = reports / "media-cleanup-review.json"
    # Slim file for git: drop per-asset blob if --slim
    payload = review
    if args.slim:
        payload = {k: v for k, v in review.items() if k != "assets"}
        payload["assets_sample"] = (review.get("assets") or [])[:20]
        payload["assets_count"] = len(review.get("assets") or [])
    review_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Full review next to library for apply tooling
    full_path = library / "contact-sheets" / "cleanup" / "media-cleanup-review.full.json"
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    inv_md = reports / "MEDIA_LIBRARY_INVENTORY.md"
    write_inventory_md(review, inv_md)

    sheets = {}
    if not args.skip_sheets:
        sheets = build_cleanup_sheets(library, review)

    print(json.dumps({
        "inventory_assets": review["inventory"]["manifest_assets"],
        "quality_counts": review["quality_counts"],
        "exact_dupe_groups": len(review["exact_duplicate_groups"]),
        "perceptual_dupe_groups": len(review["perceptual_duplicate_groups"]),
        "recommended_quarantine": review["recommended_quarantine_count"],
        "review": str(review_path),
        "full_review": str(full_path),
        "inventory_md": str(inv_md),
        "sheets": sheets,
        "dry_run": True,
    }, indent=2))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    result = apply_review(
        Path(args.manifest),
        review,
        dry_run=not args.commit,
        library=Path(args.library) if args.library else None,
        move_files=args.move_files,
    )
    print(json.dumps(result, indent=2))
    if args.commit and not result.get("dry_run"):
        print("Applied status=quarantined to", len(result.get("changed") or []), "assets", file=sys.stderr)
    else:
        print("DRY RUN — no manifest write", file=sys.stderr)
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    data = load_manifest(manifest_path)
    ids = args.ids or []
    if args.from_review:
        review = json.loads(Path(args.from_review).read_text(encoding="utf-8"))
        ids = [r["id"] if isinstance(r, dict) else r for r in (review.get("recommended_quarantine") or [])]
    result = restore_ids(
        data,
        ids,
        reason="restore_v1",
        library=Path(args.library) if args.library else None,
        move_files=args.move_files and args.commit,
    )
    result["dry_run"] = not args.commit
    if args.commit:
        bak = manifest_path.with_suffix(manifest_path.suffix + ".bak-restore")
        bak.write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")
        save_manifest(manifest_path, data)
        result["backup"] = str(bak)
    else:
        result["would_change"] = result["changed"]
        result["changed"] = []
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="media_cleanup_v1", description="Media library audit & smart cleanup V1")
    sub = p.add_subparsers(dest="cmd", required=True)
    lib_default = str(_default_library())

    a = sub.add_parser("audit", help="Inventory + classify + duplicates (dry-run)")
    a.add_argument("--library", default=lib_default)
    a.add_argument("--manifest", default=None)
    a.add_argument("--reports", default="reports")
    a.add_argument("--phash-threshold", type=int, default=10)
    a.add_argument("--limit", type=int, default=None)
    a.add_argument("--skip-sheets", action="store_true")
    a.add_argument("--slim", action="store_true", help="Omit full assets[] from git review JSON")
    a.set_defaults(func=cmd_audit)

    ap = sub.add_parser("apply-quarantine", help="Apply review quarantine (default dry-run)")
    ap.add_argument("--library", default=lib_default)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--review", required=True)
    ap.add_argument("--commit", action="store_true", help="Actually write status into manifest")
    ap.add_argument("--move-files", action="store_true", help="Also move files (still refuses unstable)")
    ap.set_defaults(func=cmd_apply)

    r = sub.add_parser("restore", help="Restore assets to active (default dry-run)")
    r.add_argument("--library", default=lib_default)
    r.add_argument("--manifest", required=True)
    r.add_argument("--ids", nargs="*", default=[])
    r.add_argument("--from-review", default=None)
    r.add_argument("--commit", action="store_true")
    r.add_argument("--move-files", action="store_true")
    r.set_defaults(func=cmd_restore)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
