#!/usr/bin/env python3
"""Copy the pre-rendered entry.png to $MAKEFUN_OUTPUT_DIR (default /output).

Standard library only; no network. entry.png is produced by render.py and
committed alongside this file, so the output is byte-identical on every run.
"""
import os
import shutil
import sys


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    dst = os.path.join(out_dir, "entry.png")
    try:
        os.makedirs(out_dir, exist_ok=True)
        shutil.copyfile(src, dst)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {dst} ({os.path.getsize(dst)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
