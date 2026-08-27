"""Thin wrapper around the official `kaggle` CLI -- push, pull, or check
status on one of this repo's GPU kernels, then exit. Not an orchestration
or polling system: Austin runs Kaggle himself most of the time, this is
only for the occasional case of triggering it from a terminal here.

Requires `kaggle` (pip install kaggle) and ~/.kaggle/kaggle.json (or the
KAGGLE_USERNAME/KAGGLE_KEY environment variables) already configured --
see https://github.com/Kaggle/kaggle-api#api-credentials. This script does
not provision, validate, or create that credential; it should never be
pasted into a session -- download it directly from your Kaggle account
settings and place it at that path yourself.

Usage:
    python scripts/kaggle_helper.py push   season_aggregate_gpu
    python scripts/kaggle_helper.py pull   season_aggregate_gpu
    python scripts/kaggle_helper.py status season_aggregate_gpu
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

KERNELS_DIR = Path(__file__).parent.parent / "notebooks" / "kaggle"
KNOWN_KERNELS = {"season_aggregate_gpu", "statcast_era_gpu"}


def _kernel_id(kernel_dir: Path) -> str | None:
    import json

    meta_path = kernel_dir / "kernel-metadata.json"
    if not meta_path.is_file():
        return None
    return json.loads(meta_path.read_text()).get("id")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["push", "pull", "status"])
    parser.add_argument("kernel", choices=sorted(KNOWN_KERNELS))
    args = parser.parse_args()

    kernel_dir = KERNELS_DIR / args.kernel
    if not kernel_dir.is_dir():
        print(f"No such kernel folder: {kernel_dir}", file=sys.stderr)
        return 2

    if args.action in ("push", "pull"):
        cmd = ["kaggle", "kernels", args.action, "-p", str(kernel_dir)]
        if args.action == "pull":
            cmd.append("-m")  # also pull metadata, matching the local kernel-metadata.json shape
    else:
        kernel_id = _kernel_id(kernel_dir)
        if not kernel_id or kernel_id.startswith("<"):
            print(
                f"{kernel_dir / 'kernel-metadata.json'} has no real Kaggle kernel id set yet "
                "-- fill in \"id\": \"<your-kaggle-username>/<kernel-slug>\" before checking status.",
                file=sys.stderr,
            )
            return 2
        cmd = ["kaggle", "kernels", "status", kernel_id]

    try:
        return subprocess.run(cmd, check=False).returncode
    except FileNotFoundError:
        print("`kaggle` CLI not found -- pip install kaggle first.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
